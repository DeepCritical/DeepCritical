from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from typing import Any

import pytest
from pydantic import ValidationError

from DeepResearch.src.document_processing.alignment import DoclingGrobidAligner
from DeepResearch.src.document_processing.canonical import (
    CANONICAL_DOCUMENT_SCHEMA_VERSION,
    CanonicalAnchorRole,
    CanonicalBlock,
    CanonicalBlockKind,
    CanonicalDiagnosticSeverity,
    CanonicalDocumentError,
    CanonicalDocumentView,
    CanonicalizationConfig,
    CanonicalMappingDiagnostic,
    CanonicalRelationship,
    CanonicalRelationshipKind,
    CanonicalRelationshipStatus,
    CanonicalSourceAnchor,
    CanonicalTable,
    InvalidCanonicalDocumentError,
    UnsupportedCanonicalDocumentVersionError,
    build_canonical_document_view,
    canonical_block_content_sha256,
    canonical_block_id,
    canonical_diagnostic_id,
    canonical_document_bytes,
    canonical_relationship_id,
    canonical_view_id,
    load_canonical_document,
    normalize_canonical_text,
)
from DeepResearch.src.document_processing.models import (
    ArtifactLocation,
    ArtifactLocationRole,
    BioCLocator,
    ContentSpan,
    ContentSpanSet,
    DocumentArtifact,
    JatsLocator,
    PdfBoundingBox,
    PdfLocator,
    RepresentationAnchor,
    sha256_bytes,
)
from DeepResearch.src.document_processing.products import build_data_product_ref
from DeepResearch.src.document_processing.storage import ContentAddressedStore
from DeepResearch.src.document_processing.validation import validate_content_integrity

FIXTURE_ROOT = (
    Path(__file__).parents[1] / "fixtures" / "document_processing" / "canonical"
)


def _document() -> dict[str, Any]:
    return {
        "schema_name": "DoclingDocument",
        "version": "1.0.0",
        "name": "Fallback title",
        "body": {
            "self_ref": "#/body",
            "children": [
                {"$ref": "#/groups/0"},
                {"$ref": "#/tables/0"},
                {"$ref": "#/pictures/0"},
                {"$ref": "#/formulas/0"},
            ],
        },
        "groups": [
            {
                "self_ref": "#/groups/0",
                "label": "section_group",
                "children": [
                    {"$ref": "#/texts/0"},
                    {"$ref": "#/texts/1"},
                    {"$ref": "#/texts/2"},
                    {"$ref": "#/texts/5"},
                    {"$ref": "#/texts/6"},
                ],
            }
        ],
        "texts": [
            {
                "self_ref": "#/texts/0",
                "label": "title",
                "text": "  APOE4\tpathway  ",
            },
            {
                "self_ref": "#/texts/1",
                "label": "section_header",
                "text": "Methods",
            },
            {
                "self_ref": "#/texts/2",
                "label": "paragraph",
                "text": "Endosomal pH was measured.",
            },
            {
                "self_ref": "#/texts/3",
                "label": "caption",
                "text": "Table 1. Cohort.",
            },
            {
                "self_ref": "#/texts/4",
                "label": "caption",
                "text": "Figure 1. Endosomes.",
            },
            {
                "self_ref": "#/texts/5",
                "label": "citation",
                "text": "[1]",
            },
            {
                "self_ref": "#/texts/6",
                "label": "reference",
                "text": "Smith 2026 endosomal study.",
            },
        ],
        "tables": [
            {
                "self_ref": "#/tables/0",
                "label": "table",
                "captions": [{"$ref": "#/texts/3"}],
                "data": {"grid": [["Group", "N"], ["APOE4", 12]]},
            }
        ],
        "pictures": [
            {
                "self_ref": "#/pictures/0",
                "label": "picture",
                "captions": [{"$ref": "#/texts/4"}],
            }
        ],
        "formulas": [
            {
                "self_ref": "#/formulas/0",
                "label": "formula",
                "text": "pH = -log10[H+]",
            }
        ],
        "key_value_items": [],
        "pages": {"1": {"page_no": 1}},
    }


def _tei() -> bytes:
    return b"""<TEI xmlns="http://www.tei-c.org/ns/1.0"><text><body>
    <p><ref type="bibr" target="#b1">[1]</ref></p>
    </body><back><listBibl><biblStruct xml:id="b1">
    Smith 2026 endosomal study.
    </biblStruct></listBibl></back></text></TEI>"""


