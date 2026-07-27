from __future__ import annotations

import pytest
from bioc import BioCCollection, BioCDocument, BioCPassage, biocjson

from DeepResearch.src.document_processing.adapters import (
    BioCAdapter,
    JATSLocatorAdapter,
    NativeTextLocator,
)
from DeepResearch.src.document_processing.alignment import (
    AlignmentStatus,
    DoclingGrobidAligner,
    ScholarlyAlignmentOverlay,
)
from DeepResearch.src.document_processing.routing import (
    DocumentRouter,
    InputFormat,
    ManagedParserPolicy,
    ProcessingStage,
)
from DeepResearch.src.document_processing.validation import (
    DoclingQualityValidator,
    align_bioc_content_spans,
    align_jats_content_spans,
    build_docling_content_spans,
    build_pdf_content_spans,
)


def _docling_document(*, second_item_has_geometry: bool = True) -> dict:
    second_provenance = (
        [
            {
                "page_no": 1,
                "bbox": {
                    "l": 10,
                    "t": 40,
                    "r": 90,
                    "b": 30,
                    "coord_origin": "BOTTOMLEFT",
                },
            }
        ]
        if second_item_has_geometry
        else []
    )
    return {
        "schema_name": "DoclingDocument",
        "version": "1.0.0",
        "name": "paper",
        "body": {
            "self_ref": "#/body",
            "children": [{"$ref": "#/texts/0"}, {"$ref": "#/texts/1"}],
        },
        "furniture": {"self_ref": "#/furniture", "children": []},
        "groups": [],
        "texts": [
            {
                "self_ref": "#/texts/0",
                "label": "section_header",
                "text": "Methods",
                "prov": [
                    {
                        "page_no": 1,
                        "bbox": {
                            "l": 10,
                            "t": 20,
                            "r": 90,
                            "b": 10,
                            "coord_origin": "BOTTOMLEFT",
                        },
                    }
                ],
            },
            {
                "self_ref": "#/texts/1",
                "label": "paragraph",
                "text": "Amyloid beta was measured in the study cohort.",
                "prov": second_provenance,
            },
        ],
        "tables": [],
        "pictures": [],
        "key_value_items": [],
        "pages": {"1": {"page_no": 1}},
    }


@pytest.mark.parametrize("input_format", ["html", "docx", "pptx", "xlsx", "image"])
def test_non_native_formats_receive_explicit_docling_item_spans(
    input_format: str,
) -> None:
    spans = build_docling_content_spans(
        _docling_document(),
        artifact_id="artifact-1",
        processing_run_id="run-1",
        representation_product_id="product-docling-document",
        input_format=input_format,
    )

    assert len(spans) == 2
    assert spans[0].representation_anchor.char_start == 0
    assert spans[0].representation_anchor.char_end == len("Methods")
    assert spans[0].representation_anchor.product_id == "product-docling-document"
    assert spans[0].source_locator.kind == "docling_item"
    assert spans[0].source_locator.input_format == input_format
    assert spans[0].source_locator.item_ref == "#/texts/0"
    assert spans == build_docling_content_spans(
        _docling_document(),
        artifact_id="artifact-1",
        processing_run_id="run-1",
        representation_product_id="product-docling-document",
        input_format=input_format,
    )


def test_router_exposes_native_and_pdf_fallback_stages() -> None:
    router = DocumentRouter()
    jats = router.route(
        b'<article xmlns:xlink="http://www.w3.org/1999/xlink"><body/></article>',
        filename="paper.nxml",
        media_type="application/xml",
    )
    assert jats.input_format is InputFormat.JATS
    assert jats.required_stages == (ProcessingStage.DOCLING,)

    pdf = router.route(
        b"%PDF-1.7\nsynthetic",
        filename="paper.pdf",
        media_type="application/pdf",
    )
    assert pdf.required_stages == (ProcessingStage.DOCLING, ProcessingStage.GROBID)
    assert pdf.conditional_stages == (
        ProcessingStage.OCRMY_PDF,
        ProcessingStage.GROBID,
    )


def test_router_recognizes_bioc_json_and_managed_policy_is_closed() -> None:
    content = b'{"source":"PMC","date":"2026","key":"k","documents":[]}'
    assert DocumentRouter().detect(content) is InputFormat.BIOC_JSON
    with pytest.raises(PermissionError, match="disabled"):
        ManagedParserPolicy().require_allowed("mathpix")


