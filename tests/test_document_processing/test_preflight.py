from __future__ import annotations

import errno
from io import BytesIO
from pathlib import Path
from typing import Any

import pytest
from pydantic import ValidationError
from pypdf import PdfWriter

from DeepResearch.src.document_processing import preflight as preflight_module
from DeepResearch.src.document_processing.models import DiagnosticSeverity
from DeepResearch.src.document_processing.preflight import (
    PdfPageCountSource,
    PreflightDecision,
    PreflightDiagnosticCode,
    PreflightLimits,
    PreflightResult,
    SourceSnapshotError,
    preflight_bytes,
    preflight_path,
    verified_open_path,
)


def _pdf(
    pages: int = 2,
    *,
    password: str | None = None,
    decoy_metadata: bool = False,
) -> bytes:
    writer = PdfWriter()
    for _ in range(pages):
        writer.add_blank_page(width=72, height=72)
    if decoy_metadata:
        writer.add_metadata({"/Subject": "/Encrypt /Type /Page /Count 999"})
    if password is not None:
        writer.encrypt(password)
    output = BytesIO()
    writer.write(output)
    return output.getvalue()


def _codes(result: PreflightResult) -> set[PreflightDiagnosticCode]:
    return {item.code for item in result.diagnostics}


def test_limits_reject_non_positive_values() -> None:
    with pytest.raises(ValidationError):
        PreflightLimits(max_source_bytes=0)
    with pytest.raises(ValidationError):
        PreflightLimits(max_pdf_pages=0)