def _product(
    name: str,
    digest_character: str,
    *,
    artifact_id: str,
    producer_run_id: str,
):
    return build_data_product_ref(
        name=name,
        blob_sha256=digest_character * 64,
        uri=f"cas://sha256/{digest_character * 64}",
        byte_size=64,
        producer_run_id=producer_run_id,
        source_artifact_ids=(artifact_id,),
    )


def _locator(format_name: str, index: int, length: int):
    if format_name == "pdf":
        return PdfLocator(
            page_number=1,
            bounding_box=PdfBoundingBox(
                left=10,
                top=10 + index,
                right=90,
                bottom=20 + index,
                page_width=100,
                page_height=100,
            ),
        )
    if format_name == "jats":
        return JatsLocator(
            xml_id=f"node-{index}",
            xpath=f"/article[1]/body[1]/p[{index + 1}]",
        )
    return BioCLocator(
        document_index=0,
        document_id="PMC-CANONICAL",
        passage_index=index,
        offset=index * 100,
        length=length,
    )


def _fixture(format_name: str) -> CanonicalDocumentView:
    document = _document()
    artifact_id = f"canonical-{format_name}"
    source_bytes = f"source-{format_name}".encode()
    source_sha256 = sha256_bytes(source_bytes)
    artifact = DocumentArtifact(
        artifact_id=artifact_id,
        source_sha256=source_sha256,
        acquisition_uri=f"https://example.test/{artifact_id}",
        identifiers={"pmc": "PMC-CANONICAL"},
        media_type={
            "pdf": "application/pdf",
            "jats": "application/xml",
            "bioc": "application/bioc+json",
        }[format_name],
        raw_location=ArtifactLocation(
            uri=f"cas://sha256/{source_sha256}",
            sha256=source_sha256,
            byte_size=len(source_bytes),
            media_type={
                "pdf": "application/pdf",
                "jats": "application/xml",
                "bioc": "application/bioc+json",
            }[format_name],
            role=ArtifactLocationRole.RAW,
        ),
    )
    producer = f"docling-{format_name}"
    docling_product = _product(
        "docling_document",
        "a",
        artifact_id=artifact_id,
        producer_run_id=producer,
    )
    content_spans_product = _product(
        "content_spans",
        "b",
        artifact_id=artifact_id,
        producer_run_id=producer,
    )
    grobid_product = _product(
        "grobid_tei",
        "c",
        artifact_id=artifact_id,
        producer_run_id=f"grobid-{format_name}",
    )
    alignment_product = _product(
        "alignment_overlay",
        "d",
        artifact_id=artifact_id,
        producer_run_id=f"alignment-{format_name}",
    )
    integrity_product = _product(
        "content_integrity_overlay",
        "e",
        artifact_id=artifact_id,
        producer_run_id=f"integrity-{format_name}",
    )
    text_nodes = [
        (f"#/texts/{index}", item["text"])
        for index, item in enumerate(document["texts"])
    ] + [("#/formulas/0", document["formulas"][0]["text"])]
    spans = tuple(
        ContentSpan(
            span_id=f"span-{format_name}-{index}",
            artifact_id=artifact_id,
            processing_run_id=producer,
            representation_anchor=RepresentationAnchor(
                product_id=docling_product.product_id,
                node_id=node_id,
                char_start=0,
                char_end=len(text),
            ),
            content_sha256=sha256_bytes(text.encode()),
            source_locator=_locator(format_name, index, len(text)),
        )
        for index, (node_id, text) in enumerate(text_nodes)
    )
    span_set = ContentSpanSet(
        artifact_id=artifact_id,
        processing_run_id=producer,
        representation_product_id=docling_product.product_id,
        spans=spans,
    )
    overlay = DoclingGrobidAligner(minimum_score=0.7).align(document, _tei())
    integrity = validate_content_integrity(
        document, scholarly_overlay=overlay
    ).to_dict()
    return build_canonical_document_view(
        artifact=artifact,
        docling_document=document,
        docling_product=docling_product,
        content_span_set=span_set,
        source_products=(
            docling_product,
            content_spans_product,
            grobid_product,
            alignment_product,
            integrity_product,
        ),
        configuration=CanonicalizationConfig(),
        scholarly_overlay=overlay,
        integrity_report=integrity,
    )


