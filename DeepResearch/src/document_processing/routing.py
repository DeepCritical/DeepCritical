"""Deterministic, policy-visible routing for scientific document artifacts."""

from __future__ import annotations

import json
import re
import zipfile
from dataclasses import dataclass
from enum import StrEnum
from io import BytesIO
from pathlib import PurePath
from typing import Final


class InputFormat(StrEnum):
    JATS = "jats"
    BIOC_XML = "bioc_xml"
    BIOC_JSON = "bioc_json"
    PDF = "pdf"
    HTML = "html"
    DOCX = "docx"
    PPTX = "pptx"
    XLSX = "xlsx"
    IMAGE = "image"
    UNKNOWN = "unknown"


class ProcessingStage(StrEnum):
    DOCLING = "docling"
    GROBID = "grobid"
    BIOC_ADAPTER = "bioc_adapter"
    OCRMY_PDF = "ocrmypdf"
    MANAGED_PARSER = "managed_parser"
    QUARANTINE = "quarantine"


@dataclass(frozen=True, slots=True)
class RouteDecision:
    input_format: InputFormat
    required_stages: tuple[ProcessingStage, ...]
    conditional_stages: tuple[ProcessingStage, ...] = ()
    reason: str = ""


_MEDIA_TYPES: Final[dict[str, InputFormat]] = {
    "application/pdf": InputFormat.PDF,
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": InputFormat.DOCX,
    "application/vnd.openxmlformats-officedocument.presentationml.presentation": InputFormat.PPTX,
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": InputFormat.XLSX,
    "text/html": InputFormat.HTML,
    "application/xhtml+xml": InputFormat.HTML,
    "application/bioc+json": InputFormat.BIOC_JSON,
    "application/bioc+xml": InputFormat.BIOC_XML,
    "application/jats+xml": InputFormat.JATS,
}

_EXTENSIONS: Final[dict[str, InputFormat]] = {
    ".pdf": InputFormat.PDF,
    ".docx": InputFormat.DOCX,
    ".pptx": InputFormat.PPTX,
    ".xlsx": InputFormat.XLSX,
    ".html": InputFormat.HTML,
    ".htm": InputFormat.HTML,
    ".nxml": InputFormat.JATS,
    ".jats": InputFormat.JATS,
    ".jpg": InputFormat.IMAGE,
    ".jpeg": InputFormat.IMAGE,
    ".png": InputFormat.IMAGE,
    ".tif": InputFormat.IMAGE,
    ".tiff": InputFormat.IMAGE,
    ".bmp": InputFormat.IMAGE,
    ".webp": InputFormat.IMAGE,
}

_SNIFF_LIMIT_BYTES: Final = 64 * 1024
_UTF8_BOM: Final = b"\xef\xbb\xbf"
_ASCII_WHITESPACE: Final = b" \t\r\n"


