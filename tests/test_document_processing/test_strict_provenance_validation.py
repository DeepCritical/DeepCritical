from __future__ import annotations

from copy import deepcopy
from typing import Any

import pytest

from DeepResearch.src.document_processing.adapters import NativeTextLocator
from DeepResearch.src.document_processing.validation import (
    DoclingQualityValidator,
    align_bioc_content_spans,
    build_docling_content_spans,
    build_pdf_content_spans,
    probably_image_only,
)


def _bbox(**overrides: Any) -> dict[str, Any]:
    value: dict[str, Any] = {
        "l": 10,
        "t": 30,
        "r": 90,
        "b": 10,
        "coord_origin": "BOTTOMLEFT",
    }
    value.update(overrides)
    return value


def _document(*, item_count: int = 1) -> dict[str, Any]:
    texts = [
        {
            "self_ref": f"#/texts/{index}",
            "label": "paragraph",
            "text": "abcdefghij",
            "prov": [{"page_no": 1, "bbox": _bbox()}],
        }
        for index in range(item_count)
    ]
    return {
        "schema_name": "DoclingDocument",
        "version": "1.0.0",
        "name": "paper",
        "body": {
            "self_ref": "#/body",
            "children": [{"$ref": f"#/texts/{index}"} for index in range(item_count)],
        },
        "furniture": {"self_ref": "#/furniture", "children": []},
        "groups": [],
        "texts": texts,
        "tables": [],
        "pictures": [],
        "key_value_items": [],
        "pages": {
            "1": {
                "page_no": 1,
                "size": {"width": 100, "height": 100},
            }
        },
    }


@pytest.mark.parametrize(
    "charspan",
    [
        [-1, 3],
        [0, 11],
        [4, 4],
        [8, 2],
        [False, 2],
        [0.0, 2],
        [0],
        "0,2",
    ],
)
def test_invalid_character_ranges_are_rejected_without_clamping(
    charspan: object,
) -> None:
    document = _document()
    document["texts"][0]["prov"][0]["charspan"] = charspan

    report = DoclingQualityValidator().validate(document, require_pdf_geometry=True)
    spans = build_pdf_content_spans(
        document,
        artifact_id="artifact-1",
        parser_run_id="run-1",
    )

    assert not report.acceptable
    assert report.locator_coverage == 0
    assert any(
        issue.code == "PDF_PROVENANCE_CHARSPAN_INVALID" for issue in report.issues
    )
    assert spans == ()


@pytest.mark.parametrize(
    ("provenance", "expected_code"),
    [
        ("not-an-object", "PDF_PROVENANCE_ENTRY_MALFORMED"),
        ({"page_no": 1}, "PDF_PROVENANCE_BBOX_MALFORMED"),
        (
            {"page_no": 1, "bbox": _bbox(coord_origin="CENTER")},
            "PDF_PROVENANCE_COORDINATE_ORIGIN_INVALID",
        ),
        (
            {"page_no": 1, "bbox": _bbox(l=-1)},
            "PDF_PROVENANCE_BBOX_NEGATIVE",
        ),
        (
            {"page_no": 1, "bbox": _bbox(l=90, r=10)},
            "PDF_PROVENANCE_BBOX_INVALID",
        ),
        (
            {"page_no": 1, "bbox": _bbox(t=10, b=30)},
            "PDF_PROVENANCE_BBOX_INVALID",
        ),
        (
            {"page_no": 1, "bbox": _bbox(r=float("inf"))},
            "PDF_PROVENANCE_BBOX_MALFORMED",
        ),
        (
            {"page_no": 1, "bbox": _bbox(r=101)},
            "PDF_PROVENANCE_BBOX_OUT_OF_PAGE",
        ),
        (
            {"page_no": 1, "bbox": _bbox(t=101)},
            "PDF_PROVENANCE_BBOX_OUT_OF_PAGE",
        ),
        (
            {"page_no": True, "bbox": _bbox()},
            "PDF_PROVENANCE_PAGE_INVALID",
        ),
        (
            {"page_no": 0, "bbox": _bbox()},
            "PDF_PROVENANCE_PAGE_INVALID",
        ),
    ],
)
def test_malformed_pdf_provenance_is_diagnosed_and_never_exported(
    provenance: object,
    expected_code: str,
) -> None:
    document = _document()
    document["texts"][0]["prov"] = [provenance]

    report = DoclingQualityValidator().validate(document, require_pdf_geometry=True)

    assert not report.acceptable
    assert any(issue.code == expected_code for issue in report.issues)
    assert (
        build_pdf_content_spans(
            document,
            artifact_id="artifact-1",
            parser_run_id="run-1",
        )
        == ()
    )


def test_malformed_provenance_collection_is_not_silently_treated_as_empty() -> None:
    document = _document()
    document["texts"][0]["prov"] = {"unexpected": "mapping"}

    report = DoclingQualityValidator().validate(document, require_pdf_geometry=True)

    assert not report.acceptable
    assert any(
        issue.code == "PDF_PROVENANCE_COLLECTION_INVALID" for issue in report.issues
    )