def _summary(view: CanonicalDocumentView) -> dict[str, Any]:
    blocks = {block.block_id: block for block in view.blocks}
    located_text_blocks = sum(
        bool(
            block.text
            and any(
                anchor.source_locator is not None for anchor in block.source_anchors
            )
        )
        for block in view.blocks
    )
    text_blocks = sum(block.text is not None for block in view.blocks)
    return {
        "schema_version": view.schema_version,
        "metadata_title": view.metadata.title,
        "block_kinds": [block.kind.value for block in view.blocks],
        "root_kinds": [blocks[block_id].kind.value for block_id in view.root_block_ids],
        "relationship_kinds": [relation.kind.value for relation in view.relationships],
        "relationship_statuses": [
            relation.status.value for relation in view.relationships
        ],
        "source_locator_kinds": sorted(
            {
                anchor.source_locator.kind
                for block in view.blocks
                for anchor in block.source_anchors
                if anchor.source_locator is not None
            }
        ),
        "source_product_names": [product.name for product in view.source_products],
        "diagnostic_codes": [diagnostic.code for diagnostic in view.diagnostics],
        "text_blocks": text_blocks,
        "located_text_blocks": located_text_blocks,
    }


@pytest.mark.parametrize("format_name", ["pdf", "jats", "bioc"])
def test_golden_canonical_views_are_deterministic_and_fully_anchored(
    format_name: str,
) -> None:
    first = _fixture(format_name)
    second = _fixture(format_name)
    expected = json.loads(
        (FIXTURE_ROOT / f"{format_name}.json").read_text(encoding="utf-8")
    )

    assert first == second
    assert canonical_document_bytes(first) == canonical_document_bytes(second)
    assert _summary(first) == expected
    assert first.view_id.startswith("canonical-view-")
    assert all(block.block_id.startswith("block-") for block in first.blocks)
    assert _summary(first)["text_blocks"] == _summary(first)["located_text_blocks"]
    assert all(
        relation.status is CanonicalRelationshipStatus.RESOLVED
        for relation in first.relationships
    )


def test_normalization_and_table_content_are_processor_independent() -> None:
    view = _fixture("pdf")

    assert normalize_canonical_text(" A\tB\nC ") == "A B C"
    title = next(
        block for block in view.blocks if block.kind is CanonicalBlockKind.TITLE
    )
    table = next(
        block for block in view.blocks if block.kind is CanonicalBlockKind.TABLE
    )
    assert title.text == "APOE4 pathway"
    assert table.table is not None
    assert table.table.rows == (("Group", "N"), ("APOE4", "12"))


def test_canonical_schema_dispatch_rejects_unknown_and_invalid_payloads() -> None:
    view = _fixture("jats")
    payload = json.loads(canonical_document_bytes(view))

    payload["schema_version"] = "deepcritical-canonical-document-view-v99"
    with pytest.raises(UnsupportedCanonicalDocumentVersionError, match="v99"):
        load_canonical_document(json.dumps(payload).encode())
    payload.pop("schema_version")
    with pytest.raises(UnsupportedCanonicalDocumentVersionError, match="None"):
        load_canonical_document(json.dumps(payload).encode())
    with pytest.raises(InvalidCanonicalDocumentError, match="valid JSON"):
        load_canonical_document(b"{not-json")
    with pytest.raises(InvalidCanonicalDocumentError, match="JSON object"):
        load_canonical_document(b"[]")

    tampered = json.loads(canonical_document_bytes(view))
    tampered["blocks"][0]["content_sha256"] = "0" * 64
    with pytest.raises(InvalidCanonicalDocumentError, match="contract"):
        load_canonical_document(json.dumps(tampered).encode())


def test_canonical_configuration_is_closed_and_typed() -> None:
    with pytest.raises(ValidationError):
        CanonicalizationConfig(text_normalization="lowercase-v1")
    with pytest.raises(ValidationError):
        CanonicalizationConfig(extra_policy="not-allowed")


