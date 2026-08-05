"""Versioned, project-owned canonical document representation.

The canonical view is derived from immutable parser-native products.  It keeps
ordered structure and stable block identities without absorbing scientific
annotations or replacing the native products used to build it.
"""

from __future__ import annotations

import json
import re
import unicodedata
from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum
from typing import Any, Literal, cast

from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

from .alignment import AlignmentStatus, ScholarlyAlignmentOverlay
from .models import (
    ContentSpan,
    ContentSpanSet,
    DataProductRef,
    DocumentArtifact,
    FrozenModel,
    Sha256,
    SourceLocator,
    sha256_bytes,
)

CANONICAL_DOCUMENT_SCHEMA_VERSION = "deepcritical-canonical-document-view-v1"
CANONICAL_TEXT_NORMALIZATION = "unicode-nfc-collapse-whitespace-v1"
CANONICAL_ANCHORING_POLICY = "source-spans-and-native-nodes-v1"


class CanonicalDocumentError(ValueError):
    """Base error for canonical document construction and loading."""


class UnsupportedCanonicalDocumentVersionError(CanonicalDocumentError):
    """A canonical document blob uses an unknown or missing schema version."""


class InvalidCanonicalDocumentError(CanonicalDocumentError):
    """A canonical document blob is malformed or violates its contract."""


class CanonicalBlockKind(StrEnum):
    """Closed structural vocabulary for processor-independent document blocks."""

    TITLE = "title"
    SECTION = "section"
    PARAGRAPH = "paragraph"
    LIST_ITEM = "list_item"
    TABLE = "table"
    FIGURE = "figure"
    CAPTION = "caption"
    FORMULA = "formula"
    CITATION = "citation"
    REFERENCE = "reference"
    GROUP = "group"
    OTHER = "other"


class CanonicalAnchorRole(StrEnum):
    """Why a native representation anchor is attached to a canonical block."""

    PRIMARY = "primary"
    SOURCE = "source"
    SCHOLARLY = "scholarly"


class CanonicalRelationshipKind(StrEnum):
    """Closed relationships retained from parser-native structure."""

    HAS_CAPTION = "has_caption"
    CITES = "cites"


class CanonicalRelationshipStatus(StrEnum):
    """Resolution state for one native structural relationship."""

    RESOLVED = "resolved"
    PARTIAL = "partial"
    UNRESOLVED = "unresolved"


class CanonicalDiagnosticSeverity(StrEnum):
    """Severity of a canonicalization mapping diagnostic."""

    WARNING = "warning"
    ERROR = "error"


class CanonicalizationConfig(BaseModel):
    """Closed, persisted policy for one canonicalization component instance."""

    model_config = ConfigDict(extra="forbid", frozen=True, validate_default=True)

    text_normalization: Literal["unicode-nfc-collapse-whitespace-v1"] = (
        CANONICAL_TEXT_NORMALIZATION
    )
    anchoring_policy: Literal["source-spans-and-native-nodes-v1"] = (
        CANONICAL_ANCHORING_POLICY
    )


class CanonicalSourceAnchor(FrozenModel):
    """Exact node or character range in one immutable native product."""

    role: CanonicalAnchorRole
    product_id: str
    node_id: str
    char_start: int | None = Field(default=None, ge=0)
    char_end: int | None = Field(default=None, gt=0)
    source_locator: SourceLocator | None = None

    @model_validator(mode="after")
    def _validate_range(self) -> CanonicalSourceAnchor:
        if (self.char_start is None) != (self.char_end is None):
            raise ValueError("canonical anchor character bounds must be paired")
        if (
            self.char_start is not None
            and self.char_end is not None
            and self.char_end <= self.char_start
        ):
            raise ValueError("canonical anchor char_end must exceed char_start")
        if not self.product_id.strip() or not self.node_id.strip():
            raise ValueError("canonical anchor identifiers must not be empty")
        return self


class CanonicalTable(FrozenModel):
    """Normalized table cells in source row order."""

    rows: tuple[tuple[str, ...], ...] = ()


