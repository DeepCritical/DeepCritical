from __future__ import annotations

from pathlib import Path

from DeepResearch.src.tools.mgrep.chunking import extract_chunks_from_file
from DeepResearch.src.tools.mgrep.discovery import compute_file_digest


def test_python_chunking_extracts_structured_symbols(tmp_path: Path):
    path = tmp_path / "parser.py"
    path.write_text(
        (
            "class Parser:\n"
            "    def run(self):\n"
            "        return 'semantic parser'\n"
            "\n"
            "async def build_async():\n"
            "    return 'workflow engine'\n"
            "\n"
            "def helper():\n"
            "    return 'config search'\n"
        ),
        encoding="utf-8",
    )

    chunks = extract_chunks_from_file(path, tmp_path, compute_file_digest(path))

    assert [chunk.kind for chunk in chunks] == [
        "class",
        "function",
        "async_function",
        "function",
    ]
    assert [chunk.symbol_name for chunk in chunks] == [
        "Parser",
        "run",
        "build_async",
        "helper",
    ]
    assert chunks[0].line_start == 1
    assert chunks[-1].line_end == 9


def test_markdown_chunking_splits_on_headings(tmp_path: Path):
    path = tmp_path / "guide.md"
    path.write_text(
        "# Intro\nsemantic parser\n\n## Details\nworkflow search\n",
        encoding="utf-8",
    )

    chunks = extract_chunks_from_file(path, tmp_path, compute_file_digest(path))

    assert [chunk.kind for chunk in chunks] == ["section", "section"]
    assert [chunk.symbol_name for chunk in chunks] == ["Intro", "Details"]
    assert chunks[1].line_start == 4


def test_plain_text_chunking_preserves_paragraph_line_ranges(tmp_path: Path):
    path = tmp_path / "notes.txt"
    path.write_text(
        "semantic parser\nline two\n\nworkflow engine\n\nvector search\n",
        encoding="utf-8",
    )

    chunks = extract_chunks_from_file(path, tmp_path, compute_file_digest(path))

    assert [chunk.kind for chunk in chunks] == ["paragraph", "paragraph", "paragraph"]
    assert [(chunk.line_start, chunk.line_end) for chunk in chunks] == [
        (1, 2),
        (4, 4),
        (6, 6),
    ]
