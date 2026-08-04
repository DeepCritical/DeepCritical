from __future__ import annotations

import asyncio
import sys
from collections.abc import Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest

from DeepResearch.src.document_processing import clients as client_module
from DeepResearch.src.document_processing import resources as resource_module
from DeepResearch.src.document_processing.clients import (
    ContainerOCRmyPDFRunner,
    OCRmyPDFRunner,
    ParserServiceError,
)
from DeepResearch.src.document_processing.models import (
    MemoryMeasurement,
    MemoryMeasurementScope,
    MemoryMeasurementStatus,
)
from DeepResearch.src.document_processing.resources import (
    CgroupV2MemoryLease,
    MemoryMeasurementRequest,
)


class _LifecycleLease:
    def __init__(self, *, finish_raises: bool = False) -> None:
        self.request = MemoryMeasurementRequest(
            measurement_id="ocr-lifecycle-test",
            component_id="ocrmypdf",
            boundary="ocr-test",
        )
        self.finish_raises = finish_raises
        self.aborted = False
        self.finish_count = 0

    @property
    def container_cgroup_parent(self) -> str:
        return "/deepcritical/ocr-lifecycle-test"

    def attach_pid(self, pid: int) -> None:
        raise AssertionError(f"unexpected late PID attachment: {pid}")

    def wrap_subprocess_command(self, command: Sequence[str]) -> tuple[str, ...]:
        return tuple(command)

    def abort(self) -> None:
        self.aborted = True

    def finish(self) -> MemoryMeasurement:
        self.finish_count += 1
        if self.finish_raises:
            raise RuntimeError("fixture finish failed")
        return MemoryMeasurement(
            status=MemoryMeasurementStatus.MEASURED,
            method="cgroup-v2-memory.peak",
            scope=MemoryMeasurementScope.INVOCATION_CGROUP,
            boundary=self.request.boundary,
            peak_memory_bytes=4096,
            environment_sha256="a" * 64,
            measurement_id=self.request.measurement_id,
            started_at=datetime(2026, 7, 18, tzinfo=UTC),
            finished_at=datetime(2026, 7, 18, 0, 0, 1, tzinfo=UTC),
            exclusive=True,
            shared_overhead_excluded=True,
            memory_events={"oom_kill": 0},
        )


class _LifecycleMeter:
    def __init__(self, *, finish_raises: bool = False) -> None:
        self.lease = _LifecycleLease(finish_raises=finish_raises)

    def begin(self, request: MemoryMeasurementRequest) -> _LifecycleLease:
        self.lease.request = request
        return self.lease


class _HangingProcess:
    pid = None
    returncode = None

    def __init__(self) -> None:
        self.started = asyncio.Event()
        self.release = asyncio.Event()
        self.killed = False

    async def communicate(self) -> tuple[bytes, bytes]:
        self.started.set()
        await self.release.wait()
        self.returncode = -9
        return b"partial stdout", b"partial stderr"

    def kill(self) -> None:
        self.killed = True
        self.release.set()


class _CompletedProcess:
    pid = None

    def __init__(
        self, returncode: int = 0, stdout: bytes = b"", stderr: bytes = b""
    ) -> None:
        self.returncode = returncode
        self._stdout = stdout
        self._stderr = stderr

    async def communicate(self) -> tuple[bytes, bytes]:
        return self._stdout, self._stderr

    def kill(self) -> None:
        raise AssertionError("completed fixture must not be killed")