class DocumentRouter:
    """Classify inputs and expose every parser and fallback before execution."""

    def __init__(self, *, reject_extension_only: bool = True) -> None:
        self.reject_extension_only = reject_extension_only

    def detect(
        self,
        content: bytes,
        *,
        filename: str | None = None,
        media_type: str | None = None,
    ) -> InputFormat:
        normalized_media_type = (media_type or "").split(";", 1)[0].strip().lower()
        media_guess = _MEDIA_TYPES.get(normalized_media_type)

        sniffed = _sniff_format(content)
        if normalized_media_type.startswith("image/"):
            if sniffed is not InputFormat.IMAGE:
                return InputFormat.UNKNOWN
            if not _image_media_types_match(
                normalized_media_type,
                _sniff_image_media_type(content),
            ):
                return InputFormat.UNKNOWN
        if sniffed is not InputFormat.UNKNOWN:
            if media_guess is not None and media_guess is not sniffed:
                return InputFormat.UNKNOWN
            return sniffed
        if media_guess is not None:
            # All declared supported types have a bounded content sniffer. A
            # filename-derived declaration is not evidence on its own.
            return InputFormat.UNKNOWN

        if normalized_media_type.startswith("image/"):
            return InputFormat.UNKNOWN
        suffix = PurePath(filename or "").suffix.lower()
        extension_guess = _EXTENSIONS.get(suffix)
        if extension_guess is not None and not self.reject_extension_only:
            return extension_guess
        return sniffed

    def route(
        self,
        content: bytes,
        *,
        filename: str | None = None,
        media_type: str | None = None,
        ocr_enabled: bool = True,
        grobid_enabled: bool = True,
    ) -> RouteDecision:
        input_format = self.detect(content, filename=filename, media_type=media_type)
        if input_format is InputFormat.JATS:
            return RouteDecision(
                input_format=input_format,
                required_stages=(ProcessingStage.DOCLING,),
                reason="Native JATS is preserved as authoritative and converted by Docling.",
            )
        if input_format in {InputFormat.BIOC_XML, InputFormat.BIOC_JSON}:
            return RouteDecision(
                input_format=input_format,
                required_stages=(
                    ProcessingStage.BIOC_ADAPTER,
                    ProcessingStage.DOCLING,
                ),
                reason="BioC is retained as an annotation interchange source and projected through Docling.",
            )
        if input_format is InputFormat.PDF:
            conditional = (
                (ProcessingStage.OCRMY_PDF, ProcessingStage.GROBID)
                if ocr_enabled and grobid_enabled
                else ()
            )
            return RouteDecision(
                input_format=input_format,
                required_stages=(
                    (ProcessingStage.DOCLING, ProcessingStage.GROBID)
                    if grobid_enabled
                    else (ProcessingStage.DOCLING,)
                ),
                conditional_stages=conditional,
                reason="Docling supplies layout; GROBID supplies scholarly annotations; OCR is explicit scan fallback.",
            )
        if input_format in {
            InputFormat.HTML,
            InputFormat.DOCX,
            InputFormat.PPTX,
            InputFormat.XLSX,
            InputFormat.IMAGE,
        }:
            return RouteDecision(
                input_format=input_format,
                required_stages=(ProcessingStage.DOCLING,),
                reason="Docling is the primary converter for this supported format.",
            )
        return RouteDecision(
            input_format=input_format,
            required_stages=(ProcessingStage.QUARANTINE,),
            reason="No parser is configured for the detected media type.",
        )


@dataclass(frozen=True, slots=True)
class ManagedParserPolicy:
    """Guard against accidental external document uploads."""

    enabled: bool = False
    allowed_providers: tuple[str, ...] = ()

    def require_allowed(self, provider: str) -> None:
        if not self.enabled:
            raise PermissionError(
                "Managed document parsers are disabled; approve upload, retention, and license policy first."
            )
        if provider not in self.allowed_providers:
            raise PermissionError(f"Managed parser {provider!r} is not allowlisted")


def _sniff_format(content: bytes) -> InputFormat:
    prefix = content[:_SNIFF_LIMIT_BYTES].lstrip(_ASCII_WHITESPACE)
    if prefix.startswith(b"%PDF-"):
        return InputFormat.PDF
    text_prefix = _without_utf8_bom(prefix).lstrip(_ASCII_WHITESPACE)
    if text_prefix.startswith((b"{", b"[")):
        if _looks_like_bioc_json(content, text_prefix):
            return InputFormat.BIOC_JSON
        return InputFormat.UNKNOWN
    if text_prefix.startswith(b"<"):
        root_prefix = _strip_xml_misc(text_prefix)
        lowered = root_prefix[:2048].lower()
        if lowered.startswith(b"<!doctype html") or re.match(
            rb"<(?:[a-z0-9_.-]+:)?html(?:\s|/?>)", lowered
        ):
            return InputFormat.HTML
        if re.match(rb"<(?:[a-z0-9_.-]+:)?collection(?:\s|/?>)", lowered):
            return InputFormat.BIOC_XML
        if lowered.startswith(b"<!doctype article") or re.match(
            rb"<(?:[a-z0-9_.-]+:)?article(?:\s|/?>)", lowered
        ):
            return InputFormat.JATS
    if prefix.startswith(b"PK"):
        return _sniff_ooxml_format(content)
    if _sniff_image_media_type(prefix) is not None:
        return InputFormat.IMAGE
    return InputFormat.UNKNOWN