def test_page_references_must_be_present_and_within_document_bounds() -> None:
    document = _document(item_count=2)
    document["pages"]["3"] = {
        "page_no": 3,
        "size": {"width": 100, "height": 100},
    }
    document["texts"][0]["prov"][0]["page_no"] = 2
    document["texts"][1]["prov"][0]["page_no"] = 3

    report = DoclingQualityValidator().validate(document, require_pdf_geometry=True)

    assert not report.acceptable
    assert {
        issue.code
        for issue in report.issues
        if issue.code.startswith("PDF_PROVENANCE_PAGE_")
    } == {
        "PDF_PROVENANCE_PAGE_NOT_PRESENT",
        "PDF_PROVENANCE_PAGE_OUT_OF_BOUNDS",
    }
    assert (
        build_pdf_content_spans(
            document,
            artifact_id="artifact-1",
            parser_run_id="run-1",
        )
        == ()
    )


def test_one_invalid_locator_cannot_hide_at_the_coverage_threshold() -> None:
    document = _document(item_count=20)
    document["texts"][-1]["prov"][0]["bbox"]["coord_origin"] = "UNKNOWN"

    report = DoclingQualityValidator(0.95).validate(document, require_pdf_geometry=True)

    assert report.locator_coverage == 0.95
    assert not report.acceptable
    assert any(
        issue.code == "PDF_PROVENANCE_COORDINATE_ORIGIN_INVALID"
        for issue in report.issues
    )
    assert not any(
        issue.code == "PDF_LOCATOR_COVERAGE_BELOW_THRESHOLD" for issue in report.issues
    )


def test_malformed_text_entry_is_counted_and_is_always_a_quality_error() -> None:
    document = _document(item_count=20)
    document["texts"][-1] = "not-a-docling-item"
    document["body"]["children"] = document["body"]["children"][:-1]

    report = DoclingQualityValidator(0.95).validate(document, require_pdf_geometry=True)

    assert report.text_item_count == 20
    assert report.located_text_item_count == 19
    assert report.locator_coverage == 0.95
    assert not report.acceptable
    malformed = [
        issue
        for issue in report.issues
        if issue.code == "MALFORMED_DOCLING_CONTENT_ENTRY"
    ]
    assert len(malformed) == 1
    assert malformed[0].item_ref == "#/texts/19"


@pytest.mark.parametrize("collection", ["texts", "tables", "pictures"])
def test_malformed_content_entry_is_not_a_resolvable_reference(
    collection: str,
) -> None:
    document = _document()
    malformed_index = len(document[collection])
    document[collection].append(None)
    malformed_ref = f"#/{collection}/{malformed_index}"
    document["body"]["children"].append({"$ref": malformed_ref})

    report = DoclingQualityValidator().validate(document, require_pdf_geometry=True)

    assert not report.acceptable
    assert report.broken_reference_count == 1
    assert any(
        issue.code == "MALFORMED_DOCLING_CONTENT_ENTRY"
        and issue.item_ref == malformed_ref
        for issue in report.issues
    )
    assert any(
        issue.code == "BROKEN_DOCLING_REFERENCE" and issue.item_ref == malformed_ref
        for issue in report.issues
    )


def test_duplicate_self_refs_and_canonical_aliases_are_global_errors() -> None:
    document = _document(item_count=2)
    document["texts"][1]["self_ref"] = "#/texts/0"

    report = DoclingQualityValidator().validate(document, require_pdf_geometry=True)

    assert not report.acceptable
    assert "DUPLICATE_DOCLING_SELF_REF" in {issue.code for issue in report.issues}
    assert "DOCLING_CANONICAL_REFERENCE_COLLISION" in {
        issue.code for issue in report.issues
    }


def test_span_ids_remain_unique_for_rejected_duplicate_self_refs() -> None:
    document = _document(item_count=2)
    document["texts"][1] = deepcopy(document["texts"][0])

    pdf_spans = build_pdf_content_spans(
        document,
        artifact_id="artifact-1",
        parser_run_id="run-1",
    )
    docling_spans = build_docling_content_spans(
        document,
        artifact_id="artifact-1",
        parser_run_id="run-1",
        input_format="html",
    )

    assert len(pdf_spans) == 2
    assert len({span.span_id for span in pdf_spans}) == 2
    assert len(docling_spans) == 2
    assert len({span.span_id for span in docling_spans}) == 2


def test_image_only_detection_does_not_credit_invalid_or_unknown_page_ranges() -> None:
    document = _document()
    document["texts"][0]["text"] = "x" * 20
    document["texts"][0]["prov"] = [{"page_no": 1, "charspan": [-1, 20]}]

    assert probably_image_only(
        document,
        minimum_characters_per_page=20,
        image_only_page_ratio=1,
    )

    document["texts"][0]["prov"] = [{"page_no": 2, "charspan": [0, 20]}]
    assert probably_image_only(
        document,
        minimum_characters_per_page=20,
        image_only_page_ratio=1,
    )


def test_bioc_sentence_index_is_preserved_in_span_and_alignment_overlay() -> None:
    document = _document()
    native = NativeTextLocator(
        text="abcdefghij",
        source_kind="bioc_json",
        document_index=0,
        document_id="PMC1",
        passage_index=2,
        sentence_index=3,
        offset=42,
        length=10,
    )

    result = align_bioc_content_spans(
        document,
        (native,),
        artifact_id="artifact-1",
        parser_run_id="run-1",
    )

    assert result.aligned_count == 1
    assert result.records[0].sentence_index == 3
    assert result.records[0].to_dict()["sentence_index"] == 3
    assert result.spans[0].source_locator.sentence_index == 3
