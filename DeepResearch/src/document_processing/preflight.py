"""Bounded hostile-input checks performed before parser submission.

DeepCritical owns the resource policy and diagnostic contract, not a PDF
parser.  PDF encryption and page-tree inspection are delegated to ``pypdf``
after the source has passed a strict byte-size gate.
"""

from __future__ import annotations

import errno
import os
import re
import stat
from contextlib import contextmanager
from dataclasses import dataclass
from enum import StrEnum
from io import BytesIO
from pathlib import Path
from typing import BinaryIO, Iterator

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


class SourceSnapshotError(RuntimeError):
    """A path could not yield one stable, policy-compliant descriptor snapshot."""

    def __init__(self, result: PreflightResult) -> None:
        super().__init__(result.diagnostics[0].message)
        self.result = result


@dataclass(frozen=True, slots=True)
class VerifiedSource:
    """An opened source whose descriptor matches the pre-open path identity."""

    path: Path
    stream: BinaryIO
    opened_stat: os.stat_result


@dataclass(frozen=True, slots=True)
class _PdfInspection:
    encrypted: bool | None
    page_count: int | None
    page_count_source: PdfPageCountSource | None
    structure_complete: bool
    error_type: str | None = None


def _source_snapshot_signature(value: os.stat_result) -> tuple[int, ...]:
    return (
        value.st_dev,
        value.st_ino,
        value.st_mode,
        value.st_size,
        value.st_mtime_ns,
        value.st_ctime_ns,
    )


def _source_path_descriptor_signature(value: os.stat_result) -> tuple[int, ...]:
    """Return metadata comparable between a path stat and descriptor stat.

    Windows can report creation time through ``lstat().st_ctime_ns`` while
    ``fstat().st_ctime_ns`` reflects the latest metadata change for the same
    file. File identity, type, size, and modification time remain comparable;
    descriptor-to-descriptor validation retains the full signature.
    """

    signature = _source_snapshot_signature(value)
    return signature[:-1] if os.name == "nt" else signature


def _snapshot_failure(
    code: PreflightDiagnosticCode,
    message: str,
    path: Path,
    *,
    byte_size: int | None = None,
    error_type: str | None = None,
) -> PreflightResult:
    details: dict[str, str | int | bool] = {"path": str(path)}
    if error_type is not None:
        details["error_type"] = error_type
    return _single_failure(
        code,
        message,
        byte_size=byte_size,
        details=details,
    )


def _open_source_descriptor(path: Path, flags: int) -> int:
    """Open *path* through one patchable boundary for deterministic race tests."""

    return os.open(path, flags)


def _verified_path_stat(path: Path, *, allow_symlinks: bool) -> os.stat_result:
    try:
        path_stat = path.lstat()
    except FileNotFoundError as exc:
        raise SourceSnapshotError(
            _snapshot_failure(
                PreflightDiagnosticCode.SOURCE_NOT_FOUND,
                "Source path does not exist.",
                path,
                error_type=type(exc).__name__,
            )
        ) from exc
    except OSError as exc:
        raise SourceSnapshotError(
            _snapshot_failure(
                PreflightDiagnosticCode.SOURCE_STAT_FAILED,
                "Source metadata could not be read.",
                path,
                error_type=type(exc).__name__,
            )
        ) from exc

    if stat.S_ISLNK(path_stat.st_mode):
        if not allow_symlinks:
            raise SourceSnapshotError(
                _snapshot_failure(
                    PreflightDiagnosticCode.SOURCE_SYMLINK_NOT_ALLOWED,
                    "Symbolic-link sources are disabled by preflight policy.",
                    path,
                    byte_size=path_stat.st_size,
                )
            )
        try:
            path_stat = path.stat()
        except OSError as exc:
            raise SourceSnapshotError(
                _snapshot_failure(
                    PreflightDiagnosticCode.SOURCE_STAT_FAILED,
                    "Symbolic-link target metadata could not be read.",
                    path,
                    error_type=type(exc).__name__,
                )
            ) from exc

    if not stat.S_ISREG(path_stat.st_mode):
        raise SourceSnapshotError(
            _snapshot_failure(
                PreflightDiagnosticCode.SOURCE_NOT_REGULAR_FILE,
                "Source is not a regular file.",
                path,
                byte_size=path_stat.st_size,
            )
        )
    return path_stat


