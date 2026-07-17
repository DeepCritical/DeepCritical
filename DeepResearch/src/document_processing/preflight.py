"""Bounded hostile-input checks performed before parser submission.

DeepCritical owns the resource policy and diagnostic contract, not a PDF
parser.  PDF encryption and page-tree inspection are delegated to ``pypdf``
after the source has passed a strict byte-size gate.
"""

from __future__ import annotations

import os
import re
import stat
from dataclasses import dataclass
from enum import StrEnum
from io import BytesIO
from pathlib import Path
from typing import BinaryIO

from pydantic import Field
from pypdf import PdfReader
from pypdf.errors import PdfReadError

from .models import DiagnosticSeverity, FrozenModel

_DEFAULT_MAX_SOURCE_BYTES = 100 * 1024 * 1024
_DEFAULT_MAX_PDF_PAGES = 1_000
_HEADER_BYTES = 1_024
_PDF_HEADER = re.compile(rb"%PDF-[12]\.\d")


class PreflightDecision(StrEnum):
    """Whether a source may proceed to parser routing."""

    PROCEED = "proceed"
    QUARANTINE = "quarantine"


class PreflightDiagnosticCode(StrEnum):
    """Stable codes emitted by document preflight."""

    SOURCE_NOT_FOUND = "SOURCE_NOT_FOUND"
    SOURCE_STAT_FAILED = "SOURCE_STAT_FAILED"
    SOURCE_NOT_REGULAR_FILE = "SOURCE_NOT_REGULAR_FILE"
    SOURCE_SYMLINK_NOT_ALLOWED = "SOURCE_SYMLINK_NOT_ALLOWED"
    SOURCE_TOO_LARGE = "SOURCE_TOO_LARGE"
    SOURCE_EMPTY = "SOURCE_EMPTY"
    SOURCE_READ_FAILED = "SOURCE_READ_FAILED"
    SOURCE_SNAPSHOT_CHANGED = "SOURCE_SNAPSHOT_CHANGED"
    PDF_HEADER_INVALID = "PDF_HEADER_INVALID"
    PDF_ENCRYPTED = "PDF_ENCRYPTED"
    PDF_PAGE_LIMIT_EXCEEDED = "PDF_PAGE_LIMIT_EXCEEDED"
    PDF_PAGE_COUNT_UNCERTAIN = "PDF_PAGE_COUNT_UNCERTAIN"
    PDF_STRUCTURE_UNCERTAIN = "PDF_STRUCTURE_UNCERTAIN"


class PdfPageCountSource(StrEnum):
    """Established inspector used to resolve the PDF page tree."""

    PYPDF = "pypdf"


class PreflightLimits(FrozenModel):
    """Resource and acceptance policy applied before parsing."""

    max_source_bytes: int = Field(default=_DEFAULT_MAX_SOURCE_BYTES, gt=0)
    max_pdf_pages: int = Field(default=_DEFAULT_MAX_PDF_PAGES, gt=0)
    allow_encrypted_pdfs: bool = False
    require_pdf_page_count: bool = True
    quarantine_on_pdf_structure_uncertainty: bool = True
    allow_symlinks: bool = False


class PreflightDiagnostic(FrozenModel):
    """One machine-actionable preflight observation."""

    code: PreflightDiagnosticCode
    severity: DiagnosticSeverity
    message: str
    details: dict[str, str | int | bool] = Field(default_factory=dict)


class PreflightResult(FrozenModel):
    """Complete preflight decision for one source snapshot."""

    decision: PreflightDecision
    byte_size: int | None = Field(default=None, ge=0)
    is_pdf: bool = False
    pdf_encrypted: bool | None = None
    pdf_page_count: int | None = Field(default=None, ge=0)
    pdf_page_count_source: PdfPageCountSource | None = None
    diagnostics: tuple[PreflightDiagnostic, ...] = ()

    @property
    def may_proceed(self) -> bool:
        """Return true only when the source passed every configured check."""

        return self.decision is PreflightDecision.PROCEED


