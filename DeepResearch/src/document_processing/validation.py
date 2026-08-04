"""Parser-output validation, deterministic hashing, and evidence span creation."""

from __future__ import annotations

import json
import math
from dataclasses import dataclass
from enum import StrEnum
from typing import Any, Literal, cast

from .adapters import NativeTextLocator
from .alignment import AlignmentRecord, AlignmentStatus, ScholarlyAlignmentOverlay
from .models import (
    BioCLocator,
    ContentSpan,
    DoclingInputFormat,
    DoclingItemLocator,
    JatsLocator,
    PdfBoundingBox,
    PdfLocator,
    RepresentationAnchor,
    sha256_bytes,
)


class QualitySeverity(StrEnum):
    WARNING = "warning"
    ERROR = "error"


class ContentIntegrityKind(StrEnum):
    TABLE = "table"
    FIGURE = "figure"
    CITATION = "citation"


class ContentIntegrityStatus(StrEnum):
    RESOLVED = "resolved"
    UNALIGNED = "unaligned"


@dataclass(frozen=True, slots=True)
class QualityIssue:
    code: str
    message: str
    severity: QualitySeverity
    item_ref: str | None = None
    page_number: int | None = None


@dataclass(frozen=True, slots=True)
class DoclingQualityReport:
    content_sha256: str
    text_item_count: int
    located_text_item_count: int
    locator_coverage: float
    reference_count: int
    broken_reference_count: int
    issues: tuple[QualityIssue, ...]

    @property
    def acceptable(self) -> bool:
        return not any(issue.severity is QualitySeverity.ERROR for issue in self.issues)


@dataclass(frozen=True, slots=True)
class ContentIntegrityRecord:
    """One explicit table, figure, or citation relationship outcome."""

    record_id: str
    kind: ContentIntegrityKind
    status: ContentIntegrityStatus
    source_ref: str
    source_docling_item_ref: str | None
    declared_target_refs: tuple[str, ...]
    resolved_docling_item_refs: tuple[str, ...]
    unresolved_target_refs: tuple[str, ...]
    reason_codes: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "record_id": self.record_id,
            "kind": self.kind.value,
            "status": self.status.value,
            "source_ref": self.source_ref,
            "source_docling_item_ref": self.source_docling_item_ref,
            "declared_target_refs": list(self.declared_target_refs),
            "resolved_docling_item_refs": list(self.resolved_docling_item_refs),
            "unresolved_target_refs": list(self.unresolved_target_refs),
            "reason_codes": list(self.reason_codes),
        }


@dataclass(frozen=True, slots=True)
class ContentIntegrityReport:
    """Non-destructive integrity overlay for Docling and GROBID relationships."""

    document_sha256: str
    records: tuple[ContentIntegrityRecord, ...]
    issues: tuple[QualityIssue, ...]
    scholarly_overlay_present: bool

    @property
    def resolved_count(self) -> int:
        return sum(
            record.status is ContentIntegrityStatus.RESOLVED for record in self.records
        )

    @property
    def unaligned_count(self) -> int:
        return len(self.records) - self.resolved_count

    def to_dict(self) -> dict[str, Any]:
        return {
            "document_sha256": self.document_sha256,
            "scholarly_overlay_present": self.scholarly_overlay_present,
            "resolved_count": self.resolved_count,
            "unaligned_count": self.unaligned_count,
            "records": [record.to_dict() for record in self.records],
            "issues": [
                {
                    "code": issue.code,
                    "message": issue.message,
                    "severity": issue.severity.value,
                    "item_ref": issue.item_ref,
                    "page_number": issue.page_number,
                }
                for issue in self.issues
            ],
        }


@dataclass(frozen=True, slots=True)
class JatsLocatorAlignmentRecord:
    locator_id: str
    locator_index: int
    content_sha256: str
    xml_id: str | None
    xpath: str | None
    status: str
    docling_item_ref: str | None = None
    content_span_id: str | None = None
    match_method: str | None = None
    reason: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "locator_id": self.locator_id,
            "locator_index": self.locator_index,
            "content_sha256": self.content_sha256,
            "xml_id": self.xml_id,
            "xpath": self.xpath,
            "status": self.status,
            "docling_item_ref": self.docling_item_ref,
            "content_span_id": self.content_span_id,
            "match_method": self.match_method,
            "reason": self.reason,
        }


@dataclass(frozen=True, slots=True)
class JatsContentSpanAlignment:
    spans: tuple[ContentSpan, ...]
    records: tuple[JatsLocatorAlignmentRecord, ...]

    @property
    def aligned_count(self) -> int:
        return sum(record.status == "aligned" for record in self.records)

    @property
    def unaligned_count(self) -> int:
        return sum(record.status == "unaligned" for record in self.records)


@dataclass(frozen=True, slots=True)
class BioCLocatorAlignmentRecord:
    """Explicit alignment outcome for one native BioC passage locator."""

    locator_id: str
    locator_index: int
    content_sha256: str
    document_index: int | None
    document_id: str | None
    passage_index: int | None
    sentence_index: int | None
    offset: int | None
    length: int | None
    status: str
    docling_item_ref: str | None = None
    content_span_id: str | None = None
    match_method: str | None = None
    reason: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "locator_id": self.locator_id,
            "locator_index": self.locator_index,
            "content_sha256": self.content_sha256,
            "document_index": self.document_index,
            "document_id": self.document_id,
            "passage_index": self.passage_index,
            "sentence_index": self.sentence_index,
            "offset": self.offset,
            "length": self.length,
            "status": self.status,
            "docling_item_ref": self.docling_item_ref,
            "content_span_id": self.content_span_id,
            "match_method": self.match_method,
            "reason": self.reason,
        }


@dataclass(frozen=True, slots=True)
class BioCContentSpanAlignment:
    """BioC evidence spans plus one explicit outcome per native locator."""

    spans: tuple[ContentSpan, ...]
    records: tuple[BioCLocatorAlignmentRecord, ...]

    @property
    def aligned_count(self) -> int:
        return sum(record.status == "aligned" for record in self.records)

    @property
    def unaligned_count(self) -> int:
        return sum(record.status == "unaligned" for record in self.records)


