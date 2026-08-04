"""Opt-in compatibility contracts for the real document-processing stack.

The module is inert unless ``DEEPCRITICAL_RUN_LIVE_DOCUMENT_PROCESSING=1`` is
present before pytest starts. Its fixtures generate reusable synthetic PDFs, so
the lane never uploads licensed or corpus material.
"""

from __future__ import annotations

import io
import os
import re
import shutil
import zlib
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

import pytest
import yaml
from defusedxml import ElementTree
from pypdf import PdfReader

from DeepResearch.src.document_processing.clients import (
    ContainerOCRmyPDFRunner,
    DoclingServeClient,
    GrobidClient,
)

_LIVE_ENABLED = os.getenv("DEEPCRITICAL_RUN_LIVE_DOCUMENT_PROCESSING") == "1"
_LIVE_OCR_ENABLED = os.getenv("DEEPCRITICAL_RUN_LIVE_DOCUMENT_PROCESSING_OCR") == "1"
_DIGEST_ADDRESSED_IMAGE = re.compile(r"^\S+@sha256:[0-9a-f]{64}$")
_TEI_NAMESPACE = "http://www.tei-c.org/ns/1.0"

pytestmark = [
    pytest.mark.document_processing_live,
    pytest.mark.integration,
    pytest.mark.requires_network,
    pytest.mark.skipif(
        not _LIVE_ENABLED,
        reason=(
            "set DEEPCRITICAL_RUN_LIVE_DOCUMENT_PROCESSING=1 to run real "
            "parser-stack contracts"
        ),
    ),
]


@dataclass(frozen=True, slots=True)
class _LiveStackConfig:
    docling_url: str
    docling_api_key: str
    grobid_url: str
    grobid_api_key: str
    connect_timeout_seconds: float
    request_timeout_seconds: float
    task_timeout_seconds: float
    expected_docling_version: str
    expected_docling_serve_version: str
    expected_grobid_version: str


