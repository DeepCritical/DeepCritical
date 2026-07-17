from io import BytesIO
from zipfile import ZipFile

import pytest

from DeepResearch.src.document_processing.routing import DocumentRouter, InputFormat


def test_extension_only_detection_is_closed_by_default() -> None:
    content = b"not actually a PDF"

    assert (
        DocumentRouter().detect(content, filename="misleading.pdf")
        is InputFormat.UNKNOWN
    )
    assert (
        DocumentRouter(reject_extension_only=False).detect(
            content,
            filename="legacy.pdf",
        )
        is InputFormat.PDF
    )


def test_html_article_element_is_not_misclassified_as_jats() -> None:
    content = b"""<!doctype html><html><body><article>News</article></body></html>"""

    assert DocumentRouter().detect(content, media_type="text/html") is InputFormat.HTML


@pytest.mark.parametrize(
    ("filename", "media_type"),
    [
        (
            "renamed.docx",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        ),
        (
            "renamed.xlsx",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        ),
        (
            "renamed.pptx",
            "application/vnd.openxmlformats-officedocument.presentationml.presentation",
        ),
        ("renamed.png", "image/png"),
    ],
)
def test_extension_derived_media_type_cannot_accept_renamed_garbage(
    filename: str,
    media_type: str,
) -> None:
    detected = DocumentRouter(reject_extension_only=True).detect(
        b"arbitrary renamed bytes",
        filename=filename,
        media_type=media_type,
    )

    assert detected is InputFormat.UNKNOWN


@pytest.mark.parametrize(
    ("marker", "expected"),
    [
        ("word/document.xml", InputFormat.DOCX),
        ("xl/workbook.xml", InputFormat.XLSX),
        ("ppt/presentation.xml", InputFormat.PPTX),
    ],
)
def test_ooxml_detection_uses_package_structure(
    marker: str, expected: InputFormat
) -> None:
    payload = BytesIO()
    with ZipFile(payload, "w") as archive:
        archive.writestr("[Content_Types].xml", "<Types/>")
        archive.writestr(marker, "<document/>")

    assert DocumentRouter().detect(payload.getvalue()) is expected


def test_declared_image_type_must_match_magic() -> None:
    png = b"\x89PNG\r\n\x1a\n" + (b"\x00" * 32)

    assert (
        DocumentRouter().detect(png, filename="image.png", media_type="image/png")
        is InputFormat.IMAGE
    )
    assert (
        DocumentRouter().detect(png, filename="image.jpg", media_type="image/jpeg")
        is InputFormat.UNKNOWN
    )
