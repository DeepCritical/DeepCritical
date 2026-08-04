from __future__ import annotations

import pytest
from bioc import BioCCollection, BioCDocument, BioCPassage, BioCSentence, biocjson

from DeepResearch.src.document_processing.adapters import AdapterError, BioCAdapter
from DeepResearch.src.document_processing.routing import DocumentRouter, InputFormat


def test_bioc_sentence_only_passage_preserves_native_sentence_locators() -> None:
    collection = BioCCollection()
    collection.source = "PMC"
    collection.date = "20260718"
    collection.key = "sentence-only"
    document = BioCDocument()
    document.id = "PMC-SENTENCES"
    passage = BioCPassage()
    passage.offset = 100
    passage.infons["section"] = "Abstract"

    first = BioCSentence()
    first.offset = 100
    first.text = "First sentence."
    first.infons["sentence-id"] = "s1"
    passage.add_sentence(first)

    second = BioCSentence()
    second.offset = 116
    second.text = "Second sentence."
    second.infons["sentence-id"] = "s2"
    passage.add_sentence(second)
    document.add_passage(passage)
    collection.add_document(document)

    adapted = BioCAdapter().adapt(
        biocjson.dumps(collection).encode("utf-8"),
        input_format=InputFormat.BIOC_JSON,
    )

    assert b"First sentence." in adapted.content
    assert b"Second sentence." in adapted.content
    assert b'data-bioc-sentence="0"' in adapted.content
    assert [locator.sentence_index for locator in adapted.locator_overlay] == [0, 1]
    assert [locator.offset for locator in adapted.locator_overlay] == [100, 116]
    assert [locator.length for locator in adapted.locator_overlay] == [
        len("First sentence."),
        len("Second sentence."),
    ]
    assert adapted.locator_overlay[0].passage_index == 0
    assert adapted.locator_overlay[0].infons == {"sentence-id": "s1"}
    assert adapted.overlay_json()[1]["sentence_index"] == 1


def test_bioc_passage_text_and_sentences_preserve_both_locator_levels() -> None:
    collection = BioCCollection()
    collection.source = "PMC"
    collection.date = "20260718"
    collection.key = "passage-and-sentences"
    document = BioCDocument()
    document.id = "PMC-MIXED"
    passage = BioCPassage()
    passage.offset = 200
    passage.text = "First sentence. Second sentence."
    passage.infons["section"] = "Results"

    first = BioCSentence()
    first.offset = 200
    first.text = "First sentence."
    first.infons["sentence-id"] = "s1"
    passage.add_sentence(first)

    second = BioCSentence()
    second.offset = 216
    second.text = "Second sentence."
    second.infons["sentence-id"] = "s2"
    passage.add_sentence(second)
    document.add_passage(passage)
    collection.add_document(document)

    adapted = BioCAdapter().adapt(
        biocjson.dumps(collection).encode("utf-8"),
        input_format=InputFormat.BIOC_JSON,
    )

    # Docling receives the complete passage once; sentence evidence remains in
    # the metadata overlay instead of becoming duplicate sibling paragraphs.
    assert adapted.content.count(b"First sentence. Second sentence.") == 1
    assert b'data-bioc-sentences="locator-overlay"' in adapted.content
    assert b'data-bioc-sentence="0"' not in adapted.content
    assert [locator.sentence_index for locator in adapted.locator_overlay] == [
        None,
        0,
        1,
    ]
    assert [locator.offset for locator in adapted.locator_overlay] == [200, 200, 216]
    assert adapted.locator_overlay[0].infons == {"section": "Results"}
    assert adapted.locator_overlay[1].infons == {"sentence-id": "s1"}
    assert adapted.locator_overlay[2].infons == {"sentence-id": "s2"}


@pytest.mark.parametrize(
    "content",
    [
        b"""<!DOCTYPE collection [<!ENTITY injected "not allowed">]>
        <collection><source>PMC</source><date>2026</date><key>&injected;</key></collection>""",
        b"""<!DOCTYPE collection SYSTEM "https://example.invalid/bioc.dtd">
        <collection><source>PMC</source><date>2026</date><key>k</key></collection>""",
    ],
)
def test_bioc_xml_rejects_dtds_and_entities(content: bytes) -> None:
    with pytest.raises(AdapterError, match="Invalid bioc_xml document"):
        BioCAdapter().adapt(content, input_format=InputFormat.BIOC_XML)


@pytest.mark.parametrize(
    ("content", "input_format"),
    [
        (
            b'{"source":"PMC","key":"missing-date","infons":{},"documents":[]}',
            InputFormat.BIOC_JSON,
        ),
        (
            b"""<collection><source>PMC</source><date>2026</date><key>k</key>
            <document><id>PMC1</id><passage><offset>not-an-integer</offset>
            </passage></document></collection>""",
            InputFormat.BIOC_XML,
        ),
        (b"<collection><document>", InputFormat.BIOC_XML),
    ],
)
def test_bioc_malformed_parser_failures_are_normalized(
    content: bytes,
    input_format: InputFormat,
) -> None:
    with pytest.raises(AdapterError):
        BioCAdapter().adapt(content, input_format=input_format)


@pytest.mark.parametrize(
    ("content", "expected"),
    [
        (
            b'\xef\xbb\xbf<?xml version="1.0"?>\n'
            b"<!-- provenance --><?review approved?>\n"
            b"<collection><source>PMC</source><date>2026</date>"
            b"<key>k</key></collection>",
            InputFormat.BIOC_XML,
        ),
        (
            b"\xef\xbb\xbf<!-- provenance --><?review approved?>\n"
            b"<article><body/></article>",
            InputFormat.JATS,
        ),
        (
            b'\xef\xbb\xbf{"source":"PMC","date":"2026","key":"k",'
            b'"infons":{},"documents":[]}',
            InputFormat.BIOC_JSON,
        ),
    ],
)
def test_router_handles_utf8_bom_and_xml_misc(
    content: bytes,
    expected: InputFormat,
) -> None:
    assert DocumentRouter().detect(content) is expected


def test_bioc_json_adapter_accepts_a_utf8_bom() -> None:
    content = (
        b'\xef\xbb\xbf{"source":"PMC","date":"2026","key":"k",'
        b'"infons":{},"documents":[]}'
    )

    adapted = BioCAdapter().adapt(content, input_format=InputFormat.BIOC_JSON)

    assert adapted.native_format is InputFormat.BIOC_JSON
    assert adapted.locator_overlay == ()


def test_router_keeps_declared_native_mime_bound_to_detected_signature() -> None:
    bioc = b"\xef\xbb\xbf<!-- provenance --><collection/>"

    assert DocumentRouter().detect(bioc) is InputFormat.BIOC_XML
    assert (
        DocumentRouter().detect(bioc, media_type="application/jats+xml")
        is InputFormat.UNKNOWN
    )


def test_router_does_not_search_past_the_bounded_json_sniff_window() -> None:
    content = (
        b'{"padding":"'
        + (b"x" * 70_000)
        + b'","source":"PMC","date":"2026","key":"k","documents":[]}'
    )

    assert DocumentRouter().detect(content) is InputFormat.UNKNOWN