def _without_utf8_bom(content: bytes) -> bytes:
    return content.removeprefix(_UTF8_BOM)


def _looks_like_bioc_json(content: bytes, prefix: bytes) -> bool:
    required_keys = {"source", "date", "key", "documents"}
    if len(content) <= _SNIFF_LIMIT_BYTES:
        try:
            value = json.loads(_without_utf8_bom(content).decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            return False
        return isinstance(value, dict) and required_keys.issubset(value)
    return required_keys.issubset(_top_level_json_keys(prefix))


def _top_level_json_keys(content: bytes) -> set[str]:
    """Collect object keys from a bounded JSON prefix without parsing its body."""

    keys: set[str] = set()
    stack: list[int] = []
    index = 0
    while index < len(content):
        token = content[index]
        if token == ord('"'):
            start = index
            index += 1
            while index < len(content):
                if content[index] == ord("\\"):
                    index += 2
                    continue
                if content[index] == ord('"'):
                    break
                index += 1
            if index >= len(content):
                return keys
            end = index + 1
            lookahead = end
            while lookahead < len(content) and content[lookahead] in _ASCII_WHITESPACE:
                lookahead += 1
            if stack == [ord("{")] and (
                lookahead < len(content) and content[lookahead] == ord(":")
            ):
                try:
                    key = json.loads(content[start:end].decode("utf-8"))
                except (UnicodeDecodeError, json.JSONDecodeError):
                    return keys
                if isinstance(key, str):
                    keys.add(key)
            index = end
            continue
        if token in (ord("{"), ord("[")):
            stack.append(token)
        elif token == ord("}"):
            if not stack or stack[-1] != ord("{"):
                return keys
            stack.pop()
        elif token == ord("]"):
            if not stack or stack[-1] != ord("["):
                return keys
            stack.pop()
        index += 1
    return keys


def _strip_xml_misc(content: bytes) -> bytes:
    """Skip bounded XML declarations, processing instructions, and comments."""

    remaining = content
    while True:
        remaining = remaining.lstrip(_ASCII_WHITESPACE)
        if remaining.startswith(b"<?"):
            end = remaining.find(b"?>", 2)
            if end < 0:
                return b""
            remaining = remaining[end + 2 :]
            continue
        if remaining.startswith(b"<!--"):
            end = remaining.find(b"-->", 4)
            if end < 0:
                return b""
            remaining = remaining[end + 3 :]
            continue
        return remaining


def _sniff_ooxml_format(content: bytes) -> InputFormat:
    """Classify an OOXML package from bounded ZIP metadata without extraction."""

    try:
        with zipfile.ZipFile(BytesIO(content)) as archive:
            names = archive.namelist()
    except (OSError, ValueError, zipfile.BadZipFile, zipfile.LargeZipFile):
        return InputFormat.UNKNOWN
    if len(names) > 20_000 or "[Content_Types].xml" not in names:
        return InputFormat.UNKNOWN
    markers = {
        InputFormat.DOCX: "word/document.xml",
        InputFormat.PPTX: "ppt/presentation.xml",
        InputFormat.XLSX: "xl/workbook.xml",
    }
    matches = [
        input_format for input_format, marker in markers.items() if marker in names
    ]
    return matches[0] if len(matches) == 1 else InputFormat.UNKNOWN


def _sniff_image_media_type(content: bytes) -> str | None:
    if content.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if content.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if content.startswith((b"II*\x00", b"MM\x00*")):
        return "image/tiff"
    if content.startswith(b"BM"):
        return "image/bmp"
    if len(content) >= 12 and content.startswith(b"RIFF") and content[8:12] == b"WEBP":
        return "image/webp"
    return None


def _image_media_types_match(declared: str, detected: str | None) -> bool:
    aliases = {
        "image/jpg": "image/jpeg",
        "image/pjpeg": "image/jpeg",
        "image/x-png": "image/png",
        "image/x-tiff": "image/tiff",
        "image/x-ms-bmp": "image/bmp",
    }
    return aliases.get(declared, declared) == detected


__all__ = [
    "DocumentRouter",
    "InputFormat",
    "ManagedParserPolicy",
    "ProcessingStage",
    "RouteDecision",
]