def test_store_round_trip_dispatches_canonical_product_schema(tmp_path: Path) -> None:
    store = ContentAddressedStore(tmp_path / "store")
    source = store.put_blob(b"canonical-source")
    artifact = DocumentArtifact(
        artifact_id="canonical-persisted",
        source_sha256=source.sha256,
        acquisition_uri="https://example.test/canonical-persisted",
        media_type="application/pdf",
        raw_location=source.as_location(
            media_type="application/pdf", role=ArtifactLocationRole.RAW
        ),
    )
    store.save_artifact(artifact)
    view = _fixture("pdf").model_copy(
        update={
            "artifact_id": artifact.artifact_id,
            "source_sha256": artifact.source_sha256,
        }
    )
    payload = view.model_dump(mode="json")
    payload["view_id"] = "pending"
    payload["view_id"] = canonical_view_id(payload)
    persisted_view = CanonicalDocumentView.model_validate(payload)
    blob = store.put_canonical_document(persisted_view)
    product = build_data_product_ref(
        name="canonical_document_view",
        blob_sha256=blob.sha256,
        uri=blob.uri,
        byte_size=blob.byte_size,
        producer_run_id="canonical-run",
        source_artifact_ids=(artifact.artifact_id,),
    )

    assert store.read_canonical_document(product) == persisted_view
    with pytest.raises(ValueError, match="not a canonical"):
        store.read_canonical_document(
            build_data_product_ref(
                name="docling_document",
                blob_sha256=blob.sha256,
                uri=blob.uri,
                byte_size=blob.byte_size,
                producer_run_id="canonical-run",
                source_artifact_ids=(artifact.artifact_id,),
            )
        )


def test_explicit_diagnostics_preserve_unresolved_native_mapping() -> None:
    view = _fixture("bioc")
    document = _document()
    document["body"]["children"].append({"$ref": "#/texts/404"})
    broken_integrity = {
        "records": [
            {
                "kind": "figure",
                "source_ref": "#/pictures/0",
                "source_docling_item_ref": "#/pictures/0",
                "declared_target_refs": ["#/texts/404"],
                "resolved_docling_item_refs": [],
                "unresolved_target_refs": ["#/texts/404"],
                "reason_codes": ["caption_target_not_found"],
            }
        ]
    }
    base = _fixture_inputs("bioc", document)
    broken = build_canonical_document_view(
        **base,
        integrity_report=broken_integrity,
    )

    assert view.diagnostics == ()
    assert {diagnostic.code for diagnostic in broken.diagnostics} == {
        "UNRESOLVED_NATIVE_REFERENCE",
        "UNRESOLVED_CANONICAL_RELATIONSHIP",
    }
    assert broken.relationships[0].status is CanonicalRelationshipStatus.UNRESOLVED


def _fixture_inputs(format_name: str, document: dict[str, Any]) -> dict[str, Any]:
    complete = _fixture(format_name)
    docling_product = next(
        product
        for product in complete.source_products
        if product.name == "docling_document"
    )
    content_product = next(
        product
        for product in complete.source_products
        if product.name == "content_spans"
    )
    artifact_source = f"source-{format_name}".encode()
    artifact = DocumentArtifact(
        artifact_id=complete.artifact_id,
        source_sha256=sha256_bytes(artifact_source),
        acquisition_uri=f"https://example.test/{complete.artifact_id}",
        identifiers={"pmc": "PMC-CANONICAL"},
        media_type=complete.metadata.media_type,
        raw_location=ArtifactLocation(
            uri=f"cas://sha256/{sha256_bytes(artifact_source)}",
            sha256=sha256_bytes(artifact_source),
            byte_size=len(artifact_source),
            media_type=complete.metadata.media_type,
            role=ArtifactLocationRole.RAW,
        ),
    )
    text_spans = tuple(
        ContentSpan(
            span_id=f"broken-{index}",
            artifact_id=complete.artifact_id,
            processing_run_id=docling_product.producer_run_id,
            representation_anchor=RepresentationAnchor(
                product_id=docling_product.product_id,
                node_id=f"#/texts/{index}",
                char_start=0,
                char_end=len(item["text"]),
            ),
            content_sha256=sha256_bytes(item["text"].encode()),
            source_locator=_locator(format_name, index, len(item["text"])),
        )
        for index, item in enumerate(document["texts"])
    )
    formula_text = document["formulas"][0]["text"]
    formula_span = ContentSpan(
        span_id="broken-formula",
        artifact_id=complete.artifact_id,
        processing_run_id=docling_product.producer_run_id,
        representation_anchor=RepresentationAnchor(
            product_id=docling_product.product_id,
            node_id="#/formulas/0",
            char_start=0,
            char_end=len(formula_text),
        ),
        content_sha256=sha256_bytes(formula_text.encode()),
        source_locator=_locator(format_name, len(document["texts"]), len(formula_text)),
    )
    return {
        "artifact": artifact,
        "docling_document": document,
        "docling_product": docling_product,
        "content_span_set": ContentSpanSet(
            artifact_id=complete.artifact_id,
            processing_run_id=docling_product.producer_run_id,
            representation_product_id=docling_product.product_id,
            spans=(*text_spans, formula_span),
        ),
        "source_products": (docling_product, content_product),
        "configuration": CanonicalizationConfig(),
    }


