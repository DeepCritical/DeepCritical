"""Trustworthy parser-stage memory measurement primitives.

The meter intentionally supports only a delegated Linux cgroup-v2 subtree.
It does not sample the client process, Docker statistics, or a shared service
cgroup: those values cannot be attributed to one parser invocation.
"""

from __future__ import annotations

import os
import re
import shutil
import signal
import sys
import time
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Mapping, Protocol, runtime_checkable

from .models import (
    MemoryMeasurement,
    MemoryMeasurementScope,
    MemoryMeasurementStatus,
    Sha256,
)

_SAFE_NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,127}$")
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_SIGKILL = getattr(signal, "SIGKILL", 9)


@dataclass(frozen=True, slots=True)
class MemoryMeasurementRequest:
    """Static identity used to create one isolated measurement boundary."""

    measurement_id: str
    component_id: str
    boundary: str


@runtime_checkable
class MemoryMeasurementLease(Protocol):
    """An invocation-owned boundary that is finished exactly once."""

    @property
    def container_cgroup_parent(self) -> str | None:
        """Return a host cgroup parent usable by an OCI runtime, if available."""

    def attach_pid(self, pid: int) -> None:
        """Attach a directly spawned local process to this boundary."""

    def wrap_subprocess_command(self, command: Sequence[str]) -> tuple[str, ...]:
        """Return a command which enters the boundary before parser exec."""

    def abort(self) -> None:
        """Kill every process in this invocation-owned boundary."""

    def finish(self) -> MemoryMeasurement:
        """Read final memory accounting and release the boundary."""


@runtime_checkable
class InvocationMemoryMeter(Protocol):
    """Injectable creator of parser invocation memory boundaries."""

    def begin(self, request: MemoryMeasurementRequest) -> MemoryMeasurementLease:
        """Create a fresh boundary before launching parser work."""


def parse_trusted_memory_measurement(
    value: MemoryMeasurement | Mapping[str, object] | None,
) -> MemoryMeasurement | None:
    """Validate an explicitly supplied, trusted service measurement payload."""

    if value is None or isinstance(value, MemoryMeasurement):
        return value
    return MemoryMeasurement.model_validate(value)


class UnavailableMemoryMeter:
    """Safe default for platforms/deployments without isolated accounting."""

    def __init__(self, *, failure_code: str = "memory_meter_unavailable") -> None:
        self.failure_code = failure_code

    def begin(self, request: MemoryMeasurementRequest) -> _UnavailableLease:
        return _UnavailableLease(request, self.failure_code)


@dataclass(frozen=True, slots=True)
class _UnavailableLease:
    request: MemoryMeasurementRequest
    failure_code: str

    @property
    def container_cgroup_parent(self) -> str | None:
        return None

    def attach_pid(self, pid: int) -> None:
        if pid <= 0:
            raise ValueError("pid must be positive")

    def wrap_subprocess_command(self, command: Sequence[str]) -> tuple[str, ...]:
        if not command:
            raise ValueError("subprocess command must not be empty")
        return tuple(command)

    def abort(self) -> None:
        """There is no process boundary to abort for an unavailable meter."""

    def finish(self) -> MemoryMeasurement:
        return MemoryMeasurement(
            status=MemoryMeasurementStatus.UNAVAILABLE,
            boundary=self.request.boundary,
            measurement_id=self.request.measurement_id,
            failure_code=self.failure_code,
        )