def test_router_detects_bioc_json_when_metadata_exceeds_sniff_prefix() -> None:
    content = (
        b'{"source":"PMC","date":"2026","key":"collection","infons":'
        b'{"padding":"' + (b"x" * 10_000) + b'"},"documents":[]}'
    )

    route = DocumentRouter().route(
        content,
        filename="collection.json",
        media_type="application/json",
    )

    assert route.input_format is InputFormat.BIOC_JSON
    assert route.required_stages == (
        ProcessingStage.BIOC_ADAPTER,
        ProcessingStage.DOCLING,
    )


def test_grobid_alignment_keeps_unaligned_annotations_and_coordinates() -> None:
    tei = b"""<TEI xmlns="http://www.tei-c.org/ns/1.0">
      <text><body><div>
        <head coords="1,10,10,80,10">Methods</head>
        <p coords="1,10,30,80,10">Amyloid beta was measured in the study cohort.</p>
        <ref target="#b1">Citation absent from Docling</ref>
      </div></body></text>
    </TEI>"""
    overlay = DoclingGrobidAligner(minimum_score=0.7).align(_docling_document(), tei)

    assert overlay.aligned_count == 2
    assert overlay.unaligned_count == 1
    assert any(
        record.status is AlignmentStatus.UNALIGNED
        and record.annotation.kind == "ref"
        and record.docling_item_ref is None
        for record in overlay.records
    )
    head = next(
        record for record in overlay.records if record.annotation.kind == "head"
    )
    assert head.annotation.coordinates[0].page_number == 1


def test_grobid_overlay_retains_author_identities_and_affiliations() -> None:
    tei = b"""<TEI xmlns="http://www.tei-c.org/ns/1.0">
      <teiHeader><fileDesc><sourceDesc><biblStruct><analytic>
        <author>
          <persName coords="1,10,10,40,8">Alice Example</persName>
          <affiliation><orgName>Memory Research Lab</orgName></affiliation>
        </author>
      </analytic></biblStruct></sourceDesc></fileDesc></teiHeader>
    </TEI>"""

    annotations = DoclingGrobidAligner().extract_annotations(tei)

    person = next(
        annotation for annotation in annotations if annotation.kind == "persName"
    )
    affiliation = next(
        annotation for annotation in annotations if annotation.kind == "affiliation"
    )
    assert person.text == "Alice Example"
    assert person.coordinates[0].page_number == 1
    assert affiliation.text == "Memory Research Lab"


def test_scholarly_alignment_overlay_round_trips_without_realigning() -> None:
    tei = b"""<TEI xmlns="http://www.tei-c.org/ns/1.0">
      <text><body><div><head coords="1,10,10,80,10">Methods</head></div></body></text>
    </TEI>"""
    overlay = DoclingGrobidAligner(minimum_score=0.7).align(_docling_document(), tei)

    restored = ScholarlyAlignmentOverlay.from_dict(overlay.to_dict())

    assert restored == overlay


def test_scholarly_alignment_overlay_rejects_tampered_persisted_evidence() -> None:
    tei = b"""<TEI xmlns="http://www.tei-c.org/ns/1.0">
      <text><body><div><head>Methods</head></div></body></text>
    </TEI>"""
    overlay = DoclingGrobidAligner(minimum_score=0.7).align(_docling_document(), tei)
    payload = overlay.to_dict()
    payload["records"][0]["annotation"]["text"] = "Tampered"

    with pytest.raises(ValueError, match="invalid scholarly alignment overlay"):
        ScholarlyAlignmentOverlay.from_dict(payload)


def test_pdf_quality_and_spans_enforce_geometry_threshold() -> None:
    validator = DoclingQualityValidator(minimum_pdf_locator_coverage=0.95)
    complete = validator.validate(_docling_document(), require_pdf_geometry=True)
    assert complete.acceptable
    assert complete.locator_coverage == 1.0

    spans = build_pdf_content_spans(
        _docling_document(),
        artifact_id="artifact-1",
        processing_run_id="run-1",
        representation_product_id="product-docling-document",
    )
    assert len(spans) == 2
    assert spans[0].source_locator.kind == "pdf"
    assert spans[0].source_locator.page_number == 1

    incomplete = validator.validate(
        _docling_document(second_item_has_geometry=False),
        require_pdf_geometry=True,
    )
    assert not incomplete.acceptable
    assert any(
        issue.code == "PDF_LOCATOR_COVERAGE_BELOW_THRESHOLD"
        for issue in incomplete.issues
    )


