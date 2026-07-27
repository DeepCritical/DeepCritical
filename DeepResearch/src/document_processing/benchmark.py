"""Offline, deterministic document-processing benchmark support.

The benchmark deliberately consumes parser observations instead of invoking a parser.
This keeps the corpus reusable across Docling, GROBID, OCR and future adapters while
making network access an explicit concern of a separate acquisition step.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
import unicodedata
from collections import Counter
from collections.abc import Iterable, Mapping, Sequence
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any, cast

from .models import (
    ContentSpan,
    ContentSpanSet,
    DocumentArtifact,
    JatsLocator,
    MemoryMeasurement,
    PdfLocator,
    ProcessingRun,
    ProcessingRunStatus,
    RuntimeAttestation,
    RuntimeAttestationSource,
    configuration_sha256,
)
from .storage import ContentAddressedStore, StorageError

MANIFEST_SCHEMA_VERSION = "1.0"
OBSERVATION_SCHEMA_VERSION = "1.0"
REPORT_SCHEMA_VERSION = "1.0"
BASELINE_MIN_DOCUMENTS = 50
BASELINE_MAX_DOCUMENTS = 75
REQUIRED_CATEGORIES = frozenset(
    {
        "multi-column",
        "scanned",
        "table-heavy",
        "figure-heavy",
        "malformed",
    }
)
OUTCOMES = ("complete", "partial", "quarantined", "failed")
QUALITY_METRICS = (
    "text_fidelity",
    "reading_order",
    "headings",
    "tables",
    "figure_caption_association",
    "references",
    "locator_coverage",
    "determinism",
)
_MEMORY_SCOPED_PARSER_NAMES = frozenset({"docling", "grobid", "ocrmypdf"})
_MEMORY_SCOPE = "heavy_parser_invocations"

_SHA256_RE = re.compile(r"^[0-9a-fA-F]{64}$")
_WORD_RE = re.compile(r"\w+", flags=re.UNICODE)


class BenchmarkError(ValueError):
    """Raised when benchmark inputs are missing, invalid, or incomparable."""


def _mapping(value: Any, context: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise BenchmarkError(f"{context} must be an object")
    return value


def _string(value: Any, context: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise BenchmarkError(f"{context} must be a non-empty string")
    return value.strip()


def _number(value: Any, context: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise BenchmarkError(f"{context} must be a number")
    result = float(value)
    if not math.isfinite(result) or result < 0:
        raise BenchmarkError(f"{context} must be finite and non-negative")
    return result


def _nonnegative_integer(value: Any, context: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise BenchmarkError(f"{context} must be a non-negative integer")
    return value


def _sha256(value: Any, context: str) -> str:
    digest = _string(value, context)
    if not _SHA256_RE.fullmatch(digest):
        raise BenchmarkError(f"{context} must be a 64-character SHA-256 digest")
    return digest.lower()


def _sha256_path(path: Path) -> str:
    digest = hashlib.sha256()
    try:
        with path.open("rb") as stream:
            for block in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(block)
    except OSError as exc:
        raise BenchmarkError(f"cannot read {path}: {exc}") from exc
    return digest.hexdigest()


def _read_json_object(path: Path, context: str) -> dict[str, Any]:
    if not path.is_file():
        raise BenchmarkError(f"{context} does not exist or is not a file: {path}")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise BenchmarkError(f"cannot read {context} {path}: {exc}") from exc
    if not isinstance(payload, dict):
        raise BenchmarkError(f"{context} must contain a JSON object")
    return payload


def _relative_path(root: Path, value: Any, context: str) -> Path:
    relative = Path(_string(value, context))
    if relative.is_absolute():
        raise BenchmarkError(f"{context} must be relative to artifact_root")
    resolved_root = root.resolve()
    resolved = (resolved_root / relative).resolve()
    try:
        resolved.relative_to(resolved_root)
    except ValueError as exc:
        raise BenchmarkError(f"{context} escapes artifact_root: {relative}") from exc
    return resolved


def _artifact_root(manifest: Mapping[str, Any], manifest_path: Path) -> Path:
    root_value = manifest.get("artifact_root", ".")
    relative = Path(_string(root_value, "manifest.artifact_root"))
    if relative.is_absolute():
        raise BenchmarkError("manifest.artifact_root must be relative to the manifest")
    return (manifest_path.parent / relative).resolve()


def _validate_descriptor(descriptor: Any, context: str) -> Mapping[str, Any]:
    item = _mapping(descriptor, context)
    _string(item.get("path"), f"{context}.path")
    _sha256(item.get("sha256"), f"{context}.sha256")
    if "media_type" in item:
        _string(item.get("media_type"), f"{context}.media_type")
    return item


def _verify_descriptor(
    root: Path,
    descriptor: Mapping[str, Any],
    context: str,
) -> Path:
    path = _relative_path(root, descriptor["path"], f"{context}.path")
    if not path.is_file():
        raise BenchmarkError(f"{context} artifact is missing: {path}")
    expected = _sha256(descriptor["sha256"], f"{context}.sha256")
    actual = _sha256_path(path)
    if actual != expected:
        raise BenchmarkError(
            f"{context} SHA-256 mismatch: expected {expected}, got {actual} ({path})"
        )
    return path


def _validate_manifest(
    manifest: Mapping[str, Any],
    manifest_path: Path,
    *,
    enforce_baseline: bool,
    verify_artifacts: bool,
) -> None:
    version = _string(manifest.get("schema_version"), "manifest.schema_version")
    if version != MANIFEST_SCHEMA_VERSION:
        raise BenchmarkError(
            f"unsupported manifest schema_version {version!r}; "
            f"expected {MANIFEST_SCHEMA_VERSION!r}"
        )
    _string(manifest.get("name"), "manifest.name")
    root = _artifact_root(manifest, manifest_path)

    raw_documents = manifest.get("documents")
    if not isinstance(raw_documents, list) or not raw_documents:
        raise BenchmarkError("manifest.documents must be a non-empty array")

    seen_ids: set[str] = set()
    category_coverage: set[str] = set()
    for index, raw_document in enumerate(raw_documents):
        context = f"manifest.documents[{index}]"
        document = _mapping(raw_document, context)
        document_id = _string(document.get("id"), f"{context}.id")
        if document_id in seen_ids:
            raise BenchmarkError(f"duplicate document id in manifest: {document_id}")
        seen_ids.add(document_id)

        pmcid = _string(document.get("pmcid"), f"{context}.pmcid")
        if enforce_baseline and not re.fullmatch(r"PMC\d+", pmcid):
            raise BenchmarkError(
                f"{context}.pmcid must have the form PMC followed by digits"
            )

        categories = document.get("categories")
        if not isinstance(categories, list) or not categories:
            raise BenchmarkError(f"{context}.categories must be a non-empty array")
        parsed_categories = {
            _string(category, f"{context}.categories") for category in categories
        }
        unknown = parsed_categories - REQUIRED_CATEGORIES
        if unknown:
            raise BenchmarkError(
                f"{context}.categories contains unsupported values: {sorted(unknown)}"
            )
        category_coverage.update(parsed_categories)

        reuse = _mapping(document.get("reuse"), f"{context}.reuse")
        _string(reuse.get("license"), f"{context}.reuse.license")
        _string(reuse.get("license_url"), f"{context}.reuse.license_url")
        if reuse.get("reuse_allowed") is not True:
            raise BenchmarkError(f"{context}.reuse.reuse_allowed must be true")
        if not isinstance(reuse.get("verified"), bool):
            raise BenchmarkError(f"{context}.reuse.verified must be a boolean")
        if enforce_baseline and reuse["verified"] is not True:
            raise BenchmarkError(
                f"{context}.reuse.verified must be true for a baseline corpus"
            )

        artifacts = _mapping(document.get("artifacts"), f"{context}.artifacts")
        for kind, expected_media_type in (
            ("jats", {"application/xml", "text/xml", "application/jats+xml"}),
            ("pdf", {"application/pdf"}),
        ):
            artifact_context = f"{context}.artifacts.{kind}"
            descriptor = _validate_descriptor(artifacts.get(kind), artifact_context)
            media_type = _string(
                descriptor.get("media_type"), f"{artifact_context}.media_type"
            )
            if media_type not in expected_media_type:
                raise BenchmarkError(
                    f"{artifact_context}.media_type must be one of "
                    f"{sorted(expected_media_type)}"
                )
            if verify_artifacts:
                _verify_descriptor(root, descriptor, artifact_context)

    document_count = len(raw_documents)
    if enforce_baseline and not (
        BASELINE_MIN_DOCUMENTS <= document_count <= BASELINE_MAX_DOCUMENTS
    ):
        raise BenchmarkError(
            "baseline corpus must contain between "
            f"{BASELINE_MIN_DOCUMENTS} and {BASELINE_MAX_DOCUMENTS} documents; "
            f"found {document_count}"
        )
    if enforce_baseline:
        missing_categories = REQUIRED_CATEGORIES - category_coverage
        if missing_categories:
            raise BenchmarkError(
                "baseline corpus does not cover required categories: "
                f"{sorted(missing_categories)}"
            )

    thresholds = _mapping(manifest.get("thresholds", {}), "manifest.thresholds")
    for metric, raw_threshold in thresholds.items():
        if metric not in QUALITY_METRICS:
            raise BenchmarkError(f"unsupported quality threshold: {metric}")
        threshold = _number(raw_threshold, f"manifest.thresholds.{metric}")
        if threshold > 1:
            raise BenchmarkError(f"manifest.thresholds.{metric} must be at most 1")

    allowed_outcomes = manifest.get(
        "allowed_outcomes", ["complete", "partial", "quarantined"]
    )
    if not isinstance(allowed_outcomes, list) or not allowed_outcomes:
        raise BenchmarkError("manifest.allowed_outcomes must be a non-empty array")
    parsed_outcomes = {
        _string(value, "manifest.allowed_outcomes") for value in allowed_outcomes
    }
    invalid_outcomes = parsed_outcomes - set(OUTCOMES)
    if invalid_outcomes:
        raise BenchmarkError(
            f"manifest.allowed_outcomes contains invalid values: {sorted(invalid_outcomes)}"
        )

    limits = _mapping(
        manifest.get("performance_limits", {}), "manifest.performance_limits"
    )
    supported_limits = {
        "min_documents_per_second",
        "min_characters_per_second",
        "max_peak_memory_bytes",
    }
    unsupported_limits = set(limits) - supported_limits
    if unsupported_limits:
        raise BenchmarkError(
            f"unsupported performance limits: {sorted(unsupported_limits)}"
        )
    for name, value in limits.items():
        _number(value, f"manifest.performance_limits.{name}")

    observation_sets = _mapping(
        manifest.get("observation_sets", {}), "manifest.observation_sets"
    )
    if "reference" in observation_sets:
        _validate_descriptor(
            observation_sets["reference"], "manifest.observation_sets.reference"
        )


def load_manifest(
    path: str | Path,
    *,
    enforce_baseline: bool = False,
    verify_artifacts: bool = True,
) -> dict[str, Any]:
    """Load and validate a benchmark manifest.

    ``enforce_baseline`` is intentionally opt-in. Unit tests and parser development can
    therefore use small paired fixtures while release baselines enforce 50--75 licensed,
    verified PMC records and coverage of every required document category.
    """

    manifest_path = Path(path).expanduser().resolve()
    manifest = _read_json_object(manifest_path, "manifest")
    _validate_manifest(
        manifest,
        manifest_path,
        enforce_baseline=enforce_baseline,
        verify_artifacts=verify_artifacts,
    )
    return manifest


def _docling_collection(
    document: Mapping[str, Any], collection: str
) -> list[dict[str, Any]]:
    values = document.get(collection, [])
    if not isinstance(values, list):
        raise BenchmarkError(f"DoclingDocument.{collection} must be an array")
    result: list[dict[str, Any]] = []
    for index, value in enumerate(values):
        if not isinstance(value, Mapping):
            raise BenchmarkError(
                f"DoclingDocument.{collection}[{index}] must be an object"
            )
        result.append(dict(cast("Mapping[str, Any]", value)))
    return result


def _docling_item_ref(item: Mapping[str, Any], collection: str, index: int) -> str:
    item_ref = item.get("self_ref")
    if isinstance(item_ref, str) and item_ref.strip():
        return item_ref.strip()
    return f"#/{collection}/{index}"


def _docling_item_index(
    document: Mapping[str, Any],
) -> dict[str, tuple[str, dict[str, Any]]]:
    index: dict[str, tuple[str, dict[str, Any]]] = {}
    for collection in (
        "groups",
        "texts",
        "tables",
        "pictures",
        "key_value_items",
        "form_items",
    ):
        for position, item in enumerate(_docling_collection(document, collection)):
            item_ref = _docling_item_ref(item, collection, position)
            if item_ref in index:
                raise BenchmarkError(
                    f"DoclingDocument contains duplicate item reference {item_ref!r}"
                )
            index[item_ref] = (collection, item)
    return index


def _ordered_docling_text_items(
    document: Mapping[str, Any],
    index: Mapping[str, tuple[str, dict[str, Any]]],
) -> list[tuple[str, dict[str, Any]]]:
    ordered: list[tuple[str, dict[str, Any]]] = []
    visited: set[str] = set()
    active: set[str] = set()

    def visit(value: Any) -> None:
        if not isinstance(value, Mapping):
            return
        item_ref = value.get("$ref")
        if isinstance(item_ref, str):
            if item_ref in active:
                raise BenchmarkError(
                    f"DoclingDocument hierarchy contains a cycle at {item_ref!r}"
                )
            if item_ref in visited:
                return
            indexed = index.get(item_ref)
            if indexed is None:
                raise BenchmarkError(
                    f"DoclingDocument hierarchy references missing item {item_ref!r}"
                )
            visited.add(item_ref)
            active.add(item_ref)
            collection, item = indexed
            if collection == "texts":
                ordered.append((item_ref, item))
            children = item.get("children", [])
            if isinstance(children, list):
                for child in children:
                    visit(child)
            active.remove(item_ref)
            return

        children = value.get("children", [])
        if isinstance(children, list):
            for child in children:
                visit(child)

    body = document.get("body")
    if isinstance(body, Mapping):
        visit(body)

    # Docling's body tree is authoritative for hierarchy and reading order. Some
    # valid documents retain furniture or detached caption/reference text outside
    # that tree, so append those items in their parser-native collection order.
    for position, item in enumerate(_docling_collection(document, "texts")):
        item_ref = _docling_item_ref(item, "texts", position)
        if item_ref not in visited:
            ordered.append((item_ref, item))
    return ordered


def _caption_refs(
    value: Any,
    *,
    path: str = "captions",
) -> tuple[list[str], list[dict[str, str]]]:
    refs: list[str] = []
    issues: list[dict[str, str]] = []
    if isinstance(value, str):
        if value.startswith("#/"):
            refs.append(value)
        else:
            issues.append(
                {
                    "path": path,
                    "reason": "malformed_reference",
                    "value_type": "string",
                }
            )
    elif isinstance(value, Mapping):
        item_ref = value.get("$ref")
        if isinstance(item_ref, str) and item_ref.startswith("#/"):
            refs.append(item_ref)
        else:
            issues.append(
                {
                    "path": path,
                    "reason": "malformed_reference",
                    "value_type": "object",
                }
            )
    elif isinstance(value, list):
        for position, item in enumerate(value):
            item_refs, item_issues = _caption_refs(
                item,
                path=f"{path}[{position}]",
            )
            refs.extend(item_refs)
            issues.extend(item_issues)
    elif value is not None:
        issues.append(
            {
                "path": path,
                "reason": "malformed_reference",
                "value_type": type(value).__name__,
            }
        )
    else:
        issues.append(
            {
                "path": path,
                "reason": "malformed_reference",
                "value_type": "null",
            }
        )
    return refs, issues


def _caption_fields(
    item: Mapping[str, Any],
    index: Mapping[str, tuple[str, dict[str, Any]]],
) -> tuple[list[str], str, list[dict[str, str]]]:
    caption_refs, issues = _caption_refs(item.get("captions", []))
    caption_texts: list[str] = []
    for caption_ref in caption_refs:
        indexed = index.get(caption_ref)
        if indexed is None:
            issues.append(
                {
                    "source_id": caption_ref,
                    "reason": "missing_item",
                }
            )
            continue
        collection, caption_item = indexed
        if collection != "texts":
            issues.append(
                {
                    "source_id": caption_ref,
                    "reason": "non_text_item",
                }
            )
            continue
        text = caption_item.get("text")
        if isinstance(text, str) and text.strip():
            caption_texts.append(text.strip())
        else:
            issues.append(
                {
                    "source_id": caption_ref,
                    "reason": "empty_text",
                }
            )
    return caption_refs, "\n".join(caption_texts), issues


def _table_text(table: Mapping[str, Any]) -> str:
    for field in ("text", "markdown", "html"):
        value = table.get(field)
        if isinstance(value, str) and value.strip():
            return value.strip()

    data = table.get("data")
    if not isinstance(data, Mapping):
        return ""
    grid = data.get("grid")
    if isinstance(grid, list):
        rows: list[str] = []
        for row in grid:
            if not isinstance(row, list):
                continue
            cells: list[str] = []
            for cell in row:
                if isinstance(cell, Mapping):
                    text = cell.get("text")
                    cells.append(text.strip() if isinstance(text, str) else "")
                elif isinstance(cell, str):
                    cells.append(cell.strip())
                else:
                    cells.append("")
            rows.append(" | ".join(cells))
        if rows:
            return "\n".join(rows)

    cells = data.get("table_cells")
    if isinstance(cells, list):
        values = [
            str(cell["text"]).strip()
            for cell in cells
            if isinstance(cell, Mapping)
            and isinstance(cell.get("text"), str)
            and str(cell["text"]).strip()
        ]
        return "\n".join(values)
    return ""


def _locator_from_span(span: ContentSpan) -> dict[str, Any]:
    locator = span.source_locator
    if isinstance(locator, PdfLocator):
        bbox = locator.bounding_box
        return {
            "page": locator.page_number,
            "bbox": [bbox.left, bbox.top, bbox.right, bbox.bottom],
        }
    if not isinstance(locator, JatsLocator):
        raise BenchmarkError(
            f"benchmark observations do not support {locator.kind!r} locators"
        )
    result: dict[str, Any] = {}
    if locator.xml_id is not None:
        result["xml_id"] = locator.xml_id
    if locator.xpath is not None:
        result["xpath"] = locator.xpath
    return result


def _read_json_blob(store: ContentAddressedStore, digest: str, context: str) -> Any:
    try:
        return json.loads(store.read_blob(digest))
    except (StorageError, UnicodeError, json.JSONDecodeError) as exc:
        raise BenchmarkError(
            f"cannot read persisted {context} {digest}: {exc}"
        ) from exc


def _content_spans(
    store: ContentAddressedStore,
    run: ProcessingRun,
) -> list[ContentSpan]:
    digest = run.output_sha256("content_spans")
    if digest is None:
        raise BenchmarkError(
            f"processing run {run.run_id!r} has no persisted content_spans output"
        )
    payload = _read_json_blob(store, digest, "content spans")
    try:
        span_set = ContentSpanSet.model_validate(payload)
    except ValueError as exc:
        raise BenchmarkError(
            f"invalid persisted content span set for run {run.run_id!r}: {exc}"
        ) from exc
    if (
        span_set.artifact_id != run.artifact_id
        or span_set.processing_run_id != run.run_id
    ):
        raise BenchmarkError(
            f"persisted content span set does not belong to processing run "
            f"{run.run_id!r}"
        )
    representation = run.output("docling_document")
    if (
        representation is not None
        and span_set.representation_product_id != representation.product_id
    ):
        raise BenchmarkError(
            f"persisted content span set for run {run.run_id!r} targets a "
            "different representation product"
        )
    return list(span_set.spans)


def _content_span_index(
    store: ContentAddressedStore,
    run: ProcessingRun,
) -> dict[str, ContentSpan]:
    selected: dict[str, ContentSpan] = {}
    for span in sorted(
        _content_spans(store, run),
        key=lambda value: (
            value.representation_anchor.node_id,
            value.representation_anchor.char_start,
            value.representation_anchor.char_end,
            value.span_id,
        ),
    ):
        selected.setdefault(span.representation_anchor.node_id, span)
    return selected


def _docling_references(
    ordered_texts: Sequence[tuple[str, Mapping[str, Any]]],
) -> list[dict[str, Any]]:
    references: list[dict[str, Any]] = []
    for item_ref, item in ordered_texts:
        label = item.get("label")
        text = item.get("text")
        if (
            isinstance(label, str)
            and label.casefold().replace("-", "_") == "reference"
            and isinstance(text, str)
            and text.strip()
        ):
            references.append({"source_id": item_ref, "text": text.strip()})
    return references


def _derivation_runs_to_root(
    store: ContentAddressedStore,
    artifact_id: str,
    root_artifact_id: str,
    pipeline_run_id: str | None,
    repetition_group_id: str | None,
) -> tuple[ProcessingRun, ...]:
    derivation_runs: list[ProcessingRun] = []
    visited: set[str] = set()
    current_id = artifact_id
    while current_id != root_artifact_id:
        if current_id in visited:
            raise BenchmarkError(f"artifact lineage contains a cycle at {current_id!r}")
        visited.add(current_id)
        artifact = store.get_artifact(current_id)
        parent_id = artifact.parent_artifact_id
        if parent_id is None:
            raise BenchmarkError(
                f"artifact {artifact_id!r} is not derived from benchmark artifact "
                f"{root_artifact_id!r}"
            )
        workflow_creators = [
            run
            for run in store.list_processing_runs(artifact_id=parent_id)
            if run.pipeline_run_id == pipeline_run_id
            and run.repetition_group_id == repetition_group_id
            and run.status
            in {ProcessingRunStatus.COMPLETE, ProcessingRunStatus.PARTIAL}
            and any(
                product.blob_sha256 == artifact.source_sha256 for product in run.outputs
            )
        ]
        creator_run_id = artifact.raw_location.created_by_run_id
        if workflow_creators:
            creator_run = workflow_creators[-1]
        elif creator_run_id is None:
            raise BenchmarkError(
                f"derived artifact {current_id!r} has no creating ProcessingRun"
            )
        else:
            creator_run = store.get_processing_run(creator_run_id)
            if (
                creator_run.pipeline_run_id != pipeline_run_id
                or creator_run.repetition_group_id != repetition_group_id
            ):
                raise BenchmarkError(
                    f"derived artifact {current_id!r} has no creator in workflow "
                    f"{pipeline_run_id!r}"
                )
        if creator_run.artifact_id != parent_id:
            raise BenchmarkError(
                f"derivative creator run {creator_run_id!r} does not belong to "
                f"parent artifact {parent_id!r}"
            )
        if creator_run.status not in {
            ProcessingRunStatus.COMPLETE,
            ProcessingRunStatus.PARTIAL,
        } or not any(
            product.blob_sha256 == artifact.source_sha256
            for product in creator_run.outputs
        ):
            raise BenchmarkError(
                f"derivative creator run {creator_run_id!r} does not own successful "
                f"output {artifact.source_sha256}"
            )
        store.verify_blob(artifact.source_sha256)
        derivation_runs.append(creator_run)
        current_id = parent_id
    derivation_runs.reverse()
    return tuple(derivation_runs)


def _grobid_run_for_alignment(
    store: ContentAddressedStore,
    alignment_run: ProcessingRun,
) -> tuple[ProcessingRun, tuple[ProcessingRun, ...]]:
    tei_digest = alignment_run.configuration.get("grobid_tei_sha256")
    if not isinstance(tei_digest, str) or not _SHA256_RE.fullmatch(tei_digest):
        raise BenchmarkError(
            f"alignment run {alignment_run.run_id!r} does not pin a valid "
            "grobid_tei_sha256"
        )
    matching = [
        run
        for run in store.list_processing_runs(
            component_id="grobid",
        )
        if run.status in {ProcessingRunStatus.COMPLETE, ProcessingRunStatus.PARTIAL}
        and run.output_sha256("grobid_tei") == tei_digest
        and run.pipeline_run_id == alignment_run.pipeline_run_id
        and run.repetition_group_id == alignment_run.repetition_group_id
    ]
    lineage_matches: list[tuple[ProcessingRun, tuple[ProcessingRun, ...]]] = []
    for run in matching:
        try:
            lineage = _derivation_runs_to_root(
                store,
                run.artifact_id,
                alignment_run.artifact_id,
                alignment_run.pipeline_run_id,
                alignment_run.repetition_group_id,
            )
        except BenchmarkError:
            continue
        lineage_matches.append((run, lineage))
    if not lineage_matches:
        raise BenchmarkError(
            f"alignment run {alignment_run.run_id!r} pins GROBID TEI {tei_digest}, "
            "but no successful GROBID ProcessingRun in the source/derivative lineage "
            "owns that output"
        )
    selected, lineage = lineage_matches[-1]
    store.verify_blob(tei_digest)
    return selected, lineage


def _scholarly_references(
    store: ContentAddressedStore,
    artifact_id: str,
    docling_document_sha256: str,
    pipeline_run_id: str | None,
    repetition_group_id: str | None,
) -> tuple[
    list[dict[str, Any]] | None,
    dict[str, Any] | None,
    ProcessingRun | None,
    ProcessingRun | None,
    tuple[ProcessingRun, ...],
]:
    runs = store.list_processing_runs(
        artifact_id=artifact_id,
        component_id="docling-grobid-aligner",
    )
    matching = [
        run
        for run in runs
        if run.status in {ProcessingRunStatus.COMPLETE, ProcessingRunStatus.PARTIAL}
        and run.configuration.get("docling_document_sha256") == docling_document_sha256
        and run.pipeline_run_id == pipeline_run_id
        and run.repetition_group_id == repetition_group_id
        and run.output("alignment_overlay") is not None
    ]
    if not matching:
        return None, None, None, None, ()

    run = matching[-1]
    grobid_run, derivation_runs = _grobid_run_for_alignment(store, run)
    digest = run.require_output("alignment_overlay").blob_sha256
    payload = _read_json_blob(store, digest, "Docling-GROBID alignment overlay")
    if not isinstance(payload, Mapping) or not isinstance(payload.get("records"), list):
        raise BenchmarkError(
            f"persisted alignment overlay for run {run.run_id!r} has no records array"
        )

    references: list[dict[str, Any]] = []
    for position, raw_record in enumerate(payload["records"]):
        if not isinstance(raw_record, Mapping):
            raise BenchmarkError(
                f"alignment overlay record {position} for run {run.run_id!r} "
                "must be an object"
            )
        annotation = raw_record.get("annotation")
        if (
            not isinstance(annotation, Mapping)
            or annotation.get("kind") != "biblStruct"
        ):
            continue
        text = annotation.get("text")
        if not isinstance(text, str) or not text.strip():
            continue
        source_id = annotation.get("xml_id") or annotation.get("annotation_id")
        reference: dict[str, Any] = {"text": text.strip()}
        if isinstance(source_id, str) and source_id.strip():
            reference["source_id"] = source_id.strip()
        references.append(reference)
    return (
        references,
        {
            "processing_run_id": run.run_id,
            "pipeline_run_id": run.pipeline_run_id,
            "repetition_group_id": run.repetition_group_id,
            "component_id": run.component_id,
            "component_version": run.component_version,
            "configuration_sha256": run.configuration_sha256,
            "output_sha256": digest,
            "docling_document_sha256": run.configuration.get("docling_document_sha256"),
            "grobid_tei_sha256": run.configuration.get("grobid_tei_sha256"),
            "grobid_processing_run": {
                "processing_run_id": grobid_run.run_id,
                "artifact_id": grobid_run.artifact_id,
                "component_id": grobid_run.component_id,
                "component_version": grobid_run.component_version,
                "configuration_sha256": grobid_run.configuration_sha256,
                "output_sha256": grobid_run.require_output("grobid_tei").blob_sha256,
            },
            "derivation_processing_runs": [
                {
                    "processing_run_id": derivation_run.run_id,
                    "pipeline_run_id": derivation_run.pipeline_run_id,
                    "repetition_group_id": derivation_run.repetition_group_id,
                    "component_id": derivation_run.component_id,
                    "component_version": derivation_run.component_version,
                    "configuration_sha256": derivation_run.configuration_sha256,
                }
                for derivation_run in derivation_runs
            ],
        },
        run,
        grobid_run,
        derivation_runs,
    )


def _docling_observation_fields(
    store: ContentAddressedStore,
    run: ProcessingRun,
    document: Mapping[str, Any],
) -> tuple[
    dict[str, Any],
    dict[str, Any],
    ProcessingRun | None,
    ProcessingRun | None,
    tuple[ProcessingRun, ...],
]:
    item_index = _docling_item_index(document)
    ordered_texts = _ordered_docling_text_items(document, item_index)
    spans = _content_span_index(store, run)

    textual_items: list[dict[str, Any]] = []
    reading_order: list[str] = []
    headings: list[dict[str, Any]] = []
    for item_ref, item in ordered_texts:
        text = item.get("text")
        if not isinstance(text, str) or not text.strip():
            continue
        normalized_text = text.strip()
        reading_order.append(normalized_text)
        textual_item: dict[str, Any] = {"id": item_ref, "text": normalized_text}
        span = spans.get(item_ref)
        if span is not None:
            textual_item["locator"] = _locator_from_span(span)
        textual_items.append(textual_item)

        label = item.get("label")
        if isinstance(label, str) and label.casefold().replace("-", "_") in {
            "title",
            "section_header",
        }:
            heading: dict[str, Any] = {"text": normalized_text}
            level = item.get("level")
            if isinstance(level, int) and not isinstance(level, bool) and level >= 0:
                heading["level"] = level
            headings.append(heading)

    tables: list[dict[str, Any]] = []
    for position, table in enumerate(_docling_collection(document, "tables")):
        source_id = _docling_item_ref(table, "tables", position)
        _, caption, caption_issues = _caption_fields(table, item_index)
        table_observation: dict[str, Any] = {"source_id": source_id}
        if caption:
            table_observation["caption"] = caption
        if caption_issues:
            table_observation["caption"] = caption
            table_observation["caption_status"] = "partial" if caption else "unaligned"
            table_observation["caption_diagnostics"] = caption_issues
            unresolved_refs = [
                issue["source_id"] for issue in caption_issues if "source_id" in issue
            ]
            if unresolved_refs:
                table_observation["unresolved_caption_refs"] = unresolved_refs
        text = _table_text(table)
        if text:
            table_observation["text"] = text
        tables.append(table_observation)

    figures: list[dict[str, Any]] = []
    for position, picture in enumerate(_docling_collection(document, "pictures")):
        source_id = _docling_item_ref(picture, "pictures", position)
        caption_refs, caption, caption_issues = _caption_fields(picture, item_index)
        figure: dict[str, Any] = {"source_id": source_id}
        if caption_refs:
            figure["caption_id"] = caption_refs[0]
        if caption:
            figure["caption"] = caption
        if caption_issues:
            figure["caption"] = caption
            figure["caption_status"] = "partial" if caption else "unaligned"
            figure["caption_diagnostics"] = caption_issues
            unresolved_refs = [
                issue["source_id"] for issue in caption_issues if "source_id" in issue
            ]
            if unresolved_refs:
                figure["unresolved_caption_refs"] = unresolved_refs
        figures.append(figure)

    (
        scholarly_references,
        scholarly_provenance,
        scholarly_run,
        grobid_run,
        derivation_runs,
    ) = _scholarly_references(
        store,
        run.artifact_id,
        run.require_output("docling_document").blob_sha256,
        run.pipeline_run_id,
        run.repetition_group_id,
    )
    references = (
        scholarly_references
        if scholarly_references is not None
        else _docling_references(ordered_texts)
    )
    fields = {
        "text": "\n\n".join(reading_order),
        "reading_order": reading_order,
        "headings": headings,
        "tables": tables,
        "figures": figures,
        "references": references,
        "textual_items": textual_items,
    }
    reference_provenance: dict[str, Any] = {
        "reference_source": (
            "grobid_alignment_overlay"
            if scholarly_references is not None
            else "docling_document"
        )
    }
    if scholarly_provenance is not None:
        reference_provenance["scholarly_overlay"] = scholarly_provenance
    return (
        fields,
        reference_provenance,
        scholarly_run,
        grobid_run,
        derivation_runs,
    )


def _select_manifest_artifact(
    document: Mapping[str, Any],
    source_artifact: str,
    artifacts_by_hash: Mapping[str, Sequence[DocumentArtifact]],
) -> DocumentArtifact:
    document_id = str(document["id"])
    artifacts = _mapping(document["artifacts"], f"manifest document {document_id}")
    descriptor = _mapping(
        artifacts[source_artifact],
        f"manifest document {document_id}.artifacts.{source_artifact}",
    )
    source_sha256 = _sha256(
        descriptor.get("sha256"),
        f"manifest document {document_id}.artifacts.{source_artifact}.sha256",
    )
    matches = list(artifacts_by_hash.get(source_sha256, ()))
    if not matches:
        raise BenchmarkError(
            f"manifest document {document_id!r} {source_artifact} hash "
            f"{source_sha256} has no DocumentArtifact in the CAS"
        )
    if len(matches) == 1:
        return matches[0]

    pmcid = str(document["pmcid"]).casefold()
    identifier_matches = [
        artifact
        for artifact in matches
        if artifact.identifiers.get("pmcid", "").casefold() == pmcid
    ]
    if len(identifier_matches) == 1:
        return identifier_matches[0]
    raise BenchmarkError(
        f"manifest document {document_id!r} {source_artifact} hash {source_sha256} "
        "matches multiple CAS artifacts; add a unique pmcid identifier to the "
        f"artifact records: {sorted(artifact.artifact_id for artifact in matches)}"
    )


def _select_processing_run(
    store: ContentAddressedStore,
    artifact: DocumentArtifact,
    component_id: str,
    configuration_hash: str | None,
    output_policy_hash: str | None,
) -> ProcessingRun:
    runs = store.list_processing_runs(
        artifact_id=artifact.artifact_id,
        component_id=component_id,
        configuration_sha256=configuration_hash,
    )
    if output_policy_hash is not None:
        runs = [run for run in runs if run.output_policy_sha256 == output_policy_hash]
    if runs:
        return runs[-1]
    if configuration_hash is not None or output_policy_hash is not None:
        selectors = []
        if configuration_hash is not None:
            selectors.append(f"configuration hash {configuration_hash}")
        if output_policy_hash is not None:
            selectors.append(f"output-policy hash {output_policy_hash}")
        raise BenchmarkError(
            f"artifact {artifact.artifact_id!r} has no {component_id!r} processing run "
            f"with {' and '.join(selectors)}"
        )

    terminal_failures = [
        run
        for run in store.list_processing_runs(artifact_id=artifact.artifact_id)
        if run.status in {ProcessingRunStatus.QUARANTINED, ProcessingRunStatus.FAILED}
    ]
    if terminal_failures:
        return terminal_failures[-1]
    raise BenchmarkError(
        f"artifact {artifact.artifact_id!r} has no {component_id!r} processing run "
        "and no explicit quarantined or failed terminal run"
    )


_CONTENT_CONFIGURATION_KEYS = frozenset(
    {
        "docling_document_sha256",
        "grobid_tei_sha256",
        "input_sha256",
        "native_locator_overlay_sha256",
        "scholarly_alignment_sha256",
        "source_sha256",
        # This records why the conditional OCR branch was taken for one input.  It
        # is evidence about an execution, not a parameter of the OCR recipe.
        "fallback_reason",
        # Input kind changes which branch executes; it is not a parser-policy
        # change.  The benchmark records the actual branch separately.
        "input_format",
        "pdf_span_algorithm",
        "jats_locator_alignment_algorithm",
        "bioc_locator_alignment_algorithm",
    }
)

_PIPELINE_STAGE_NAMES = frozenset(
    {"docling", "grobid", "ocrmypdf", "docling-grobid-aligner"}
)
_OUTPUT_POLICY_SCHEMA = "deepcritical-document-output-policy-v1"
_RUNTIME_PROVENANCE_SCHEMA = "deepcritical-benchmark-runtime-provenance-v2"
_RUNTIME_ATTESTATION_SCHEMA = "deepcritical-runtime-attestation-v1"
_REMOTE_ATTESTATION_CONTRACT = (
    "deepcritical-authenticated-runtime-attestation-reporter-v1"
)
_OCR_ATTESTATION_CONTRACT = "deepcritical-container-ocr-runner-v1"

# These names are the runtime-attestation contract. Values must match exactly;
# finding a configured version as a substring of an unrelated component value
# is deliberately insufficient.
_CANONICAL_COMPONENT_KEYS: dict[str, tuple[str, ...]] = {
    "docling": ("docling", "docling_serve"),
    "grobid": ("grobid",),
    "ocrmypdf": ("ocrmypdf",),
}


def _output_policy_snapshot(run: ProcessingRun) -> dict[str, Any] | None:
    """Return one run's persisted static output policy, if it has one.

    Older, non-baseline fixtures did not record this contract.  They remain
    readable for development comparisons, but baseline generation must never
    infer a policy by combining their per-stage configurations.
    """

    if not run.output_policy_snapshot:
        return None
    if run.output_policy_sha256 is None:
        raise BenchmarkError(
            f"processing run {run.run_id!r} has an output policy without its hash"
        )
    snapshot = dict(run.output_policy_snapshot)
    actual_hash = configuration_sha256(snapshot)
    if actual_hash != run.output_policy_sha256:
        raise BenchmarkError(
            f"processing run {run.run_id!r} output policy hash does not match its snapshot"
        )
    if snapshot.get("schema") != _OUTPUT_POLICY_SCHEMA:
        raise BenchmarkError(
            f"processing run {run.run_id!r} has unsupported output policy schema"
        )
    if not isinstance(snapshot.get("document_processing_config"), Mapping):
        raise BenchmarkError(
            f"processing run {run.run_id!r} output policy has no full processing configuration"
        )
    if not isinstance(snapshot.get("effective_parser_options"), Mapping):
        raise BenchmarkError(
            f"processing run {run.run_id!r} output policy has no effective parser options"
        )
    if not isinstance(snapshot.get("execution_limits"), Mapping):
        raise BenchmarkError(
            f"processing run {run.run_id!r} output policy has no execution limits"
        )
    if not isinstance(snapshot.get("runtime_trust_policy"), Mapping):
        raise BenchmarkError(
            f"processing run {run.run_id!r} output policy has no runtime trust policy"
        )
    if not isinstance(snapshot.get("routing"), Mapping):
        raise BenchmarkError(
            f"processing run {run.run_id!r} output policy has no routing contract"
        )
    if not isinstance(snapshot.get("algorithms"), Mapping):
        raise BenchmarkError(
            f"processing run {run.run_id!r} output policy has no algorithm inventory"
        )
    if not isinstance(snapshot.get("contract_schemas"), Mapping):
        raise BenchmarkError(
            f"processing run {run.run_id!r} output policy has no schema inventory"
        )
    return snapshot


def _benchmark_recipe_hash(run: ProcessingRun) -> str:
    configuration = {
        key: value
        for key, value in run.configuration.items()
        if key not in _CONTENT_CONFIGURATION_KEYS
    }
    return configuration_sha256(configuration)


def _pipeline_recipe_identity(recipe: Mapping[str, Any]) -> str:
    """Return the stable identity of the configured conditional pipeline."""

    return configuration_sha256(dict(recipe))


def _primary_parser_identity(
    run: ProcessingRun,
    pipeline_recipe: Mapping[str, Any] | None = None,
) -> dict[str, str]:
    return {
        "name": run.component_id,
        "version": run.component_version,
        "configuration_hash": (
            _pipeline_recipe_identity(pipeline_recipe)
            if pipeline_recipe is not None
            else _benchmark_recipe_hash(run)
        ),
    }


def _composite_parser_identity(
    run: ProcessingRun,
    grobid_run: ProcessingRun,
    scholarly_run: ProcessingRun,
    derivation_runs: Sequence[ProcessingRun],
    pipeline_recipe: Mapping[str, Any] | None = None,
) -> tuple[dict[str, str], dict[str, Any]]:
    """Report executed stages without making them the candidate recipe identity.

    A scanned PDF legitimately executes OCR and a second GROBID attempt while a
    born-digital PDF does not.  They remain comparable when the conditional
    policy and all configured stage recipes are identical.
    """

    components: dict[str, Any] = {
        "schema": "deepcritical-benchmark-executed-composition-v2",
        "primary": {
            "component_id": run.component_id,
            "component_version": run.component_version,
            "configuration_sha256": _benchmark_recipe_hash(run),
        },
        "grobid": {
            "component_id": grobid_run.component_id,
            "component_version": grobid_run.component_version,
            "configuration_sha256": _benchmark_recipe_hash(grobid_run),
        },
        "scholarly_alignment": {
            "component_id": scholarly_run.component_id,
            "component_version": scholarly_run.component_version,
            "configuration_sha256": _benchmark_recipe_hash(scholarly_run),
        },
        "derivations": [
            {
                "component_id": derivation.component_id,
                "component_version": derivation.component_version,
                "configuration_sha256": _benchmark_recipe_hash(derivation),
            }
            for derivation in derivation_runs
        ],
    }
    return _primary_parser_identity(run, pipeline_recipe), components


def _descendant_artifact_ids(
    store: ContentAddressedStore,
    root_artifact_id: str,
) -> set[str]:
    """Return the immutable artifact subtree rooted at ``root_artifact_id``."""

    children: dict[str, list[str]] = {}
    for artifact in store.list_artifacts():
        if artifact.parent_artifact_id is not None:
            children.setdefault(artifact.parent_artifact_id, []).append(
                artifact.artifact_id
            )
    selected = {root_artifact_id}
    pending = [root_artifact_id]
    while pending:
        parent_id = pending.pop()
        for child_id in children.get(parent_id, []):
            if child_id not in selected:
                selected.add(child_id)
                pending.append(child_id)
    return selected


def _workflow_stage_runs(
    store: ContentAddressedStore,
    root_artifact_id: str,
    pipeline_run_id: str | None,
    repetition_group_id: str | None,
) -> tuple[ProcessingRun, ...]:
    """Find parser attempts in one source-to-derivative workflow.

    Preflight and content-integrity timing are deliberately excluded: this bake-off
    measures conversion and scholarly-processing performance.  Their immutable
    records remain available in CAS and are validated by the processing contract.
    """

    artifact_ids = _descendant_artifact_ids(store, root_artifact_id)
    runs = [
        candidate
        for artifact_id in artifact_ids
        for candidate in store.list_processing_runs(artifact_id=artifact_id)
        if candidate.component_id in _PIPELINE_STAGE_NAMES
        and candidate.pipeline_run_id == pipeline_run_id
        and candidate.repetition_group_id == repetition_group_id
    ]
    return tuple(
        sorted(
            runs,
            key=lambda candidate: (
                candidate.started_at,
                candidate.finished_at,
                candidate.run_id,
            ),
        )
    )


def _workflow_output_policy_snapshot(
    store: ContentAddressedStore,
    root_artifact_id: str,
    pipeline_run_id: str | None,
    repetition_group_id: str | None,
) -> dict[str, Any] | None:
    """Get one workflow's declared static policy without stage unioning."""

    stages = _workflow_stage_runs(
        store,
        root_artifact_id,
        pipeline_run_id,
        repetition_group_id,
    )
    snapshots = [(stage.run_id, _output_policy_snapshot(stage)) for stage in stages]
    present = [(run_id, snapshot) for run_id, snapshot in snapshots if snapshot]
    if not present:
        return None
    missing = [run_id for run_id, snapshot in snapshots if snapshot is None]
    if missing:
        raise BenchmarkError(
            "workflow has mixed output-policy provenance; missing persisted policy "
            f"on stages {sorted(missing)}"
        )
    identities = {configuration_sha256(snapshot): snapshot for _, snapshot in present}
    if len(identities) != 1:
        raise BenchmarkError(
            "workflow stages declare different output policies; a benchmark must "
            "not reconstruct or union them"
        )
    return next(iter(identities.values()))


