from __future__ import annotations

from pathlib import Path

from DeepResearch.src.tools.mgrep.discovery import discover_repository_files


def test_discover_repository_files_honors_ignore_rules_and_store_dir(
    tmp_path: Path, mgrep_config
):
    (tmp_path / "keep.py").write_text(
        "def keep():\n    return 'ok'\n", encoding="utf-8"
    )
    (tmp_path / "notes.md").write_text("# Notes\n\nsemantic search\n", encoding="utf-8")
    (tmp_path / "ignored.py").write_text("def ignored():\n    pass\n", encoding="utf-8")
    (tmp_path / "secret.txt").write_text("secret\n", encoding="utf-8")
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "guide.md").write_text("# Guide\n", encoding="utf-8")
    (tmp_path / "bad.txt").write_bytes(b"\xff\xfeabc")
    (tmp_path / ".gitignore").write_text("ignored.py\ndocs/\n", encoding="utf-8")
    (tmp_path / ".mgrepignore").write_text("secret.txt\n", encoding="utf-8")

    store_dir = tmp_path / ".deepcritical" / "mgrep"
    store_dir.mkdir(parents=True)
    (store_dir / "manifest.json").write_text("{}", encoding="utf-8")

    discovery = discover_repository_files(tmp_path, mgrep_config)

    relative_paths = [path.relative_to(tmp_path).as_posix() for path in discovery.files]
    assert relative_paths == ["keep.py", "notes.md"]
    assert discovery.skipped_count >= 5