class DoclingQualityValidator:
    """Enforce evidence-locator and internal-reference guarantees."""

    def __init__(self, minimum_pdf_locator_coverage: float = 0.95) -> None:
        if not 0.95 <= minimum_pdf_locator_coverage <= 1:
            raise ValueError("minimum_pdf_locator_coverage must be between 0.95 and 1")
        self.minimum_pdf_locator_coverage = minimum_pdf_locator_coverage

    def validate(
        self,
        document: dict[str, Any],
        *,
        require_pdf_geometry: bool,
    ) -> DoclingQualityReport:
        issues: list[QualityIssue] = []
        if document.get("schema_name") != "DoclingDocument":
            issues.append(
                QualityIssue(
                    code="INVALID_DOCLING_SCHEMA",
                    message="Serialized output does not identify itself as DoclingDocument",
                    severity=QualitySeverity.ERROR,
                )
            )

        texts = document.get("texts")
        if not isinstance(texts, list):
            texts = []
            issues.append(
                QualityIssue(
                    code="MISSING_TEXT_COLLECTION",
                    message="DoclingDocument has no text collection",
                    severity=QualitySeverity.ERROR,
                )
            )

        text_items: list[tuple[int, dict[str, Any]]] = []
        for index, item in enumerate(texts):
            if not isinstance(item, dict):
                issues.append(_malformed_content_entry_issue("texts", index, item))
                continue
            text_items.append((index, cast("dict[str, Any]", item)))

        for collection_name in ("tables", "pictures"):
            collection = document.get(collection_name)
            if collection is None:
                continue
            if not isinstance(collection, list):
                issues.append(
                    QualityIssue(
                        code="MALFORMED_DOCLING_CONTENT_COLLECTION",
                        message=(
                            f"Docling {collection_name} collection must be a list"
                        ),
                        severity=QualitySeverity.ERROR,
                        item_ref=f"#/{collection_name}",
                    )
                )
                continue
            for index, item in enumerate(collection):
                if not isinstance(item, dict):
                    issues.append(
                        _malformed_content_entry_issue(collection_name, index, item)
                    )
        nonempty_text_item_count = 0
        located = 0
        for index, item in text_items:
            item_ref = _item_ref(item, "texts", index)
            text = item.get("text")
            has_nonempty_text = isinstance(text, str) and bool(text.strip())
            if not has_nonempty_text:
                issues.append(
                    QualityIssue(
                        code="EMPTY_TEXT_ITEM",
                        message="Textual Docling item has no text",
                        severity=QualitySeverity.WARNING,
                        item_ref=item_ref,
                    )
                )
            else:
                nonempty_text_item_count += 1
            if require_pdf_geometry and isinstance(text, str):
                valid_provenance, provenance_issues = _validated_pdf_provenance(
                    document,
                    item,
                    item_ref=item_ref,
                    text_length=len(text),
                )
                issues.extend(provenance_issues)
                if valid_provenance:
                    located += 1
                elif has_nonempty_text:
                    issues.append(
                        QualityIssue(
                            code="PDF_TEXT_ITEM_LOCATOR_MISSING",
                            message=(
                                "Non-empty PDF text item has no valid "
                                "page/bounding-box provenance"
                            ),
                            severity=QualitySeverity.WARNING,
                            item_ref=item_ref,
                        )
                    )

        coverage = located / len(texts) if texts else 0.0
        if require_pdf_geometry and coverage < self.minimum_pdf_locator_coverage:
            issues.append(
                QualityIssue(
                    code="PDF_LOCATOR_COVERAGE_BELOW_THRESHOLD",
                    message=(
                        f"{coverage:.1%} of PDF text items have valid page/bounding-box "
                        f"provenance; required {self.minimum_pdf_locator_coverage:.1%}"
                    ),
                    severity=QualitySeverity.ERROR,
                )
            )

        refs, broken_refs = _validate_references(document)
        issues.extend(_reference_definition_issues(document))
        for item_ref in broken_refs:
            issues.append(
                QualityIssue(
                    code="BROKEN_DOCLING_REFERENCE",
                    message="Docling parent/child reference does not resolve",
                    severity=QualitySeverity.ERROR,
                    item_ref=item_ref,
                )
            )

        if not texts:
            issues.append(
                QualityIssue(
                    code="NO_TEXT_ITEMS",
                    message="Conversion produced no textual items",
                    severity=QualitySeverity.ERROR,
                )
            )
        elif nonempty_text_item_count == 0:
            issues.append(
                QualityIssue(
                    code="NO_NONEMPTY_TEXT_ITEMS",
                    message="Conversion produced no non-empty textual items",
                    severity=QualitySeverity.ERROR,
                )
            )
        try:
            content_sha256 = docling_document_sha256(document)
        except ValueError:
            issues.append(
                QualityIssue(
                    code="NON_CANONICAL_DOCLING_NUMBER",
                    message=(
                        "DoclingDocument contains a non-finite number and cannot be "
                        "encoded as canonical JSON"
                    ),
                    severity=QualitySeverity.ERROR,
                )
            )
            content_sha256 = sha256_bytes(
                json.dumps(
                    document,
                    ensure_ascii=False,
                    allow_nan=True,
                    sort_keys=True,
                    separators=(",", ":"),
                ).encode("utf-8")
            )
        return DoclingQualityReport(
            content_sha256=content_sha256,
            text_item_count=len(texts),
            located_text_item_count=located,
            locator_coverage=coverage,
            reference_count=refs,
            broken_reference_count=len(broken_refs),
            issues=tuple(issues),
        )


