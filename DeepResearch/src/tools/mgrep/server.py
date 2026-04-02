"""MCP-style server adapter for repo-local mgrep semantic search."""

from __future__ import annotations

import asyncio
import threading
from datetime import datetime
from typing import Any

from DeepResearch.src.datatypes.bioinformatics_mcp import MCPServerBase, mcp_tool
from DeepResearch.src.datatypes.mcp import (
    MCPServerConfig,
    MCPServerDeployment,
    MCPServerStatus,
    MCPServerType,
    MCPToolSpec,
)
from DeepResearch.src.datatypes.mgrep import MgrepConfig

from .service import MgrepService


def _run_async(coro: Any) -> Any:
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coro)

    result: dict[str, Any] = {}
    error: dict[str, BaseException] = {}

    def _runner() -> None:
        try:
            result["value"] = asyncio.run(coro)
        except BaseException as exc:  # pragma: no cover - exercised in async callers
            error["value"] = exc

    thread = threading.Thread(target=_runner, daemon=True)
    thread.start()
    thread.join()

    if "value" in error:
        raise error["value"]
    return result.get("value")


class MgrepServer(MCPServerBase):
    """Thin MCP-compatible adapter over the shared mgrep service."""

    def __init__(self, config: MCPServerConfig | None = None):
        if config is None:
            config = MCPServerConfig(
                server_name="mgrep",
                server_type=MCPServerType.MGREP,
                capabilities=["index", "sync", "search", "get_stats"],
            )
        super().__init__(config)

    def _build_service(self, repo_root: str = ".") -> MgrepService:
        return MgrepService(repo_root=repo_root, config=MgrepConfig())

    @mcp_tool(
        MCPToolSpec(
            name="index",
            description="Build or rebuild the repo-local semantic search index",
            inputs={"repo_root": "str"},
            outputs={"indexed_file_count": "int", "indexed_chunk_count": "int"},
            server_type=MCPServerType.MGREP,
        )
    )
    def index(self, repo_root: str = ".") -> dict[str, Any]:
        return _run_async(self._build_service(repo_root).index()).model_dump()

    @mcp_tool(
        MCPToolSpec(
            name="sync",
            description="Incrementally sync the repo-local semantic search index",
            inputs={"repo_root": "str"},
            outputs={"indexed_file_count": "int", "indexed_chunk_count": "int"},
            server_type=MCPServerType.MGREP,
        )
    )
    def sync(self, repo_root: str = ".") -> dict[str, Any]:
        return _run_async(self._build_service(repo_root).sync()).model_dump()

    @mcp_tool(
        MCPToolSpec(
            name="search",
            description="Semantic search over a local repository index",
            inputs={
                "repo_root": "str",
                "query": "str",
                "top_k": "int",
                "path": "Optional[str]",
                "smart": "bool",
            },
            outputs={"results": "list", "total_results": "int"},
            server_type=MCPServerType.MGREP,
        )
    )
    def search(
        self,
        query: str,
        repo_root: str = ".",
        top_k: int = 10,
        path: str | None = None,
        smart: bool = False,
    ) -> dict[str, Any]:
        service = self._build_service(repo_root)
        response = _run_async(
            service.smart_search(query, top_k=top_k, path=path)
            if smart
            else service.search(query, top_k=top_k, path=path)
        )
        return response.model_dump()

    @mcp_tool(
        MCPToolSpec(
            name="get_stats",
            description="Read stats for the local semantic search index",
            inputs={"repo_root": "str"},
            outputs={"indexed_file_count": "int", "indexed_chunk_count": "int"},
            server_type=MCPServerType.MGREP,
        )
    )
    def get_stats(self, repo_root: str = ".") -> dict[str, Any]:
        return self._build_service(repo_root).get_stats().model_dump()

    async def deploy_with_testcontainers(self) -> MCPServerDeployment:
        self.container_id = "local-mgrep"
        self.container_name = "local-mgrep"
        return MCPServerDeployment(
            server_name=self.name,
            server_type=self.server_type,
            container_id=self.container_id,
            container_name=self.container_name,
            status=MCPServerStatus.RUNNING,
            created_at=datetime.now(),
            started_at=datetime.now(),
            tools_available=self.list_tools(),
            configuration=self.config,
        )

    async def stop_with_testcontainers(self) -> bool:
        self.container_id = None
        self.container_name = None
        return True
