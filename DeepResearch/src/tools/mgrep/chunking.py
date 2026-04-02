"""Chunk extraction for repo-local mgrep-style indexing."""

from __future__ import annotations

import ast
import re
from pathlib import Path
from typing import Any

from DeepResearch.src.datatypes.mgrep import MgrepChunk, build_chunk_id

_PARAGRAPH_SPLIT_RE = re.compile(r"\n\s*\n", re.MULTILINE)


def _language_for_path(path: Path) -> str:
    mapping = {
        ".py": "python",
        ".md": "markdown",
        ".txt": "text",
        ".json": "json",
        ".yaml": "yaml",
        ".yml": "yaml",
        ".toml": "toml",
    }
    return mapping.get(path.suffix.lower(), "text")


def _make_chunk(
    *,
    path: Path,
    repo_root: Path,
    digest: str,
    kind: str,
    symbol_name: str | None,
    line_start: int,
    line_end: int,
    text: str,
    metadata: dict[str, Any] | None = None,
) -> MgrepChunk:
    relative_path = path.relative_to(repo_root).as_posix()
    return MgrepChunk(
        id=build_chunk_id(
            relative_path=relative_path,
            digest=digest,
            kind=kind,
            symbol_name=symbol_name,
            line_start=line_start,
            line_end=line_end,
        ),
        path=str(path),
        relative_path=relative_path,
        language=_language_for_path(path),
        kind=kind,
        symbol_name=symbol_name,
        line_start=line_start,
        line_end=line_end,
        text=text.strip(),
        digest=digest,
        metadata=metadata or {},
    )


def _chunk_python(
    path: Path, repo_root: Path, digest: str, text: str
) -> list[MgrepChunk]:
    lines = text.splitlines()
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return _chunk_plain_text(path, repo_root, digest, text)

    nodes = [
        node
        for node in ast.walk(tree)
        if isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef))
    ]
    nodes.sort(key=lambda node: (node.lineno, getattr(node, "end_lineno", node.lineno)))

    chunks: list[MgrepChunk] = []
    for node in nodes:
        line_start = getattr(node, "lineno", 1)
        line_end = getattr(node, "end_lineno", line_start)
        snippet = "\n".join(lines[line_start - 1 : line_end]).strip()
        if not snippet:
            continue
        if isinstance(node, ast.ClassDef):
            kind = "class"
        elif isinstance(node, ast.AsyncFunctionDef):
            kind = "async_function"
        else:
            kind = "function"
        chunks.append(
            _make_chunk(
                path=path,
                repo_root=repo_root,
                digest=digest,
                kind=kind,
                symbol_name=getattr(node, "name", None),
                line_start=line_start,
                line_end=line_end,
                text=snippet,
            )
        )

    if chunks:
        return chunks

    return [
        _make_chunk(
            path=path,
            repo_root=repo_root,
            digest=digest,
            kind="module",
            symbol_name=path.stem,
            line_start=1,
            line_end=max(len(lines), 1),
            text=text,
        )
    ]


def _chunk_markdown(
    path: Path, repo_root: Path, digest: str, text: str
) -> list[MgrepChunk]:
    lines = text.splitlines()
    heading_indices = [
        index for index, line in enumerate(lines) if line.lstrip().startswith("#")
    ]
    if not heading_indices:
        return _chunk_plain_text(path, repo_root, digest, text)

    chunks: list[MgrepChunk] = []
    for position, start_index in enumerate(heading_indices):
        end_index = (
            heading_indices[position + 1] - 1
            if position + 1 < len(heading_indices)
            else len(lines) - 1
        )
        snippet_lines = lines[start_index : end_index + 1]
        snippet = "\n".join(snippet_lines).strip()
        if not snippet:
            continue
        heading_text = snippet_lines[0].lstrip("#").strip() or path.stem
        chunks.append(
            _make_chunk(
                path=path,
                repo_root=repo_root,
                digest=digest,
                kind="section",
                symbol_name=heading_text,
                line_start=start_index + 1,
                line_end=end_index + 1,
                text=snippet,
                metadata={"heading": heading_text},
            )
        )

    return chunks


def _chunk_plain_text(
    path: Path, repo_root: Path, digest: str, text: str
) -> list[MgrepChunk]:
    lines = text.splitlines()
    if not text.strip():
        return []

    chunks: list[MgrepChunk] = []
    boundaries = list(_PARAGRAPH_SPLIT_RE.finditer(text))
    spans: list[tuple[int, int]] = []
    start = 0
    for boundary in boundaries:
        end = boundary.start()
        if end > start:
            spans.append((start, end))
        start = boundary.end()
    if start < len(text):
        spans.append((start, len(text)))

    for index, (start_offset, end_offset) in enumerate(spans):
        raw_block = text[start_offset:end_offset]
        snippet = raw_block.strip()
        if not snippet:
            continue
        leading_trim = len(raw_block) - len(raw_block.lstrip())
        start_line = text[: start_offset + leading_trim].count("\n") + 1
        end_line = start_line + snippet.count("\n")
        chunks.append(
            _make_chunk(
                path=path,
                repo_root=repo_root,
                digest=digest,
                kind="paragraph",
                symbol_name=f"{path.stem}:{index + 1}",
                line_start=start_line,
                line_end=end_line,
                text=snippet,
            )
        )

    if chunks:
        return chunks

    return [
        _make_chunk(
            path=path,
            repo_root=repo_root,
            digest=digest,
            kind="paragraph",
            symbol_name=path.stem,
            line_start=1,
            line_end=max(len(lines), 1),
            text=text,
        )
    ]


def extract_chunks_from_file(
    path: Path, repo_root: Path, digest: str
) -> list[MgrepChunk]:
    """Extract searchable chunks from one repository file."""
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return []
    language = _language_for_path(path)
    if language == "python":
        return _chunk_python(path, repo_root, digest, text)
    if language == "markdown":
        return _chunk_markdown(path, repo_root, digest, text)
    return _chunk_plain_text(path, repo_root, digest, text)