class CanonicalBlock(FrozenModel):
    """One immutable block in canonical document order."""

    block_id: str
    native_node_id: str
    native_label: str
    kind: CanonicalBlockKind
    ordinal: int = Field(ge=0)
    parent_block_id: str | None = None
    child_block_ids: tuple[str, ...] = ()
    text: str | None = None
    table: CanonicalTable | None = None
    content_sha256: Sha256
    source_anchors: tuple[CanonicalSourceAnchor, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def _validate_content(self) -> CanonicalBlock:
        expected_hash = canonical_block_content_sha256(
            kind=self.kind,
            text=self.text,
            table=self.table,
        )
        if self.content_sha256 != expected_hash:
            raise ValueError("canonical block content hash does not match its content")
        expected_id = canonical_block_id(
            native_node_id=self.native_node_id,
            kind=self.kind,
            content_sha256=self.content_sha256,
        )
        if self.block_id != expected_id:
            raise ValueError("canonical block ID does not match its stable identity")
        if (self.kind is CanonicalBlockKind.TABLE) != (self.table is not None):
            raise ValueError("only table blocks may contain canonical table data")
        if self.text is not None and not self.text:
            raise ValueError("canonical block text must be non-empty when present")
        if len(set(self.child_block_ids)) != len(self.child_block_ids):
            raise ValueError("canonical child block IDs must be unique")
        anchor_keys = {
            json.dumps(
                anchor.model_dump(mode="json"),
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
            )
            for anchor in self.source_anchors
        }
        if len(anchor_keys) != len(self.source_anchors):
            raise ValueError("canonical source anchors must be unique")
        return self


class CanonicalRelationship(FrozenModel):
    """Resolved and unresolved native relationship evidence."""

    relationship_id: str
    kind: CanonicalRelationshipKind
    status: CanonicalRelationshipStatus
    source_block_id: str | None = None
    target_block_ids: tuple[str, ...] = ()
    declared_target_refs: tuple[str, ...] = ()
    unresolved_target_refs: tuple[str, ...] = ()
    reason_codes: tuple[str, ...] = ()
    source_anchor: CanonicalSourceAnchor | None = None

    @model_validator(mode="after")
    def _validate_identity(self) -> CanonicalRelationship:
        expected_id = canonical_relationship_id(
            kind=self.kind,
            source_block_id=self.source_block_id,
            target_block_ids=self.target_block_ids,
            declared_target_refs=self.declared_target_refs,
            unresolved_target_refs=self.unresolved_target_refs,
            reason_codes=self.reason_codes,
            source_anchor=self.source_anchor,
        )
        if self.relationship_id != expected_id:
            raise ValueError("canonical relationship ID does not match its content")
        if len(set(self.target_block_ids)) != len(self.target_block_ids):
            raise ValueError("canonical relationship targets must be unique")
        if self.status is CanonicalRelationshipStatus.RESOLVED and (
            self.source_block_id is None
            or not self.target_block_ids
            or self.unresolved_target_refs
            or self.reason_codes
        ):
            raise ValueError("resolved canonical relationships must resolve completely")
        if self.status is CanonicalRelationshipStatus.UNRESOLVED and (
            self.source_block_id is not None and self.target_block_ids
        ):
            raise ValueError(
                "partially resolved relationships must use status='partial'"
            )
        return self


class CanonicalMappingDiagnostic(FrozenModel):
    """Explicit evidence that a native node or relationship did not map cleanly."""

    diagnostic_id: str
    severity: CanonicalDiagnosticSeverity
    code: str
    message: str
    product_id: str | None = None
    native_node_ids: tuple[str, ...] = ()

    @model_validator(mode="after")
    def _validate_identity(self) -> CanonicalMappingDiagnostic:
        expected_id = canonical_diagnostic_id(
            severity=self.severity,
            code=self.code,
            message=self.message,
            product_id=self.product_id,
            native_node_ids=self.native_node_ids,
        )
        if self.diagnostic_id != expected_id:
            raise ValueError("canonical diagnostic ID does not match its content")
        if not self.code.strip() or not self.message.strip():
            raise ValueError("canonical diagnostic values must not be empty")
        return self


class CanonicalDocumentMetadata(FrozenModel):
    """Source-level metadata retained without scientific interpretation."""

    title: str | None = None
    media_type: str
    identifiers: dict[str, str] = Field(default_factory=dict)


class CanonicalDocumentView(FrozenModel):
    """Versioned canonical structure targeting exact immutable native products."""

    schema_version: Literal["deepcritical-canonical-document-view-v1"] = (
        CANONICAL_DOCUMENT_SCHEMA_VERSION
    )
    view_id: str
    artifact_id: str
    source_sha256: Sha256
    normalization_policy: Literal["unicode-nfc-collapse-whitespace-v1"]
    anchoring_policy: Literal["source-spans-and-native-nodes-v1"]
    metadata: CanonicalDocumentMetadata
    source_products: tuple[DataProductRef, ...] = Field(min_length=2)
    root_block_ids: tuple[str, ...] = Field(min_length=1)
    blocks: tuple[CanonicalBlock, ...] = Field(min_length=1)
    relationships: tuple[CanonicalRelationship, ...] = ()
    diagnostics: tuple[CanonicalMappingDiagnostic, ...] = ()

    @model_validator(mode="after")
    def _validate_graph_and_identity(self) -> CanonicalDocumentView:
        products = {product.product_id: product for product in self.source_products}
        if len(products) != len(self.source_products):
            raise ValueError("canonical source products must be unique")
        blocks = {block.block_id: block for block in self.blocks}
        if len(blocks) != len(self.blocks):
            raise ValueError("canonical block IDs must be unique")
        if tuple(block.ordinal for block in self.blocks) != tuple(
            range(len(self.blocks))
        ):
            raise ValueError("canonical block ordinals must be contiguous")
        if len(set(self.root_block_ids)) != len(self.root_block_ids):
            raise ValueError("canonical root block IDs must be unique")
        expected_roots = tuple(
            block.block_id for block in self.blocks if block.parent_block_id is None
        )
        if self.root_block_ids != expected_roots:
            raise ValueError("canonical roots must match blocks without parents")
        for block in self.blocks:
            if block.parent_block_id is not None:
                parent = blocks.get(block.parent_block_id)
                if parent is None or block.block_id not in parent.child_block_ids:
                    raise ValueError("canonical parent and child links must agree")
                if parent.ordinal >= block.ordinal:
                    raise ValueError("canonical parents must precede their children")
            for child_id in block.child_block_ids:
                child = blocks.get(child_id)
                if child is None or child.parent_block_id != block.block_id:
                    raise ValueError("canonical child and parent links must agree")
            for anchor in block.source_anchors:
                if anchor.product_id not in products:
                    raise ValueError("canonical anchor references an unknown product")
        relationship_ids: set[str] = set()
        for relationship in self.relationships:
            if relationship.relationship_id in relationship_ids:
                raise ValueError("canonical relationship IDs must be unique")
            relationship_ids.add(relationship.relationship_id)
            if (
                relationship.source_block_id is not None
                and relationship.source_block_id not in blocks
            ):
                raise ValueError("canonical relationship source does not exist")
            if any(target not in blocks for target in relationship.target_block_ids):
                raise ValueError("canonical relationship target does not exist")
            if (
                relationship.source_anchor is not None
                and relationship.source_anchor.product_id not in products
            ):
                raise ValueError("canonical relationship anchor product does not exist")
        diagnostic_ids = [diagnostic.diagnostic_id for diagnostic in self.diagnostics]
        if len(set(diagnostic_ids)) != len(diagnostic_ids):
            raise ValueError("canonical diagnostic IDs must be unique")
        if any(
            diagnostic.product_id is not None and diagnostic.product_id not in products
            for diagnostic in self.diagnostics
        ):
            raise ValueError("canonical diagnostic product does not exist")
        expected_view_id = canonical_view_id(self.model_dump(mode="json"))
        if self.view_id != expected_view_id:
            raise ValueError("canonical view ID does not match its content")
        return self


@dataclass(frozen=True, slots=True)
class _NativeNode:
    canonical_ref: str
    declared_ref: str
    collection: str
    item: dict[str, Any]
    native_label: str
    kind: CanonicalBlockKind
    text: str | None
    table: CanonicalTable | None


def normalize_canonical_text(value: str) -> str:
    """Normalize text using the only policy accepted by schema version 1."""

    normalized = unicodedata.normalize("NFC", value)
    return re.sub(r"\s+", " ", normalized, flags=re.UNICODE).strip()


def canonical_block_content_sha256(
    *,
    kind: CanonicalBlockKind,
    text: str | None,
    table: CanonicalTable | None,
) -> str:
    """Hash normalized block content independently of parser-native metadata."""

    return _canonical_hash(
        {
            "kind": kind.value,
            "text": text,
            "table": table.model_dump(mode="json") if table is not None else None,
        }
    )


def canonical_block_id(
    *, native_node_id: str, kind: CanonicalBlockKind, content_sha256: str
) -> str:
    """Return a deterministic local block identity."""

    return "block-" + _canonical_hash(
        {
            "schema": "deepcritical-canonical-block-id-v1",
            "native_node_id": native_node_id,
            "kind": kind.value,
            "content_sha256": content_sha256,
        }
    )


def canonical_relationship_id(
    *,
    kind: CanonicalRelationshipKind,
    source_block_id: str | None,
    target_block_ids: tuple[str, ...],
    declared_target_refs: tuple[str, ...],
    unresolved_target_refs: tuple[str, ...],
    reason_codes: tuple[str, ...],
    source_anchor: CanonicalSourceAnchor | None,
) -> str:
    """Return a deterministic relationship identity."""

    return "relationship-" + _canonical_hash(
        {
            "schema": "deepcritical-canonical-relationship-id-v1",
            "kind": kind.value,
            "source_block_id": source_block_id,
            "target_block_ids": target_block_ids,
            "declared_target_refs": declared_target_refs,
            "unresolved_target_refs": unresolved_target_refs,
            "reason_codes": reason_codes,
            "source_anchor": (
                source_anchor.model_dump(mode="json")
                if source_anchor is not None
                else None
            ),
        }
    )


def canonical_diagnostic_id(
    *,
    severity: CanonicalDiagnosticSeverity,
    code: str,
    message: str,
    product_id: str | None,
    native_node_ids: tuple[str, ...],
) -> str:
    """Return a deterministic mapping-diagnostic identity."""

    return "canonical-diagnostic-" + _canonical_hash(
        {
            "schema": "deepcritical-canonical-diagnostic-id-v1",
            "severity": severity.value,
            "code": code,
            "message": message,
            "product_id": product_id,
            "native_node_ids": native_node_ids,
        }
    )


def canonical_view_id(payload: Mapping[str, Any]) -> str:
    """Return the deterministic identity of a complete canonical view payload."""

    identity = dict(payload)
    identity.pop("view_id", None)
    return "canonical-view-" + _canonical_hash(identity)


def canonical_document_bytes(view: CanonicalDocumentView) -> bytes:
    """Serialize a validated canonical view with deterministic JSON bytes."""

    return json.dumps(
        view.model_dump(mode="json"),
        allow_nan=False,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def load_canonical_document(data: bytes) -> CanonicalDocumentView:
    """Dispatch on schema version before validating a canonical document blob."""

    try:
        payload = json.loads(data)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise InvalidCanonicalDocumentError(
            "canonical document is not valid JSON"
        ) from exc
    if not isinstance(payload, dict):
        raise InvalidCanonicalDocumentError("canonical document must be a JSON object")
    version = payload.get("schema_version")
    if version != CANONICAL_DOCUMENT_SCHEMA_VERSION:
        raise UnsupportedCanonicalDocumentVersionError(
            f"unsupported canonical document schema_version {version!r}"
        )
    try:
        return CanonicalDocumentView.model_validate(payload)
    except ValidationError as exc:
        raise InvalidCanonicalDocumentError(
            "canonical document contract is invalid"
        ) from exc


def build_canonical_document_view(
    *,
    artifact: DocumentArtifact,
    docling_document: dict[str, Any],
    docling_product: DataProductRef,
    content_span_set: ContentSpanSet,
    source_products: tuple[DataProductRef, ...],
    configuration: CanonicalizationConfig,
    scholarly_overlay: ScholarlyAlignmentOverlay | None = None,
    integrity_report: Mapping[str, Any] | None = None,
) -> CanonicalDocumentView:
    """Build a deterministic canonical view from immutable native products."""

    products = tuple(dict.fromkeys(source_products))
    product_ids = {product.product_id for product in products}
    if docling_product.product_id not in product_ids:
        raise CanonicalDocumentError(
            "Docling product must be a canonical source product"
        )
    if content_span_set.representation_product_id != docling_product.product_id:
        raise CanonicalDocumentError("content spans target a different Docling product")

    diagnostics: list[CanonicalMappingDiagnostic] = []
    nodes = _collect_native_nodes(docling_document, diagnostics, docling_product)
    canonical_index = {node.canonical_ref: node for node in nodes}
    declared_index: dict[str, list[_NativeNode]] = {}
    for node in nodes:
        declared_index.setdefault(node.declared_ref, []).append(node)

    ordered_nodes: list[_NativeNode] = []
    parent_by_ref: dict[str, str | None] = {}
    visited: set[str] = set()

    def resolve(reference: str, *, context: str) -> _NativeNode | None:
        direct = canonical_index.get(reference)
        if direct is not None:
            return direct
        matches = declared_index.get(reference, [])
        if len(matches) == 1:
            return matches[0]
        code = (
            "UNRESOLVED_NATIVE_REFERENCE"
            if not matches
            else "AMBIGUOUS_NATIVE_REFERENCE"
        )
        diagnostics.append(
            _diagnostic(
                severity=CanonicalDiagnosticSeverity.ERROR,
                code=code,
                message=f"{context} reference {reference!r} did not resolve uniquely",
                product_id=docling_product.product_id,
                native_node_ids=(reference,),
            )
        )
        return None

    def visit(reference: str, parent_ref: str | None) -> None:
        node = resolve(reference, context="document hierarchy")
        if node is None or node.canonical_ref in visited:
            return
        visited.add(node.canonical_ref)
        ordered_nodes.append(node)
        parent_by_ref[node.canonical_ref] = parent_ref
        if node.kind is CanonicalBlockKind.GROUP:
            for child_ref in _child_references(node.item):
                visit(child_ref, node.canonical_ref)

    body = docling_document.get("body")
    if isinstance(body, Mapping):
        for reference in _reference_values(body.get("children")):
            visit(reference, None)
    else:
        diagnostics.append(
            _diagnostic(
                severity=CanonicalDiagnosticSeverity.ERROR,
                code="MISSING_DOCUMENT_BODY",
                message="Docling document body is missing or malformed",
                product_id=docling_product.product_id,
            )
        )
    for node in nodes:
        if node.canonical_ref not in visited:
            visited.add(node.canonical_ref)
            ordered_nodes.append(node)
            parent_by_ref[node.canonical_ref] = None

    spans_by_node: dict[str, list[ContentSpan]] = {}
    for span in content_span_set.spans:
        spans_by_node.setdefault(span.representation_anchor.node_id, []).append(span)

    grobid_product = next(
        (product for product in products if product.name == "grobid_tei"), None
    )
    scholarly_by_node: dict[str, list[CanonicalSourceAnchor]] = {}
    if scholarly_overlay is not None:
        for record in scholarly_overlay.records:
            annotation = record.annotation
            if record.status is AlignmentStatus.ALIGNED and record.docling_item_ref:
                if grobid_product is None:
                    diagnostics.append(
                        _diagnostic(
                            severity=CanonicalDiagnosticSeverity.ERROR,
                            code="MISSING_GROBID_SOURCE_PRODUCT",
                            message="Scholarly alignment has no GROBID source product",
                            native_node_ids=(annotation.tei_path,),
                        )
                    )
                    continue
                scholarly_by_node.setdefault(record.docling_item_ref, []).append(
                    CanonicalSourceAnchor(
                        role=CanonicalAnchorRole.SCHOLARLY,
                        product_id=grobid_product.product_id,
                        node_id=annotation.tei_path,
                        char_start=0,
                        char_end=len(annotation.text),
                    )
                )
            elif grobid_product is not None:
                diagnostics.append(
                    _diagnostic(
                        severity=CanonicalDiagnosticSeverity.WARNING,
                        code="UNRESOLVED_SCHOLARLY_ANCHOR",
                        message="GROBID annotation did not align to a canonical block",
                        product_id=grobid_product.product_id,
                        native_node_ids=(annotation.tei_path,),
                    )
                )

    provisional: list[dict[str, Any]] = []
    block_id_by_ref: dict[str, str] = {}
    for ordinal, node in enumerate(ordered_nodes):
        content_hash = canonical_block_content_sha256(
            kind=node.kind,
            text=node.text,
            table=node.table,
        )
        block_id = canonical_block_id(
            native_node_id=node.canonical_ref,
            kind=node.kind,
            content_sha256=content_hash,
        )
        block_id_by_ref[node.canonical_ref] = block_id
        anchors: list[CanonicalSourceAnchor] = [
            CanonicalSourceAnchor(
                role=CanonicalAnchorRole.PRIMARY,
                product_id=docling_product.product_id,
                node_id=node.declared_ref,
                char_start=0 if node.text else None,
                char_end=len(_native_text(node.item)) if node.text else None,
            )
        ]
        matched_spans = spans_by_node.get(node.declared_ref, [])
        for span in matched_spans:
            anchors.append(
                CanonicalSourceAnchor(
                    role=CanonicalAnchorRole.SOURCE,
                    product_id=span.representation_anchor.product_id,
                    node_id=span.representation_anchor.node_id,
                    char_start=span.representation_anchor.char_start,
                    char_end=span.representation_anchor.char_end,
                    source_locator=span.source_locator,
                )
            )
        anchors.extend(scholarly_by_node.get(node.declared_ref, []))
        if node.text and not matched_spans:
            diagnostics.append(
                _diagnostic(
                    severity=CanonicalDiagnosticSeverity.WARNING,
                    code="MISSING_SOURCE_SPAN",
                    message="Canonical text block has no source-locator span",
                    product_id=docling_product.product_id,
                    native_node_ids=(node.declared_ref,),
                )
            )
        provisional.append(
            {
                "block_id": block_id,
                "native_node_id": node.canonical_ref,
                "native_label": node.native_label,
                "kind": node.kind,
                "ordinal": ordinal,
                "text": node.text,
                "table": node.table,
                "content_sha256": content_hash,
                "source_anchors": tuple(_unique_anchors(anchors)),
            }
        )

    children_by_ref: dict[str, list[str]] = {}
    for child_ref, parent_ref in parent_by_ref.items():
        if parent_ref is not None:
            children_by_ref.setdefault(parent_ref, []).append(child_ref)

    def parent_block_id(native_node_id: str) -> str | None:
        parent_ref = parent_by_ref[native_node_id]
        return block_id_by_ref[parent_ref] if parent_ref is not None else None

    blocks = tuple(
        CanonicalBlock(
            **values,
            parent_block_id=parent_block_id(values["native_node_id"]),
            child_block_ids=tuple(
                block_id_by_ref[child]
                for child in children_by_ref.get(values["native_node_id"], [])
            ),
        )
        for values in provisional
    )

    relationships = _build_relationships(
        integrity_report or {},
        resolve=resolve,
        block_id_by_ref=block_id_by_ref,
        scholarly_overlay=scholarly_overlay,
        grobid_product=grobid_product,
        diagnostics=diagnostics,
    )
    title = next(
        (block.text for block in blocks if block.kind is CanonicalBlockKind.TITLE),
        None,
    )
    if title is None:
        name = docling_document.get("name")
        title = normalize_canonical_text(name) if isinstance(name, str) else None
        title = title or None
    payload: dict[str, Any] = {
        "schema_version": CANONICAL_DOCUMENT_SCHEMA_VERSION,
        "artifact_id": artifact.artifact_id,
        "source_sha256": artifact.source_sha256,
        "normalization_policy": configuration.text_normalization,
        "anchoring_policy": configuration.anchoring_policy,
        "metadata": CanonicalDocumentMetadata(
            title=title,
            media_type=artifact.media_type,
            identifiers=artifact.identifiers,
        ),
        "source_products": products,
        "root_block_ids": tuple(
            block.block_id for block in blocks if block.parent_block_id is None
        ),
        "blocks": blocks,
        "relationships": relationships,
        "diagnostics": tuple(_unique_diagnostics(diagnostics)),
    }
    payload["view_id"] = canonical_view_id(_json_payload(payload))
    return CanonicalDocumentView.model_validate(payload)


def _collect_native_nodes(
    document: Mapping[str, Any],
    diagnostics: list[CanonicalMappingDiagnostic],
    docling_product: DataProductRef,
) -> tuple[_NativeNode, ...]:
    nodes: list[_NativeNode] = []
    for collection in ("texts", "tables", "pictures", "formulas", "groups"):
        values = document.get(collection, [])
        if not isinstance(values, list):
            diagnostics.append(
                _diagnostic(
                    severity=CanonicalDiagnosticSeverity.ERROR,
                    code="INVALID_NATIVE_COLLECTION",
                    message=f"Docling collection {collection!r} is not a list",
                    product_id=docling_product.product_id,
                    native_node_ids=(f"#/{collection}",),
                )
            )
            continue
        for index, raw_item in enumerate(values):
            canonical_ref = f"#/{collection}/{index}"
            if not isinstance(raw_item, Mapping):
                diagnostics.append(
                    _diagnostic(
                        severity=CanonicalDiagnosticSeverity.ERROR,
                        code="INVALID_NATIVE_NODE",
                        message="Docling collection item is not an object",
                        product_id=docling_product.product_id,
                        native_node_ids=(canonical_ref,),
                    )
                )
                continue
            item = dict(raw_item)
            declared = item.get("self_ref")
            declared_ref = (
                declared if isinstance(declared, str) and declared else canonical_ref
            )
            native_label_value = item.get("label")
            native_label = (
                native_label_value
                if isinstance(native_label_value, str) and native_label_value
                else collection.rstrip("s")
            )
            kind = _block_kind(collection, native_label)
            raw_text = _native_text(item)
            text = normalize_canonical_text(raw_text) or None
            table = _canonical_table(item) if kind is CanonicalBlockKind.TABLE else None
            nodes.append(
                _NativeNode(
                    canonical_ref=canonical_ref,
                    declared_ref=declared_ref,
                    collection=collection,
                    item=item,
                    native_label=native_label,
                    kind=kind,
                    text=text,
                    table=table,
                )
            )
    return tuple(nodes)


def _block_kind(collection: str, label: str) -> CanonicalBlockKind:
    normalized = label.casefold().replace("-", "_").replace(" ", "_")
    if collection == "tables":
        return CanonicalBlockKind.TABLE
    if collection == "pictures":
        return CanonicalBlockKind.FIGURE
    if collection == "formulas":
        return CanonicalBlockKind.FORMULA
    if collection == "groups":
        return CanonicalBlockKind.GROUP
    aliases = {
        "title": CanonicalBlockKind.TITLE,
        "document_title": CanonicalBlockKind.TITLE,
        "section_header": CanonicalBlockKind.SECTION,
        "section": CanonicalBlockKind.SECTION,
        "paragraph": CanonicalBlockKind.PARAGRAPH,
        "text": CanonicalBlockKind.PARAGRAPH,
        "list_item": CanonicalBlockKind.LIST_ITEM,
        "caption": CanonicalBlockKind.CAPTION,
        "formula": CanonicalBlockKind.FORMULA,
        "citation": CanonicalBlockKind.CITATION,
        "reference": CanonicalBlockKind.REFERENCE,
    }
    return aliases.get(normalized, CanonicalBlockKind.OTHER)


def _native_text(item: Mapping[str, Any]) -> str:
    for key in ("text", "orig", "caption_text", "name"):
        value = item.get(key)
        if isinstance(value, str):
            return value
    return ""


def _canonical_table(item: Mapping[str, Any]) -> CanonicalTable:
    data = item.get("data")
    if not isinstance(data, Mapping):
        return CanonicalTable()
    grid = data.get("grid") or data.get("table_cells")
    if not isinstance(grid, list):
        return CanonicalTable()
    rows: list[tuple[str, ...]] = []
    for raw_row in grid:
        if isinstance(raw_row, list):
            rows.append(tuple(normalize_canonical_text(str(cell)) for cell in raw_row))
        elif isinstance(raw_row, Mapping):
            value = raw_row.get("text")
            rows.append((normalize_canonical_text(str(value or "")),))
    return CanonicalTable(rows=tuple(rows))


def _child_references(item: Mapping[str, Any]) -> tuple[str, ...]:
    return _reference_values(item.get("children"))


def _reference_values(value: Any) -> tuple[str, ...]:
    if not isinstance(value, list):
        return ()
    references: list[str] = []
    for entry in value:
        if isinstance(entry, Mapping):
            reference = entry.get("$ref")
            if isinstance(reference, str) and reference:
                references.append(reference)
    return tuple(references)


def _build_relationships(
    integrity_report: Mapping[str, Any],
    *,
    resolve: Any,
    block_id_by_ref: Mapping[str, str],
    scholarly_overlay: ScholarlyAlignmentOverlay | None,
    grobid_product: DataProductRef | None,
    diagnostics: list[CanonicalMappingDiagnostic],
) -> tuple[CanonicalRelationship, ...]:
    records = integrity_report.get("records", [])
    if not isinstance(records, list):
        diagnostics.append(
            _diagnostic(
                severity=CanonicalDiagnosticSeverity.ERROR,
                code="INVALID_INTEGRITY_RELATIONSHIPS",
                message="Content-integrity records are not a list",
            )
        )
        return ()
    annotation_by_id = (
        {
            record.annotation.annotation_id: record.annotation
            for record in scholarly_overlay.records
        }
        if scholarly_overlay is not None
        else {}
    )
    relationships: list[CanonicalRelationship] = []
    for raw_record in records:
        if not isinstance(raw_record, Mapping):
            continue
        kind_value = raw_record.get("kind")
        if kind_value not in {"table", "figure", "citation"}:
            continue
        relation_kind = (
            CanonicalRelationshipKind.CITES
            if kind_value == "citation"
            else CanonicalRelationshipKind.HAS_CAPTION
        )
        source_ref = raw_record.get("source_docling_item_ref") or raw_record.get(
            "source_ref"
        )
        source_node = (
            resolve(str(source_ref), context="relationship source")
            if source_ref
            else None
        )
        source_block_id = (
            block_id_by_ref.get(source_node.canonical_ref)
            if source_node is not None
            else None
        )
        target_ids: list[str] = []
        for target_ref in _string_tuple(raw_record.get("resolved_docling_item_refs")):
            target_node = resolve(target_ref, context="relationship target")
            if target_node is not None:
                target_id = block_id_by_ref.get(target_node.canonical_ref)
                if target_id is not None:
                    target_ids.append(target_id)
        declared = _string_tuple(raw_record.get("declared_target_refs"))
        unresolved = _string_tuple(raw_record.get("unresolved_target_refs"))
        reasons = _string_tuple(raw_record.get("reason_codes"))
        if (
            source_block_id is not None
            and target_ids
            and not unresolved
            and not reasons
        ):
            status = CanonicalRelationshipStatus.RESOLVED
        elif source_block_id is not None and target_ids:
            status = CanonicalRelationshipStatus.PARTIAL
        else:
            status = CanonicalRelationshipStatus.UNRESOLVED
        source_anchor = None
        annotation_id = raw_record.get("source_ref")
        annotation = annotation_by_id.get(annotation_id)
        if annotation is not None and grobid_product is not None:
            source_anchor = CanonicalSourceAnchor(
                role=CanonicalAnchorRole.SCHOLARLY,
                product_id=grobid_product.product_id,
                node_id=annotation.tei_path,
                char_start=0,
                char_end=len(annotation.text),
            )
        relationship_id = canonical_relationship_id(
            kind=relation_kind,
            source_block_id=source_block_id,
            target_block_ids=tuple(dict.fromkeys(target_ids)),
            declared_target_refs=declared,
            unresolved_target_refs=unresolved,
            reason_codes=reasons,
            source_anchor=source_anchor,
        )
        relationships.append(
            CanonicalRelationship(
                relationship_id=relationship_id,
                kind=relation_kind,
                status=status,
                source_block_id=source_block_id,
                target_block_ids=tuple(dict.fromkeys(target_ids)),
                declared_target_refs=declared,
                unresolved_target_refs=unresolved,
                reason_codes=reasons,
                source_anchor=source_anchor,
            )
        )
        if status is not CanonicalRelationshipStatus.RESOLVED:
            diagnostics.append(
                _diagnostic(
                    severity=CanonicalDiagnosticSeverity.WARNING,
                    code="UNRESOLVED_CANONICAL_RELATIONSHIP",
                    message=f"{relation_kind.value} relationship did not resolve completely",
                    product_id=(
                        grobid_product.product_id
                        if annotation is not None and grobid_product
                        else None
                    ),
                    native_node_ids=tuple(
                        dict.fromkeys((str(source_ref), *declared, *unresolved))
                    ),
                )
            )
    return tuple(relationships)


def _diagnostic(
    *,
    severity: CanonicalDiagnosticSeverity,
    code: str,
    message: str,
    product_id: str | None = None,
    native_node_ids: tuple[str, ...] = (),
) -> CanonicalMappingDiagnostic:
    diagnostic_id = canonical_diagnostic_id(
        severity=severity,
        code=code,
        message=message,
        product_id=product_id,
        native_node_ids=native_node_ids,
    )
    return CanonicalMappingDiagnostic(
        diagnostic_id=diagnostic_id,
        severity=severity,
        code=code,
        message=message,
        product_id=product_id,
        native_node_ids=native_node_ids,
    )


def _unique_anchors(
    anchors: list[CanonicalSourceAnchor],
) -> tuple[CanonicalSourceAnchor, ...]:
    unique: dict[str, CanonicalSourceAnchor] = {}
    for anchor in anchors:
        key = json.dumps(
            anchor.model_dump(mode="json"),
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        unique.setdefault(key, anchor)
    return tuple(unique.values())


def _unique_diagnostics(
    diagnostics: list[CanonicalMappingDiagnostic],
) -> tuple[CanonicalMappingDiagnostic, ...]:
    return tuple(
        {diagnostic.diagnostic_id: diagnostic for diagnostic in diagnostics}.values()
    )


def _string_tuple(value: Any) -> tuple[str, ...]:
    if not isinstance(value, (list, tuple)):
        return ()
    return tuple(str(item) for item in value if isinstance(item, str) and item)


def _json_payload(payload: Mapping[str, Any]) -> dict[str, Any]:
    return cast(
        "dict[str, Any]",
        json.loads(
            json.dumps(
                payload,
                default=lambda value: value.model_dump(mode="json"),
                allow_nan=False,
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
            )
        ),
    )


def _canonical_hash(payload: Mapping[str, Any]) -> str:
    return sha256_bytes(
        json.dumps(
            payload,
            allow_nan=False,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    )


__all__ = [
    "CANONICAL_ANCHORING_POLICY",
    "CANONICAL_DOCUMENT_SCHEMA_VERSION",
    "CANONICAL_TEXT_NORMALIZATION",
    "CanonicalAnchorRole",
    "CanonicalBlock",
    "CanonicalBlockKind",
    "CanonicalDiagnosticSeverity",
    "CanonicalDocumentError",
    "CanonicalDocumentMetadata",
    "CanonicalDocumentView",
    "CanonicalMappingDiagnostic",
    "CanonicalRelationship",
    "CanonicalRelationshipKind",
    "CanonicalRelationshipStatus",
    "CanonicalSourceAnchor",
    "CanonicalTable",
    "CanonicalizationConfig",
    "InvalidCanonicalDocumentError",
    "UnsupportedCanonicalDocumentVersionError",
    "build_canonical_document_view",
    "canonical_block_content_sha256",
    "canonical_block_id",
    "canonical_document_bytes",
    "canonical_view_id",
    "load_canonical_document",
    "normalize_canonical_text",
]