@dataclass(frozen=True, slots=True)
class _PdfInspection:
    encrypted: bool | None
    page_count: int | None
    page_count_source: PdfPageCountSource | None
    structure_complete: bool
    error_type: str | None = None


def preflight_path(
    source: str | Path,
    *,
    limits: PreflightLimits | None = None,
    media_type: str | None = None,
) -> PreflightResult:
    """Inspect a path without opening sources that exceed the byte limit.

    ``lstat`` precedes ``open`` and ``fstat`` verifies the opened handle.  The
    caller must still apply the same byte limit while streaming the accepted
    snapshot into durable storage, which closes the remaining file-growth race.
    """

    policy = limits or PreflightLimits()
    path = Path(source)
    try:
        path_stat = path.lstat()
    except FileNotFoundError:
        return _single_failure(
            PreflightDiagnosticCode.SOURCE_NOT_FOUND,
            "Source path does not exist.",
            details={"path": str(path)},
        )
    except OSError as exc:
        return _single_failure(
            PreflightDiagnosticCode.SOURCE_STAT_FAILED,
            "Source metadata could not be read.",
            details={"path": str(path), "error_type": type(exc).__name__},
        )

    if stat.S_ISLNK(path_stat.st_mode) and not policy.allow_symlinks:
        return _single_failure(
            PreflightDiagnosticCode.SOURCE_SYMLINK_NOT_ALLOWED,
            "Symbolic-link sources are disabled by preflight policy.",
            byte_size=path_stat.st_size,
            details={"path": str(path)},
        )
    if stat.S_ISLNK(path_stat.st_mode):
        try:
            path_stat = path.stat()
        except OSError as exc:
            return _single_failure(
                PreflightDiagnosticCode.SOURCE_STAT_FAILED,
                "Symbolic-link target metadata could not be read.",
                details={"path": str(path), "error_type": type(exc).__name__},
            )

    if not stat.S_ISREG(path_stat.st_mode):
        return _single_failure(
            PreflightDiagnosticCode.SOURCE_NOT_REGULAR_FILE,
            "Source is not a regular file.",
            byte_size=path_stat.st_size,
            details={"path": str(path)},
        )
    if path_stat.st_size > policy.max_source_bytes:
        return too_large_result(path_stat.st_size, policy.max_source_bytes)
    if path_stat.st_size == 0:
        return _single_failure(
            PreflightDiagnosticCode.SOURCE_EMPTY,
            "Source is empty.",
            byte_size=0,
        )

    try:
        with path.open("rb") as stream:
            opened_stat = os.fstat(stream.fileno())
            if not stat.S_ISREG(opened_stat.st_mode):
                return _single_failure(
                    PreflightDiagnosticCode.SOURCE_NOT_REGULAR_FILE,
                    "Opened source is not a regular file.",
                    byte_size=opened_stat.st_size,
                    details={"path": str(path)},
                )
            if opened_stat.st_size > policy.max_source_bytes:
                return too_large_result(opened_stat.st_size, policy.max_source_bytes)
            if opened_stat.st_size == 0:
                return _single_failure(
                    PreflightDiagnosticCode.SOURCE_EMPTY,
                    "Source became empty before inspection.",
                    byte_size=0,
                )

            result = preflight_stream(
                stream,
                byte_size=opened_stat.st_size,
                filename=path.name,
                media_type=media_type,
                limits=policy,
            )
            final_size = os.fstat(stream.fileno()).st_size
            if final_size > policy.max_source_bytes:
                return too_large_result(
                    final_size, policy.max_source_bytes, is_pdf=result.is_pdf
                )
            return result
    except OSError as exc:
        return _single_failure(
            PreflightDiagnosticCode.SOURCE_READ_FAILED,
            "Source could not be opened or read.",
            byte_size=path_stat.st_size,
            details={"path": str(path), "error_type": type(exc).__name__},
        )