def test_pdf_quality_diagnoses_each_locator_exception_at_passing_threshold() -> None:
    document = _docling_document()
    document["texts"] = [
        {
            "self_ref": f"#/texts/{index}",
            "label": "paragraph",
            "text": f"Evidence item {index}",
            "prov": (
                [
                    {
                        "page_no": 1,
                        "bbox": {
                            "l": 10,
                            "t": 20,
                            "r": 90,
                            "b": 10,
                            "coord_origin": "BOTTOMLEFT",
                        },
                    }
                ]
                if index < 19
                else []
            ),
        }
        for index in range(20)
    ]

    report = DoclingQualityValidator(minimum_pdf_locator_coverage=0.95).validate(
        document,
        require_pdf_geometry=True,
    )

    assert report.acceptable
    assert report.locator_coverage == 0.95
    locator_issues = [
        issue
        for issue in report.issues
        if issue.code == "PDF_TEXT_ITEM_LOCATOR_MISSING"
    ]
    assert len(locator_issues) == 1
    assert locator_issues[0].item_ref == "#/texts/19"
    assert not any(
        issue.code == "PDF_LOCATOR_COVERAGE_BELOW_THRESHOLD" for issue in report.issues
    )


def test_pdf_spans_preserve_multi_page_item_character_ranges() -> None:
    document = _docling_document()
    document["texts"] = [
        {
            "self_ref": "#/texts/0",
            "label": "paragraph",
            "text": "abcdefghij",
            "prov": [
                {
                    "page_no": 1,
                    "charspan": [0, 4],
                    "bbox": {
                        "l": 10,
                        "t": 20,
                        "r": 90,
                        "b": 10,
                        "coord_origin": "BOTTOMLEFT",
                    },
                },
                {
                    "page_no": 2,
                    "charspan": [4, 10],
                    "bbox": {
                        "l": 10,
                        "t": 40,
                        "r": 90,
                        "b": 30,
                        "coord_origin": "BOTTOMLEFT",
                    },
                },
            ],
        }
    ]
    document["body"]["children"] = [{"$ref": "#/texts/0"}]
    document["pages"] = {"1": {"page_no": 1}, "2": {"page_no": 2}}

    spans = build_pdf_content_spans(
        document,
        artifact_id="artifact-1",
        processing_run_id="run-1",
        representation_product_id="product-docling-document",
    )

    assert [
        (span.representation_anchor.char_start, span.representation_anchor.char_end)
        for span in spans
    ] == [
        (0, 4),
        (4, 10),
    ]
    assert [span.source_locator.page_number for span in spans] == [1, 2]
    assert spans[0].content_sha256 != spans[1].content_sha256


def test_multi_region_pdf_without_charspans_is_explicitly_rejected() -> None:
    document = _docling_document()
    document["texts"][0]["prov"].append(
        {
            "page_no": 2,
            "bbox": {
                "l": 10,
                "t": 40,
                "r": 90,
                "b": 30,
                "coord_origin": "BOTTOMLEFT",
            },
        }
    )

    report = DoclingQualityValidator().validate(
        document,
        require_pdf_geometry=True,
    )
    spans = build_pdf_content_spans(
        document,
        artifact_id="artifact-1",
        processing_run_id="run-1",
        representation_product_id="product-docling-document",
    )

    assert not report.acceptable
    assert any(
        issue.code == "PDF_MULTI_PROVENANCE_CHARSPAN_MISSING" for issue in report.issues
    )
    assert not any(span.representation_anchor.node_id == "#/texts/0" for span in spans)


def test_jats_locator_adapter_preserves_xml_id_and_xpath() -> None:
    locators = JATSLocatorAdapter().extract_locators(
        b"""<article><body><sec id="s1"><title>Results</title>
        <p id="p1">Measured outcome.</p></sec></body></article>"""
    )
    paragraph = next(
        locator for locator in locators if locator.text == "Measured outcome."
    )
    assert paragraph.xml_id == "p1"
    assert paragraph.xpath == "/article[1]/body[1]/sec[1]/p[1]"


def test_jats_span_alignment_records_every_aligned_and_unaligned_locator() -> None:
    locators = (
        NativeTextLocator(
            text="Methods",
            source_kind="jats",
            xml_id="heading-1",
            xpath="/article[1]/body[1]/sec[1]/title[1]",
        ),
        NativeTextLocator(
            text="No matching Docling text",
            source_kind="jats",
            xml_id="paragraph-2",
            xpath="/article[1]/body[1]/sec[1]/p[1]",
        ),
    )

    result = align_jats_content_spans(
        _docling_document(),
        locators,
        artifact_id="artifact-1",
        processing_run_id="run-1",
        representation_product_id="product-docling-document",
    )

    assert len(result.spans) == 1
    assert len(result.records) == len(locators)
    assert result.aligned_count == 1
    assert result.unaligned_count == 1
    aligned = next(record for record in result.records if record.status == "aligned")
    unaligned = next(
        record for record in result.records if record.status == "unaligned"
    )
    assert aligned.content_span_id == result.spans[0].span_id
    assert aligned.match_method == "normalized_exact"
    assert unaligned.content_span_id is None
    assert unaligned.reason == "no_normalized_exact_match"


