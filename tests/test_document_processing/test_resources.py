from __future__ import annotations

import os
from pathlib import Path

import pytest

from DeepResearch.src.document_processing import _cgroup_exec
from DeepResearch.src.document_processing import resources as resource_module
from DeepResearch.src.document_processing.models import MemoryMeasurementStatus
from DeepResearch.src.document_processing.resources import (
    LinuxCgroupV2InvocationMeter,
    MemoryMeasurementRequest,
    UnavailableMemoryMeter,
    parse_trusted_memory_measurement,
)


def test_linux_meter_rejects_unverifiable_environment_identity_first() -> None:
    with pytest.raises(ValueError, match="lowercase SHA-256"):
        LinuxCgroupV2InvocationMeter(
            "/sys/fs/cgroup/deepcritical",
            environment_sha256="not-a-sha256",
        )


def test_effective_cgroup_limit_uses_tightest_ancestor(tmp_path: Path) -> None:
    cgroup_root = tmp_path / "cgroup"
    delegated_parent = cgroup_root / "service.slice" / "deepcritical"
    invocation = delegated_parent / "docling-run-1"
    invocation.mkdir(parents=True)
    limits = {
        cgroup_root: "max",
        cgroup_root / "service.slice": "1073741824",
        delegated_parent: "536870912",
        invocation: "805306368",
    }
    for cgroup, limit in limits.items():
        (cgroup / "memory.max").write_text(limit, encoding="ascii")

    effective_limit = resource_module._read_effective_memory_limit(
        invocation,
        cgroup_root=cgroup_root,
    )

    assert effective_limit == 536870912


def test_effective_cgroup_limit_preserves_fully_unlimited_hierarchy(
    tmp_path: Path,
) -> None:
    cgroup_root = tmp_path / "cgroup"
    invocation = cgroup_root / "deepcritical" / "ocr-run-1"
    invocation.mkdir(parents=True)
    for cgroup in (cgroup_root, invocation.parent, invocation):
        (cgroup / "memory.max").write_text("max", encoding="ascii")

    effective_limit = resource_module._read_effective_memory_limit(
        invocation,
        cgroup_root=cgroup_root,
    )

    assert effective_limit is None


def test_effective_cgroup_limit_fails_closed_on_malformed_ancestor(
    tmp_path: Path,
) -> None:
    cgroup_root = tmp_path / "cgroup"
    invocation = cgroup_root / "deepcritical" / "ocr-run-1"
    invocation.mkdir(parents=True)
    (invocation / "memory.max").write_text("max", encoding="ascii")
    (invocation.parent / "memory.max").write_text("invalid", encoding="ascii")
    (cgroup_root / "memory.max").write_text("max", encoding="ascii")

    with pytest.raises(ValueError, match="invalid literal"):
        resource_module._read_effective_memory_limit(
            invocation,
            cgroup_root=cgroup_root,
        )


def test_cgroup_bootstrap_joins_boundary_before_exec(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    cgroup_root = tmp_path / "cgroup"
    boundary = cgroup_root / "deepcritical" / "ocr-run"
    boundary.mkdir(parents=True)
    cgroup_procs = boundary / "cgroup.procs"
    cgroup_procs.write_text("", encoding="ascii")
    real_path = Path

    def fixture_path(value: str) -> Path:
        return cgroup_root if value == "/sys/fs/cgroup" else real_path(value)

    class ExecCalled(RuntimeError):
        pass

    def fake_execvp(executable: str, command: tuple[str, ...]) -> None:
        assert executable == "ocrmypdf"
        assert command == ("ocrmypdf", "input.pdf", "output.pdf")
        assert cgroup_procs.read_text(encoding="ascii") == "4242"
        raise ExecCalled

    monkeypatch.setattr(_cgroup_exec, "Path", fixture_path)
    monkeypatch.setattr(os, "getpid", lambda: 4242)
    monkeypatch.setattr(os, "execvp", fake_execvp)

    with pytest.raises(ExecCalled):
        _cgroup_exec.enter_cgroup_and_exec(
            [str(cgroup_procs), "ocrmypdf", "input.pdf", "output.pdf"]
        )


def test_unavailable_meter_never_fabricates_a_zero_peak() -> None:
    measurement = (
        UnavailableMemoryMeter()
        .begin(
            MemoryMeasurementRequest(
                measurement_id="run-1", parser_name="ocrmypdf", boundary="ocr-local"
            )
        )
        .finish()
    )

    assert measurement.status is MemoryMeasurementStatus.UNAVAILABLE
    assert measurement.peak_memory_bytes is None
    assert measurement.failure_code == "memory_meter_unavailable"


def test_trusted_measurement_payload_is_strictly_validated() -> None:
    payload: dict[str, object] = {
        "status": "measured",
        "method": "cgroup-v2-memory.peak",
        "scope": "invocation_cgroup",
        "boundary": "docling-rq-job",
        "peak_memory_bytes": 42,
        "environment_sha256": "f" * 64,
        "measurement_id": "docling-task-1",
        "exclusive": True,
    }
    measurement = parse_trusted_memory_measurement(payload)

    assert measurement is not None
    assert measurement.peak_memory_bytes == 42
    payload["peak_memory_bytes"] = None
    with pytest.raises(ValueError, match="measured memory requires"):
        parse_trusted_memory_measurement(payload)
