from __future__ import annotations

import math

import pytest

from DeepResearch.src.document_processing.alignment import (
    AlignmentStatus,
    DoclingGrobidAligner,
    ScholarlyAlignmentOverlay,
)


def _document() -> dict:
    return {
        "texts": [
            {
                "self_ref": "#/texts/0",
                "text": "Methods",
                "prov": [],
            }
        ],
        "tables": [],
        "pictures": [],
    }


@pytest.mark.parametrize(
    "payload",
    [
        b"<html><p>Methods</p></html>",
        b"<TEI><text><p>Methods</p></text></TEI>",
        b'<TEI xmlns="urn:not-tei"><text><p>Methods</p></text></TEI>',
    ],
)
def test_alignment_rejects_well_formed_non_tei_xml(payload: bytes) -> None:
    with pytest.raises(ValueError, match="canonical TEI namespace"):
        DoclingGrobidAligner().extract_annotations(payload)


@pytest.mark.parametrize(
    "coords",
    [
        "",
        "1,2,3,4",
        "0,2,3,4,5",
        "1,-2,3,4,5",
        "1,2,3,0,5",
        "1,nan,3,4,5",
        "1,2,3,inf,5",
        "1,2,3,4,5;broken",
    ],
)
def test_invalid_grobid_coordinates_are_explicitly_unaligned(coords: str) -> None:
    tei = (
        '<TEI xmlns="http://www.tei-c.org/ns/1.0"><text><body>'
        f'<head coords="{coords}">Methods</head>'
        "</body></text></TEI>"
    ).encode()

    overlay = DoclingGrobidAligner().align(_document(), tei)

    assert overlay.aligned_count == 0
    assert overlay.unaligned_count == 1
    record = overlay.records[0]
    assert record.status is AlignmentStatus.UNALIGNED
    assert record.docling_item_ref is None
    assert record.annotation.raw_coordinates == coords
    assert record.annotation.coordinate_error is not None
    assert record.reason is not None
    assert record.reason.startswith("invalid_grobid_coordinates:")
    assert all(
        math.isfinite(value)
        for coordinate in record.annotation.coordinates
        for value in (coordinate.x, coordinate.y, coordinate.width, coordinate.height)
    )


def test_overlay_rejects_coordinate_tampering() -> None:
    tei = b"""<TEI xmlns="http://www.tei-c.org/ns/1.0"><text><body>
    <head coords="1,2,3,4,5">Methods</head>
    </body></text></TEI>"""
    overlay = DoclingGrobidAligner().align(_document(), tei)
    payload = overlay.to_dict()
    payload["records"][0]["annotation"]["coordinates"][0]["width"] = 999

    with pytest.raises(ValueError, match="invalid scholarly alignment overlay"):
        ScholarlyAlignmentOverlay.from_dict(payload)


def test_valid_coordinates_still_align_and_round_trip() -> None:
    tei = b"""<TEI xmlns="http://www.tei-c.org/ns/1.0"><text><body>
    <head coords="1,2,3,4,5">Methods</head>
    </body></text></TEI>"""

    overlay = DoclingGrobidAligner().align(_document(), tei)

    assert overlay.algorithm_version == "token-sequence-v2"
    assert overlay.aligned_count == 1
    assert overlay.records[0].reason is None
    assert ScholarlyAlignmentOverlay.from_dict(overlay.to_dict()) == overlay


def test_foreign_namespace_elements_never_become_scholarly_evidence() -> None:
    tei = b"""<TEI xmlns="http://www.tei-c.org/ns/1.0" xmlns:foreign="urn:evil">
    <text><body><head>Methods</head>
    <foreign:ref target="#fabricated">Fabricated citation</foreign:ref>
    </body></text></TEI>"""

    annotations = DoclingGrobidAligner().extract_annotations(tei)

    assert any(annotation.kind == "head" for annotation in annotations)
    assert all(annotation.text != "Fabricated citation" for annotation in annotations)
    assert all("tei:" in annotation.tei_path for annotation in annotations)