def test_view_contract_rejects_tampered_graph_and_identity() -> None:
    view = _fixture("pdf")
    payload = json.loads(canonical_document_bytes(view))
    payload["root_block_ids"] = payload["root_block_ids"][1:]
    payload["view_id"] = "pending"
    payload["view_id"] = canonical_view_id(payload)

    with pytest.raises(ValidationError, match="roots"):
        CanonicalDocumentView.model_validate(payload)

    duplicate = deepcopy(json.loads(canonical_document_bytes(view)))
    duplicate["source_products"].append(duplicate["source_products"][0])
    duplicate["view_id"] = canonical_view_id(duplicate)
    with pytest.raises(ValidationError, match="source products"):
        CanonicalDocumentView.model_validate(duplicate)

    empty = deepcopy(json.loads(canonical_document_bytes(view)))
    empty["blocks"] = []
    empty["root_block_ids"] = []
    empty["view_id"] = canonical_view_id(empty)
    with pytest.raises(ValidationError, match="at least 1 item"):
        CanonicalDocumentView.model_validate(empty)


def _identify_block(payload: dict[str, Any]) -> None:
    kind = CanonicalBlockKind(payload["kind"])
    table = (
        CanonicalTable.model_validate(payload["table"])
        if payload.get("table") is not None
        else None
    )
    payload["content_sha256"] = canonical_block_content_sha256(
        kind=kind,
        text=payload.get("text"),
        table=table,
    )
    payload["block_id"] = canonical_block_id(
        native_node_id=payload["native_node_id"],
        kind=kind,
        content_sha256=payload["content_sha256"],
    )


def _identify_relationship(payload: dict[str, Any]) -> None:
    anchor = (
        CanonicalSourceAnchor.model_validate(payload["source_anchor"])
        if payload.get("source_anchor") is not None
        else None
    )
    payload["relationship_id"] = canonical_relationship_id(
        kind=CanonicalRelationshipKind(payload["kind"]),
        source_block_id=payload.get("source_block_id"),
        target_block_ids=tuple(payload.get("target_block_ids", ())),
        declared_target_refs=tuple(payload.get("declared_target_refs", ())),
        unresolved_target_refs=tuple(payload.get("unresolved_target_refs", ())),
        reason_codes=tuple(payload.get("reason_codes", ())),
        source_anchor=anchor,
    )


def _identify_diagnostic(payload: dict[str, Any]) -> None:
    payload["diagnostic_id"] = canonical_diagnostic_id(
        severity=CanonicalDiagnosticSeverity(payload["severity"]),
        code=payload["code"],
        message=payload["message"],
        product_id=payload.get("product_id"),
        native_node_ids=tuple(payload.get("native_node_ids", ())),
    )


def _validate_tampered_view(payload: dict[str, Any], match: str) -> None:
    payload["view_id"] = canonical_view_id(payload)
    with pytest.raises(ValidationError, match=match):
        CanonicalDocumentView.model_validate(payload)