def _workflow_pipeline_recipe(
    store: ContentAddressedStore,
    root_artifact_id: str,
    pipeline_run_id: str | None,
    repetition_group_id: str | None,
) -> dict[str, Any]:
    """Normalize static configurations for one conditional processing workflow."""

    persisted_policy = _workflow_output_policy_snapshot(
        store,
        root_artifact_id,
        pipeline_run_id,
        repetition_group_id,
    )
    if persisted_policy is not None:
        return persisted_policy

    components: dict[str, dict[str, dict[str, Any]]] = {}
    for stage in _workflow_stage_runs(
        store,
        root_artifact_id,
        pipeline_run_id,
        repetition_group_id,
    ):
        static_configuration = {
            key: value
            for key, value in stage.configuration.items()
            if key not in _CONTENT_CONFIGURATION_KEYS
        }
        static_hash = configuration_sha256(static_configuration)
        components.setdefault(stage.component_id, {})[static_hash] = {
            "component_version": stage.component_version,
            "configuration": static_configuration,
        }
    return {
        "schema": "deepcritical-benchmark-pipeline-recipe-v1",
        "routing_policy": "conditional-document-processing-v1",
        "components": {
            name: [
                {"configuration_sha256": digest, **component}
                for digest, component in sorted(entries.items())
            ]
            for name, entries in sorted(components.items())
        },
    }