@pytest.mark.asyncio
async def test_local_timeout_aborts_boundary_and_retains_measurement_once(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    process = _HangingProcess()
    meter = _LifecycleMeter()

    async def fake_subprocess(*command: str, **kwargs: Any) -> _HangingProcess:
        return process

    monkeypatch.setattr(asyncio, "create_subprocess_exec", fake_subprocess)
    runner = OCRmyPDFRunner(timeout_seconds=0.001, memory_meter=meter)

    with pytest.raises(ParserServiceError) as raised:
        await runner.convert(b"%PDF-original")

    assert raised.value.code == "ocrmypdf_timeout"
    assert raised.value.memory_measurement is not None
    assert raised.value.memory_measurement.status is MemoryMeasurementStatus.MEASURED
    assert meter.lease.aborted is True
    assert meter.lease.finish_count == 1
    assert process.killed is True


@pytest.mark.asyncio
async def test_local_cancellation_aborts_reaps_and_finishes_once(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    process = _HangingProcess()
    meter = _LifecycleMeter()

    async def fake_subprocess(*command: str, **kwargs: Any) -> _HangingProcess:
        return process

    monkeypatch.setattr(asyncio, "create_subprocess_exec", fake_subprocess)
    runner = OCRmyPDFRunner(timeout_seconds=60, memory_meter=meter)
    task = asyncio.create_task(runner.convert(b"%PDF-original"))
    await process.started.wait()

    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task

    assert process.killed is True
    assert meter.lease.aborted is True
    assert meter.lease.finish_count == 1


@pytest.mark.asyncio
async def test_repeated_cancellation_cannot_interrupt_subprocess_cleanup(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    cleanup_started = asyncio.Event()
    cleanup_release = asyncio.Event()
    cleanup_finished = asyncio.Event()

    async def blocking_cleanup(*args: Any, **kwargs: Any) -> tuple[str, ...]:
        cleanup_started.set()
        await cleanup_release.wait()
        cleanup_finished.set()
        return ()

    monkeypatch.setattr(client_module, "_cleanup_subprocess", blocking_cleanup)
    completion = asyncio.create_task(asyncio.sleep(0, result=(b"", b"")))
    await completion
    cleanup = asyncio.create_task(
        client_module._shielded_subprocess_cleanup(
            object(),
            completion,
            abort_hook=None,
            cleanup_timeout_seconds=1,
        )
    )
    await cleanup_started.wait()

    cleanup.cancel("first shutdown request")
    await asyncio.sleep(0)
    cleanup.cancel("second shutdown request")
    await asyncio.sleep(0)
    cleanup.cancel("third shutdown request")
    await asyncio.sleep(0)

    assert not cleanup.done()
    assert not cleanup_finished.is_set()
    cleanup_release.set()
    with pytest.raises(asyncio.CancelledError):
        await cleanup
    assert cleanup_finished.is_set()


@pytest.mark.asyncio
async def test_cancellation_during_timeout_cleanup_preserves_cancellation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    process = _HangingProcess()
    cleanup_started = asyncio.Event()
    cleanup_release = asyncio.Event()
    cleanup_finished = asyncio.Event()

    async def fake_subprocess(*command: str, **kwargs: Any) -> _HangingProcess:
        return process

    async def blocking_cleanup(
        process: Any,
        completion: asyncio.Task[tuple[bytes, bytes]],
        **kwargs: Any,
    ) -> tuple[str, ...]:
        cleanup_started.set()
        await cleanup_release.wait()
        completion.cancel()
        with pytest.raises(asyncio.CancelledError):
            await completion
        cleanup_finished.set()
        return ()

    monkeypatch.setattr(asyncio, "create_subprocess_exec", fake_subprocess)
    monkeypatch.setattr(client_module, "_cleanup_subprocess", blocking_cleanup)
    invocation = asyncio.create_task(
        client_module._run_capped_subprocess(
            ("fixture-parser",),
            timeout_seconds=0.001,
            output_limit_bytes=128,
            cleanup_timeout_seconds=1,
            timeout_message="fixture timeout",
            timeout_code="fixture_timeout",
        )
    )
    await cleanup_started.wait()

    invocation.cancel("request cancelled during timeout cleanup")
    await asyncio.sleep(0)
    assert not invocation.done()
    cleanup_release.set()

    with pytest.raises(asyncio.CancelledError):
        await invocation
    assert cleanup_finished.is_set()


@pytest.mark.asyncio
async def test_failed_measurement_finish_is_retained_on_timeout(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    process = _HangingProcess()
    meter = _LifecycleMeter(finish_raises=True)

    async def fake_subprocess(*command: str, **kwargs: Any) -> _HangingProcess:
        return process

    monkeypatch.setattr(asyncio, "create_subprocess_exec", fake_subprocess)
    runner = OCRmyPDFRunner(timeout_seconds=0.001, memory_meter=meter)

    with pytest.raises(ParserServiceError) as raised:
        await runner.convert(b"%PDF-original")

    assert raised.value.memory_measurement is not None
    assert raised.value.memory_measurement.status is MemoryMeasurementStatus.FAILED
    assert raised.value.memory_measurement.failure_code is not None
    assert raised.value.memory_measurement.failure_code.startswith(
        "memory_measurement_finish_failed"
    )
    assert meter.lease.finish_count == 1


@pytest.mark.asyncio
async def test_measurement_finish_failure_is_not_retried_after_successful_parse(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    meter = _LifecycleMeter(finish_raises=True)

    async def fake_subprocess(*command: str, **kwargs: Any) -> _CompletedProcess:
        Path(command[-1]).write_bytes(b"%PDF-searchable")
        return _CompletedProcess()

    monkeypatch.setattr(asyncio, "create_subprocess_exec", fake_subprocess)
    runner = OCRmyPDFRunner(memory_meter=meter)

    result = await runner.convert(b"%PDF-original")

    assert result.memory_measurement is not None
    assert result.memory_measurement.status is MemoryMeasurementStatus.FAILED
    assert meter.lease.finish_count == 1


@pytest.mark.asyncio
async def test_container_timeout_force_removes_exact_named_workload(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    process = _HangingProcess()
    meter = _LifecycleMeter()
    commands: list[tuple[str, ...]] = []

    async def fake_subprocess(*command: str, **kwargs: Any) -> Any:
        commands.append(command)
        if command[1:3] == ("rm", "--force"):
            return _CompletedProcess()
        return process

    monkeypatch.setattr(asyncio, "create_subprocess_exec", fake_subprocess)
    runner = ContainerOCRmyPDFRunner(
        "jbarlow83/ocrmypdf:v17.4.1",
        timeout_seconds=0.001,
        memory_meter=meter,
    )

    with pytest.raises(ParserServiceError) as raised:
        await runner.convert(b"%PDF-original")

    run_command = commands[0]
    workload = run_command[run_command.index("--name") + 1]
    assert ("docker", "rm", "--force", workload) in commands
    assert raised.value.code == "ocrmypdf_container_timeout"
    assert raised.value.memory_measurement is not None
    assert meter.lease.aborted is True
    assert meter.lease.finish_count == 1


@pytest.mark.asyncio
async def test_probe_timeout_force_removes_its_unique_container(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    process = _HangingProcess()
    commands: list[tuple[str, ...]] = []

    async def fake_subprocess(*command: str, **kwargs: Any) -> Any:
        commands.append(command)
        if command[1:3] == ("rm", "--force"):
            return _CompletedProcess()
        return process

    monkeypatch.setattr(asyncio, "create_subprocess_exec", fake_subprocess)
    runner = ContainerOCRmyPDFRunner(
        "jbarlow83/ocrmypdf:v17.4.1", probe_timeout_seconds=0.001
    )

    with pytest.raises(ParserServiceError, match="probe timeout"):
        await runner.version()

    probe = commands[0]
    workload = probe[probe.index("--name") + 1]
    assert ("docker", "rm", "--force", workload) in commands


@pytest.mark.asyncio
async def test_container_cleanup_failure_is_visible_on_timeout(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    process = _HangingProcess()

    async def fake_subprocess(*command: str, **kwargs: Any) -> Any:
        if command[1:3] == ("rm", "--force"):
            return _CompletedProcess(returncode=1, stderr=b"permission denied")
        return process

    monkeypatch.setattr(asyncio, "create_subprocess_exec", fake_subprocess)
    runner = ContainerOCRmyPDFRunner(
        "jbarlow83/ocrmypdf:v17.4.1", timeout_seconds=0.001
    )

    with pytest.raises(ParserServiceError) as raised:
        await runner.convert(b"%PDF-original")

    assert raised.value.response_body is not None
    assert "container force-remove failed" in raised.value.response_body


@pytest.mark.asyncio
async def test_real_subprocess_capture_is_strictly_capped_with_marker() -> None:
    limit = 128
    process, stdout, stderr = await client_module._run_capped_subprocess(
        (
            sys.executable,
            "-c",
            "import sys;sys.stdout.write('x'*4096);sys.stderr.write('y'*4096)",
        ),
        timeout_seconds=10,
        output_limit_bytes=limit,
        cleanup_timeout_seconds=10,
        timeout_message="fixture timeout",
        timeout_code="fixture_timeout",
    )

    assert process.returncode == 0
    assert len(stdout) == limit
    assert len(stderr) == limit
    assert stdout.endswith(client_module._OUTPUT_TRUNCATION_MARKER)
    assert stderr.endswith(client_module._OUTPUT_TRUNCATION_MARKER)


def test_posix_cleanup_targets_the_whole_process_group(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[tuple[int, int]] = []

    class Process:
        pid = 4321

        def kill(self) -> None:
            raise AssertionError("process-group kill should be used")

    monkeypatch.setattr(client_module.os, "name", "posix")
    monkeypatch.setattr(client_module.signal, "SIGKILL", 9, raising=False)
    monkeypatch.setattr(
        client_module.os,
        "killpg",
        lambda pid, sig: calls.append((pid, sig)),
        raising=False,
    )
    errors: list[str] = []

    client_module._kill_process_group(Process(), errors)

    assert calls == [(4321, 9)]
    assert errors == []


def test_cgroup_abort_prefers_recursive_cgroup_kill(tmp_path: Path) -> None:
    cgroup = tmp_path / "invocation"
    cgroup.mkdir()
    kill_file = cgroup / "cgroup.kill"
    kill_file.write_text("0", encoding="ascii")
    lease = CgroupV2MemoryLease(
        request=MemoryMeasurementRequest(
            measurement_id="run-1",
            component_id="ocrmypdf",
            boundary="fixture",
        ),
        path=cgroup,
        environment_sha256="b" * 64,
        effective_memory_limit_bytes=None,
        started_at=datetime.now(UTC),
    )

    lease.abort()

    assert kill_file.read_text(encoding="ascii") == "1"


def test_cgroup_abort_fallback_kills_only_invocation_descendants(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    cgroup = tmp_path / "invocation"
    cgroup.mkdir()
    procs = cgroup / "cgroup.procs"
    procs.write_text("4242\n", encoding="ascii")
    calls: list[tuple[int, int]] = []

    def fake_kill(pid: int, sig: int) -> None:
        calls.append((pid, sig))
        procs.write_text("", encoding="ascii")

    monkeypatch.setattr(resource_module.os, "getpid", lambda: 9999)
    monkeypatch.setattr(resource_module.os, "kill", fake_kill)
    lease = CgroupV2MemoryLease(
        request=MemoryMeasurementRequest(
            measurement_id="run-2",
            component_id="ocrmypdf",
            boundary="fixture",
        ),
        path=cgroup,
        environment_sha256="c" * 64,
        effective_memory_limit_bytes=None,
        started_at=datetime.now(UTC),
    )

    lease.abort()

    assert calls == [(4242, resource_module._SIGKILL)]