def test_oversized_path_is_rejected_before_open(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source = tmp_path / "large.bin"
    source.write_bytes(b"012345")

    def forbidden_open(*args: object, **kwargs: object) -> object:
        raise AssertionError("oversized source must not be opened")

    monkeypatch.setattr(Path, "open", forbidden_open)
    result = preflight_path(source, limits=PreflightLimits(max_source_bytes=5))

    assert result.decision is PreflightDecision.QUARANTINE
    assert result.byte_size == 6
    assert _codes(result) == {PreflightDiagnosticCode.SOURCE_TOO_LARGE}
    assert result.diagnostics[0].details == {
        "actual_bytes": 6,
        "max_source_bytes": 5,
    }


def test_preflight_rejects_regular_file_swap_during_verified_open(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = tmp_path / "source.html"
    replacement = tmp_path / "replacement.html"
    displaced = tmp_path / "displaced.html"
    source.write_text("<html>original</html>", encoding="utf-8")
    replacement.write_text("<html>replacement</html>", encoding="utf-8")
    real_open = preflight_module._open_source_descriptor

    def swap_before_open(path: Path, flags: int) -> int:
        source.rename(displaced)
        replacement.rename(source)
        return real_open(path, flags)

    monkeypatch.setattr(
        preflight_module,
        "_open_source_descriptor",
        swap_before_open,
    )

    result = preflight_path(source, media_type="text/html")

    assert result.decision is PreflightDecision.QUARANTINE
    assert _codes(result) == {PreflightDiagnosticCode.SOURCE_SNAPSHOT_CHANGED}


def test_preflight_rejects_descriptor_mutation_after_inspection(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = tmp_path / "source.html"
    source.write_text("<html>stable</html>", encoding="utf-8")
    real_signature = preflight_module._source_snapshot_signature
    calls = 0

    def drift_on_final_stat(value: Any) -> tuple[int, ...]:
        nonlocal calls
        calls += 1
        signature = real_signature(value)
        if calls == 4:
            return (*signature[:-1], signature[-1] + 1)
        return signature

    monkeypatch.setattr(
        preflight_module,
        "_source_snapshot_signature",
        drift_on_final_stat,
    )

    result = preflight_path(source, media_type="text/html")

    assert result.decision is PreflightDecision.QUARANTINE
    assert _codes(result) == {PreflightDiagnosticCode.SOURCE_SNAPSHOT_CHANGED}


def test_verified_open_rejects_path_replacement_after_read(tmp_path: Path) -> None:
    source = tmp_path / "source.html"
    replacement = tmp_path / "replacement.html"
    displaced = tmp_path / "displaced.html"
    source.write_text("<html>original</html>", encoding="utf-8")
    replacement.write_text("<html>replacement</html>", encoding="utf-8")

    def replace_after_read() -> None:
        with verified_open_path(source) as verified:
            assert verified.stream.read() == b"<html>original</html>"
            source.rename(displaced)
            replacement.rename(source)

    with pytest.raises(SourceSnapshotError) as error:
        replace_after_read()

    assert _codes(error.value.result) == {
        PreflightDiagnosticCode.SOURCE_SNAPSHOT_CHANGED
    }


def test_missing_and_non_regular_paths_are_explicit(tmp_path: Path) -> None:
    missing = preflight_path(tmp_path / "missing.pdf")
    directory = preflight_path(tmp_path)

    assert _codes(missing) == {PreflightDiagnosticCode.SOURCE_NOT_FOUND}
    assert _codes(directory) == {PreflightDiagnosticCode.SOURCE_NOT_REGULAR_FILE}
    assert missing.decision is PreflightDecision.QUARANTINE
    assert directory.decision is PreflightDecision.QUARANTINE


def test_symlink_policy_is_explicit_and_allowed_targets_are_inspected(
    tmp_path: Path,
) -> None:
    target = tmp_path / "target.html"
    source = tmp_path / "source.html"
    target.write_text("<html>target</html>", encoding="utf-8")
    try:
        source.symlink_to(target)
    except OSError:
        pytest.skip("symbolic links are unavailable on this platform")

    rejected = preflight_path(source, media_type="text/html")
    accepted = preflight_path(
        source,
        media_type="text/html",
        limits=PreflightLimits(allow_symlinks=True),
    )

    assert _codes(rejected) == {PreflightDiagnosticCode.SOURCE_SYMLINK_NOT_ALLOWED}
    assert accepted.may_proceed


def test_source_metadata_errors_are_machine_readable(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source = tmp_path / "source.html"
    source.write_text("<html>source</html>", encoding="utf-8")

    def stat_failure(*args: object, **kwargs: object) -> object:
        raise PermissionError("metadata denied")

    monkeypatch.setattr(Path, "lstat", stat_failure)

    result = preflight_path(source, media_type="text/html")

    assert _codes(result) == {PreflightDiagnosticCode.SOURCE_STAT_FAILED}
    assert result.diagnostics[0].details["error_type"] == "PermissionError"


def test_allowed_symlink_target_metadata_errors_are_machine_readable(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    target = tmp_path / "target.html"
    source = tmp_path / "source.html"
    target.write_text("<html>target</html>", encoding="utf-8")
    try:
        source.symlink_to(target)
    except OSError:
        pytest.skip("symbolic links are unavailable on this platform")
    real_stat = Path.stat

    def target_stat_failure(path: Path, *args: object, **kwargs: object) -> object:
        if path == source:
            raise PermissionError("target metadata denied")
        return real_stat(path, *args, **kwargs)

    monkeypatch.setattr(Path, "stat", target_stat_failure)

    result = preflight_path(
        source,
        media_type="text/html",
        limits=PreflightLimits(allow_symlinks=True),
    )

    assert _codes(result) == {PreflightDiagnosticCode.SOURCE_STAT_FAILED}
    assert result.diagnostics[0].details["error_type"] == "PermissionError"


def test_pdf_path_uses_established_inspector(tmp_path: Path) -> None:
    source = tmp_path / "paper.pdf"
    source.write_bytes(_pdf(2))

    result = preflight_path(source)

    assert result.may_proceed
    assert result.byte_size == source.stat().st_size
    assert result.pdf_page_count == 2
    assert result.pdf_page_count_source is PdfPageCountSource.PYPDF


def test_path_open_failure_is_machine_readable(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source = tmp_path / "paper.pdf"
    source.write_bytes(_pdf())

    def denied_open(*args: object, **kwargs: object) -> object:
        raise PermissionError("denied for test")

    monkeypatch.setattr(
        preflight_module,
        "_open_source_descriptor",
        denied_open,
    )
    result = preflight_path(source)

    assert result.decision is PreflightDecision.QUARANTINE
    assert _codes(result) == {PreflightDiagnosticCode.SOURCE_READ_FAILED}
    assert result.diagnostics[0].details["error_type"] == "PermissionError"


def test_symlink_swap_during_open_fails_closed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source = tmp_path / "paper.pdf"
    source.write_bytes(_pdf())

    def symlink_race(*args: object, **kwargs: object) -> int:
        raise OSError(errno.ELOOP, "symbolic-link loop")

    monkeypatch.setattr(preflight_module, "_open_source_descriptor", symlink_race)

    result = preflight_path(source)

    assert _codes(result) == {PreflightDiagnosticCode.SOURCE_SYMLINK_NOT_ALLOWED}


def test_empty_path_is_quarantined_before_open(tmp_path: Path) -> None:
    source = tmp_path / "empty.bin"
    source.write_bytes(b"")

    result = preflight_path(source)

    assert _codes(result) == {PreflightDiagnosticCode.SOURCE_EMPTY}


def test_empty_and_oversized_bytes_are_quarantined() -> None:
    empty = preflight_bytes(b"")
    oversized = preflight_bytes(b"1234", limits=PreflightLimits(max_source_bytes=3))

    assert _codes(empty) == {PreflightDiagnosticCode.SOURCE_EMPTY}
    assert _codes(oversized) == {PreflightDiagnosticCode.SOURCE_TOO_LARGE}


def test_non_pdf_at_exact_byte_limit_may_proceed() -> None:
    result = preflight_bytes(b"text", limits=PreflightLimits(max_source_bytes=4))

    assert result.may_proceed
    assert result.byte_size == 4
    assert not result.is_pdf
    assert result.diagnostics == ()


def test_pdf_page_count_within_limit_may_proceed() -> None:
    result = preflight_bytes(_pdf(2), limits=PreflightLimits(max_pdf_pages=2))

    assert result.decision is PreflightDecision.PROCEED
    assert result.is_pdf
    assert result.pdf_encrypted is False
    assert result.pdf_page_count == 2
    assert result.pdf_page_count_source is PdfPageCountSource.PYPDF
    assert result.diagnostics == ()


def test_pdf_page_limit_is_enforced() -> None:
    result = preflight_bytes(_pdf(2), limits=PreflightLimits(max_pdf_pages=1))

    assert result.decision is PreflightDecision.QUARANTINE
    assert result.pdf_page_count == 2
    assert _codes(result) == {PreflightDiagnosticCode.PDF_PAGE_LIMIT_EXCEEDED}
    assert result.diagnostics[0].severity is DiagnosticSeverity.FATAL


def test_pdf_metadata_is_not_mistaken_for_structure() -> None:
    result = preflight_bytes(_pdf(1, decoy_metadata=True))

    assert result.may_proceed
    assert result.pdf_encrypted is False
    assert result.pdf_page_count == 1


def test_encrypted_pdf_is_quarantined_by_default() -> None:
    result = preflight_bytes(_pdf(2, password="secret"))

    assert result.pdf_encrypted is True
    assert result.decision is PreflightDecision.QUARANTINE
    assert PreflightDiagnosticCode.PDF_ENCRYPTED in _codes(result)
    encryption = next(
        item
        for item in result.diagnostics
        if item.code is PreflightDiagnosticCode.PDF_ENCRYPTED
    )
    assert encryption.details == {"allowed_by_policy": False}


def test_encrypted_pdf_can_be_retained_when_unknown_count_is_allowed() -> None:
    result = preflight_bytes(
        _pdf(2, password="secret"),
        limits=PreflightLimits(
            allow_encrypted_pdfs=True,
            require_pdf_page_count=False,
        ),
    )

    assert result.may_proceed
    assert result.pdf_encrypted is True
    assert result.pdf_page_count is None
    assert _codes(result) == {
        PreflightDiagnosticCode.PDF_ENCRYPTED,
        PreflightDiagnosticCode.PDF_PAGE_COUNT_UNCERTAIN,
    }
    assert all(
        item.severity is DiagnosticSeverity.WARNING for item in result.diagnostics
    )


def test_corrupted_pdf_fails_closed_with_explicit_structure_diagnostics() -> None:
    result = preflight_bytes(b"%PDF-1.7\nnot-a-valid-pdf\n%%EOF\n")

    assert result.decision is PreflightDecision.QUARANTINE
    assert result.pdf_page_count is None
    assert _codes(result) == {
        PreflightDiagnosticCode.PDF_PAGE_COUNT_UNCERTAIN,
        PreflightDiagnosticCode.PDF_STRUCTURE_UNCERTAIN,
    }
    structure = next(
        item
        for item in result.diagnostics
        if item.code is PreflightDiagnosticCode.PDF_STRUCTURE_UNCERTAIN
    )
    assert structure.details["error_type"] in {"PdfReadError", "PdfStreamError"}


def test_structure_uncertainty_policy_can_retain_with_warnings() -> None:
    result = preflight_bytes(
        b"%PDF-1.7\nnot-a-valid-pdf\n%%EOF\n",
        limits=PreflightLimits(
            require_pdf_page_count=False,
            quarantine_on_pdf_structure_uncertainty=False,
        ),
    )

    assert result.may_proceed
    assert all(
        item.severity is DiagnosticSeverity.WARNING for item in result.diagnostics
    )


@pytest.mark.parametrize(
    ("filename", "media_type"),
    [
        ("paper.pdf", None),
        (None, "application/pdf; version=1.7"),
    ],
)
def test_pdf_metadata_without_header_is_rejected(
    filename: str | None, media_type: str | None
) -> None:
    result = preflight_bytes(b"not a pdf", filename=filename, media_type=media_type)

    assert result.is_pdf
    assert result.decision is PreflightDecision.QUARANTINE
    assert _codes(result) == {PreflightDiagnosticCode.PDF_HEADER_INVALID}


def test_result_is_machine_serializable() -> None:
    result = preflight_bytes(_pdf(2), limits=PreflightLimits(max_pdf_pages=1))

    payload = result.model_dump(mode="json")

    assert payload["decision"] == "quarantine"
    assert payload["diagnostics"][0]["code"] == "PDF_PAGE_LIMIT_EXCEEDED"
    assert payload["diagnostics"][0]["details"]["actual_pages"] == 2