class LinuxCgroupV2InvocationMeter:
    """Meter one invocation in a pre-delegated cgroup-v2 child directory.

    The deployment must hand the application a writable parent cgroup.  This
    class refuses broad roots and never resets a cgroup it did not create.
    Local parser runners should use ``lease.wrap_subprocess_command`` so the
    bootstrap joins the boundary before it execs parser code. ``attach_pid`` is
    reserved for a caller that can keep an already-spawned process stopped until
    attachment. Container runners use ``container_cgroup_parent`` and finish the
    lease after the runtime has removed its descendant cgroup.
    """

    def __init__(self, parent: str | Path, *, environment_sha256: Sha256) -> None:
        self.parent = Path(parent).resolve()
        normalized_environment = str(environment_sha256).strip().lower()
        if not _SHA256.fullmatch(normalized_environment):
            raise ValueError("environment_sha256 must be a lowercase SHA-256 digest")
        self.environment_sha256 = normalized_environment
        cgroup_root = Path("/sys/fs/cgroup")
        self.cgroup_root = cgroup_root
        controllers = cgroup_root / "cgroup.controllers"
        if os.name != "posix" or not controllers.is_file():
            raise RuntimeError("Linux cgroup-v2 memory accounting is unavailable")
        if "memory" not in controllers.read_text(encoding="utf-8").split():
            raise RuntimeError("cgroup-v2 memory controller is unavailable")
        if (
            self.parent == cgroup_root
            or not self.parent.is_relative_to(cgroup_root)
            or not self.parent.is_dir()
        ):
            raise ValueError("cgroup parent must be a pre-provisioned delegated child")
        if not (self.parent / "cgroup.procs").is_file():
            raise ValueError("cgroup parent is not a valid delegated cgroup")

    def begin(self, request: MemoryMeasurementRequest) -> CgroupV2MemoryLease:
        _validate_safe_name(request.measurement_id)
        _validate_safe_name(request.component_id)
        child = self.parent / f"{request.component_id}-{request.measurement_id}"
        if child.exists():
            raise RuntimeError("memory measurement cgroup already exists")
        child.mkdir(mode=0o700)
        try:
            peak_path = child / "memory.peak"
            if not peak_path.is_file():
                raise RuntimeError("cgroup-v2 memory.peak is unavailable")
            # A fresh empty child avoids resetting a shared or prior invocation.
            peak_path.write_text("0", encoding="ascii")
            limit = _read_effective_memory_limit(child, cgroup_root=self.cgroup_root)
        except Exception:
            shutil.rmtree(child, ignore_errors=True)
            raise
        return CgroupV2MemoryLease(
            request=request,
            path=child,
            environment_sha256=self.environment_sha256,
            effective_memory_limit_bytes=limit,
            started_at=datetime.now(UTC),
        )


@dataclass(slots=True)
class CgroupV2MemoryLease:
    """One cgroup-v2 measurement which owns a newly-created child cgroup."""

    request: MemoryMeasurementRequest
    path: Path
    environment_sha256: Sha256
    effective_memory_limit_bytes: int | None
    started_at: datetime
    _finished: bool = False

    @property
    def container_cgroup_parent(self) -> str:
        """Cgroupfs-relative boundary for an OCI ``--cgroup-parent`` option."""

        relative = self.path.relative_to("/sys/fs/cgroup").as_posix()
        return f"/{relative}"

    def attach_pid(self, pid: int) -> None:
        """Move one parser root process into the fresh child boundary."""

        if self._finished:
            raise RuntimeError("memory measurement lease is already finished")
        if pid <= 0:
            raise ValueError("pid must be positive")
        (self.path / "cgroup.procs").write_text(str(pid), encoding="ascii")

    def wrap_subprocess_command(self, command: Sequence[str]) -> tuple[str, ...]:
        """Enter the boundary in a bootstrap process, then exec the parser."""

        if self._finished:
            raise RuntimeError("memory measurement lease is already finished")
        if not command:
            raise ValueError("subprocess command must not be empty")
        return (
            sys.executable,
            "-m",
            "DeepResearch.src.document_processing._cgroup_exec",
            os.fspath(self.path / "cgroup.procs"),
            *command,
        )

    def abort(self) -> None:
        """Kill all invocation descendants without escaping the owned cgroup.

        Linux's ``cgroup.kill`` is atomic and recursive, so it is preferred.
        Older cgroup-v2 deployments may not expose that file; the fallback
        repeatedly kills PIDs found below this invocation-owned subtree until
        it is empty. Cleanup failures are raised to the caller instead of being
        hidden, because a parser descendant left alive can keep processing
        licensed source material after the request was cancelled.
        """

        if self._finished:
            raise RuntimeError("memory measurement lease is already finished")
        coordinator_pid = os.getpid()
        if coordinator_pid in _read_descendant_pids(self.path):
            raise RuntimeError(
                "refusing to abort a cgroup containing the coordinator process"
            )
        kill_path = self.path / "cgroup.kill"
        if kill_path.is_file():
            kill_path.write_text("1", encoding="ascii")
            return

        deadline = time.monotonic() + 2.0
        while True:
            pids = _read_descendant_pids(self.path)
            if not pids:
                return
            for pid in pids:
                if pid == coordinator_pid:
                    raise RuntimeError("coordinator entered the invocation cgroup")
                try:
                    os.kill(pid, _SIGKILL)
                except ProcessLookupError:
                    continue
            if time.monotonic() >= deadline:
                remaining = _read_descendant_pids(self.path)
                if remaining:
                    raise RuntimeError(
                        "invocation cgroup still contains live processes after abort"
                    )
                return
            time.sleep(0.01)

    def finish(self) -> MemoryMeasurement:
        """Read the terminal peak/events before removing the empty cgroup."""

        if self._finished:
            raise RuntimeError("memory measurement lease is already finished")
        self._finished = True
        finished_at = datetime.now(UTC)
        try:
            peak = int((self.path / "memory.peak").read_text(encoding="ascii").strip())
            events = _read_memory_events(self.path / "memory.events")
            measurement = MemoryMeasurement(
                status=MemoryMeasurementStatus.MEASURED,
                method="cgroup-v2-memory.peak",
                scope=MemoryMeasurementScope.INVOCATION_CGROUP,
                boundary=self.request.boundary,
                peak_memory_bytes=peak,
                effective_memory_limit_bytes=self.effective_memory_limit_bytes,
                environment_sha256=self.environment_sha256,
                measurement_id=self.request.measurement_id,
                started_at=self.started_at,
                finished_at=finished_at,
                exclusive=True,
                shared_overhead_excluded=True,
                memory_events=events,
            )
        except Exception as exc:
            measurement = MemoryMeasurement(
                status=MemoryMeasurementStatus.FAILED,
                boundary=self.request.boundary,
                measurement_id=self.request.measurement_id,
                started_at=self.started_at,
                finished_at=finished_at,
                failure_code=f"cgroup_v2_read_failed:{exc.__class__.__name__}",
            )
        try:
            self.path.rmdir()
        except OSError:
            # A live child must not be forcibly deleted; the failed/unavailable
            # result makes the missing cleanup visible instead of hiding it.
            if measurement.status is MemoryMeasurementStatus.MEASURED:
                return MemoryMeasurement(
                    status=MemoryMeasurementStatus.FAILED,
                    boundary=self.request.boundary,
                    measurement_id=self.request.measurement_id,
                    started_at=self.started_at,
                    finished_at=finished_at,
                    failure_code="cgroup_v2_cleanup_failed",
                )
        return measurement