@contextmanager
def verified_open_path(
    source: str | Path,
    *,
    limits: PreflightLimits | None = None,
) -> Iterator[VerifiedSource]:
    """Open one stable source snapshot without following forbidden symlinks.

    The path identity is checked against the opened descriptor and checked
    again after the caller finishes inspecting or reading it. On POSIX,
    ``O_NOFOLLOW`` closes the lstat/open symlink race when symlinks are
    forbidden; ``O_CLOEXEC`` prevents descriptor inheritance.
    """

    policy = limits or PreflightLimits()
    path = Path(source)
    path_stat = _verified_path_stat(path, allow_symlinks=policy.allow_symlinks)
    if path_stat.st_size > policy.max_source_bytes:
        raise SourceSnapshotError(
            too_large_result(path_stat.st_size, policy.max_source_bytes)
        )
    if path_stat.st_size == 0:
        raise SourceSnapshotError(
            _single_failure(
                PreflightDiagnosticCode.SOURCE_EMPTY,
                "Source is empty.",
                byte_size=0,
            )
        )

    flags = os.O_RDONLY | getattr(os, "O_BINARY", 0) | getattr(os, "O_CLOEXEC", 0)
    if not policy.allow_symlinks:
        flags |= getattr(os, "O_NOFOLLOW", 0)
    try:
        descriptor = _open_source_descriptor(path, flags)
    except OSError as exc:
        if not policy.allow_symlinks and exc.errno in {errno.ELOOP, errno.EMLINK}:
            raise SourceSnapshotError(
                _snapshot_failure(
                    PreflightDiagnosticCode.SOURCE_SYMLINK_NOT_ALLOWED,
                    "Source became a symbolic link while it was being opened.",
                    path,
                    error_type=type(exc).__name__,
                )
            ) from exc
        raise

    with os.fdopen(descriptor, "rb") as stream:
        opened_stat = os.fstat(stream.fileno())
        if (
            not stat.S_ISREG(opened_stat.st_mode)
            or not os.path.samestat(path_stat, opened_stat)
            or _source_path_descriptor_signature(path_stat)
            != _source_path_descriptor_signature(opened_stat)
        ):
            raise SourceSnapshotError(
                _snapshot_failure(
                    PreflightDiagnosticCode.SOURCE_SNAPSHOT_CHANGED,
                    "Source identity changed while opening the intake snapshot.",
                    path,
                    byte_size=opened_stat.st_size,
                )
            )
        yield VerifiedSource(path=path, stream=stream, opened_stat=opened_stat)
        final_stat = os.fstat(stream.fileno())
        if _source_snapshot_signature(opened_stat) != _source_snapshot_signature(
            final_stat
        ):
            raise SourceSnapshotError(
                _snapshot_failure(
                    PreflightDiagnosticCode.SOURCE_SNAPSHOT_CHANGED,
                    "Source changed while its intake snapshot was being read.",
                    path,
                    byte_size=final_stat.st_size,
                )
            )
        final_path_stat = _verified_path_stat(
            path, allow_symlinks=policy.allow_symlinks
        )
        if not os.path.samestat(
            final_path_stat, final_stat
        ) or _source_path_descriptor_signature(
            final_path_stat
        ) != _source_path_descriptor_signature(final_stat):
            raise SourceSnapshotError(
                _snapshot_failure(
                    PreflightDiagnosticCode.SOURCE_SNAPSHOT_CHANGED,
                    "Source path changed while its snapshot was being inspected.",
                    path,
                    byte_size=final_stat.st_size,
                )
            )


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
    try:
        with verified_open_path(source, limits=policy) as verified:
            result = preflight_stream(
                verified.stream,
                byte_size=verified.opened_stat.st_size,
                filename=verified.path.name,
                media_type=media_type,
                limits=policy,
            )
            return result
    except SourceSnapshotError as exc:
        return exc.result
    except OSError as exc:
        path = Path(source)
        return _single_failure(
            PreflightDiagnosticCode.SOURCE_READ_FAILED,
            "Source could not be opened or read.",
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
    "SourceSnapshotError",
    "VerifiedSource",
    "preflight_bytes",
    "preflight_path",
    "preflight_stream",
    "too_large_result",
    "verified_open_path",
]