def test_nested_contracts_reject_inconsistent_identifiers_and_content() -> None:
    view = _fixture("pdf")

    for anchor, match in (
        (
            {
                "role": "primary",
                "product_id": "product",
                "node_id": "node",
                "char_start": 0,
            },
            "bounds must be paired",
        ),
        (
            {
                "role": "primary",
                "product_id": "product",
                "node_id": "node",
                "char_start": 1,
                "char_end": 1,
            },
            "char_end must exceed",
        ),
        (
            {
                "role": "primary",
                "product_id": " ",
                "node_id": "node",
            },
            "identifiers must not be empty",
        ),
    ):
        with pytest.raises(ValidationError, match=match):
            CanonicalSourceAnchor.model_validate(anchor)

    title = next(
        block for block in view.blocks if block.kind is CanonicalBlockKind.TITLE
    )
    invalid_block_id = title.model_dump(mode="json")
    invalid_block_id["block_id"] = "block-wrong"
    with pytest.raises(ValidationError, match="block ID"):
        CanonicalBlock.model_validate(invalid_block_id)

    table_as_paragraph = next(
        block for block in view.blocks if block.kind is CanonicalBlockKind.TABLE
    ).model_dump(mode="json")
    table_as_paragraph["kind"] = "paragraph"
    _identify_block(table_as_paragraph)
    with pytest.raises(ValidationError, match="only table"):
        CanonicalBlock.model_validate(table_as_paragraph)

    empty_text = title.model_dump(mode="json")
    empty_text["text"] = ""
    _identify_block(empty_text)
    with pytest.raises(ValidationError, match="text must be non-empty"):
        CanonicalBlock.model_validate(empty_text)

    group = next(
        block for block in view.blocks if block.kind is CanonicalBlockKind.GROUP
    )
    duplicate_child = group.model_dump(mode="json")
    duplicate_child["child_block_ids"].append(duplicate_child["child_block_ids"][0])
    with pytest.raises(ValidationError, match="child block IDs"):
        CanonicalBlock.model_validate(duplicate_child)

    duplicate_anchor = title.model_dump(mode="json")
    duplicate_anchor["source_anchors"].append(duplicate_anchor["source_anchors"][0])
    with pytest.raises(ValidationError, match="source anchors"):
        CanonicalBlock.model_validate(duplicate_anchor)

    resolved = view.relationships[0].model_dump(mode="json")
    wrong_relationship_id = deepcopy(resolved)
    wrong_relationship_id["relationship_id"] = "relationship-wrong"
    with pytest.raises(ValidationError, match="relationship ID"):
        CanonicalRelationship.model_validate(wrong_relationship_id)

    duplicate_target = deepcopy(resolved)
    duplicate_target["target_block_ids"].append(duplicate_target["target_block_ids"][0])
    _identify_relationship(duplicate_target)
    with pytest.raises(ValidationError, match="targets must be unique"):
        CanonicalRelationship.model_validate(duplicate_target)

    incomplete_resolved = deepcopy(resolved)
    incomplete_resolved["reason_codes"] = ["not-complete"]
    _identify_relationship(incomplete_resolved)
    with pytest.raises(ValidationError, match="resolve completely"):
        CanonicalRelationship.model_validate(incomplete_resolved)

    unresolved_with_targets = deepcopy(resolved)
    unresolved_with_targets["status"] = "unresolved"
    _identify_relationship(unresolved_with_targets)
    with pytest.raises(ValidationError, match="status='partial'"):
        CanonicalRelationship.model_validate(unresolved_with_targets)

    diagnostic = {
        "diagnostic_id": "canonical-diagnostic-wrong",
        "severity": "warning",
        "code": "TEST",
        "message": "test diagnostic",
    }
    with pytest.raises(ValidationError, match="diagnostic ID"):
        CanonicalMappingDiagnostic.model_validate(diagnostic)
    diagnostic["code"] = " "
    _identify_diagnostic(diagnostic)
    with pytest.raises(ValidationError, match="must not be empty"):
        CanonicalMappingDiagnostic.model_validate(diagnostic)