def _validate_safe_name(value: str) -> None:
    if not _SAFE_NAME.fullmatch(value):
        raise ValueError("measurement identifiers must be safe cgroup path components")


def _read_memory_limit(path: Path) -> int | None:
    raw = path.read_text(encoding="ascii").strip()
    return None if raw == "max" else int(raw)


def _read_effective_memory_limit(
    invocation_cgroup: Path,
    *,
    cgroup_root: Path,
) -> int | None:
    """Return the tightest ``memory.max`` from an invocation to the root.

    A cgroup whose own limit is ``max`` can still be constrained by any
    ancestor. Reading every level also makes malformed or unreadable ancestor
    accounting fail closed instead of reporting a misleading comparable cap.
    ``None`` is reserved for a hierarchy that is unlimited at every level.
    """

    if not invocation_cgroup.is_relative_to(cgroup_root):
        raise ValueError("invocation cgroup must be below the cgroup-v2 root")

    effective_limit: int | None = None
    current = invocation_cgroup
    while True:
        limit = _read_memory_limit(current / "memory.max")
        if limit is not None:
            effective_limit = (
                limit if effective_limit is None else min(effective_limit, limit)
            )
        if current == cgroup_root:
            return effective_limit
        current = current.parent


def _read_memory_events(path: Path) -> dict[str, int]:
    events: dict[str, int] = {}
    for line in path.read_text(encoding="ascii").splitlines():
        key, value = line.split(maxsplit=1)
        events[key] = int(value)
    return events


def _read_descendant_pids(path: Path) -> set[int]:
    """Read PIDs only from the invocation cgroup and its descendants."""

    cgroups = [path]
    cgroups.extend(
        candidate
        for candidate in path.rglob("*")
        if candidate.is_dir() and not candidate.is_symlink()
    )
    pids: set[int] = set()
    for cgroup in cgroups:
        procs = cgroup / "cgroup.procs"
        if not procs.is_file():
            continue
        for raw_pid in procs.read_text(encoding="ascii").splitlines():
            if raw_pid.strip():
                pids.add(int(raw_pid))
    return pids


__all__ = [
    "CgroupV2MemoryLease",
    "InvocationMemoryMeter",
    "LinuxCgroupV2InvocationMeter",
    "MemoryMeasurementLease",
    "MemoryMeasurementRequest",
    "UnavailableMemoryMeter",
    "parse_trusted_memory_measurement",
]