def test_bioc_adapter_uses_bioc_library_and_preserves_offsets() -> None:
    collection = BioCCollection()
    collection.source = "PMC"
    collection.date = "20260717"
    collection.key = "test"
    document = BioCDocument()
    document.id = "PMC1"
    passage = BioCPassage()
    passage.offset = 42
    passage.infons["section"] = "Abstract"
    passage.text = "Structured BioC text."
    document.add_passage(passage)
    collection.add_document(document)
    second_document = BioCDocument()
    second_document.id = "PMC1"
    second_passage = BioCPassage()
    second_passage.offset = 7
    second_passage.text = "Second document text."
    second_document.add_passage(second_passage)
    collection.add_document(second_document)

    adapted = BioCAdapter().adapt(
        biocjson.dumps(collection).encode("utf-8"),
        input_format=InputFormat.BIOC_JSON,
    )
    assert adapted.media_type == "text/html"
    assert b"Structured BioC text." in adapted.content
    assert adapted.locator_overlay[0].document_id == "PMC1"
    assert adapted.locator_overlay[0].document_index == 0
    assert adapted.locator_overlay[0].offset == 42
    assert adapted.locator_overlay[0].length == len("Structured BioC text.")
    assert adapted.locator_overlay[1].document_id == "PMC1"
    assert adapted.locator_overlay[1].document_index == 1


def test_bioc_alignment_records_every_locator_and_native_range() -> None:
    locators = (
        NativeTextLocator(
            text="  METHODS ",
            source_kind=InputFormat.BIOC_JSON.value,
            document_index=0,
            document_id="PMC1",
            passage_index=0,
            offset=10,
            length=10,
        ),
        NativeTextLocator(
            text="No matching Docling text",
            source_kind=InputFormat.BIOC_JSON.value,
            document_index=1,
            document_id="PMC1",
            passage_index=0,
            offset=20,
            length=24,
        ),
        NativeTextLocator(
            text="Amyloid beta was measured in the study cohort.",
            source_kind=InputFormat.BIOC_JSON.value,
            document_index=None,
            document_id="PMC2",
            passage_index=0,
            offset=0,
            length=47,
        ),
    )

    result = align_bioc_content_spans(
        _docling_document(),
        locators,
        artifact_id="artifact-1",
        processing_run_id="run-1",
        representation_product_id="product-docling-document",
    )

    assert len(result.records) == len(locators)
    assert result.aligned_count == 1
    assert result.unaligned_count == 2
    assert len(result.spans) == 1
    aligned = result.records[0]
    assert aligned.status == "aligned"
    assert aligned.match_method == "normalized_exact"
    assert aligned.document_index == 0
    assert aligned.document_id == "PMC1"
    assert aligned.content_span_id == result.spans[0].span_id
    locator = result.spans[0].source_locator
    assert locator.kind == "bioc"
    assert locator.document_index == 0
    assert locator.passage_index == 0
    assert locator.offset == 10
    assert locator.length == 10
    assert result.records[1].reason == "no_normalized_exact_match"
    assert result.records[2].reason == "missing_native_reference"


def test_bioc_alignment_consumes_duplicate_texts_in_source_order() -> None:
    document = _docling_document()
    document["texts"] = [
        {"self_ref": "#/texts/0", "text": "Repeated passage", "prov": []},
        {"self_ref": "#/texts/1", "text": "Repeated passage", "prov": []},
    ]
    locators = tuple(
        NativeTextLocator(
            text="Repeated passage",
            source_kind=InputFormat.BIOC_XML.value,
            document_index=document_index,
            document_id="duplicate-id",
            passage_index=0,
            offset=0,
            length=16,
        )
        for document_index in range(2)
    )

    first = align_bioc_content_spans(
        document,
        locators,
        artifact_id="artifact-1",
        processing_run_id="run-1",
        representation_product_id="product-docling-document",
    )
    second = align_bioc_content_spans(
        document,
        locators,
        artifact_id="artifact-1",
        processing_run_id="run-1",
        representation_product_id="product-docling-document",
    )

    assert [record.docling_item_ref for record in first.records] == [
        "#/texts/0",
        "#/texts/1",
    ]
    assert first == second
    assert first.spans[0].source_locator.document_index == 0
    assert first.spans[1].source_locator.document_index == 1
