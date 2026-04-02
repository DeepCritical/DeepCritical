from __future__ import annotations

import json
from types import SimpleNamespace

import pytest

from DeepResearch.src.tools.mgrep.service import MgrepService
from DeepResearch.src.tools.mgrep.tools import (
    MgrepIndexTool,
    MgrepSearchTool,
    MgrepStatsTool,
    MgrepSyncTool,
    semantic_repo_search_tool,
)


@pytest.mark.asyncio
async def test_tools_and_pydantic_ai_wrapper(
    monkeypatch,
    tmp_path,
    mgrep_config,
    keyword_embeddings,
    in_memory_vector_store_factory,
):
    (tmp_path / "parser.py").write_text(
        "def build_parser():\n    return 'semantic parser search'\n",
        encoding="utf-8",
    )
    service = MgrepService(
        repo_root=tmp_path,
        config=mgrep_config,
        embeddings=keyword_embeddings,
        vector_store_factory=in_memory_vector_store_factory,
    )

    monkeypatch.setattr(
        "DeepResearch.src.tools.mgrep.tools._build_service",
        lambda params: service,
    )

    index_result = MgrepIndexTool().run({"repo_root": str(tmp_path)})
    assert index_result.success is True
    assert index_result.data["indexed_file_count"] == 1

    search_result = MgrepSearchTool().run(
        {"repo_root": str(tmp_path), "query": "semantic parser"}
    )
    assert search_result.success is True
    assert search_result.data["total_results"] >= 1

    sync_result = MgrepSyncTool().run({"repo_root": str(tmp_path)})
    assert sync_result.success is True

    stats_result = MgrepStatsTool().run({"repo_root": str(tmp_path)})
    assert stats_result.success is True
    assert stats_result.data["indexed_chunk_count"] >= 1

    payload = json.loads(
        semantic_repo_search_tool(
            SimpleNamespace(
                deps={"repo_root": str(tmp_path), "query": "semantic parser"}
            )
        )
    )
    assert payload["total_results"] >= 1