def _corpus_pipeline_recipe(
    store: ContentAddressedStore,
    runs: Sequence[ProcessingRun],
) -> dict[str, Any]:
    """Pin one configured policy while preserving branch execution separately."""

    workflow_recipes = [
        _workflow_pipeline_recipe(
            store,
            run.artifact_id,
            run.pipeline_run_id,
            run.repetition_group_id,
        )
        for run in runs
    ]
    persisted = [
        recipe
        for recipe in workflow_recipes
        if recipe.get("schema") == _OUTPUT_POLICY_SCHEMA
    ]
    if persisted:
        if len(persisted) != len(workflow_recipes):
            raise BenchmarkError(
                "corpus has mixed legacy and persisted output-policy provenance"
            )
        identities = {_pipeline_recipe_identity(recipe): recipe for recipe in persisted}
        if len(identities) == 1:
            return next(iter(identities.values()))
        # This deliberately reports each complete declared policy rather than
        # fabricating a synthetic union of stages. Individual observations still
        # carry their own workflow policy below.
        return {
            "schema": "deepcritical-document-output-policy-collection-v1",
            "workflow_policies": [identities[digest] for digest in sorted(identities)],
        }

    components: dict[str, dict[str, dict[str, Any]]] = {}
    for workflow_recipe in workflow_recipes:
        raw_components = workflow_recipe["components"]
        assert isinstance(raw_components, Mapping)
        for stage_name, entries in raw_components.items():
            assert isinstance(stage_name, str)
            assert isinstance(entries, list)
            for entry in entries:
                assert isinstance(entry, Mapping)
                digest = str(entry["configuration_sha256"])
                components.setdefault(stage_name, {})[digest] = {
                    "component_version": entry["component_version"],
                    "configuration": entry["configuration"],
                }
    return {
        "schema": "deepcritical-benchmark-pipeline-recipe-v1",
        "routing_policy": "conditional-document-processing-v1",
        "components": {
            name: [
                {"configuration_sha256": digest, **component}
                for digest, component in sorted(entries.items())
            ]
            for name, entries in sorted(components.items())
        },
    }


