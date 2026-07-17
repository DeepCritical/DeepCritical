"""Enter one delegated cgroup-v2 boundary before executing a parser.

This module is an internal subprocess bootstrap. It is intentionally small so
the parser itself is exec'd only after the bootstrap PID belongs to the fresh
measurement cgroup. Existing process memory is not presented as parser usage.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import NoReturn, Sequence


def enter_cgroup_and_exec(arguments: Sequence[str]) -> NoReturn:
    """Validate the delegated target, join it, and replace this process."""

    if len(arguments) < 2:
        raise ValueError("expected a cgroup.procs path and parser command")
    cgroup_procs = Path(arguments[0]).resolve(strict=True)
    cgroup_root = Path("/sys/fs/cgroup").resolve(strict=True)
    if (
        cgroup_procs.name != "cgroup.procs"
        or not cgroup_procs.is_relative_to(cgroup_root)
        or cgroup_procs.parent == cgroup_root
    ):
        raise ValueError("cgroup target must be a delegated child cgroup.procs")
    command = tuple(arguments[1:])
    if not command[0]:
        raise ValueError("parser executable must not be empty")

    pid = os.getpid()
    cgroup_procs.write_text(str(pid), encoding="ascii")
    if str(pid) not in cgroup_procs.read_text(encoding="ascii").splitlines():
        raise RuntimeError("bootstrap PID did not enter the measurement cgroup")
    os.execvp(command[0], command)


def main() -> NoReturn:
    enter_cgroup_and_exec(sys.argv[1:])


if __name__ == "__main__":
    main()