def test_view_contract_rejects_every_inconsistent_graph_edge() -> None:
    view = _fixture("pdf")
    base = json.loads(canonical_document_bytes(view))

    duplicate_block = deepcopy(base)
    duplicate_block["blocks"].append(deepcopy(duplicate_block["blocks"][0]))
    _validate_tampered_view(duplicate_block, "block IDs must be unique")

    noncontiguous = deepcopy(base)
    noncontiguous["blocks"][1]["ordinal"] = 99
    _validate_tampered_view(noncontiguous, "ordinals must be contiguous")

    duplicate_root = deepcopy(base)
    duplicate_root["root_block_ids"].append(duplicate_root["root_block_ids"][0])
    _validate_tampered_view(duplicate_root, "root block IDs must be unique")

    missing_parent_link = deepcopy(base)
    missing_parent_link["blocks"][0]["child_block_ids"].remove(
        missing_parent_link["blocks"][1]["block_id"]
    )
    _validate_tampered_view(missing_parent_link, "parent and child links")

    parent_after_child = deepcopy(base)
    parent_after_child["blocks"][0], parent_after_child["blocks"][1] = (
        parent_after_child["blocks"][1],
        parent_after_child["blocks"][0],
    )
    for ordinal, block in enumerate(parent_after_child["blocks"]):
        block["ordinal"] = ordinal
    parent_after_child["root_block_ids"] = [
        block["block_id"]
        for block in parent_after_child["blocks"]
        if block["parent_block_id"] is None
    ]
    _validate_tampered_view(parent_after_child, "parents must precede")

    wrong_child_parent = deepcopy(base)
    root_without_parent = next(
        block
        for block in wrong_child_parent["blocks"]
        if block["parent_block_id"] is None and block["kind"] == "table"
    )
    wrong_child_parent["blocks"][0]["child_block_ids"].append(
        root_without_parent["block_id"]
    )
    _validate_tampered_view(wrong_child_parent, "child and parent links")

    unknown_anchor_product = deepcopy(base)
    unknown_anchor_product["blocks"][0]["source_anchors"][0]["product_id"] = (
        "product-missing"
    )
    _validate_tampered_view(unknown_anchor_product, "unknown product")

    duplicate_relationship = deepcopy(base)
    duplicate_relationship["relationships"].append(
        deepcopy(duplicate_relationship["relationships"][0])
    )
    _validate_tampered_view(duplicate_relationship, "relationship IDs must be unique")

    unknown_relationship_source = deepcopy(base)
    relation = unknown_relationship_source["relationships"][0]
    relation["source_block_id"] = "block-missing"
    _identify_relationship(relation)
    _validate_tampered_view(unknown_relationship_source, "source does not exist")

    unknown_relationship_target = deepcopy(base)
    relation = unknown_relationship_target["relationships"][0]
    relation["target_block_ids"] = ["block-missing"]
    _identify_relationship(relation)
    _validate_tampered_view(unknown_relationship_target, "target does not exist")

    unknown_relationship_anchor = deepcopy(base)
    relation = unknown_relationship_anchor["relationships"][-1]
    assert relation["source_anchor"] is not None
    relation["source_anchor"]["product_id"] = "product-missing"
    _identify_relationship(relation)
    _validate_tampered_view(unknown_relationship_anchor, "relationship anchor product")

    diagnostic = {
        "severity": "warning",
        "code": "GRAPH_TEST",
        "message": "graph diagnostic",
        "product_id": base["source_products"][0]["product_id"],
        "native_node_ids": [],
    }
    _identify_diagnostic(diagnostic)
    duplicate_diagnostic = deepcopy(base)
    duplicate_diagnostic["diagnostics"] = [diagnostic, deepcopy(diagnostic)]
    _validate_tampered_view(duplicate_diagnostic, "diagnostic IDs must be unique")

    unknown_diagnostic_product = deepcopy(base)
    diagnostic["product_id"] = "product-missing"
    _identify_diagnostic(diagnostic)
    unknown_diagnostic_product["diagnostics"] = [diagnostic]
    _validate_tampered_view(unknown_diagnostic_product, "diagnostic product")

    wrong_view_id = deepcopy(base)
    wrong_view_id["view_id"] = "canonical-view-wrong"
    with pytest.raises(ValidationError, match="view ID"):
        CanonicalDocumentView.model_validate(wrong_view_id)


def test_builder_rejects_products_that_do_not_match_native_inputs() -> None:
    inputs = _fixture_inputs("pdf", _document())
    docling_product = inputs["docling_product"]

    inputs["source_products"] = tuple(
        product
        for product in inputs["source_products"]
        if product.product_id != docling_product.product_id
    )
    with pytest.raises(CanonicalDocumentError, match="must be a canonical source"):
        build_canonical_document_view(**inputs)

    inputs = _fixture_inputs("pdf", _document())
    inputs["content_span_set"] = inputs["content_span_set"].model_copy(
        update={"representation_product_id": "product-missing"}
    )
    with pytest.raises(CanonicalDocumentError, match="different Docling product"):
        build_canonical_document_view(**inputs)