def _recipe_is_uniform(recipe: Mapping[str, Any]) -> bool:
    if recipe.get("schema") == _OUTPUT_POLICY_SCHEMA:
        return True
    components = recipe.get("components")
    if not isinstance(components, Mapping):
        return False
    return bool(components) and all(
        isinstance(entries, list) and len(entries) == 1
        for entries in components.values()
    )


def _require_baseline_output_policy(
    corpus_recipe: Mapping[str, Any],
    workflow_recipes: Mapping[str, Mapping[str, Any]],
) -> None:
    """Reject inferred or drifting workflow policy before baseline scoring."""

    if corpus_recipe.get("schema") != _OUTPUT_POLICY_SCHEMA:
        raise BenchmarkError(
            "baseline requires one exact persisted output-policy snapshot for every "
            "selected workflow; legacy or drifting policies are not accepted"
        )
    expected_policy_hash = _pipeline_recipe_identity(corpus_recipe)
    for run_id, workflow_recipe in workflow_recipes.items():
        if (
            workflow_recipe.get("schema") != _OUTPUT_POLICY_SCHEMA
            or _pipeline_recipe_identity(workflow_recipe) != expected_policy_hash
        ):
            raise BenchmarkError(
                "baseline requires all selected workflows to have the same exact "
                f"output-policy snapshot; workflow selected by {run_id!r} drifted"
            )


def _stage_runtime_issues(
    store: ContentAddressedStore,
    stage: ProcessingRun,
    policy: Mapping[str, Any],
) -> list[str]:
    """Validate observed runtime identity against the declared static policy."""

    issues: list[str] = []
    snapshot = _output_policy_snapshot(stage)
    if snapshot is None:
        return [f"{stage.run_id}: missing persisted output policy"]
    if snapshot != policy:
        return [f"{stage.run_id}: output policy differs from workflow policy"]

    raw_config = policy.get("document_processing_config")
    if not isinstance(raw_config, Mapping):  # guarded by _output_policy_snapshot
        return [f"{stage.run_id}: malformed processing configuration"]
    config = raw_config
    if stage.component_id == "docling":
        expected_version = config.get("docling_version")
        expected_image = config.get("docling_container_image")
        expected_digest = config.get("docling_container_digest")
        expected_models = config.get("docling_model_versions", {})
        expected_hashes = config.get("docling_model_hashes", {})
        expected_components = {
            "docling": expected_version,
            "docling_serve": config.get("docling_serve_version"),
        }
    elif stage.component_id == "grobid":
        expected_version = config.get("grobid_version")
        expected_image = config.get("grobid_container_image")
        expected_digest = config.get("grobid_container_digest")
        expected_models = config.get("grobid_model_versions", {})
        expected_hashes = config.get("grobid_model_hashes", {})
        expected_components = {"grobid": expected_version}
    elif stage.component_id == "ocrmypdf":
        expected_version = config.get("ocrmypdf_version")
        ocr_is_container = config.get("ocr_mode") == "container_cli"
        expected_image = config.get("ocr_container_image") if ocr_is_container else None
        expected_digest = (
            config.get("ocr_container_digest") if ocr_is_container else None
        )
        expected_models = {}
        expected_hashes = {}
        expected_components = {"ocrmypdf": expected_version}
    elif stage.component_id == "docling-grobid-aligner":
        algorithms = policy.get("algorithms")
        expected_algorithm = (
            algorithms.get("grobid_docling_alignment")
            if isinstance(algorithms, Mapping)
            else None
        )
        if stage.component_version != "2":
            issues.append(
                f"{stage.run_id}: alignment parser version is not pinned to 2"
            )
        if stage.configuration.get("algorithm") != expected_algorithm:
            issues.append(
                f"{stage.run_id}: alignment algorithm does not match output policy"
            )
        if stage.configuration.get("minimum_score") != config.get(
            "alignment_minimum_score"
        ):
            issues.append(
                f"{stage.run_id}: alignment threshold does not match output policy"
            )
        return issues
    else:
        return issues

    if not isinstance(expected_models, Mapping):
        issues.append(f"{stage.run_id}: model version policy is malformed")
        expected_models = {}
    if not isinstance(expected_hashes, Mapping):
        issues.append(f"{stage.run_id}: model hash policy is malformed")
        expected_hashes = {}

    raw_trust_policy = policy.get("runtime_trust_policy")
    if not isinstance(raw_trust_policy, Mapping):
        return [f"{stage.run_id}: output policy has no runtime trust policy"]
    raw_stage_trust = raw_trust_policy.get(stage.component_id)
    if not isinstance(raw_stage_trust, Mapping):
        return [
            f"{stage.run_id}: output policy has no {stage.component_id} runtime trust policy"
        ]
    expected_reporter_id = raw_stage_trust.get("expected_reporter_id")
    expected_source = raw_stage_trust.get("expected_source")
    expected_schema = raw_stage_trust.get("attestation_schema_version")
    expected_contract = (
        _OCR_ATTESTATION_CONTRACT
        if stage.component_id == "ocrmypdf"
        else _REMOTE_ATTESTATION_CONTRACT
    )
    if raw_stage_trust.get("reporter_configured") is not True:
        issues.append(f"{stage.run_id}: runtime attestation reporter is not configured")
    if not isinstance(expected_reporter_id, str) or not expected_reporter_id:
        issues.append(f"{stage.run_id}: expected runtime reporter ID is missing")
    if not isinstance(expected_source, str) or not expected_source:
        issues.append(f"{stage.run_id}: expected runtime attestation source is missing")
    if expected_schema != _RUNTIME_ATTESTATION_SCHEMA:
        issues.append(f"{stage.run_id}: runtime attestation schema is not pinned")
    if raw_stage_trust.get("attestation_contract_version") != expected_contract:
        issues.append(f"{stage.run_id}: runtime attestation contract is not pinned")
    if (
        stage.component_id == "ocrmypdf"
        and raw_stage_trust.get("local_digest_runner_version")
        != _OCR_ATTESTATION_CONTRACT
    ):
        issues.append(f"{stage.run_id}: local digest runner version is not pinned")

    if not stage.runtime_identity_required:
        issues.append(f"{stage.run_id}: runtime identity was not required")
    attestation = stage.runtime_attestation
    if attestation is None:
        issues.append(f"{stage.run_id}: task-bound runtime attestation is missing")
    else:
        attestation_digest = stage.runtime_attestation_sha256
        if attestation_digest is None:
            issues.append(f"{stage.run_id}: runtime attestation hash is missing")
        else:
            try:
                store.verify_blob(attestation_digest)
                persisted = json.loads(store.read_blob(attestation_digest))
                if persisted != attestation.model_dump(mode="json"):
                    issues.append(
                        f"{stage.run_id}: persisted runtime attestation differs from the run"
                    )
            except Exception as exc:
                issues.append(
                    f"{stage.run_id}: runtime attestation evidence is unreadable: {exc}"
                )
        if attestation.component_id != stage.component_id:
            issues.append(
                f"{stage.run_id}: attested component does not match the processing run"
            )
        if attestation.schema_version != expected_schema:
            issues.append(
                f"{stage.run_id}: attestation schema differs from output policy"
            )
        if attestation.reporter_id != expected_reporter_id:
            issues.append(
                f"{stage.run_id}: attested reporter differs from output policy"
            )
        if attestation.source.value != expected_source:
            issues.append(f"{stage.run_id}: attested source differs from output policy")
        if attestation.component_version != stage.component_version:
            issues.append(
                f"{stage.run_id}: parser version was not sourced from attestation"
            )
        if attestation.invocation_id != stage.component_invocation_id:
            issues.append(
                f"{stage.run_id}: parser invocation id does not match attestation"
            )
        if stage.container_digest != attestation.container_digest:
            issues.append(
                f"{stage.run_id}: container digest was not sourced from attestation"
            )
        if dict(stage.component_versions) != dict(attestation.component_versions):
            issues.append(
                f"{stage.run_id}: component versions were not sourced from attestation"
            )
        if dict(stage.model_versions) != dict(attestation.model_versions):
            issues.append(
                f"{stage.run_id}: model versions were not sourced from attestation"
            )
        if dict(stage.model_hashes) != dict(attestation.model_hashes):
            issues.append(
                f"{stage.run_id}: model hashes were not sourced from attestation"
            )
    if stage.component_version != expected_version:
        issues.append(f"{stage.run_id}: parser version differs from output policy")
    if attestation is not None:
        observed_image = attestation.container_reference.split("@", maxsplit=1)[0]
        declared_image = (
            str(expected_image).split("@", maxsplit=1)[0]
            if expected_image is not None
            else None
        )
        if observed_image != declared_image:
            issues.append(f"{stage.run_id}: container image differs from output policy")
    elif stage.container_image is not None:
        issues.append(
            f"{stage.run_id}: container image is present without runtime attestation"
        )
    if stage.component_id in {"docling", "grobid"} and not expected_hashes:
        issues.append(f"{stage.run_id}: model hash inventory is empty")
    if stage.component_id == "ocrmypdf" and config.get("ocr_mode") == "local_cli":
        if stage.container_image is not None or stage.container_digest is not None:
            issues.append(
                f"{stage.run_id}: local OCR run must not declare a container identity"
            )
    elif expected_digest is None or stage.container_digest != expected_digest:
        issues.append(
            f"{stage.run_id}: immutable container digest is missing or differs from output policy"
        )
    if not stage.component_versions:
        issues.append(f"{stage.run_id}: observed component versions are missing")
    else:
        for component, expected in expected_components.items():
            if (
                not isinstance(expected, str)
                or not expected
                or stage.component_versions.get(component) != expected
            ):
                issues.append(
                    f"{stage.run_id}: expected runtime component {component!r} "
                    f"version {expected!r} was not observed exactly"
                )
    if dict(stage.model_versions) != dict(expected_models):
        issues.append(f"{stage.run_id}: model versions differ from output policy")
    if dict(stage.model_hashes) != dict(expected_hashes):
        issues.append(f"{stage.run_id}: model hashes differ from output policy")
    return issues