def preflight_bytes(
    content: bytes,
    *,
    limits: PreflightLimits | None = None,
    filename: str | None = None,
    media_type: str | None = None,
) -> PreflightResult:
    """Inspect an already bounded in-memory source."""

    stream = BytesIO(content)
    return preflight_stream(
        stream,
        byte_size=len(content),
        limits=limits,
        filename=filename,
        media_type=media_type,
    )


def preflight_stream(
    stream: BinaryIO,
    *,
    byte_size: int,
    limits: PreflightLimits | None = None,
    filename: str | None = None,
    media_type: str | None = None,
) -> PreflightResult:
    """Inspect one already-open bounded descriptor without taking ownership of it."""

    policy = limits or PreflightLimits()
    if byte_size > policy.max_source_bytes:
        return too_large_result(byte_size, policy.max_source_bytes)
    if byte_size == 0:
        return _single_failure(
            PreflightDiagnosticCode.SOURCE_EMPTY,
            "Source is empty.",
            byte_size=0,
        )
    try:
        stream.seek(0)
        header = stream.read(_HEADER_BYTES)
        if not header:
            return _single_failure(
                PreflightDiagnosticCode.SOURCE_READ_FAILED,
                "Source content could not be read.",
                byte_size=byte_size,
            )
        return _preflight_open_stream(
            stream,
            header=header,
            byte_size=byte_size,
            filename=filename,
            media_type=media_type,
            limits=policy,
        )
    except OSError as exc:
        return _single_failure(
            PreflightDiagnosticCode.SOURCE_READ_FAILED,
            "Source content could not be read.",
            byte_size=byte_size,
            details={"error_type": type(exc).__name__},
        )


def _preflight_open_stream(
    stream: BinaryIO,
    *,
    header: bytes,
    byte_size: int,
    filename: str | None,
    media_type: str | None,
    limits: PreflightLimits,
) -> PreflightResult:
    pdf_by_header = _PDF_HEADER.search(header) is not None
    normalized_media_type = (media_type or "").split(";", 1)[0].strip().lower()
    pdf_by_metadata = normalized_media_type == "application/pdf" or (
        filename is not None and Path(filename).suffix.lower() == ".pdf"
    )
    is_pdf = pdf_by_header or pdf_by_metadata
    if not is_pdf:
        return PreflightResult(
            decision=PreflightDecision.PROCEED,
            byte_size=byte_size,
        )
    if not pdf_by_header:
        return _single_failure(
            PreflightDiagnosticCode.PDF_HEADER_INVALID,
            "PDF metadata or filename was provided, but no PDF header was found.",
            byte_size=byte_size,
            is_pdf=True,
        )

    stream.seek(0)
    inspection = _inspect_pdf(stream)
    diagnostics: list[PreflightDiagnostic] = []
    quarantine = False
    if inspection.encrypted:
        severity = (
            DiagnosticSeverity.WARNING
            if limits.allow_encrypted_pdfs
            else DiagnosticSeverity.FATAL
        )
        diagnostics.append(
            PreflightDiagnostic(
                code=PreflightDiagnosticCode.PDF_ENCRYPTED,
                severity=severity,
                message="PDF is encrypted.",
                details={"allowed_by_policy": limits.allow_encrypted_pdfs},
            )
        )
        quarantine = not limits.allow_encrypted_pdfs

    if inspection.page_count is None:
        severity = (
            DiagnosticSeverity.ERROR
            if limits.require_pdf_page_count
            else DiagnosticSeverity.WARNING
        )
        diagnostics.append(
            PreflightDiagnostic(
                code=PreflightDiagnosticCode.PDF_PAGE_COUNT_UNCERTAIN,
                severity=severity,
                message="pypdf could not establish the PDF page count.",
                details={"required_by_policy": limits.require_pdf_page_count},
            )
        )
        quarantine = quarantine or limits.require_pdf_page_count
    elif inspection.page_count > limits.max_pdf_pages:
        diagnostics.append(
            PreflightDiagnostic(
                code=PreflightDiagnosticCode.PDF_PAGE_LIMIT_EXCEEDED,
                severity=DiagnosticSeverity.FATAL,
                message="PDF page count exceeds the configured limit.",
                details={
                    "actual_pages": inspection.page_count,
                    "max_pdf_pages": limits.max_pdf_pages,
                },
            )
        )
        quarantine = True

    if not inspection.structure_complete:
        severity = (
            DiagnosticSeverity.ERROR
            if limits.quarantine_on_pdf_structure_uncertainty
            else DiagnosticSeverity.WARNING
        )
        details: dict[str, str | int | bool] = {
            "quarantine_by_policy": limits.quarantine_on_pdf_structure_uncertainty
        }
        if inspection.error_type is not None:
            details["error_type"] = inspection.error_type
        diagnostics.append(
            PreflightDiagnostic(
                code=PreflightDiagnosticCode.PDF_STRUCTURE_UNCERTAIN,
                severity=severity,
                message="pypdf could not validate the PDF page-tree structure.",
                details=details,
            )
        )
        quarantine = quarantine or limits.quarantine_on_pdf_structure_uncertainty

    return PreflightResult(
        decision=(
            PreflightDecision.QUARANTINE if quarantine else PreflightDecision.PROCEED
        ),
        byte_size=byte_size,
        is_pdf=True,
        pdf_encrypted=inspection.encrypted,
        pdf_page_count=inspection.page_count,
        pdf_page_count_source=inspection.page_count_source,
        diagnostics=tuple(diagnostics),
    )