def test_builder_reports_malformed_native_structures_and_missing_anchors() -> None:
    document = _document()
    inputs = _fixture_inputs("pdf", document)
    malformed = {
        "name": " Fallback\tTitle ",
        "body": "not-an-object",
        "texts": [
            42,
            {
                "self_ref": "declared-text",
                "label": "unknown-native-label",
                "orig": "Native text",
            },
        ],
        "tables": [
            {"self_ref": "#/tables/0", "label": "table"},
            {
                "self_ref": "#/tables/1",
                "label": "table",
                "data": {"grid": "not-a-list"},
            },
            {
                "self_ref": "#/tables/2",
                "label": "table",
                "data": {"table_cells": [{"text": " Cell\nvalue "}, 3]},
            },
        ],
        "pictures": "not-a-list",
        "formulas": [],
        "groups": [{"self_ref": "#/groups/0", "children": "not-a-list"}],
    }
    inputs["docling_document"] = malformed
    view = build_canonical_document_view(
        **inputs,
        integrity_report={"records": "not-a-list"},
    )

    assert view.metadata.title == "Fallback Title"
    assert {diagnostic.code for diagnostic in view.diagnostics} == {
        "INVALID_INTEGRITY_RELATIONSHIPS",
        "INVALID_NATIVE_COLLECTION",
        "INVALID_NATIVE_NODE",
        "MISSING_DOCUMENT_BODY",
        "MISSING_SOURCE_SPAN",
    }
    tables = [block for block in view.blocks if block.kind is CanonicalBlockKind.TABLE]
    assert tables[0].table == CanonicalTable()
    assert tables[1].table == CanonicalTable()
    assert tables[2].table == CanonicalTable(rows=(("Cell value",),))
    assert any(block.kind is CanonicalBlockKind.OTHER for block in view.blocks)

    invalid_children = _document()
    invalid_children["groups"][0]["children"] = "not-a-list"
    child_inputs = _fixture_inputs("pdf", _document())
    child_inputs["docling_document"] = invalid_children
    child_view = build_canonical_document_view(**child_inputs)
    group = next(
        block for block in child_view.blocks if block.kind is CanonicalBlockKind.GROUP
    )
    assert group.child_block_ids == ()


def test_builder_preserves_ambiguous_partial_and_scholarly_diagnostics() -> None:
    document = _document()
    document["groups"][0]["children"][0] = {"$ref": "declared-title"}
    document["texts"][0]["self_ref"] = "declared-title"
    document["texts"][1]["self_ref"] = "ambiguous"
    document["texts"][2]["self_ref"] = "ambiguous"
    document["groups"][0]["children"].append({"$ref": "ambiguous"})
    inputs = _fixture_inputs("pdf", _document())
    inputs["docling_document"] = document
    inputs["integrity_report"] = {
        "records": [
            42,
            {"kind": "other"},
            {
                "kind": "figure",
                "source_ref": "#/pictures/0",
                "source_docling_item_ref": "#/pictures/0",
                "declared_target_refs": ["#/texts/4"],
                "resolved_docling_item_refs": ["#/texts/4"],
                "unresolved_target_refs": ["#/texts/404"],
                "reason_codes": ["one-target-missing"],
            },
            {
                "kind": "citation",
                "source_ref": "#/texts/5",
                "resolved_docling_item_refs": "not-a-list",
            },
        ]
    }
    view = build_canonical_document_view(**inputs)

    assert CanonicalRelationshipStatus.PARTIAL in {
        relationship.status for relationship in view.relationships
    }
    assert "AMBIGUOUS_NATIVE_REFERENCE" in {
        diagnostic.code for diagnostic in view.diagnostics
    }

    overlay = DoclingGrobidAligner(minimum_score=0.7).align(_document(), _tei())
    missing_product_inputs = _fixture_inputs("pdf", _document())
    missing_product = build_canonical_document_view(
        **missing_product_inputs,
        scholarly_overlay=overlay,
    )
    assert "MISSING_GROBID_SOURCE_PRODUCT" in {
        diagnostic.code for diagnostic in missing_product.diagnostics
    }

    unrelated_overlay = DoclingGrobidAligner(minimum_score=1.0).align(
        _document(),
        b'<TEI xmlns="http://www.tei-c.org/ns/1.0"><text><body><p>'
        b"No native block contains this scholarly sentence."
        b"</p></body></text></TEI>",
    )
    assert unrelated_overlay.unaligned_count == 1
    with_product_inputs = _fixture_inputs("pdf", _document())
    grobid_product = _product(
        "grobid_tei",
        "f",
        artifact_id=with_product_inputs["artifact"].artifact_id,
        producer_run_id="grobid-unresolved",
    )
    with_product_inputs["source_products"] = (
        *with_product_inputs["source_products"],
        grobid_product,
    )
    unresolved = build_canonical_document_view(
        **with_product_inputs,
        scholarly_overlay=unrelated_overlay,
    )
    assert "UNRESOLVED_SCHOLARLY_ANCHOR" in {
        diagnostic.code for diagnostic in unresolved.diagnostics
    }


def test_schema_version_constant_is_descriptive() -> None:
    assert CANONICAL_DOCUMENT_SCHEMA_VERSION == (
        "deepcritical-canonical-document-view-v1"
    )