def _workflow_runtime_provenance(
    store: ContentAddressedStore,
    root_artifact_id: str,
    pipeline_run_id: str | None,
    repetition_group_id: str | None,
    policy: Mapping[str, Any],
) -> dict[str, Any]:
    stages = _workflow_stage_runs(
        store,
        root_artifact_id,
        pipeline_run_id,
        repetition_group_id,
    )
    issues = [
        issue
        for stage in stages
        for issue in _stage_runtime_issues(store, stage, policy)
    ]
    return {
        "schema": _RUNTIME_PROVENANCE_SCHEMA,
        "verified": not issues,
        "issues": issues,
        "stages": [
            {
                "processing_run_id": stage.run_id,
                "component_id": stage.component_id,
                "component_version": stage.component_version,
                "component_invocation_id": stage.component_invocation_id,
                "runtime_identity_required": stage.runtime_identity_required,
                "component_versions": dict(stage.component_versions),
                "container_image": stage.container_image,
                "container_digest": stage.container_digest,
                "model_versions": dict(stage.model_versions),
                "model_hashes": dict(stage.model_hashes),
                "runtime_attestation_sha256": stage.runtime_attestation_sha256,
                "runtime_attestation_output_sha256": stage.output_sha256(
                    "runtime_attestation"
                ),
                "runtime_attestation_observed_at": (
                    stage.runtime_attestation.model_dump(mode="json")["observed_at"]
                    if stage.runtime_attestation is not None
                    else None
                ),
                "runtime_attestation": (
                    stage.runtime_attestation.model_dump(mode="json")
                    if stage.runtime_attestation is not None
                    else None
                ),
            }
            for stage in stages
        ],
    }


def _projected_content_spans_hash(
    store: ContentAddressedStore,
    run: ProcessingRun,
) -> str:
    normalized_spans = [
        {
            "representation_node_id": span.representation_anchor.node_id,
            "representation_char_start": span.representation_anchor.char_start,
            "representation_char_end": span.representation_anchor.char_end,
            "content_sha256": span.content_sha256,
            "source_locator": span.source_locator.model_dump(mode="json"),
        }
        for span in _content_spans(store, run)
    ]
    normalized_spans.sort(
        key=lambda value: (
            str(value["representation_node_id"]),
            int(value["representation_char_start"]),
            int(value["representation_char_end"]),
            str(value["content_sha256"]),
            json.dumps(
                value["source_locator"],
                ensure_ascii=False,
                separators=(",", ":"),
                sort_keys=True,
            ),
        )
    )
    return configuration_sha256(
        {
            "schema": "deepcritical-benchmark-projected-spans-v1",
            "spans": normalized_spans,
        }
    )


def _composite_output_hash(
    store: ContentAddressedStore,
    run: ProcessingRun,
    scholarly_run: ProcessingRun | None,
) -> str:
    components = {
        "schema": "deepcritical-benchmark-projected-content-v1",
        "docling_document_sha256": run.require_output("docling_document").blob_sha256,
        "projected_content_spans_sha256": _projected_content_spans_hash(store, run),
    }
    if scholarly_run is not None:
        components["scholarly_alignment_sha256"] = scholarly_run.require_output(
            "alignment_overlay"
        ).blob_sha256
    return configuration_sha256(components)


def _verify_projected_components(
    store: ContentAddressedStore,
    run: ProcessingRun,
    scholarly_run: ProcessingRun | None,
) -> None:
    store.verify_blob(run.require_output("docling_document").blob_sha256)
    _projected_content_spans_hash(store, run)
    if scholarly_run is not None:
        store.verify_blob(scholarly_run.require_output("alignment_overlay").blob_sha256)


def _repeat_output_hashes(
    store: ContentAddressedStore,
    run: ProcessingRun,
    scholarly_run: ProcessingRun | None,
) -> tuple[list[str], list[str]]:
    _verify_projected_components(store, run, scholarly_run)
    current_hash = _composite_output_hash(store, run, scholarly_run)
    current_workflow_recipe = _workflow_pipeline_recipe(
        store,
        run.artifact_id,
        run.pipeline_run_id,
        run.repetition_group_id,
    )
    pipeline_run_id = run.pipeline_run_id
    repetition_group_id = run.repetition_group_id
    if pipeline_run_id is None or repetition_group_id is None:
        return [current_hash], []

    matching_runs = store.list_processing_runs(
        artifact_id=run.artifact_id,
        component_id=run.component_id,
    )
    selected_by_workflow: dict[str, ProcessingRun] = {}
    for candidate in matching_runs:
        if (
            candidate.pipeline_run_id is None
            or candidate.repetition_group_id != repetition_group_id
            or candidate.status
            not in {ProcessingRunStatus.COMPLETE, ProcessingRunStatus.PARTIAL}
            or candidate.output("docling_document") is None
            or candidate.output("content_spans") is None
            or _benchmark_recipe_hash(candidate) != _benchmark_recipe_hash(run)
        ):
            continue
        selected_by_workflow[candidate.pipeline_run_id] = candidate

    repeat_hashes = [current_hash]
    repeat_workflow_ids = [pipeline_run_id]
    for candidate_workflow_id in sorted(selected_by_workflow):
        if candidate_workflow_id == pipeline_run_id:
            continue
        candidate = selected_by_workflow[candidate_workflow_id]
        candidate_scholarly_run: ProcessingRun | None = None
        candidate_grobid_run: ProcessingRun | None = None
        candidate_workflow_recipe = _workflow_pipeline_recipe(
            store,
            candidate.artifact_id,
            candidate.pipeline_run_id,
            candidate.repetition_group_id,
        )
        if candidate_workflow_recipe != current_workflow_recipe:
            continue
        if scholarly_run is not None:
            (
                _,
                _,
                candidate_scholarly_run,
                candidate_grobid_run,
                _candidate_derivation_runs,
            ) = _scholarly_references(
                store,
                candidate.artifact_id,
                candidate.require_output("docling_document").blob_sha256,
                candidate.pipeline_run_id,
                candidate.repetition_group_id,
            )
            if candidate_scholarly_run is None or candidate_grobid_run is None:
                continue
        _verify_projected_components(store, candidate, candidate_scholarly_run)
        repeat_hashes.append(
            _composite_output_hash(store, candidate, candidate_scholarly_run)
        )
        repeat_workflow_ids.append(candidate_workflow_id)
    return repeat_hashes, repeat_workflow_ids


def _run_wall_time(run: ProcessingRun) -> float:
    measured = run.resource_usage.wall_time_seconds
    if measured is not None:
        return measured
    return max(0.0, (run.finished_at - run.started_at).total_seconds())


def _resource_fields(
    runs: Sequence[ProcessingRun],
) -> tuple[float, int | None, dict[str, Any]]:
    elapsed = sum(_run_wall_time(run) for run in runs)
    memory_runs = tuple(
        run for run in runs if run.component_id in _MEMORY_SCOPED_PARSER_NAMES
    )
    excluded_runs = tuple(
        run for run in runs if run.component_id not in _MEMORY_SCOPED_PARSER_NAMES
    )
    recorded_peaks = [run.resource_usage.peak_memory_bytes for run in memory_runs]
    peak_memory = (
        max(cast("Sequence[int]", recorded_peaks))
        if recorded_peaks and all(value is not None for value in recorded_peaks)
        else None
    )
    measurement_records: list[dict[str, Any]] = []
    environment_by_boundary: dict[str, set[str]] = {}
    baseline_comparable = bool(memory_runs)
    for run in memory_runs:
        measurement = run.resource_usage.memory_measurement
        if measurement is None:
            baseline_comparable = False
            measurement_records.append(
                {
                    "processing_run_id": run.run_id,
                    "component_id": run.component_id,
                    "measurement": None,
                }
            )
            continue
        measurement_records.append(
            {
                "processing_run_id": run.run_id,
                "component_id": run.component_id,
                "measurement": measurement.model_dump(mode="json"),
            }
        )
        if not measurement.baseline_comparable:
            baseline_comparable = False
        if measurement.boundary and measurement.environment_sha256:
            environment_by_boundary.setdefault(measurement.boundary, set()).add(
                measurement.environment_sha256
            )
    if any(len(values) != 1 for values in environment_by_boundary.values()):
        baseline_comparable = False
    return (
        elapsed,
        peak_memory,
        {
            "elapsed_seconds_method": "sum_stage_wall_time",
            "peak_memory_bytes_method": (
                "max_heavy_parser_stage_peak_memory"
                if peak_memory is not None
                else "unmeasured_when_any_heavy_parser_stage_missing"
            ),
            "processing_run_ids": [run.run_id for run in runs],
            "memory_scope": _MEMORY_SCOPE,
            "memory_required_component_ids": sorted(_MEMORY_SCOPED_PARSER_NAMES),
            "memory_required_run_ids": [run.run_id for run in memory_runs],
            "memory_excluded_runs": [
                {
                    "processing_run_id": run.run_id,
                    "component_id": run.component_id,
                    "reason": "not_an_isolated_heavy_parser_invocation",
                }
                for run in excluded_runs
            ],
            "memory_measurements": measurement_records,
            "memory_baseline_comparable": baseline_comparable,
            "memory_environment_by_boundary": {
                boundary: sorted(values)
                for boundary, values in sorted(environment_by_boundary.items())
            },
        },
    )


def _composite_resource_runs(
    store: ContentAddressedStore,
    primary_run: ProcessingRun,
    scholarly_run: ProcessingRun,
    grobid_run: ProcessingRun,
    derivation_runs: Sequence[ProcessingRun],
) -> tuple[ProcessingRun, ...]:
    """Account for selected stages and failed original-PDF GROBID attempts.

    The pipeline first tries GROBID on every PDF.  A scanned document then has an
    OCR derivative and a second GROBID run.  The unsuccessful first attempt is
    real work, so excluding it would understate scanned-route elapsed time and
    peak memory.  Preflight and content-integrity are excluded consistently (see
    ``_workflow_stage_runs``).
    """

    root_grobid_attempts = [
        candidate
        for candidate in _workflow_stage_runs(
            store,
            primary_run.artifact_id,
            primary_run.pipeline_run_id,
            primary_run.repetition_group_id,
        )
        if candidate.component_id == "grobid"
        and candidate.artifact_id == primary_run.artifact_id
    ]
    ordered = (
        primary_run,
        *root_grobid_attempts,
        *derivation_runs,
        grobid_run,
        scholarly_run,
    )
    selected: list[ProcessingRun] = []
    seen: set[str] = set()
    for stage in ordered:
        if stage.run_id not in seen:
            selected.append(stage)
            seen.add(stage.run_id)
    return tuple(selected)


def _candidate_observation(
    store: ContentAddressedStore,
    document: Mapping[str, Any],
    artifact: DocumentArtifact,
    run: ProcessingRun,
    source_artifact: str,
    pipeline_recipe: Mapping[str, Any],
) -> dict[str, Any]:
    wall_time, peak_memory, resource_provenance = _resource_fields((run,))
    observation: dict[str, Any] = {
        "document_id": str(document["id"]),
        "parser": _primary_parser_identity(run, pipeline_recipe),
        "source_artifact": source_artifact,
        "outcome": run.status.value,
        "text": "",
        "reading_order": [],
        "headings": [],
        "tables": [],
        "figures": [],
        "references": [],
        "textual_items": [],
        "output_hashes": [],
        "elapsed_seconds": wall_time,
        "provenance": {
            "artifact_id": artifact.artifact_id,
            "source_sha256": artifact.source_sha256,
            "processing_run_id": run.run_id,
            "pipeline_run_id": run.pipeline_run_id,
            "repetition_group_id": run.repetition_group_id,
            "peak_memory_bytes_recorded": peak_memory is not None,
            "resource_accounting": resource_provenance,
            "processing_run_configuration_sha256": run.configuration_sha256,
            "warnings": list(run.warnings),
        },
    }
    if peak_memory is not None:
        observation["peak_memory_bytes"] = peak_memory
    if run.status not in {ProcessingRunStatus.COMPLETE, ProcessingRunStatus.PARTIAL}:
        return observation

    document_digest = run.output_sha256("docling_document")
    if document_digest is None:
        raise BenchmarkError(
            f"successful processing run {run.run_id!r} has no docling_document output"
        )
    document_payload = _read_json_blob(store, document_digest, "DoclingDocument")
    if not isinstance(document_payload, Mapping):
        raise BenchmarkError(
            f"persisted DoclingDocument for run {run.run_id!r} must be an object"
        )
    (
        fields,
        reference_provenance,
        scholarly_run,
        grobid_run,
        derivation_runs,
    ) = _docling_observation_fields(store, run, document_payload)
    observation.update(fields)
    if scholarly_run is not None:
        if grobid_run is None:
            raise BenchmarkError(
                f"alignment run {scholarly_run.run_id!r} has no resolved GROBID run"
            )
        parser_identity, identity_components = _composite_parser_identity(
            run,
            grobid_run,
            scholarly_run,
            derivation_runs,
            pipeline_recipe,
        )
        observation["parser"] = parser_identity
        resource_runs = _composite_resource_runs(
            store,
            run,
            scholarly_run,
            grobid_run,
            derivation_runs,
        )
        wall_time, peak_memory, resource_provenance = _resource_fields(resource_runs)
        observation["elapsed_seconds"] = wall_time
        if peak_memory is None:
            observation.pop("peak_memory_bytes", None)
        else:
            observation["peak_memory_bytes"] = peak_memory
        observation["content_hash"] = _composite_output_hash(
            store,
            run,
            scholarly_run,
        )
    else:
        identity_components = None
        observation["content_hash"] = _composite_output_hash(store, run, None)
    repeat_hashes, repeat_workflow_ids = _repeat_output_hashes(
        store,
        run,
        scholarly_run,
    )
    observation["output_hashes"] = repeat_hashes
    provenance: dict[str, Any] = observation["provenance"]
    assert isinstance(provenance, dict)
    provenance.update(reference_provenance)
    provenance["peak_memory_bytes_recorded"] = peak_memory is not None
    provenance["resource_accounting"] = resource_provenance
    if identity_components is not None:
        provenance["candidate_parser_composition"] = identity_components
    if pipeline_recipe.get("schema") == _OUTPUT_POLICY_SCHEMA:
        runtime_provenance = _workflow_runtime_provenance(
            store,
            artifact.artifact_id,
            run.pipeline_run_id,
            run.repetition_group_id,
            pipeline_recipe,
        )
        provenance["output_policy_snapshot"] = pipeline_recipe
        provenance["output_policy_sha256"] = _pipeline_recipe_identity(pipeline_recipe)
        provenance["runtime_identity"] = runtime_provenance
    provenance["pipeline_recipe"] = pipeline_recipe
    provenance["pipeline_recipe_sha256"] = _pipeline_recipe_identity(pipeline_recipe)
    if len(repeat_workflow_ids) >= 2:
        provenance["determinism"] = {
            "status": "measured",
            "pipeline_run_ids": repeat_workflow_ids,
            "repetition_group_id": run.repetition_group_id,
        }
    else:
        provenance["determinism"] = {
            "status": "unmeasured",
            "reason": "insufficient_independent_end_to_end_repeats",
            "required_action": (
                "run the process command at least twice with --force-reprocess and "
                "the same --benchmark-repetition-group, using a distinct "
                "--pipeline-attempt-id for each independent repeat (reuse an ID only "
                "to retry that same attempt), then regenerate observations"
            ),
        }
    provenance["docling_document_sha256"] = document_digest
    provenance["content_spans_sha256"] = run.require_output("content_spans").blob_sha256
    return observation


