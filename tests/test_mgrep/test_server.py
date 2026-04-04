from __future__ import annotations

import pytest

from DeepResearch.src.datatypes.bioinformatics_mcp import MCPServerBase
from DeepResearch.src.datatypes.mcp import MCPServerStatus
from DeepResearch.src.tools.mgrep.server import MgrepServer
from DeepResearch.src.tools.mgrep.service import MgrepService


@pytest.mark.asyncio
async def test_mgrep_server_executes_registered_tools(
    monkeypatch,
    tmp_path,
    mgrep_config,
    keyword_embeddings,
    in_memory_vector_store_factory,
):
    monkeypatch.setattr(
        MCPServerBase, "_initialize_pydantic_ai_agent", lambda self: None
    )

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

    def _build_service(self, repo_root: str = ".", config_path: str | None = None):
        return service

    monkeypatch.setattr(MgrepServer, "_build_service", _build_service)

    server = MgrepServer()
    assert {"index", "sync", "search", "get_stats"} <= set(server.list_tools())

    indexed = server.execute_tool("index", repo_root=str(tmp_path))
    assert indexed["indexed_file_count"] == 1

    search_payload = server.execute_tool(
        "search",
        repo_root=str(tmp_path),
        query="semantic parser",
        top_k=5,
    )
    assert search_payload["total_results"] >= 1

    stats_payload = server.execute_tool("get_stats", repo_root=str(tmp_path))
    assert stats_payload["indexed_chunk_count"] >= 1

    deployment = await server.deploy_with_testcontainers()
    assert deployment.status == MCPServerStatus.RUNNING
    assert await server.stop_with_testcontainers() is True