def _required_environment(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise RuntimeError(
            f"{name} is required when live document-processing tests run"
        )
    return value


def _positive_environment_float(name: str, default: float) -> float:
    raw = os.getenv(name)
    try:
        value = default if raw is None else float(raw)
    except ValueError as exc:
        raise ValueError(f"{name} must be a positive number") from exc
    if value <= 0:
        raise ValueError(f"{name} must be a positive number")
    return value


def _configured_service_version(component_id: str, field: str) -> str:
    config_path = (
        Path(__file__).resolve().parents[2]
        / "configs"
        / "document_processing"
        / "default.yaml"
    )
    config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    value = config["services"][component_id][field]
    if not isinstance(value, str) or not value.strip():
        raise RuntimeError(
            f"configured {component_id}.{field} must be a non-empty string"
        )
    return value.strip()


@pytest.fixture(scope="session")
def live_stack_config() -> _LiveStackConfig:
    """Load only namespaced live credentials, never unit-test fixture keys."""

    return _LiveStackConfig(
        docling_url=os.getenv("DEEPCRITICAL_LIVE_DOCLING_URL", "http://127.0.0.1:5001"),
        docling_api_key=_required_environment("DEEPCRITICAL_LIVE_DOCLING_API_KEY"),
        grobid_url=os.getenv("DEEPCRITICAL_LIVE_GROBID_URL", "http://127.0.0.1:8070"),
        grobid_api_key=_required_environment("DEEPCRITICAL_LIVE_GROBID_API_KEY"),
        connect_timeout_seconds=_positive_environment_float(
            "DEEPCRITICAL_LIVE_CONNECT_TIMEOUT_SECONDS", 10.0
        ),
        request_timeout_seconds=_positive_environment_float(
            "DEEPCRITICAL_LIVE_REQUEST_TIMEOUT_SECONDS", 600.0
        ),
        task_timeout_seconds=_positive_environment_float(
            "DEEPCRITICAL_LIVE_TASK_TIMEOUT_SECONDS", 1800.0
        ),
        expected_docling_version=os.getenv(
            "DEEPCRITICAL_LIVE_EXPECTED_DOCLING_VERSION",
            _configured_service_version("docling", "component_version"),
        ).strip(),
        expected_docling_serve_version=os.getenv(
            "DEEPCRITICAL_LIVE_EXPECTED_DOCLING_SERVE_VERSION",
            _configured_service_version("docling", "serve_version"),
        ).strip(),
        expected_grobid_version=os.getenv(
            "DEEPCRITICAL_LIVE_EXPECTED_GROBID_VERSION",
            _configured_service_version("grobid", "component_version"),
        ).strip(),
    )


def _assemble_pdf(objects: list[bytes]) -> bytes:
    body = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
    offsets = [0]
    for object_number, payload in enumerate(objects, start=1):
        offsets.append(len(body))
        body.extend(f"{object_number} 0 obj\n".encode())
        body.extend(payload)
        body.extend(b"\nendobj\n")
    xref_offset = len(body)
    body.extend(f"xref\n0 {len(objects) + 1}\n".encode())
    body.extend(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        body.extend(f"{offset:010d} 00000 n \n".encode())
    body.extend(
        (
            f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\n"
            f"startxref\n{xref_offset}\n%%EOF\n"
        ).encode()
    )
    return bytes(body)


@pytest.fixture(scope="session")
def synthetic_scholarly_pdf() -> bytes:
    """Return a deterministic born-digital paper-shaped one-page PDF."""

    content = (
        b"BT\n/F1 16 Tf\n72 742 Td\n"
        b"(DeepCritical Parser Contract Study) Tj\n"
        b"0 -28 Td\n/F1 11 Tf\n(Ada Researcher and Ben Scientist) Tj\n"
        b"0 -34 Td\n/F1 13 Tf\n(Abstract) Tj\n"
        b"0 -20 Td\n/F1 10 Tf\n"
        b"(This reusable synthetic paper tests scientific document parsing.) Tj\n"
        b"0 -16 Td\n"
        b"(The experiment reports reproducible evidence and one citation.) Tj\n"
        b"0 -30 Td\n/F1 13 Tf\n(References) Tj\n"
        b"0 -20 Td\n/F1 10 Tf\n"
        b"(Researcher A. Synthetic parser evaluation. 2026.) Tj\nET\n"
    )
    return _assemble_pdf(
        [
            b"<< /Type /Catalog /Pages 2 0 R >>",
            b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
            (
                b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
                b"/Resources << /Font << /F1 5 0 R >> >> /Contents 4 0 R >>"
            ),
            b"<< /Length "
            + str(len(content)).encode()
            + b" >>\nstream\n"
            + content
            + b"endstream",
            b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        ]
    )


_BITMAP_FONT = {
    "A": ("01110", "10001", "10001", "11111", "10001", "10001", "10001"),
    "C": ("01111", "10000", "10000", "10000", "10000", "10000", "01111"),
    "D": ("11110", "10001", "10001", "10001", "10001", "10001", "11110"),
    "E": ("11111", "10000", "10000", "11110", "10000", "10000", "11111"),
    "I": ("11111", "00100", "00100", "00100", "00100", "00100", "11111"),
    "L": ("10000", "10000", "10000", "10000", "10000", "10000", "11111"),
    "O": ("01110", "10001", "10001", "10001", "10001", "10001", "01110"),
    "P": ("11110", "10001", "10001", "11110", "10000", "10000", "10000"),
    "R": ("11110", "10001", "10001", "11110", "10100", "10010", "10001"),
    "S": ("01111", "10000", "10000", "01110", "00001", "00001", "11110"),
    "T": ("11111", "00100", "00100", "00100", "00100", "00100", "00100"),
}


@pytest.fixture(scope="session")
def synthetic_image_only_pdf() -> bytes:
    """Return a deterministic raster-only PDF for the opt-in OCR contract."""

    width, height, scale = 1800, 600, 12
    pixels = bytearray(b"\xff" * (width * height))
    text = "DEEPCRITICAL OCR TEST"
    glyph_width = 6 * scale
    start_x = (width - len(text) * glyph_width) // 2
    start_y = (height - 7 * scale) // 2
    for character_index, character in enumerate(text):
        glyph = _BITMAP_FONT.get(character)
        if glyph is None:
            continue
        glyph_x = start_x + character_index * glyph_width
        for row, pattern in enumerate(glyph):
            for column, pixel in enumerate(pattern):
                if pixel != "1":
                    continue
                for y_offset in range(scale):
                    row_start = (start_y + row * scale + y_offset) * width
                    for x_offset in range(scale):
                        pixels[row_start + glyph_x + column * scale + x_offset] = 0

    compressed = zlib.compress(bytes(pixels), level=9)
    content = b"q\n540 0 0 180 36 306 cm\n/Im0 Do\nQ\n"
    image = (
        b"<< /Type /XObject /Subtype /Image /Width 1800 /Height 600 "
        b"/ColorSpace /DeviceGray /BitsPerComponent 8 /Filter /FlateDecode "
        b"/Length "
        + str(len(compressed)).encode()
        + b" >>\nstream\n"
        + compressed
        + b"\nendstream"
    )
    return _assemble_pdf(
        [
            b"<< /Type /Catalog /Pages 2 0 R >>",
            b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
            (
                b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
                b"/Resources << /XObject << /Im0 5 0 R >> >> /Contents 4 0 R >>"
            ),
            b"<< /Length "
            + str(len(content)).encode()
            + b" >>\nstream\n"
            + content
            + b"endstream",
            image,
        ]
    )


@pytest.mark.asyncio
async def test_live_docling_async_conversion_contract(
    live_stack_config: _LiveStackConfig,
    synthetic_scholarly_pdf: bytes,
) -> None:
    client = DoclingServeClient(
        live_stack_config.docling_url,
        api_key=live_stack_config.docling_api_key,
        connect_timeout_seconds=live_stack_config.connect_timeout_seconds,
        request_timeout_seconds=live_stack_config.request_timeout_seconds,
        task_timeout_seconds=live_stack_config.task_timeout_seconds,
        poll_interval_seconds=0.5,
        use_async_api=True,
    )

    health = await client.health()
    versions = await client.version()
    result = await client.convert(
        synthetic_scholarly_pdf,
        filename="deepcritical-live-contract.pdf",
        media_type="application/pdf",
        options={"do_ocr": False},
    )

    assert health.ready is True
    assert isinstance(health.readiness, Mapping)
    assert isinstance(health.versions, Mapping)
    assert versions.get("docling") == live_stack_config.expected_docling_version
    assert versions.get("docling-serve") == (
        live_stack_config.expected_docling_serve_version
    )
    assert health.versions == versions
    assert result.status in {"success", "partial_success"}
    assert result.remote_task_id
    assert result.raw_response.get("status") == result.status
    assert result.document.get("schema_name") == "DoclingDocument"
    assert isinstance(result.document.get("texts"), list)
    assert result.document["texts"]


@pytest.mark.asyncio
async def test_live_grobid_tei_contract(
    live_stack_config: _LiveStackConfig,
    synthetic_scholarly_pdf: bytes,
) -> None:
    client = GrobidClient(
        live_stack_config.grobid_url,
        api_key=live_stack_config.grobid_api_key,
        connect_timeout_seconds=live_stack_config.connect_timeout_seconds,
        timeout_seconds=live_stack_config.request_timeout_seconds,
    )

    assert await client.health() is True
    version = await client.version()
    result = await client.process_fulltext(
        synthetic_scholarly_pdf, filename="deepcritical-live-contract.pdf"
    )

    root = ElementTree.fromstring(result.tei_xml)
    assert version == live_stack_config.expected_grobid_version
    assert result.status_code == 200
    assert root.tag == f"{{{_TEI_NAMESPACE}}}TEI"
    assert root.find(f"{{{_TEI_NAMESPACE}}}teiHeader") is not None
    assert root.find(f"{{{_TEI_NAMESPACE}}}text") is not None
    assert set(result.coordinates) == set(GrobidClient.DEFAULT_COORDINATES)


@pytest.mark.asyncio
@pytest.mark.skipif(
    not _LIVE_OCR_ENABLED,
    reason=(
        "set DEEPCRITICAL_RUN_LIVE_DOCUMENT_PROCESSING_OCR=1 to run the "
        "digest-addressed OCR container contract"
    ),
)
async def test_live_digest_addressed_ocr_derivative_contract(
    synthetic_image_only_pdf: bytes,
) -> None:
    runtime = os.getenv("DEEPCRITICAL_LIVE_CONTAINER_RUNTIME", "docker").strip()
    if not runtime or shutil.which(runtime) is None:
        raise RuntimeError(
            "DEEPCRITICAL_LIVE_CONTAINER_RUNTIME must name an installed OCI runtime"
        )
    image = _required_environment("DEEPCRITICAL_LIVE_OCR_IMAGE")
    if not _DIGEST_ADDRESSED_IMAGE.fullmatch(image):
        raise RuntimeError(
            "DEEPCRITICAL_LIVE_OCR_IMAGE must be an exact image@sha256:<64 hex> "
            "reference that is already present locally"
        )

    runner = ContainerOCRmyPDFRunner(
        image,
        runtime_executable=runtime,
        timeout_seconds=_positive_environment_float(
            "DEEPCRITICAL_LIVE_OCR_TIMEOUT_SECONDS", 600.0
        ),
        probe_timeout_seconds=_positive_environment_float(
            "DEEPCRITICAL_LIVE_OCR_PROBE_TIMEOUT_SECONDS", 60.0
        ),
        jobs=1,
        require_digest_addressed=True,
    )
    result = await runner.convert(synthetic_image_only_pdf)

    derivative = PdfReader(io.BytesIO(result.pdf_bytes))
    assert result.exit_code == 0
    assert result.pdf_bytes.startswith(b"%PDF-")
    assert len(derivative.pages) == 1
    assert result.sidecar_text.strip()
    assert derivative.pages[0].extract_text().strip()
    assert result.runtime_attestation is not None
    assert result.runtime_attestation.container_reference == image
    assert result.runtime_attestation.container_digest == image.rsplit("@", 1)[1]
    assert result.runtime_attestation.component_versions["ocrmypdf"].startswith(
        "17.4.1"
    )
    assert result.runtime_attestation.component_versions["tesseract"]