def generate_candidate_observations(
    manifest_path: str | Path,
    cas_root: str | Path,
    *,
    source_artifact: str = "pdf",
    component_id: str = "docling",
    configuration_hash: str | None = None,
    output_policy_hash: str | None = None,
    enforce_baseline: bool = False,
) -> dict[str, Any]:
    """Project persisted parser evidence into the benchmark observation schema.

    This adapter is read-only with respect to parser state: it does not download a
    corpus, call a service, rerun a parser, or manufacture reference annotations.
    Manifest artifact hashes select source records; immutable processing runs and their
    verified CAS outputs supply every generated field.
    """

    if source_artifact not in {"pdf", "jats"}:
        raise BenchmarkError("source_artifact must be 'pdf' or 'jats'")
    component_id = _string(component_id, "component_id")
    if configuration_hash is not None:
        configuration_hash = _sha256(configuration_hash, "configuration_hash")
    if output_policy_hash is not None:
        output_policy_hash = _sha256(output_policy_hash, "output_policy_hash")
    if configuration_hash is not None and output_policy_hash is not None:
        raise BenchmarkError(
            "configuration_hash and output_policy_hash are mutually exclusive"
        )

    resolved_manifest_path = Path(manifest_path).expanduser().resolve()
    manifest = load_manifest(
        resolved_manifest_path,
        enforce_baseline=enforce_baseline,
        # Source bytes are read and hash-verified from CAS below. This allows the
        # generation command to operate on a manifest/CAS export without a second
        # mutable corpus copy beside the manifest.
        verify_artifacts=False,
    )
    resolved_cas_root = Path(cas_root).expanduser().resolve()
    required_directories = (
        resolved_cas_root / "blobs" / "sha256",
        resolved_cas_root / "records" / "artifacts",
        resolved_cas_root / "records" / "processing_runs",
    )
    if not resolved_cas_root.is_dir() or any(
        not directory.is_dir() for directory in required_directories
    ):
        raise BenchmarkError(
            f"CAS root is missing required persisted state: {resolved_cas_root}"
        )

    try:
        store = ContentAddressedStore(resolved_cas_root)
        artifacts = store.list_artifacts()
        artifacts_by_hash: dict[str, list[DocumentArtifact]] = {}
        for artifact in artifacts:
            artifacts_by_hash.setdefault(artifact.source_sha256, []).append(artifact)

        selected: list[tuple[Mapping[str, Any], DocumentArtifact, ProcessingRun]] = []
        documents = sorted(manifest["documents"], key=lambda item: str(item["id"]))
        for document in documents:
            document_mapping = _mapping(document, "manifest.documents")
            artifact = _select_manifest_artifact(
                document_mapping, source_artifact, artifacts_by_hash
            )
            store.verify_blob(artifact.source_sha256)
            run = _select_processing_run(
                store,
                artifact,
                component_id,
                configuration_hash,
                output_policy_hash,
            )
            selected.append((document_mapping, artifact, run))

        pipeline_recipe = _corpus_pipeline_recipe(
            store,
            [run for _, _, run in selected],
        )
        workflow_recipes = {
            run.run_id: _workflow_pipeline_recipe(
                store,
                run.artifact_id,
                run.pipeline_run_id,
                run.repetition_group_id,
            )
            for _, _, run in selected
        }
        if enforce_baseline:
            _require_baseline_output_policy(pipeline_recipe, workflow_recipes)

        observations: list[dict[str, Any]] = []
        for document_mapping, artifact, run in selected:
            workflow_recipe = workflow_recipes[run.run_id]
            if enforce_baseline:
                runtime_provenance = _workflow_runtime_provenance(
                    store,
                    artifact.artifact_id,
                    run.pipeline_run_id,
                    run.repetition_group_id,
                    workflow_recipe,
                )
                if not runtime_provenance["verified"]:
                    issues = runtime_provenance["issues"]
                    assert isinstance(issues, list)
                    raise BenchmarkError(
                        "baseline requires complete runtime provenance matching the "
                        f"declared output policy for {run.run_id!r}: {'; '.join(issues)}"
                    )
            observations.append(
                _candidate_observation(
                    store,
                    document_mapping,
                    artifact,
                    run,
                    source_artifact,
                    workflow_recipe,
                )
            )
        if enforce_baseline:
            expected_memory_environment: dict[str, str] = {}
            for observation in observations:
                document_id = str(observation["document_id"])
                memory_environment = _baseline_memory_environment(
                    observation, document_id
                )
                _merge_baseline_memory_environment(
                    expected_memory_environment,
                    memory_environment,
                    context="baseline observation generation",
                )
    except StorageError as exc:
        raise BenchmarkError(f"cannot read CAS state: {exc}") from exc

    return {
        "schema_version": OBSERVATION_SCHEMA_VERSION,
        "generator": {
            "name": "deepcritical-cas-observation-adapter",
            "version": "1",
        },
        "manifest": {
            "name": manifest["name"],
            "schema_version": manifest["schema_version"],
            "sha256": _sha256_path(resolved_manifest_path),
        },
        "selection": {
            "source_artifact": source_artifact,
            "component_id": component_id,
            "configuration_hash": configuration_hash,
            "output_policy_hash": output_policy_hash,
            "pipeline_recipe_sha256": _pipeline_recipe_identity(pipeline_recipe),
        },
        "observations": observations,
    }


def _parse_observation_payload(payload: Any, context: str) -> list[Any]:
    if isinstance(payload, list):
        return payload
    if isinstance(payload, Mapping):
        if "observations" in payload:
            observations = payload["observations"]
            if not isinstance(observations, list):
                raise BenchmarkError(f"{context}.observations must be an array")
            return observations
        if "document_id" in payload:
            return [payload]
    raise BenchmarkError(
        f"{context} must be an observation object, an array, or an object "
        "containing an observations array"
    )


def _validate_observation(observation: Mapping[str, Any], context: str) -> None:
    _string(observation.get("document_id"), f"{context}.document_id")
    outcome = _string(observation.get("outcome"), f"{context}.outcome")
    if outcome not in OUTCOMES:
        raise BenchmarkError(f"{context}.outcome must be one of {list(OUTCOMES)}")
    if "text" in observation and not isinstance(observation["text"], str):
        raise BenchmarkError(f"{context}.text must be a string")

    reading_order = observation.get("reading_order", [])
    if not isinstance(reading_order, list) or any(
        not isinstance(item, str) for item in reading_order
    ):
        raise BenchmarkError(f"{context}.reading_order must be an array of strings")

    for field in ("headings", "tables", "figures", "references", "textual_items"):
        values = observation.get(field, [])
        if not isinstance(values, list) or any(
            not isinstance(item, Mapping) for item in values
        ):
            raise BenchmarkError(f"{context}.{field} must be an array of objects")

    if "elapsed_seconds" in observation:
        _number(observation["elapsed_seconds"], f"{context}.elapsed_seconds")
    if (
        "peak_memory_bytes" in observation
        and observation["peak_memory_bytes"] is not None
    ):
        _nonnegative_integer(
            observation["peak_memory_bytes"], f"{context}.peak_memory_bytes"
        )
    if "content_hash" in observation:
        _sha256(observation["content_hash"], f"{context}.content_hash")
    if "output_hashes" in observation:
        output_hashes = observation["output_hashes"]
        if not isinstance(output_hashes, list):
            raise BenchmarkError(f"{context}.output_hashes must be an array")
        for index, digest in enumerate(output_hashes):
            _sha256(digest, f"{context}.output_hashes[{index}]")


def load_observations(path: str | Path) -> dict[str, dict[str, Any]]:
    """Load an observation set from JSON or newline-delimited JSON."""

    observation_path = Path(path).expanduser().resolve()
    if not observation_path.is_file():
        raise BenchmarkError(
            f"observation file does not exist or is not a file: {observation_path}"
        )
    try:
        raw_text = observation_path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        raise BenchmarkError(
            f"cannot read observations {observation_path}: {exc}"
        ) from exc
    if not raw_text.strip():
        raise BenchmarkError(f"observation file is empty: {observation_path}")

    try:
        payload = json.loads(raw_text)
        raw_observations = _parse_observation_payload(payload, "observations")
    except json.JSONDecodeError:
        raw_observations = []
        for line_number, line in enumerate(raw_text.splitlines(), start=1):
            if not line.strip():
                continue
            try:
                raw_observations.append(json.loads(line))
            except json.JSONDecodeError as exc:
                raise BenchmarkError(
                    f"invalid JSONL in {observation_path} at line {line_number}: {exc}"
                ) from exc

    if not raw_observations:
        raise BenchmarkError(f"no observations found in {observation_path}")

    observations: dict[str, dict[str, Any]] = {}
    for index, raw_observation in enumerate(raw_observations):
        context = f"observations[{index}]"
        observation = _mapping(raw_observation, context)
        _validate_observation(observation, context)
        document_id = str(observation["document_id"]).strip()
        if document_id in observations:
            raise BenchmarkError(
                f"duplicate observation for document_id {document_id!r} in "
                f"{observation_path}"
            )
        observations[document_id] = dict(observation)
    return observations