def _inspect_pdf(stream: BinaryIO) -> _PdfInspection:
    """Delegate bounded PDF structure inspection to pypdf."""

    try:
        reader = PdfReader(stream, strict=False, root_object_recovery_limit=1_000)
        encrypted = reader.is_encrypted
        if encrypted:
            try:
                reader.decrypt("")
            except (PdfReadError, ValueError):
                pass
        try:
            page_count = len(reader.pages)
        except (PdfReadError, ValueError, RecursionError):
            page_count = None
        return _PdfInspection(
            encrypted=encrypted,
            page_count=page_count,
            page_count_source=(
                PdfPageCountSource.PYPDF if page_count is not None else None
            ),
            # A password-protected file can be structurally valid even though
            # its page tree cannot be traversed without credentials.
            structure_complete=encrypted or page_count is not None,
        )
    except (PdfReadError, ValueError, RecursionError) as exc:
        return _PdfInspection(
            encrypted=None,
            page_count=None,
            page_count_source=None,
            structure_complete=False,
            error_type=type(exc).__name__,
        )


def too_large_result(
    byte_size: int,
    max_source_bytes: int,
    *,
    is_pdf: bool = False,
) -> PreflightResult:
    """Build the stable quarantine result for a byte-limit violation."""

    return _single_failure(
        PreflightDiagnosticCode.SOURCE_TOO_LARGE,
        "Source exceeds the configured byte limit.",
        byte_size=byte_size,
        is_pdf=is_pdf,
        details={
            "actual_bytes": byte_size,
            "max_source_bytes": max_source_bytes,
        },
    )


def _single_failure(
    code: PreflightDiagnosticCode,
    message: str,
    *,
    byte_size: int | None = None,
    is_pdf: bool = False,
    details: dict[str, str | int | bool] | None = None,
) -> PreflightResult:
    return PreflightResult(
        decision=PreflightDecision.QUARANTINE,
        byte_size=byte_size,
        is_pdf=is_pdf,
        diagnostics=(
            PreflightDiagnostic(
                code=code,
                severity=DiagnosticSeverity.FATAL,
                message=message,
                details=details or {},
            ),
        ),
    )


__all__ = [
    "PdfPageCountSource",
    "PreflightDecision",
    "PreflightDiagnostic",
    "PreflightDiagnosticCode",
    "PreflightLimits",
    "PreflightResult",
    "preflight_bytes",
    "preflight_path",
    "preflight_stream",
    "too_large_result",
]
