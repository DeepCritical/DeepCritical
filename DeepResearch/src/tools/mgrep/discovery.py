"""Repository discovery utilities for mgrep-style local indexing."""

from __future__ import annotations

import fnmatch
import hashlib
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from DeepResearch.src.datatypes.mgrep import MgrepConfig

pathspec: Any = None
try:
    import pathspec as _pathspec
except ImportError:  # pragma: no cover - exercised through fallback tests
    pass
else:
    pathspec = _pathspec


@dataclass
class DiscoveryResult:
    """Files selected for indexing plus aggregate skip information."""

    files: list[Path]
    skipped_count: int = 0


class _FallbackIgnoreMatcher:
    """Very small .gitignore-style matcher used when pathspec is unavailable."""

    def __init__(self, patterns: list[str]):
        self.patterns = patterns

    def match(self, relative_path: str, *, is_dir: bool = False) -> bool:
        ignored = False
        basename = Path(relative_path).name
        normalized = relative_path.strip("/")

        for raw_pattern in self.patterns:
            negated = raw_pattern.startswith("!")
            pattern = raw_pattern[1:] if negated else raw_pattern
            anchored = pattern.startswith("/")
            if anchored:
                pattern = pattern[1:]
            directory_only = pattern.endswith("/")
            if directory_only:
                pattern = pattern.rstrip("/")

            matched = False
            if directory_only:
                matched = normalized == pattern or normalized.startswith(pattern + "/")
            elif "/" in pattern or anchored:
                matched = fnmatch.fnmatch(normalized, pattern)
            else:
                matched = fnmatch.fnmatch(basename, pattern)

            if matched:
                ignored = not negated

        return ignored if (is_dir or normalized) else False


class IgnoreMatcher:
    """Ignore matcher backed by pathspec when available, with a fallback parser."""

    def __init__(self, repo_root: Path):
        self.repo_root = repo_root
        self.patterns = self._load_patterns()
        if pathspec is not None:
            self._matcher = pathspec.PathSpec.from_lines("gitwildmatch", self.patterns)
        else:
            self._matcher = _FallbackIgnoreMatcher(self.patterns)

    def _load_patterns(self) -> list[str]:
        patterns: list[str] = []
        for filename in (".gitignore", ".mgrepignore"):
            path = self.repo_root / filename
            if not path.exists():
                continue
            try:
                lines = path.read_text(encoding="utf-8").splitlines()
            except UnicodeDecodeError:
                continue
            for raw_line in lines:
                line = raw_line.strip()
                if not line or line.startswith("#"):
                    continue
                patterns.append(line)
        return patterns

    def matches(self, relative_path: Path, *, is_dir: bool = False) -> bool:
        normalized = relative_path.as_posix().lstrip("./")
        if not normalized:
            return False
        if hasattr(self._matcher, "match_file"):
            return bool(self._matcher.match_file(normalized))
        return bool(self._matcher.match(normalized, is_dir=is_dir))


def compute_file_digest(path: Path) -> str:
    """Compute a stable file digest for incremental indexing."""
    digest = hashlib.sha1()
    with path.open("rb") as file_handle:
        while True:
            chunk = file_handle.read(8192)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def is_binary_file(path: Path) -> bool:
    """Use a small heuristic to skip binary files in the MVP."""
    try:
        sample = path.read_bytes()[:4096]
    except OSError:
        return True
    return b"\x00" in sample


def is_decodable_text_file(path: Path) -> bool:
    """Return whether the file can be decoded as UTF-8 text."""
    try:
        path.read_bytes()[:4096].decode("utf-8")
    except UnicodeDecodeError:
        return False
    except OSError:
        return False
    return True


def discover_repository_files(repo_root: Path, config: MgrepConfig) -> DiscoveryResult:
    """Discover indexable files in a repository with ignore handling."""
    repo_root = repo_root.resolve()
    matcher = IgnoreMatcher(repo_root)
    supported_extensions = {ext.lower() for ext in config.supported_extensions}
    store_dir = (repo_root / config.store_dir).resolve()

    selected: list[Path] = []
    skipped = 0

    for current_root, dirs, files in os.walk(repo_root, followlinks=False):
        root_path = Path(current_root)
        relative_root = root_path.relative_to(repo_root)

        filtered_dirs: list[str] = []
        for directory_name in dirs:
            candidate = (root_path / directory_name).resolve()
            relative_candidate = (relative_root / directory_name).as_posix().strip("./")
            if directory_name == ".git":
                skipped += 1
                continue
            if candidate == store_dir or store_dir in candidate.parents:
                skipped += 1
                continue
            if matcher.matches(Path(relative_candidate), is_dir=True):
                skipped += 1
                continue
            filtered_dirs.append(directory_name)
        dirs[:] = filtered_dirs

        for file_name in files:
            path = root_path / file_name
            relative_path = path.relative_to(repo_root)
            extension = path.suffix.lower()

            if path.resolve().is_relative_to(store_dir):
                skipped += 1
                continue
            if matcher.matches(relative_path):
                skipped += 1
                continue
            if extension not in supported_extensions:
                skipped += 1
                continue
            if path.is_symlink():
                skipped += 1
                continue
            try:
                file_size = path.stat().st_size
            except OSError:
                skipped += 1
                continue
            if file_size > config.max_file_size_bytes:
                skipped += 1
                continue
            if is_binary_file(path):
                skipped += 1
                continue
            if not is_decodable_text_file(path):
                skipped += 1
                continue

            selected.append(path)

    selected.sort(key=lambda file_path: file_path.relative_to(repo_root).as_posix())
    return DiscoveryResult(files=selected, skipped_count=skipped)