def _normalize_text(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    normalized = unicodedata.normalize("NFKC", value).casefold()
    return " ".join(_WORD_RE.findall(normalized))


def _tokens(value: Any) -> list[str]:
    normalized = _normalize_text(value)
    return normalized.split() if normalized else []


def _multiset_f1(candidate: Iterable[str], reference: Iterable[str]) -> float:
    candidate_counts = Counter(candidate)
    reference_counts = Counter(reference)
    candidate_total = sum(candidate_counts.values())
    reference_total = sum(reference_counts.values())
    if candidate_total == 0 and reference_total == 0:
        return 1.0
    if candidate_total == 0 or reference_total == 0:
        return 0.0
    overlap = sum((candidate_counts & reference_counts).values())
    return (2.0 * overlap) / (candidate_total + reference_total)


def _applicable_multiset_f1(
    candidate: Sequence[str], reference: Sequence[str]
) -> float | None:
    """Score optional structured content without rewarding mutual absence."""

    if not candidate and not reference:
        return None
    return _multiset_f1(candidate, reference)


def _reading_order_score(candidate: Sequence[str], reference: Sequence[str]) -> float:
    """Compare normalized token streams independently of parser block boundaries.

    ``SequenceMatcher`` tolerates local insertions and deletions without the
    boundary cascade caused by fixed token windows. Its automatic popular-token
    suppression also keeps repeated boilerplate from dominating long articles.
    """

    left = [token for block in candidate for token in _tokens(block)]
    right = [token for block in reference for token in _tokens(block)]
    if not left and not right:
        return 1.0
    if not left or not right:
        return 0.0
    return SequenceMatcher(None, left, right, autojunk=True).ratio()


def _objects(observation: Mapping[str, Any], field: str) -> list[Mapping[str, Any]]:
    return [dict(item) for item in observation.get(field, [])]


def _heading_signatures(observation: Mapping[str, Any]) -> list[str]:
    signatures: list[str] = []
    for heading in _objects(observation, "headings"):
        level = heading.get("level", "")
        signatures.append(f"{level}:{_normalize_text(heading.get('text'))}")
    return signatures


def _table_signatures(observation: Mapping[str, Any]) -> list[str]:
    signatures: list[str] = []
    for index, table in enumerate(_objects(observation, "tables")):
        digest = table.get("content_hash")
        if isinstance(digest, str) and _SHA256_RE.fullmatch(digest):
            signatures.append(f"sha256:{digest.lower()}")
            continue
        caption = _normalize_text(table.get("caption"))
        content = _normalize_text(
            table.get("text", table.get("markdown", table.get("html", "")))
        )
        signatures.append(
            f"table:{caption}|{content}" if caption or content else f"empty:{index}"
        )
    return signatures


def _figure_signatures(observation: Mapping[str, Any]) -> list[str]:
    signatures: list[str] = []
    for index, figure in enumerate(_objects(observation, "figures")):
        caption = _normalize_text(figure.get("caption"))
        signatures.append(f"ordinal:{index}|caption:{caption}")
    return signatures


def _reference_signatures(observation: Mapping[str, Any]) -> list[str]:
    signatures: list[str] = []
    for index, reference in enumerate(_objects(observation, "references")):
        doi = _normalize_text(reference.get("doi"))
        if doi:
            doi = doi.removeprefix("https doi org ").removeprefix("doi ")
            signatures.append(f"doi:{doi}")
            continue
        pmid = _normalize_text(reference.get("pmid"))
        if pmid:
            signatures.append(f"pmid:{pmid}")
            continue
        text = _normalize_text(reference.get("text"))
        signatures.append(f"text:{text}" if text else f"empty:{index}")
    return signatures


def _valid_locator(value: Any, source_artifact: str) -> bool:
    if not isinstance(value, Mapping):
        return False
    if source_artifact == "jats":
        return any(
            isinstance(value.get(native_key), str) and value[native_key].strip()
            for native_key in ("xml_id", "xpath", "native")
        )
    page = value.get("page")
    bbox = value.get("bbox")
    if isinstance(page, bool) or not isinstance(page, int) or page < 1:
        return False
    if not isinstance(bbox, list) or len(bbox) != 4:
        return False
    if any(isinstance(coordinate, bool) for coordinate in bbox):
        return False
    if any(not isinstance(coordinate, (int, float)) for coordinate in bbox):
        return False
    coordinates = [float(coordinate) for coordinate in bbox]
    if any(not math.isfinite(coordinate) for coordinate in coordinates):
        return False
    left, top, right, bottom = coordinates
    return left < right and top < bottom


def _locator_counts(observation: Mapping[str, Any]) -> tuple[int, int]:
    source_artifact = str(observation.get("source_artifact", ""))
    located = 0
    total = 0
    for item in _objects(observation, "textual_items"):
        if not _normalize_text(item.get("text")):
            continue
        total += 1
        if _valid_locator(item.get("locator"), source_artifact):
            located += 1
    return located, total


def _determinism_score(observation: Mapping[str, Any]) -> float | None:
    hashes = observation.get("output_hashes", [])
    if not isinstance(hashes, list) or len(hashes) < 2:
        return None
    normalized = [str(digest).lower() for digest in hashes]
    return 1.0 if len(set(normalized)) == 1 else 0.0


def _rounded(value: float | None) -> float | None:
    return None if value is None else round(value, 6)


def _candidate_requirements(
    observation: Mapping[str, Any], document_id: str
) -> tuple[float, int | None]:
    context = f"candidate observation {document_id!r}"
    parser = _mapping(observation.get("parser"), f"{context}.parser")
    _string(parser.get("name"), f"{context}.parser.name")
    _string(parser.get("version"), f"{context}.parser.version")
    _sha256(parser.get("configuration_hash"), f"{context}.parser.configuration_hash")
    source_artifact = _string(
        observation.get("source_artifact"), f"{context}.source_artifact"
    )
    if source_artifact not in {"jats", "pdf"}:
        raise BenchmarkError(f"{context}.source_artifact must be 'jats' or 'pdf'")
    elapsed = _number(observation.get("elapsed_seconds"), f"{context}.elapsed_seconds")
    raw_peak_memory = observation.get("peak_memory_bytes")
    peak_memory = (
        _nonnegative_integer(raw_peak_memory, f"{context}.peak_memory_bytes")
        if raw_peak_memory is not None
        else None
    )
    outcome = str(observation["outcome"])
    if outcome in {"complete", "partial"}:
        content_hash = _sha256(
            observation.get("content_hash"), f"{context}.content_hash"
        )
        output_hashes = observation.get("output_hashes", [])
        if output_hashes and str(output_hashes[0]).lower() != content_hash:
            raise BenchmarkError(
                f"{context}.output_hashes[0] must equal content_hash for the recorded run"
            )
    return elapsed, peak_memory


def _candidate_pipeline_recipe(
    observation: Mapping[str, Any],
    document_id: str,
) -> Mapping[str, Any] | None:
    provenance = observation.get("provenance")
    if not isinstance(provenance, Mapping):
        return None
    recipe = provenance.get("pipeline_recipe")
    recipe_hash = provenance.get("pipeline_recipe_sha256")
    if recipe is None and recipe_hash is None:
        return None
    recipe_mapping = _mapping(
        recipe, f"candidate observation {document_id}.pipeline_recipe"
    )
    expected_hash = _sha256(
        recipe_hash,
        f"candidate observation {document_id}.pipeline_recipe_sha256",
    )
    actual_hash = _pipeline_recipe_identity(recipe_mapping)
    if actual_hash != expected_hash:
        raise BenchmarkError(
            f"candidate observation {document_id}.pipeline_recipe_sha256 does not "
            "match its declared pipeline recipe"
        )
    return recipe_mapping


def _candidate_runtime_identity_issues(
    runtime_value: Any,
    policy: Mapping[str, Any],
    document_id: str,
) -> list[str]:
    """Recompute candidate runtime validation from embedded evidence.

    ``runtime_identity.verified`` and ``runtime_identity.issues`` are candidate
    assertions, not evidence, and are intentionally ignored. This validation is
    deterministic and offline: the embedded attestation is content-addressed and
    checked against the persisted trust policy, but its hash is not represented
    as a signature or proof of who produced it.
    """

    context = f"candidate observation {document_id}.runtime_identity"
    if not isinstance(runtime_value, Mapping):
        return [f"{context} must be an object"]
    issues: list[str] = []
    if runtime_value.get("schema") != _RUNTIME_PROVENANCE_SCHEMA:
        issues.append(f"{context}.schema is unsupported")
    stages_value = runtime_value.get("stages")
    if not isinstance(stages_value, list) or not stages_value:
        issues.append(f"{context}.stages must be a non-empty array")
        return issues

    config_value = policy.get("document_processing_config")
    trust_value = policy.get("runtime_trust_policy")
    if not isinstance(config_value, Mapping):
        issues.append(f"{context} output policy has no processing configuration")
        return issues
    if not isinstance(trust_value, Mapping):
        issues.append(f"{context} output policy has no runtime trust policy")
        return issues
    config = config_value
    seen_run_ids: set[str] = set()
    heavy_stage_count = 0

    for index, stage_value in enumerate(stages_value):
        stage_context = f"{context}.stages[{index}]"
        if not isinstance(stage_value, Mapping):
            issues.append(f"{stage_context} must be an object")
            continue
        stage = cast("Mapping[str, Any]", stage_value)
        run_id_value = stage.get("processing_run_id")
        run_id = (
            run_id_value.strip()
            if isinstance(run_id_value, str) and run_id_value.strip()
            else None
        )
        if run_id is None:
            issues.append(f"{stage_context}.processing_run_id is missing")
        elif run_id in seen_run_ids:
            issues.append(f"{stage_context}.processing_run_id is duplicated")
        else:
            seen_run_ids.add(run_id)

        component_id = stage.get("component_id")
        if component_id == "docling-grobid-aligner":
            if stage.get("component_version") != "2":
                issues.append(f"{stage_context}.component_version is not pinned to 2")
            if stage.get("runtime_identity_required") is not False:
                issues.append(
                    f"{stage_context} must mark local alignment identity optional"
                )
            if stage.get("runtime_attestation") is not None:
                issues.append(
                    f"{stage_context} local alignment must not carry OCI attestation"
                )
            for field in (
                "component_invocation_id",
                "container_image",
                "container_digest",
                "runtime_attestation_sha256",
                "runtime_attestation_output_sha256",
                "runtime_attestation_observed_at",
            ):
                if stage.get(field) is not None:
                    issues.append(f"{stage_context}.{field} must be null")
            for field in ("component_versions", "model_versions", "model_hashes"):
                if stage.get(field) != {}:
                    issues.append(f"{stage_context}.{field} must be empty")
            continue
        if component_id not in _CANONICAL_COMPONENT_KEYS:
            issues.append(f"{stage_context}.component_id is unsupported")
            continue
        heavy_stage_count += 1
        if stage.get("runtime_identity_required") is not True:
            issues.append(f"{stage_context} did not require runtime identity")

        stage_trust_value = trust_value.get(component_id)
        if not isinstance(stage_trust_value, Mapping):
            issues.append(f"{stage_context} has no parser trust policy")
            continue
        stage_trust = stage_trust_value
        expected_reporter_id = stage_trust.get("expected_reporter_id")
        expected_source = stage_trust.get("expected_source")
        expected_schema = stage_trust.get("attestation_schema_version")
        expected_contract = (
            _OCR_ATTESTATION_CONTRACT
            if component_id == "ocrmypdf"
            else _REMOTE_ATTESTATION_CONTRACT
        )
        if stage_trust.get("reporter_configured") is not True:
            issues.append(f"{stage_context} runtime reporter was not configured")
        if not isinstance(expected_reporter_id, str) or not expected_reporter_id:
            issues.append(f"{stage_context} expected reporter ID is missing")
        if not isinstance(expected_source, str) or not expected_source:
            issues.append(f"{stage_context} expected source is missing")
        if expected_schema != _RUNTIME_ATTESTATION_SCHEMA:
            issues.append(f"{stage_context} attestation schema is not pinned")
        if stage_trust.get("attestation_contract_version") != expected_contract:
            issues.append(f"{stage_context} attestation contract is not pinned")
        if (
            component_id == "ocrmypdf"
            and stage_trust.get("local_digest_runner_version")
            != _OCR_ATTESTATION_CONTRACT
        ):
            issues.append(f"{stage_context} local digest runner version is not pinned")

        raw_attestation = stage.get("runtime_attestation")
        if not isinstance(raw_attestation, Mapping):
            issues.append(f"{stage_context}.runtime_attestation is missing")
            continue
        try:
            attestation = RuntimeAttestation.model_validate(dict(raw_attestation))
        except ValueError:
            issues.append(f"{stage_context}.runtime_attestation is invalid")
            continue

        if attestation.schema_version != expected_schema:
            issues.append(f"{stage_context} attestation schema differs from policy")
        if attestation.component_id != component_id:
            issues.append(f"{stage_context} attested parser does not match")
        if attestation.invocation_id != stage.get("component_invocation_id"):
            issues.append(f"{stage_context} attested invocation does not match")
        if attestation.reporter_id != expected_reporter_id:
            issues.append(f"{stage_context} attested reporter does not match policy")
        if attestation.source.value != expected_source:
            issues.append(f"{stage_context} attested source does not match policy")

        canonical_attestation = attestation.model_dump(mode="json")
        attestation_sha256 = configuration_sha256(canonical_attestation)
        declared_hashes: dict[str, str | None] = {}
        for field in (
            "runtime_attestation_sha256",
            "runtime_attestation_output_sha256",
        ):
            raw_digest = stage.get(field)
            try:
                declared_hashes[field] = _sha256(raw_digest, f"{stage_context}.{field}")
            except BenchmarkError:
                declared_hashes[field] = None
                issues.append(f"{stage_context}.{field} is not a SHA-256 digest")
        if any(
            digest is not None and digest != attestation_sha256
            for digest in declared_hashes.values()
        ):
            issues.append(
                f"{stage_context} attestation content hash/CAS binding does not match"
            )
        if (
            stage.get("runtime_attestation_observed_at")
            != canonical_attestation["observed_at"]
        ):
            issues.append(
                f"{stage_context} attestation observation time does not match"
            )

        mirrored_fields = {
            "component_version": attestation.component_version,
            "container_image": attestation.container_reference,
            "container_digest": attestation.container_digest,
            "component_versions": dict(attestation.component_versions),
            "model_versions": dict(attestation.model_versions),
            "model_hashes": dict(attestation.model_hashes),
        }
        for field, expected_value in mirrored_fields.items():
            observed_value = stage.get(field)
            if isinstance(expected_value, dict) and isinstance(observed_value, Mapping):
                observed_value = dict(observed_value)
            if observed_value != expected_value:
                issues.append(
                    f"{stage_context}.{field} was not sourced from attestation"
                )

        if component_id == "docling":
            expected_version = config.get("docling_version")
            expected_image = config.get("docling_container_image")
            expected_digest = config.get("docling_container_digest")
            expected_components = {
                "docling": expected_version,
                "docling_serve": config.get("docling_serve_version"),
            }
            expected_models = config.get("docling_model_versions", {})
            expected_model_hashes = config.get("docling_model_hashes", {})
        elif component_id == "grobid":
            expected_version = config.get("grobid_version")
            expected_image = config.get("grobid_container_image")
            expected_digest = config.get("grobid_container_digest")
            expected_components = {"grobid": expected_version}
            expected_models = config.get("grobid_model_versions", {})
            expected_model_hashes = config.get("grobid_model_hashes", {})
        else:
            expected_version = config.get("ocrmypdf_version")
            expected_image = config.get("ocr_container_image")
            expected_digest = config.get("ocr_container_digest")
            expected_components = {"ocrmypdf": expected_version}
            expected_models = {}
            expected_model_hashes = {}

        if not isinstance(expected_models, Mapping):
            issues.append(f"{stage_context} model version policy is malformed")
            expected_models = {}
        if not isinstance(expected_model_hashes, Mapping):
            issues.append(f"{stage_context} model hash policy is malformed")
            expected_model_hashes = {}

        if attestation.component_version != expected_version:
            issues.append(f"{stage_context} parser version differs from policy")
        expected_reference = (
            f"{str(expected_image).split('@', maxsplit=1)[0]}@{expected_digest}"
            if isinstance(expected_image, str)
            and expected_image
            and isinstance(expected_digest, str)
            and expected_digest
            else None
        )
        if attestation.container_reference != expected_reference:
            issues.append(f"{stage_context} container reference differs from policy")
        if attestation.container_digest != expected_digest:
            issues.append(f"{stage_context} container digest differs from policy")
        for component in _CANONICAL_COMPONENT_KEYS[component_id]:
            expected_component = expected_components.get(component)
            if (
                not isinstance(expected_component, str)
                or not expected_component
                or attestation.component_versions.get(component) != expected_component
            ):
                issues.append(
                    f"{stage_context} component {component!r} differs from policy"
                )
        if dict(attestation.model_versions) != dict(expected_models):
            issues.append(f"{stage_context} model versions differ from policy")
        if dict(attestation.model_hashes) != dict(expected_model_hashes):
            issues.append(f"{stage_context} model hashes differ from policy")

    if heavy_stage_count == 0:
        issues.append(f"{context}.stages contains no attested parser invocation")
    return issues


def _baseline_memory_environment(
    observation: Mapping[str, Any], document_id: str
) -> dict[str, str]:
    """Return a comparable per-boundary environment map or raise explicitly."""

    context = f"candidate observation {document_id!r}.resource_accounting"
    provenance = _mapping(observation.get("provenance"), f"{context}.provenance")
    accounting = _mapping(provenance.get("resource_accounting"), context)
    if accounting.get("memory_scope") != _MEMORY_SCOPE:
        raise BenchmarkError(f"{context}.memory_scope must be {_MEMORY_SCOPE!r}")
    if accounting.get("memory_baseline_comparable") is not True:
        raise BenchmarkError(
            f"{context} requires isolated cgroup-v2 peak measurements for every "
            "heavy parser stage"
        )
    required_ids_value = accounting.get("memory_required_run_ids")
    if not isinstance(required_ids_value, list) or not required_ids_value:
        raise BenchmarkError(
            f"{context}.memory_required_run_ids must be a non-empty array"
        )
    required_ids = {
        _string(value, f"{context}.memory_required_run_ids")
        for value in required_ids_value
    }
    if len(required_ids) != len(required_ids_value):
        raise BenchmarkError(f"{context}.memory_required_run_ids contains duplicates")
    records = accounting.get("memory_measurements")
    if not isinstance(records, list) or not records:
        raise BenchmarkError(f"{context}.memory_measurements must be a non-empty array")
    measured_ids: set[str] = set()
    for index, record_value in enumerate(records):
        record = _mapping(record_value, f"{context}.memory_measurements[{index}]")
        measured_ids.add(
            _string(
                record.get("processing_run_id"),
                f"{context}.memory_measurements[{index}].processing_run_id",
            )
        )
        measurement = _mapping(
            record.get("measurement"),
            f"{context}.memory_measurements[{index}].measurement",
        )
        try:
            parsed_measurement = MemoryMeasurement.model_validate(measurement)
        except ValueError as exc:
            raise BenchmarkError(
                f"{context}.memory_measurements[{index}] is invalid"
            ) from exc
        if not parsed_measurement.baseline_comparable:
            raise BenchmarkError(
                f"{context}.memory_measurements[{index}] is not baseline-comparable"
            )
    if measured_ids != required_ids or len(measured_ids) != len(records):
        raise BenchmarkError(
            f"{context}.memory_measurements must cover every required run exactly once"
        )
    raw_environment = _mapping(
        accounting.get("memory_environment_by_boundary"),
        f"{context}.memory_environment_by_boundary",
    )
    if not raw_environment:
        raise BenchmarkError(f"{context} has no memory environment identities")
    environment: dict[str, str] = {}
    for boundary, values in raw_environment.items():
        key = _string(boundary, f"{context}.memory_environment_by_boundary key")
        if not isinstance(values, list) or len(values) != 1:
            raise BenchmarkError(
                f"{context}.memory_environment_by_boundary[{key!r}] must have one hash"
            )
        environment[key] = _sha256(
            values[0], f"{context}.memory_environment_by_boundary[{key!r}][0]"
        )
    return environment


def _merge_baseline_memory_environment(
    combined: dict[str, str],
    observed: Mapping[str, str],
    *,
    context: str,
) -> None:
    """Union conditional parser boundaries while rejecting actual drift."""

    conflicts = {
        boundary: (combined[boundary], digest)
        for boundary, digest in observed.items()
        if boundary in combined and combined[boundary] != digest
    }
    if conflicts:
        details = ", ".join(
            f"{boundary!r}: {old} != {new}"
            for boundary, (old, new) in sorted(conflicts.items())
        )
        raise BenchmarkError(
            f"{context} has conflicting memory environments for the same boundary: "
            f"{details}"
        )
    combined.update(observed)


def _check_document_sets(
    expected_ids: set[str],
    observations: Mapping[str, Any],
    label: str,
) -> None:
    actual_ids = set(observations)
    missing = sorted(expected_ids - actual_ids)
    extra = sorted(actual_ids - expected_ids)
    if missing or extra:
        details: list[str] = []
        if missing:
            details.append(f"missing {missing}")
        if extra:
            details.append(f"unexpected {extra}")
        raise BenchmarkError(
            f"{label} document ids do not match manifest: {'; '.join(details)}"
        )


def _resolve_reference_path(manifest: Mapping[str, Any], manifest_path: Path) -> Path:
    observation_sets = _mapping(
        manifest.get("observation_sets", {}), "manifest.observation_sets"
    )
    if "reference" not in observation_sets:
        raise BenchmarkError(
            "reference observations were not supplied and "
            "manifest.observation_sets.reference is absent"
        )
    descriptor = _validate_descriptor(
        observation_sets["reference"], "manifest.observation_sets.reference"
    )
    return _verify_descriptor(
        _artifact_root(manifest, manifest_path),
        descriptor,
        "manifest.observation_sets.reference",
    )


def run_benchmark(
    manifest_path: str | Path,
    candidate_observations: str | Path,
    reference_observations: str | Path | None = None,
    *,
    enforce_baseline: bool = False,
) -> dict[str, Any]:
    """Compare one parser observation set with the reference corpus offline."""

    resolved_manifest_path = Path(manifest_path).expanduser().resolve()
    manifest = load_manifest(
        resolved_manifest_path,
        enforce_baseline=enforce_baseline,
        verify_artifacts=True,
    )
    candidate_path = Path(candidate_observations).expanduser().resolve()
    reference_path = (
        Path(reference_observations).expanduser().resolve()
        if reference_observations is not None
        else _resolve_reference_path(manifest, resolved_manifest_path)
    )
    candidates = load_observations(candidate_path)
    references = load_observations(reference_path)

    documents = sorted(manifest["documents"], key=lambda document: document["id"])
    expected_ids = {str(document["id"]) for document in documents}
    _check_document_sets(expected_ids, candidates, "candidate observations")
    _check_document_sets(expected_ids, references, "reference observations")

    allowed_outcomes = set(
        manifest.get("allowed_outcomes", ["complete", "partial", "quarantined"])
    )
    document_reports: list[dict[str, Any]] = []
    outcomes: dict[str, int] = dict.fromkeys(OUTCOMES, 0)
    parser_identities: set[tuple[str, str, str]] = set()
    metric_values: dict[str, list[float]] = {metric: [] for metric in QUALITY_METRICS}
    total_elapsed = 0.0
    total_characters = 0
    memory_values: list[int] = []
    baseline_memory_environment: dict[str, str] = {}
    total_located = 0
    total_locator_items = 0

    for document in documents:
        document_id = str(document["id"])
        candidate = candidates[document_id]
        reference = references[document_id]
        elapsed, peak_memory = _candidate_requirements(candidate, document_id)
        parser = _mapping(
            candidate["parser"], f"candidate observation {document_id}.parser"
        )
        parser_identity = (
            str(parser["name"]),
            str(parser["version"]),
            str(parser["configuration_hash"]).lower(),
        )
        parser_identities.add(parser_identity)
        pipeline_recipe = _candidate_pipeline_recipe(candidate, document_id)

        candidate_text = str(candidate.get("text", ""))
        reference_text = str(reference.get("text", ""))
        located, locator_items = _locator_counts(candidate)
        locator_score = (
            located / locator_items
            if locator_items
            else (1.0 if not _normalize_text(candidate_text) else 0.0)
        )
        determinism = _determinism_score(candidate)
        scores: dict[str, float | None] = {
            "text_fidelity": _multiset_f1(
                _tokens(candidate_text), _tokens(reference_text)
            ),
            "reading_order": _reading_order_score(
                candidate.get("reading_order", []),
                reference.get("reading_order", []),
            ),
            "headings": _multiset_f1(
                _heading_signatures(candidate), _heading_signatures(reference)
            ),
            "tables": _applicable_multiset_f1(
                _table_signatures(candidate), _table_signatures(reference)
            ),
            "figure_caption_association": _applicable_multiset_f1(
                _figure_signatures(candidate), _figure_signatures(reference)
            ),
            "references": _multiset_f1(
                _reference_signatures(candidate), _reference_signatures(reference)
            ),
            "locator_coverage": locator_score,
            "determinism": determinism,
        }
        for metric, value in scores.items():
            if value is not None:
                metric_values[metric].append(value)

        outcome = str(candidate["outcome"])
        outcomes[outcome] += 1
        violations: list[str] = []
        if outcome not in allowed_outcomes:
            violations.append(f"outcome {outcome!r} is not allowed")
        if (
            outcome in {"complete", "partial"}
            and _normalize_text(reference_text)
            and not _normalize_text(candidate_text)
        ):
            violations.append(
                "successful parse is empty while reference text is non-empty"
            )
        if enforce_baseline:
            if pipeline_recipe is None:
                violations.append(
                    "baseline requires a declared static output-policy snapshot and hash"
                )
            elif pipeline_recipe.get("schema") != _OUTPUT_POLICY_SCHEMA:
                violations.append(
                    "baseline requires a persisted full output-policy snapshot; "
                    "legacy inferred recipes are not accepted"
                )
            elif _pipeline_recipe_identity(pipeline_recipe) != parser_identity[2]:
                violations.append(
                    "parser.configuration_hash must equal the declared static "
                    "output-policy hash"
                )
            provenance = candidate.get("provenance")
            runtime = (
                provenance.get("runtime_identity")
                if isinstance(provenance, Mapping)
                else None
            )
            if not isinstance(runtime, Mapping):
                violations.append(
                    "baseline requires persisted executed runtime identity provenance"
                )
            else:
                runtime_issues = _candidate_runtime_identity_issues(
                    runtime,
                    pipeline_recipe or {},
                    document_id,
                )
                if runtime_issues:
                    violations.append(
                        "baseline runtime identity is incomplete or does not match the "
                        "declared output policy: " + "; ".join(runtime_issues)
                    )
            if elapsed <= 0:
                violations.append("baseline requires positive measured elapsed_seconds")
            if peak_memory is None:
                violations.append(
                    "baseline requires measured peak_memory_bytes for every heavy "
                    "parser stage"
                )
            try:
                environment = _baseline_memory_environment(candidate, document_id)
                _merge_baseline_memory_environment(
                    baseline_memory_environment,
                    environment,
                    context="baseline evaluation",
                )
            except BenchmarkError as exc:
                violations.append(str(exc))
            unmeasured_metrics = [
                metric
                for metric, value in scores.items()
                if value is None
                and metric not in {"tables", "figure_caption_association"}
            ]
            if unmeasured_metrics:
                violations.append(
                    "baseline requires every quality metric to be measured; "
                    f"missing {sorted(unmeasured_metrics)}. For determinism, run "
                    "the complete pipeline independently at least twice and supply "
                    "one output hash per end-to-end repeat."
                )

        character_count = len(candidate_text)
        characters_per_second = character_count / elapsed if elapsed > 0 else None
        total_elapsed += elapsed
        total_characters += character_count
        if peak_memory is not None:
            memory_values.append(peak_memory)
        total_located += located
        total_locator_items += locator_items
        document_reports.append(
            {
                "document_id": document_id,
                "categories": sorted(document["categories"]),
                "outcome": outcome,
                "parser": {
                    "name": parser_identity[0],
                    "version": parser_identity[1],
                    "configuration_hash": parser_identity[2],
                },
                "scores": {
                    metric: _rounded(scores[metric]) for metric in QUALITY_METRICS
                },
                "not_applicable_metrics": sorted(
                    metric for metric, value in scores.items() if value is None
                ),
                "performance": {
                    "elapsed_seconds": _rounded(elapsed),
                    "characters": character_count,
                    "characters_per_second": _rounded(characters_per_second),
                    "peak_memory_bytes": peak_memory,
                },
                "locator_items": {"located": located, "total": locator_items},
                "passed": not violations,
                "violations": violations,
            }
        )

    score_summary: dict[str, dict[str, Any]] = {}
    for metric in QUALITY_METRICS:
        values = metric_values[metric]
        aggregate = sum(values) / len(values) if values else None
        if metric == "locator_coverage":
            aggregate = (
                total_located / total_locator_items
                if total_locator_items
                else (sum(values) / len(values) if values else None)
            )
        score_summary[metric] = {
            "aggregate": _rounded(aggregate),
            "mean": _rounded(sum(values) / len(values)) if values else None,
            "minimum": _rounded(min(values)) if values else None,
            "measured_documents": len(values),
            "not_applicable_documents": len(document_reports) - len(values),
        }

    document_count = len(document_reports)
    performance = {
        "documents_per_second": _rounded(
            document_count / total_elapsed if total_elapsed > 0 else None
        ),
        "characters_per_second": _rounded(
            total_characters / total_elapsed if total_elapsed > 0 else None
        ),
        "total_elapsed_seconds": _rounded(total_elapsed),
        "mean_elapsed_seconds": _rounded(total_elapsed / document_count),
        "peak_memory_bytes": max(memory_values) if memory_values else None,
        "mean_peak_memory_bytes": _rounded(
            sum(memory_values) / len(memory_values) if memory_values else None
        ),
        "measured_peak_memory_documents": len(memory_values),
    }

    violations: list[str] = []
    if enforce_baseline and len(parser_identities) != 1:
        violations.append(
            "baseline requires one exact parser name/version/recipe configuration "
            f"identity across all documents; found {len(parser_identities)}"
        )
    if enforce_baseline:
        optional_metrics = {"tables", "figure_caption_association"}
        incomplete_metrics = [
            metric
            for metric, summary in score_summary.items()
            if (
                metric not in optional_metrics
                and summary["measured_documents"] != document_count
            )
            or (metric in optional_metrics and summary["measured_documents"] == 0)
        ]
        if incomplete_metrics:
            violations.append(
                "baseline requires complete required-metric coverage and at least "
                "one applicable table/figure document; "
                f"incomplete {sorted(incomplete_metrics)}"
            )
        if len(memory_values) != document_count:
            violations.append(
                "baseline requires measured peak memory for every document; "
                f"measured {len(memory_values)} of {document_count}"
            )
    thresholds = _mapping(manifest.get("thresholds", {}), "manifest.thresholds")
    for metric in sorted(thresholds):
        threshold = float(thresholds[metric])
        actual = score_summary[metric]["aggregate"]
        if actual is None:
            violations.append(
                f"quality threshold {metric}={threshold} cannot be evaluated: not measured"
            )
        elif actual < threshold:
            violations.append(
                f"quality threshold {metric}={threshold} not met: {actual}"
            )

    limits = _mapping(
        manifest.get("performance_limits", {}), "manifest.performance_limits"
    )
    limit_mapping = {
        "min_documents_per_second": ("documents_per_second", "minimum"),
        "min_characters_per_second": ("characters_per_second", "minimum"),
        "max_peak_memory_bytes": ("peak_memory_bytes", "maximum"),
    }
    for limit_name in sorted(limits):
        performance_name, direction = limit_mapping[limit_name]
        actual = performance[performance_name]
        expected = float(limits[limit_name])
        if actual is None:
            violations.append(
                f"performance limit {limit_name}={expected} cannot be evaluated"
            )
        elif direction == "minimum" and actual < expected:
            violations.append(
                f"performance limit {limit_name}={expected} not met: {actual}"
            )
        elif direction == "maximum" and actual > expected:
            violations.append(
                f"performance limit {limit_name}={expected} exceeded: {actual}"
            )

    operational_failures = [
        report["document_id"] for report in document_reports if not report["passed"]
    ]
    if operational_failures:
        violations.append(
            f"documents failed operational checks: {sorted(operational_failures)}"
        )

    return {
        "schema_version": REPORT_SCHEMA_VERSION,
        "manifest": {
            "name": manifest["name"],
            "schema_version": manifest["schema_version"],
            "sha256": _sha256_path(resolved_manifest_path),
            "baseline_enforced": enforce_baseline,
            "document_count": document_count,
        },
        "inputs": {
            "candidate_observations_sha256": _sha256_path(candidate_path),
            "reference_observations_sha256": _sha256_path(reference_path),
        },
        "parsers": [
            {
                "name": name,
                "version": version,
                "configuration_hash": configuration_hash,
            }
            for name, version, configuration_hash in sorted(parser_identities)
        ],
        "summary": {
            "scores": score_summary,
            "outcomes": outcomes,
            "performance": performance,
            "passed_documents": document_count - len(operational_failures),
            "failed_documents": len(operational_failures),
        },
        "documents": document_reports,
        "passed": not violations,
        "violations": violations,
    }