def docling_document_sha256(document: dict[str, Any]) -> str:
    """Hash a serialized DoclingDocument using canonical JSON encoding."""

    encoded = json.dumps(
        document,
        ensure_ascii=False,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return sha256_bytes(encoded)


@dataclass(frozen=True, slots=True)
class _IndexedDoclingItem:
    collection: str
    index: int
    value: dict[str, Any]


@dataclass(frozen=True, slots=True)
class _PdfPageGeometry:
    width: float | None
    height: float | None


@dataclass(frozen=True, slots=True)
class _ValidatedPdfProvenance:
    locator: PdfLocator
    character_span: tuple[int, int]


@dataclass(frozen=True, slots=True)
class _TextCandidate:
    canonical_ref: str
    item_ref: str
    text: str
    normalized_text: str


def validate_content_integrity(
    document: dict[str, Any],
    *,
    scholarly_overlay: ScholarlyAlignmentOverlay | None = None,
) -> ContentIntegrityReport:
    """Build a deterministic overlay without modifying ``DoclingDocument``.

    One record is emitted for every item in the Docling ``tables`` and
    ``pictures`` collections. When a scholarly overlay is supplied, one more
    record is emitted for every GROBID bibliographic ``ref``. A relationship is
    resolved only when every declared target resolves uniquely to an existing
    Docling item. All other outcomes remain explicit and retain their declared
    targets and machine-readable reasons.
    """

    item_index = _build_docling_item_index(document)
    records = [
        *_docling_caption_integrity_records(
            document,
            item_index,
            collection="tables",
            kind=ContentIntegrityKind.TABLE,
        ),
        *_docling_caption_integrity_records(
            document,
            item_index,
            collection="pictures",
            kind=ContentIntegrityKind.FIGURE,
        ),
    ]
    if scholarly_overlay is not None:
        records.extend(_citation_integrity_records(item_index, scholarly_overlay))
    collection_issues = _content_collection_issues(document)
    record_issues = tuple(
        _integrity_issue(record)
        for record in records
        if record.status is ContentIntegrityStatus.UNALIGNED
    )
    return ContentIntegrityReport(
        document_sha256=docling_document_sha256(document),
        records=tuple(records),
        issues=(*collection_issues, *record_issues),
        scholarly_overlay_present=scholarly_overlay is not None,
    )


def _build_docling_item_index(
    document: dict[str, Any],
) -> dict[str, tuple[_IndexedDoclingItem, ...]]:
    mutable_index: dict[str, list[_IndexedDoclingItem]] = {}
    for collection in ("texts", "tables", "pictures"):
        values = document.get(collection)
        if not isinstance(values, list):
            continue
        for index, value in enumerate(values):
            if not isinstance(value, dict):
                continue
            item = cast("dict[str, Any]", value)
            indexed_item = _IndexedDoclingItem(collection, index, item)
            canonical_ref = f"#/{collection}/{index}"
            mutable_index.setdefault(canonical_ref, []).append(indexed_item)
            self_ref = item.get("self_ref")
            if isinstance(self_ref, str) and self_ref and self_ref != canonical_ref:
                mutable_index.setdefault(self_ref, []).append(indexed_item)
    return {key: tuple(value) for key, value in mutable_index.items()}


def _content_collection_issues(
    document: dict[str, Any],
) -> tuple[QualityIssue, ...]:
    issues: list[QualityIssue] = []
    for collection, kind in (
        ("tables", ContentIntegrityKind.TABLE),
        ("pictures", ContentIntegrityKind.FIGURE),
    ):
        if collection not in document:
            issues.append(
                QualityIssue(
                    code=f"MISSING_{collection.upper()}_COLLECTION",
                    message=(
                        f"DoclingDocument has no {collection} collection; "
                        f"{kind.value} integrity could not be enumerated"
                    ),
                    severity=QualitySeverity.ERROR,
                )
            )
        elif not isinstance(document[collection], list):
            issues.append(
                QualityIssue(
                    code=f"INVALID_{collection.upper()}_COLLECTION",
                    message=(
                        f"DoclingDocument {collection} collection is not a list; "
                        f"{kind.value} integrity could not be enumerated"
                    ),
                    severity=QualitySeverity.ERROR,
                )
            )
    return tuple(issues)


def _docling_caption_integrity_records(
    document: dict[str, Any],
    item_index: dict[str, tuple[_IndexedDoclingItem, ...]],
    *,
    collection: str,
    kind: ContentIntegrityKind,
) -> tuple[ContentIntegrityRecord, ...]:
    values = document.get(collection)
    if not isinstance(values, list):
        return ()

    records: list[ContentIntegrityRecord] = []
    for index, value in enumerate(values):
        fallback_ref = f"#/{collection}/{index}"
        if not isinstance(value, dict):
            records.append(
                _make_integrity_record(
                    kind=kind,
                    source_ref=fallback_ref,
                    source_docling_item_ref=None,
                    reason_codes=("invalid_docling_item",),
                )
            )
            continue

        item = cast("dict[str, Any]", value)
        source_ref = fallback_ref
        declared_source_ref = _item_ref(item, collection, index)
        reasons: list[str] = []
        declared_targets: list[str] = []
        resolved_targets: list[str] = []
        unresolved_targets: list[str] = []
        source_matches = item_index.get(declared_source_ref, ())
        source_docling_item_ref: str | None = declared_source_ref
        if len(source_matches) != 1:
            source_docling_item_ref = None
            reasons.append("duplicate_source_ref")

        captions = item.get("captions")
        if captions is None:
            captions = []
        if not isinstance(captions, list):
            reasons.append("malformed_caption_collection")
            unresolved_targets.append(f"{fallback_ref}/captions")
        elif not captions:
            reasons.append("missing_caption_reference")
        else:
            for caption_index, caption in enumerate(captions):
                malformed_ref = f"{fallback_ref}/captions/{caption_index}"
                if not isinstance(caption, dict):
                    reasons.append("malformed_caption_reference")
                    unresolved_targets.append(malformed_ref)
                    continue
                target = caption.get("$ref")
                if not isinstance(target, str) or not target:
                    reasons.append("malformed_caption_reference")
                    unresolved_targets.append(malformed_ref)
                    continue

                declared_targets.append(target)
                target_matches = item_index.get(target, ())
                if not target_matches:
                    reasons.append("caption_target_not_found")
                    unresolved_targets.append(target)
                    continue
                if len(target_matches) != 1:
                    reasons.append("caption_target_ambiguous")
                    unresolved_targets.append(target)
                    continue
                target_item = target_matches[0]
                if (
                    target_item.collection != "texts"
                    or target_item.value.get("label") != "caption"
                ):
                    reasons.append("caption_target_not_caption")
                    unresolved_targets.append(target)
                    continue
                resolved_targets.append(target)

        records.append(
            _make_integrity_record(
                kind=kind,
                source_ref=source_ref,
                source_docling_item_ref=source_docling_item_ref,
                declared_target_refs=tuple(declared_targets),
                resolved_docling_item_refs=tuple(resolved_targets),
                unresolved_target_refs=tuple(unresolved_targets),
                reason_codes=_unique(reasons),
            )
        )
    return tuple(records)


def _citation_integrity_records(
    item_index: dict[str, tuple[_IndexedDoclingItem, ...]],
    overlay: ScholarlyAlignmentOverlay,
) -> tuple[ContentIntegrityRecord, ...]:
    bibliography: dict[str, list[AlignmentRecord]] = {}
    for record in overlay.records:
        annotation = record.annotation
        if annotation.kind == "biblStruct" and annotation.xml_id:
            bibliography.setdefault(annotation.xml_id, []).append(record)

    records: list[ContentIntegrityRecord] = []
    for alignment_record in overlay.records:
        annotation = alignment_record.annotation
        if annotation.kind != "ref":
            continue
        if annotation.ref_type is not None and annotation.ref_type.casefold() != "bibr":
            continue

        reasons: list[str] = []
        source_docling_item_ref: str | None = None
        if alignment_record.status is not AlignmentStatus.ALIGNED:
            reasons.append("citation_source_unaligned")
        elif alignment_record.docling_item_ref is None:
            reasons.append("citation_source_missing_docling_ref")
        else:
            source_matches = item_index.get(alignment_record.docling_item_ref, ())
            if not source_matches:
                reasons.append("citation_source_item_not_found")
            elif len(source_matches) != 1:
                reasons.append("citation_source_item_ambiguous")
            else:
                source_docling_item_ref = alignment_record.docling_item_ref

        declared_targets = tuple(
            target for target in (annotation.target or "").split() if target
        )
        resolved_targets: list[str] = []
        unresolved_targets: list[str] = []
        if not declared_targets:
            reasons.append("missing_citation_target")
        for target in declared_targets:
            if not target.startswith("#") or len(target) == 1:
                reasons.append("citation_target_not_local")
                unresolved_targets.append(target)
                continue
            bibliography_matches = bibliography.get(target[1:], ())
            if not bibliography_matches:
                reasons.append("citation_target_not_found")
                unresolved_targets.append(target)
                continue
            if len(bibliography_matches) != 1:
                reasons.append("citation_target_ambiguous")
                unresolved_targets.append(target)
                continue

            bibliography_record = bibliography_matches[0]
            if bibliography_record.status is not AlignmentStatus.ALIGNED:
                reasons.append("bibliography_target_unaligned")
                unresolved_targets.append(target)
                continue
            bibliography_docling_ref = bibliography_record.docling_item_ref
            if bibliography_docling_ref is None:
                reasons.append("bibliography_target_missing_docling_ref")
                unresolved_targets.append(target)
                continue
            target_matches = item_index.get(bibliography_docling_ref, ())
            if not target_matches:
                reasons.append("bibliography_target_item_not_found")
                unresolved_targets.append(target)
                continue
            if len(target_matches) != 1:
                reasons.append("bibliography_target_item_ambiguous")
                unresolved_targets.append(target)
                continue
            resolved_targets.append(bibliography_docling_ref)

        records.append(
            _make_integrity_record(
                kind=ContentIntegrityKind.CITATION,
                source_ref=annotation.annotation_id,
                source_docling_item_ref=source_docling_item_ref,
                declared_target_refs=declared_targets,
                resolved_docling_item_refs=tuple(resolved_targets),
                unresolved_target_refs=tuple(unresolved_targets),
                reason_codes=_unique(reasons),
            )
        )
    return tuple(records)


def _make_integrity_record(
    *,
    kind: ContentIntegrityKind,
    source_ref: str,
    source_docling_item_ref: str | None,
    declared_target_refs: tuple[str, ...] = (),
    resolved_docling_item_refs: tuple[str, ...] = (),
    unresolved_target_refs: tuple[str, ...] = (),
    reason_codes: tuple[str, ...] = (),
) -> ContentIntegrityRecord:
    status = (
        ContentIntegrityStatus.UNALIGNED
        if reason_codes
        else ContentIntegrityStatus.RESOLVED
    )
    identity = {
        "kind": kind.value,
        "status": status.value,
        "source_ref": source_ref,
        "source_docling_item_ref": source_docling_item_ref,
        "declared_target_refs": declared_target_refs,
        "resolved_docling_item_refs": resolved_docling_item_refs,
        "unresolved_target_refs": unresolved_target_refs,
        "reason_codes": reason_codes,
    }
    record_id = sha256_bytes(
        json.dumps(
            identity,
            ensure_ascii=False,
            allow_nan=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    )
    return ContentIntegrityRecord(
        record_id=record_id,
        kind=kind,
        status=status,
        source_ref=source_ref,
        source_docling_item_ref=source_docling_item_ref,
        declared_target_refs=declared_target_refs,
        resolved_docling_item_refs=resolved_docling_item_refs,
        unresolved_target_refs=unresolved_target_refs,
        reason_codes=reason_codes,
    )


def _integrity_issue(record: ContentIntegrityRecord) -> QualityIssue:
    structural_reasons = {
        "duplicate_source_ref",
        "invalid_docling_item",
        "malformed_caption_collection",
        "malformed_caption_reference",
    }
    severity = (
        QualitySeverity.ERROR
        if structural_reasons.intersection(record.reason_codes)
        else QualitySeverity.WARNING
    )
    return QualityIssue(
        code=f"UNALIGNED_{record.kind.value.upper()}",
        message=(
            f"{record.kind.value} relationship is unaligned: "
            f"{', '.join(record.reason_codes)}"
        ),
        severity=severity,
        item_ref=record.source_docling_item_ref or record.source_ref,
    )


def _unique(values: list[str]) -> tuple[str, ...]:
    return tuple(dict.fromkeys(values))


def _content_span_id(
    *,
    artifact_id: str,
    processing_run_id: str,
    canonical_item_ref: str,
    declared_item_ref: str,
    start: int,
    end: int,
    content_sha256: str,
    source_locator: dict[str, Any],
    alignment_locator_id: str | None = None,
) -> str:
    """Hash an unambiguous, position-aware span identity.

    The canonical collection position is retained separately from a declared
    ``self_ref``. This keeps IDs unique even when malformed parser output
    repeats a self reference, while quality validation still rejects that
    document.
    """

    identity = {
        "artifact_id": artifact_id,
        "processing_run_id": processing_run_id,
        "canonical_item_ref": canonical_item_ref,
        "declared_item_ref": declared_item_ref,
        "start": start,
        "end": end,
        "content_sha256": content_sha256,
        "source_locator": source_locator,
        "alignment_locator_id": alignment_locator_id,
    }
    return sha256_bytes(
        json.dumps(
            identity,
            ensure_ascii=False,
            allow_nan=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    )


def build_pdf_content_spans(
    document: dict[str, Any],
    *,
    artifact_id: str,
    processing_run_id: str,
    representation_product_id: str,
) -> tuple[ContentSpan, ...]:
    """Build stable item-local spans for every unambiguous PDF text region."""

    spans: list[ContentSpan] = []
    texts = document.get("texts")
    if not isinstance(texts, list):
        return ()
    for index, item in enumerate(texts):
        if not isinstance(item, dict):
            continue
        item_dict = cast("dict[str, Any]", item)
        text = item_dict.get("text")
        if not isinstance(text, str) or not text:
            continue
        item_ref = _item_ref(item_dict, "texts", index)
        provenance_entries, _issues = _validated_pdf_provenance(
            document,
            item_dict,
            item_ref=item_ref,
            text_length=len(text),
        )
        if not provenance_entries:
            continue
        seen: set[tuple[int, int, str]] = set()
        for provenance in provenance_entries:
            start, end = provenance.character_span
            locator = provenance.locator
            locator_json = json.dumps(
                locator.model_dump(mode="json"),
                sort_keys=True,
                separators=(",", ":"),
            )
            identity = (start, end, locator_json)
            if identity in seen:
                continue
            seen.add(identity)
            content_sha256 = sha256_bytes(text[start:end].encode("utf-8"))
            spans.append(
                ContentSpan(
                    span_id=_content_span_id(
                        artifact_id=artifact_id,
                        processing_run_id=processing_run_id,
                        canonical_item_ref=f"#/texts/{index}",
                        declared_item_ref=item_ref,
                        start=start,
                        end=end,
                        content_sha256=content_sha256,
                        source_locator=locator.model_dump(mode="json"),
                    ),
                    artifact_id=artifact_id,
                    processing_run_id=processing_run_id,
                    representation_anchor=RepresentationAnchor(
                        product_id=representation_product_id,
                        node_id=item_ref,
                        char_start=start,
                        char_end=end,
                    ),
                    content_sha256=content_sha256,
                    source_locator=locator,
                )
            )
    return tuple(spans)


def build_docling_content_spans(
    document: dict[str, Any],
    *,
    artifact_id: str,
    processing_run_id: str,
    input_format: DoclingInputFormat,
    representation_product_id: str,
) -> tuple[ContentSpan, ...]:
    """Build full-item spans using an explicit parser-native Docling locator.

    HTML, Office, and image inputs do not share a reliable source-native locator
    contract.  Their lossless ``DoclingDocument`` is retained, so the stable item
    reference is preferable to inventing an XPath, Office object ID, or geometry.
    """

    spans: list[ContentSpan] = []
    texts = document.get("texts")
    if not isinstance(texts, list):
        return ()
    for index, item in enumerate(texts):
        if not isinstance(item, dict):
            continue
        item_dict = cast("dict[str, Any]", item)
        content = item_dict.get("text")
        if not isinstance(content, str) or not content:
            continue
        item_ref = _item_ref(item_dict, "texts", index)
        locator = DoclingItemLocator(input_format=input_format, item_ref=item_ref)
        locator_payload = locator.model_dump(mode="json")
        content_sha256 = sha256_bytes(content.encode("utf-8"))
        spans.append(
            ContentSpan(
                span_id=_content_span_id(
                    artifact_id=artifact_id,
                    processing_run_id=processing_run_id,
                    canonical_item_ref=f"#/texts/{index}",
                    declared_item_ref=item_ref,
                    start=0,
                    end=len(content),
                    content_sha256=content_sha256,
                    source_locator=locator_payload,
                ),
                artifact_id=artifact_id,
                processing_run_id=processing_run_id,
                representation_anchor=RepresentationAnchor(
                    product_id=representation_product_id,
                    node_id=item_ref,
                    char_start=0,
                    char_end=len(content),
                ),
                content_sha256=content_sha256,
                source_locator=locator,
            )
        )
    return tuple(spans)


def build_jats_content_spans(
    document: dict[str, Any],
    locators: tuple[NativeTextLocator, ...],
    *,
    artifact_id: str,
    processing_run_id: str,
    representation_product_id: str,
) -> tuple[ContentSpan, ...]:
    """Align exact/native JATS text to Docling items and retain XPath/xml:id."""

    return align_jats_content_spans(
        document,
        locators,
        artifact_id=artifact_id,
        processing_run_id=processing_run_id,
        representation_product_id=representation_product_id,
    ).spans


def build_bioc_content_spans(
    document: dict[str, Any],
    locators: tuple[NativeTextLocator, ...],
    *,
    artifact_id: str,
    processing_run_id: str,
    representation_product_id: str,
) -> tuple[ContentSpan, ...]:
    """Build evidence spans for normalized-exact BioC passage matches."""

    return align_bioc_content_spans(
        document,
        locators,
        artifact_id=artifact_id,
        processing_run_id=processing_run_id,
        representation_product_id=representation_product_id,
    ).spans


def align_bioc_content_spans(
    document: dict[str, Any],
    locators: tuple[NativeTextLocator, ...],
    *,
    artifact_id: str,
    processing_run_id: str,
    representation_product_id: str,
) -> BioCContentSpanAlignment:
    """Align BioC passages without dropping duplicate or unmatched locators.

    Matching is deterministic: native locators and Docling text items are
    considered in source order, and a Docling item can satisfy at most one
    locator.  Collection/document coordinates remain in a separate overlay;
    serialized ``DoclingDocument`` content is never rewritten.
    """

    candidates = _text_candidates(document)
    used_items: set[str] = set()
    spans: list[ContentSpan] = []
    records: list[BioCLocatorAlignmentRecord] = []
    for locator_index, native in enumerate(locators):
        native_content_sha256 = sha256_bytes(native.text.encode("utf-8"))
        locator_id = sha256_bytes(
            "\x1f".join(
                (
                    str(locator_index),
                    str(native.document_index),
                    native.document_id or "",
                    str(native.passage_index),
                    str(native.sentence_index),
                    str(native.offset),
                    str(native.length),
                    native_content_sha256,
                )
            ).encode("utf-8")
        )
        native_values = (
            native.document_index,
            native.passage_index,
            native.offset,
            native.length,
        )
        if any(value is None for value in native_values):
            records.append(
                _bioc_alignment_record(
                    locator_id=locator_id,
                    locator_index=locator_index,
                    native=native,
                    content_sha256=native_content_sha256,
                    reason="missing_native_reference",
                )
            )
            continue

        try:
            source_locator = BioCLocator(
                document_index=cast("int", native.document_index),
                document_id=native.document_id,
                passage_index=cast("int", native.passage_index),
                sentence_index=native.sentence_index,
                offset=cast("int", native.offset),
                length=cast("int", native.length),
            )
        except ValueError:
            records.append(
                _bioc_alignment_record(
                    locator_id=locator_id,
                    locator_index=locator_index,
                    native=native,
                    content_sha256=native_content_sha256,
                    reason="invalid_native_reference",
                )
            )
            continue

        best = next(
            (
                candidate
                for candidate in candidates
                if candidate.canonical_ref not in used_items
                and candidate.normalized_text == _normalized(native.text)
            ),
            None,
        )
        if best is None:
            records.append(
                _bioc_alignment_record(
                    locator_id=locator_id,
                    locator_index=locator_index,
                    native=native,
                    content_sha256=native_content_sha256,
                    reason="no_normalized_exact_match",
                )
            )
            continue

        item_ref = best.item_ref
        item_text = best.text
        used_items.add(best.canonical_ref)
        content_sha256 = sha256_bytes(item_text.encode("utf-8"))
        span = ContentSpan(
            span_id=_content_span_id(
                artifact_id=artifact_id,
                processing_run_id=processing_run_id,
                canonical_item_ref=best.canonical_ref,
                declared_item_ref=item_ref,
                start=0,
                end=len(item_text),
                content_sha256=content_sha256,
                source_locator=source_locator.model_dump(mode="json"),
                alignment_locator_id=locator_id,
            ),
            artifact_id=artifact_id,
            processing_run_id=processing_run_id,
            representation_anchor=RepresentationAnchor(
                product_id=representation_product_id,
                node_id=item_ref,
                char_start=0,
                char_end=len(item_text),
            ),
            content_sha256=content_sha256,
            source_locator=source_locator,
        )
        spans.append(span)
        records.append(
            _bioc_alignment_record(
                locator_id=locator_id,
                locator_index=locator_index,
                native=native,
                content_sha256=native_content_sha256,
                status="aligned",
                docling_item_ref=item_ref,
                content_span_id=span.span_id,
                match_method="normalized_exact",
            )
        )
    return BioCContentSpanAlignment(tuple(spans), tuple(records))


def _bioc_alignment_record(
    *,
    locator_id: str,
    locator_index: int,
    native: NativeTextLocator,
    content_sha256: str,
    status: str = "unaligned",
    docling_item_ref: str | None = None,
    content_span_id: str | None = None,
    match_method: str | None = None,
    reason: str | None = None,
) -> BioCLocatorAlignmentRecord:
    return BioCLocatorAlignmentRecord(
        locator_id=locator_id,
        locator_index=locator_index,
        content_sha256=content_sha256,
        document_index=native.document_index,
        document_id=native.document_id,
        passage_index=native.passage_index,
        sentence_index=native.sentence_index,
        offset=native.offset,
        length=native.length,
        status=status,
        docling_item_ref=docling_item_ref,
        content_span_id=content_span_id,
        match_method=match_method,
        reason=reason,
    )


def align_jats_content_spans(
    document: dict[str, Any],
    locators: tuple[NativeTextLocator, ...],
    *,
    artifact_id: str,
    processing_run_id: str,
    representation_product_id: str,
) -> JatsContentSpanAlignment:
    """Return both evidence spans and an explicit outcome for every locator."""

    candidates = _text_candidates(document)

    used_items: set[str] = set()
    spans: list[ContentSpan] = []
    records: list[JatsLocatorAlignmentRecord] = []
    for locator_index, native in enumerate(locators):
        normalized_native = _normalized(native.text)
        native_content_sha256 = sha256_bytes(native.text.encode("utf-8"))
        locator_id = sha256_bytes(
            "\x1f".join(
                (
                    str(locator_index),
                    native.xml_id or "",
                    native.xpath or "",
                    native_content_sha256,
                )
            ).encode("utf-8")
        )
        best: _TextCandidate | None = None
        match_method: str | None = None
        for candidate in candidates:
            if candidate.canonical_ref in used_items:
                continue
            if candidate.normalized_text == normalized_native:
                best = candidate
                match_method = "normalized_exact"
                break
        if native.xml_id is None and native.xpath is None:
            records.append(
                JatsLocatorAlignmentRecord(
                    locator_id=locator_id,
                    locator_index=locator_index,
                    content_sha256=native_content_sha256,
                    xml_id=None,
                    xpath=None,
                    status="unaligned",
                    reason="missing_native_reference",
                )
            )
            continue
        if best is None:
            records.append(
                JatsLocatorAlignmentRecord(
                    locator_id=locator_id,
                    locator_index=locator_index,
                    content_sha256=native_content_sha256,
                    xml_id=native.xml_id,
                    xpath=native.xpath,
                    status="unaligned",
                    reason="no_normalized_exact_match",
                )
            )
            continue
        used_items.add(best.canonical_ref)
        item_ref = best.item_ref
        item_text = best.text
        locator = JatsLocator(xml_id=native.xml_id, xpath=native.xpath)
        content_sha256 = sha256_bytes(item_text.encode("utf-8"))
        span = ContentSpan(
            span_id=_content_span_id(
                artifact_id=artifact_id,
                processing_run_id=processing_run_id,
                canonical_item_ref=best.canonical_ref,
                declared_item_ref=item_ref,
                start=0,
                end=len(item_text),
                content_sha256=content_sha256,
                source_locator=locator.model_dump(mode="json"),
                alignment_locator_id=locator_id,
            ),
            artifact_id=artifact_id,
            processing_run_id=processing_run_id,
            representation_anchor=RepresentationAnchor(
                product_id=representation_product_id,
                node_id=item_ref,
                char_start=0,
                char_end=len(item_text),
            ),
            content_sha256=content_sha256,
            source_locator=locator,
        )
        spans.append(span)
        records.append(
            JatsLocatorAlignmentRecord(
                locator_id=locator_id,
                locator_index=locator_index,
                content_sha256=native_content_sha256,
                xml_id=native.xml_id,
                xpath=native.xpath,
                status="aligned",
                docling_item_ref=item_ref,
                content_span_id=span.span_id,
                match_method=match_method,
            )
        )
    return JatsContentSpanAlignment(tuple(spans), tuple(records))


def _text_candidates(document: dict[str, Any]) -> list[_TextCandidate]:
    candidates: list[_TextCandidate] = []
    texts = document.get("texts")
    if not isinstance(texts, list):
        return candidates
    for index, item in enumerate(texts):
        if not isinstance(item, dict):
            continue
        item_dict = cast("dict[str, Any]", item)
        item_text = item_dict.get("text")
        if not isinstance(item_text, str):
            continue
        candidates.append(
            _TextCandidate(
                canonical_ref=f"#/texts/{index}",
                item_ref=_item_ref(item_dict, "texts", index),
                text=item_text,
                normalized_text=_normalized(item_text),
            )
        )
    return candidates


def probably_image_only(
    document: dict[str, Any],
    *,
    minimum_characters_per_page: int = 20,
    image_only_page_ratio: float = 0.8,
) -> bool:
    """Return whether enough pages lack provenance-backed searchable text."""

    if minimum_characters_per_page < 0:
        raise ValueError("minimum_characters_per_page must be non-negative")
    if not 0 <= image_only_page_ratio <= 1:
        raise ValueError("image_only_page_ratio must be between 0 and 1")

    page_numbers = _document_page_numbers(document)
    characters_by_page = dict.fromkeys(page_numbers, 0)
    texts = document.get("texts")
    if isinstance(texts, list):
        for item in texts:
            if not isinstance(item, dict):
                continue
            item_dict = cast("dict[str, Any]", item)
            for page_number, character_count in _item_characters_by_page(
                item_dict
            ).items():
                if page_number in characters_by_page:
                    characters_by_page[page_number] += character_count

    image_only_pages = sum(
        character_count < minimum_characters_per_page
        for character_count in characters_by_page.values()
    )
    return image_only_pages / len(characters_by_page) >= image_only_page_ratio


def _document_page_numbers(document: dict[str, Any]) -> set[int]:
    page_numbers: set[int] = set()
    pages = document.get("pages")
    if isinstance(pages, dict):
        for key, page in pages.items():
            if isinstance(page, dict):
                page_number = page.get("page_no")
                if (
                    isinstance(page_number, int)
                    and not isinstance(page_number, bool)
                    and page_number >= 1
                ):
                    page_numbers.add(page_number)
                    continue
                if page_number is not None:
                    continue
            try:
                key_page_number = int(key)
            except (TypeError, ValueError):
                continue
            if key_page_number >= 1:
                page_numbers.add(key_page_number)
    return page_numbers or {1}


def _item_characters_by_page(item: dict[str, Any]) -> dict[int, int]:
    text = item.get("text")
    provenance = item.get("prov")
    if not isinstance(text, str) or not text or not isinstance(provenance, list):
        return {}

    entries_by_page: dict[int, list[tuple[int, int] | None]] = {}
    for entry in provenance:
        if not isinstance(entry, dict):
            return {}
        page_number = entry.get("page_no")
        if (
            not isinstance(page_number, int)
            or isinstance(page_number, bool)
            or page_number < 1
        ):
            return {}
        if "charspan" in entry:
            character_span = _valid_character_span(entry["charspan"], len(text))
            if character_span is None:
                return {}
        elif len(provenance) > 1:
            return {}
        else:
            character_span = None
        entries_by_page.setdefault(page_number, []).append(character_span)
    if not entries_by_page:
        return {}

    if all(
        span is not None
        for page_entries in entries_by_page.values()
        for span in page_entries
    ):
        return {
            page_number: _covered_character_count(
                [cast("tuple[int, int]", span) for span in page_entries]
            )
            for page_number, page_entries in entries_by_page.items()
        }

    if len(entries_by_page) == 1 and len(provenance) == 1:
        return {next(iter(entries_by_page)): len(text)}
    return {}


def _valid_character_span(value: Any, text_length: int) -> tuple[int, int] | None:
    if (
        not isinstance(value, (list, tuple))
        or len(value) != 2
        or not all(
            isinstance(position, int) and not isinstance(position, bool)
            for position in value
        )
    ):
        return None
    start = cast("int", value[0])
    end = cast("int", value[1])
    if start < 0 or end > text_length or end <= start:
        return None
    return start, end


def _covered_character_count(spans: list[tuple[int, int]]) -> int:
    count = 0
    current_start = -1
    current_end = -1
    for start, end in sorted(spans):
        if start > current_end:
            if current_start >= 0:
                count += current_end - current_start
            current_start = start
            current_end = end
        else:
            current_end = max(current_end, end)
    if current_start >= 0:
        count += current_end - current_start
    return count


def _validated_pdf_provenance(
    document: dict[str, Any],
    item: dict[str, Any],
    *,
    item_ref: str,
    text_length: int,
) -> tuple[tuple[_ValidatedPdfProvenance, ...], tuple[QualityIssue, ...]]:
    """Return only provenance entries whose source coordinates are trustworthy."""

    provenance = item.get("prov")
    if provenance is None:
        return (), ()
    if not isinstance(provenance, list):
        return (), (
            _pdf_quality_issue(
                "PDF_PROVENANCE_COLLECTION_INVALID",
                "PDF provenance must be a list",
                item_ref=item_ref,
            ),
        )

    pages, invalid_page_geometry, page_count = _pdf_page_geometries(document)
    is_multi_region = len(provenance) > 1
    valid: list[_ValidatedPdfProvenance] = []
    issues: list[QualityIssue] = []
    for provenance_index, raw_entry in enumerate(provenance):
        entry_label = f"provenance entry {provenance_index}"
        if not isinstance(raw_entry, dict):
            issues.append(
                _pdf_quality_issue(
                    "PDF_PROVENANCE_ENTRY_MALFORMED",
                    f"{entry_label} must be an object",
                    item_ref=item_ref,
                )
            )
            continue
        entry = cast("dict[str, Any]", raw_entry)
        page_number = entry.get("page_no")
        if (
            not isinstance(page_number, int)
            or isinstance(page_number, bool)
            or page_number < 1
        ):
            issues.append(
                _pdf_quality_issue(
                    "PDF_PROVENANCE_PAGE_INVALID",
                    f"{entry_label} has an invalid page number",
                    item_ref=item_ref,
                )
            )
            continue
        if page_number > page_count:
            issues.append(
                _pdf_quality_issue(
                    "PDF_PROVENANCE_PAGE_OUT_OF_BOUNDS",
                    (
                        f"{entry_label} references page {page_number}, outside the "
                        f"document's 1..{page_count} page range"
                    ),
                    item_ref=item_ref,
                    page_number=page_number,
                )
            )
            continue
        if page_number not in pages:
            issues.append(
                _pdf_quality_issue(
                    "PDF_PROVENANCE_PAGE_NOT_PRESENT",
                    f"{entry_label} references page {page_number}, which is not present",
                    item_ref=item_ref,
                    page_number=page_number,
                )
            )
            continue
        if page_number in invalid_page_geometry:
            issues.append(
                _pdf_quality_issue(
                    "PDF_PAGE_GEOMETRY_INVALID",
                    f"Page {page_number} has malformed width or height metadata",
                    item_ref=item_ref,
                    page_number=page_number,
                )
            )
            continue

        locator, locator_issue = _strict_pdf_locator(
            entry,
            page_geometry=pages[page_number],
            item_ref=item_ref,
            entry_label=entry_label,
        )
        if locator_issue is not None:
            issues.append(locator_issue)
            continue

        if "charspan" in entry:
            character_span = _valid_character_span(entry["charspan"], text_length)
            if character_span is None:
                issues.append(
                    _pdf_quality_issue(
                        "PDF_PROVENANCE_CHARSPAN_INVALID",
                        (
                            f"{entry_label} has a character range outside the "
                            f"item-local 0..{text_length} bounds"
                        ),
                        item_ref=item_ref,
                        page_number=page_number,
                    )
                )
                continue
        elif is_multi_region:
            issues.append(
                _pdf_quality_issue(
                    "PDF_MULTI_PROVENANCE_CHARSPAN_MISSING",
                    (
                        "A multi-region PDF text item lacks an item-local "
                        f"character range for {entry_label}"
                    ),
                    item_ref=item_ref,
                    page_number=page_number,
                )
            )
            continue
        elif text_length > 0:
            character_span = (0, text_length)
        else:
            continue

        valid.append(
            _ValidatedPdfProvenance(
                locator=cast("PdfLocator", locator),
                character_span=character_span,
            )
        )
    return tuple(valid), tuple(issues)


def _strict_pdf_locator(
    provenance: dict[str, Any],
    *,
    page_geometry: _PdfPageGeometry,
    item_ref: str,
    entry_label: str,
) -> tuple[PdfLocator | None, QualityIssue | None]:
    page_number = cast("int", provenance["page_no"])
    bbox = provenance.get("bbox")
    if not isinstance(bbox, dict):
        return None, _pdf_quality_issue(
            "PDF_PROVENANCE_BBOX_MALFORMED",
            f"{entry_label} has no bounding-box object",
            item_ref=item_ref,
            page_number=page_number,
        )

    bbox_dict = cast("dict[str, Any]", bbox)
    origin_value = bbox_dict.get("coord_origin")
    origins: dict[str, Literal["top_left", "bottom_left"]] = {
        "TOPLEFT": "top_left",
        "top_left": "top_left",
        "BOTTOMLEFT": "bottom_left",
        "bottom_left": "bottom_left",
    }
    if not isinstance(origin_value, str) or origin_value not in origins:
        return None, _pdf_quality_issue(
            "PDF_PROVENANCE_COORDINATE_ORIGIN_INVALID",
            f"{entry_label} has an unknown coordinate origin",
            item_ref=item_ref,
            page_number=page_number,
        )
    origin = origins[origin_value]

    coordinate_values: dict[str, float] = {}
    for coordinate in ("l", "t", "r", "b"):
        value = bbox_dict.get(coordinate)
        if (
            not isinstance(value, (int, float))
            or isinstance(value, bool)
            or not math.isfinite(value)
        ):
            return None, _pdf_quality_issue(
                "PDF_PROVENANCE_BBOX_MALFORMED",
                f"{entry_label} has a non-finite or non-numeric '{coordinate}' value",
                item_ref=item_ref,
                page_number=page_number,
            )
        coordinate_values[coordinate] = float(value)

    left = coordinate_values["l"]
    first_vertical = coordinate_values["t"]
    right = coordinate_values["r"]
    second_vertical = coordinate_values["b"]
    if min(left, first_vertical, right, second_vertical) < 0:
        return None, _pdf_quality_issue(
            "PDF_PROVENANCE_BBOX_NEGATIVE",
            f"{entry_label} has a negative bounding-box coordinate",
            item_ref=item_ref,
            page_number=page_number,
        )
    if left >= right:
        return None, _pdf_quality_issue(
            "PDF_PROVENANCE_BBOX_INVALID",
            f"{entry_label} must have l < r",
            item_ref=item_ref,
            page_number=page_number,
        )
    if origin == "top_left":
        if first_vertical >= second_vertical:
            return None, _pdf_quality_issue(
                "PDF_PROVENANCE_BBOX_INVALID",
                f"{entry_label} with TOPLEFT origin must have t < b",
                item_ref=item_ref,
                page_number=page_number,
            )
        top, bottom = first_vertical, second_vertical
    else:
        if second_vertical >= first_vertical:
            return None, _pdf_quality_issue(
                "PDF_PROVENANCE_BBOX_INVALID",
                f"{entry_label} with BOTTOMLEFT origin must have b < t",
                item_ref=item_ref,
                page_number=page_number,
            )
        top, bottom = second_vertical, first_vertical

    if page_geometry.width is not None and right > page_geometry.width:
        return None, _pdf_quality_issue(
            "PDF_PROVENANCE_BBOX_OUT_OF_PAGE",
            f"{entry_label} exceeds page {page_number} width",
            item_ref=item_ref,
            page_number=page_number,
        )
    if page_geometry.height is not None and bottom > page_geometry.height:
        return None, _pdf_quality_issue(
            "PDF_PROVENANCE_BBOX_OUT_OF_PAGE",
            f"{entry_label} exceeds page {page_number} height",
            item_ref=item_ref,
            page_number=page_number,
        )

    return (
        PdfLocator(
            page_number=page_number,
            bounding_box=PdfBoundingBox(
                left=left,
                right=right,
                top=top,
                bottom=bottom,
                page_width=page_geometry.width,
                page_height=page_geometry.height,
                coordinate_origin=origin,
            ),
        ),
        None,
    )


def _pdf_page_geometries(
    document: dict[str, Any],
) -> tuple[dict[int, _PdfPageGeometry], set[int], int]:
    pages = document.get("pages")
    if not isinstance(pages, dict):
        return {}, set(), 0

    geometries: dict[int, _PdfPageGeometry] = {}
    invalid_geometry: set[int] = set()
    duplicate_page_numbers: set[int] = set()
    for key, raw_page in pages.items():
        if not isinstance(raw_page, dict):
            continue
        page = cast("dict[str, Any]", raw_page)
        page_number = page.get("page_no")
        if page_number is None:
            try:
                page_number = int(key)
            except (TypeError, ValueError):
                continue
        elif (
            not isinstance(page_number, int)
            or isinstance(page_number, bool)
            or page_number < 1
        ):
            try:
                invalid_page_number = int(key)
            except (TypeError, ValueError):
                continue
            invalid_geometry.add(invalid_page_number)
            geometries[invalid_page_number] = _PdfPageGeometry(None, None)
            continue
        if page_number in geometries:
            duplicate_page_numbers.add(page_number)

        size = page.get("size")
        if size is None:
            geometries[page_number] = _PdfPageGeometry(None, None)
            continue
        if not isinstance(size, dict):
            invalid_geometry.add(page_number)
            geometries[page_number] = _PdfPageGeometry(None, None)
            continue
        width = size.get("width")
        height = size.get("height")
        if not _is_finite_positive_number(width) or not _is_finite_positive_number(
            height
        ):
            invalid_geometry.add(page_number)
            geometries[page_number] = _PdfPageGeometry(None, None)
            continue
        geometries[page_number] = _PdfPageGeometry(float(width), float(height))
    invalid_geometry.update(duplicate_page_numbers)
    return geometries, invalid_geometry, len(pages)


def _is_finite_positive_number(value: Any) -> bool:
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(value)
        and value > 0
    )


def _pdf_quality_issue(
    code: str,
    message: str,
    *,
    item_ref: str,
    page_number: int | None = None,
) -> QualityIssue:
    return QualityIssue(
        code=code,
        message=message,
        severity=QualitySeverity.ERROR,
        item_ref=item_ref,
        page_number=page_number,
    )


def _reference_definition_issues(
    document: dict[str, Any],
) -> tuple[QualityIssue, ...]:
    """Reject ambiguous self references across the complete content tree."""

    canonical_paths: set[str] = set()
    self_ref_occurrences: dict[str, list[str]] = {}

    def visit(value: Any, path: str) -> None:
        if isinstance(value, dict):
            canonical_paths.add(path)
            self_ref = value.get("self_ref")
            if isinstance(self_ref, str) and self_ref:
                self_ref_occurrences.setdefault(self_ref, []).append(path)
            for key, nested in value.items():
                escaped_key = str(key).replace("~", "~0").replace("/", "~1")
                visit(nested, f"{path}/{escaped_key}")
        elif isinstance(value, list):
            canonical_paths.add(path)
            for index, nested in enumerate(value):
                visit(nested, f"{path}/{index}")

    visit(document, "#")
    issues: list[QualityIssue] = []
    for self_ref, paths in sorted(self_ref_occurrences.items()):
        if len(paths) > 1:
            issues.append(
                QualityIssue(
                    code="DUPLICATE_DOCLING_SELF_REF",
                    message=(
                        f"Docling self_ref {self_ref!r} is declared by multiple "
                        f"items: {', '.join(paths)}"
                    ),
                    severity=QualitySeverity.ERROR,
                    item_ref=self_ref,
                )
            )
        colliding_paths = tuple(
            path for path in paths if self_ref in canonical_paths and path != self_ref
        )
        if colliding_paths:
            issues.append(
                QualityIssue(
                    code="DOCLING_CANONICAL_REFERENCE_COLLISION",
                    message=(
                        f"Docling self_ref {self_ref!r} aliases a different "
                        f"canonical item from {', '.join(colliding_paths)}"
                    ),
                    severity=QualitySeverity.ERROR,
                    item_ref=self_ref,
                )
            )
    return tuple(issues)


def _validate_references(document: dict[str, Any]) -> tuple[int, tuple[str, ...]]:
    resolvable: set[str] = {"#"}
    malformed_index_refs: set[str] = set()
    for name in (
        "groups",
        "texts",
        "tables",
        "pictures",
        "key_value_items",
        "form_items",
        "field_regions",
        "field_items",
    ):
        values = document.get(name)
        if isinstance(values, list):
            for index, value in enumerate(values):
                if not isinstance(value, dict):
                    malformed_index_refs.add(f"#/{name}/{index}")
                    continue
                resolvable.add(f"#/{name}/{index}")
                value_dict = cast("dict[str, Any]", value)
                self_ref = value_dict.get("self_ref")
                if isinstance(self_ref, str):
                    resolvable.add(self_ref)
    resolvable.update({"#/body", "#/furniture"})
    resolvable.difference_update(malformed_index_refs)

    refs: list[str] = []
    for value in document.values():
        _collect_refs(value, refs)
    broken = tuple(sorted({ref for ref in refs if ref not in resolvable}))
    return len(refs), broken


def _collect_refs(value: Any, refs: list[str]) -> None:
    if isinstance(value, dict):
        ref = value.get("$ref")
        if isinstance(ref, str):
            refs.append(ref)
        for nested in value.values():
            _collect_refs(nested, refs)
    elif isinstance(value, list):
        for nested in value:
            _collect_refs(nested, refs)


def _item_ref(item: dict[str, Any], collection: str, index: int) -> str:
    value = item.get("self_ref")
    return value if isinstance(value, str) and value else f"#/{collection}/{index}"


def _malformed_content_entry_issue(
    collection: str,
    index: int,
    value: Any,
) -> QualityIssue:
    return QualityIssue(
        code="MALFORMED_DOCLING_CONTENT_ENTRY",
        message=(
            f"Docling {collection} entry {index} must be an object, "
            f"not {type(value).__name__}"
        ),
        severity=QualitySeverity.ERROR,
        item_ref=f"#/{collection}/{index}",
    )


def _normalized(text: str) -> str:
    return " ".join(text.casefold().split())


__all__ = [
    "BioCContentSpanAlignment",
    "BioCLocatorAlignmentRecord",
    "ContentIntegrityKind",
    "ContentIntegrityRecord",
    "ContentIntegrityReport",
    "ContentIntegrityStatus",
    "DoclingQualityReport",
    "DoclingQualityValidator",
    "JatsContentSpanAlignment",
    "JatsLocatorAlignmentRecord",
    "QualityIssue",
    "QualitySeverity",
    "align_bioc_content_spans",
    "align_jats_content_spans",
    "build_bioc_content_spans",
    "build_docling_content_spans",
    "build_jats_content_spans",
    "build_pdf_content_spans",
    "docling_document_sha256",
    "probably_image_only",
    "validate_content_integrity",
]
