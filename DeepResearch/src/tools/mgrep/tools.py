"""ToolRunner and Pydantic-AI wrappers for mgrep-style semantic search."""

from __future__ import annotations

import asyncio
import json
import threading
from pathlib import Path
from typing import Any

from DeepResearch.src.datatypes.mgrep import MgrepConfig
from DeepResearch.src.tools.base import ExecutionResult, ToolRunner, ToolSpec, registry

from .service import MgrepService


def _repo_root_from_params(params: dict[str, Any]) -> str:
    return str(params.get("repo_root") or Path.cwd())


def _build_service(params: dict[str, Any]) -> MgrepService:
    return MgrepService(repo_root=_repo_root_from_params(params), config=MgrepConfig())


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


class MgrepIndexTool(ToolRunner):
    """Force a full rebuild of the local semantic search index."""

    def __init__(self):
        super().__init__(
            ToolSpec(
                name="mgrep_index",
                description="Build or rebuild a repo-local semantic search index",
                inputs={"repo_root": "TEXT (optional)"},
                outputs={
                    "repo_root": "TEXT",
                    "indexed_file_count": "INTEGER",
                    "indexed_chunk_count": "INTEGER",
                },
            )
        )

    def run(self, params: dict[str, Any]) -> ExecutionResult:
        try:
            service = _build_service(params)
            stats = _run_async(service.index())
        except Exception as exc:
            return ExecutionResult(success=False, error=f"mgrep index failed: {exc!s}")
        return ExecutionResult(success=True, data=stats.model_dump())


class MgrepSyncTool(ToolRunner):
    """Incrementally update the local semantic search index."""

    def __init__(self):
        super().__init__(
            ToolSpec(
                name="mgrep_sync",
                description="Incrementally sync a repo-local semantic search index",
                inputs={"repo_root": "TEXT (optional)"},
                outputs={
                    "repo_root": "TEXT",
                    "indexed_file_count": "INTEGER",
                    "indexed_chunk_count": "INTEGER",
                },
            )
        )

    def run(self, params: dict[str, Any]) -> ExecutionResult:
        try:
            service = _build_service(params)
            stats = _run_async(service.sync())
        except Exception as exc:
            return ExecutionResult(success=False, error=f"mgrep sync failed: {exc!s}")
        return ExecutionResult(success=True, data=stats.model_dump())


class MgrepSearchTool(ToolRunner):
    """Run repo-local semantic search with structured results."""

    def __init__(self):
        super().__init__(
            ToolSpec(
                name="mgrep_search",
                description="Semantic search over a local repository index",
                inputs={
                    "query": "TEXT",
                    "repo_root": "TEXT (optional)",
                    "path": "TEXT (optional)",
                    "top_k": "INTEGER (optional)",
                    "smart": "BOOLEAN (optional)",
                },
                outputs={"results": "JSON", "total_results": "INTEGER"},
            )
        )

    def run(self, params: dict[str, Any]) -> ExecutionResult:
        query = str(params.get("query", "")).strip()
        if not query:
            return ExecutionResult(success=False, error="Query is required")

        top_k = int(params.get("top_k", 10))
        path = params.get("path")
        smart = bool(params.get("smart", False))

        try:
            service = _build_service(params)
            response = _run_async(
                service.smart_search(query, top_k=top_k, path=path)
                if smart
                else service.search(query, top_k=top_k, path=path)
            )
        except Exception as exc:
            return ExecutionResult(success=False, error=f"mgrep search failed: {exc!s}")
        return ExecutionResult(success=True, data=response.model_dump())


class MgrepStatsTool(ToolRunner):
    """Read local semantic-search index stats."""

    def __init__(self):
        super().__init__(
            ToolSpec(
                name="mgrep_stats",
                description="Read stats for a repo-local semantic search index",
                inputs={"repo_root": "TEXT (optional)"},
                outputs={
                    "indexed_file_count": "INTEGER",
                    "indexed_chunk_count": "INTEGER",
                    "last_sync_time": "TEXT",
                },
            )
        )

    def run(self, params: dict[str, Any]) -> ExecutionResult:
        try:
            service = _build_service(params)
            stats = service.get_stats()
        except Exception as exc:
            return ExecutionResult(success=False, error=f"mgrep stats failed: {exc!s}")
        return ExecutionResult(success=True, data=stats.model_dump())


def semantic_repo_search(ctx: Any) -> str:
    """Pydantic-AI-friendly semantic repo search wrapper."""
    params = ctx.deps if isinstance(getattr(ctx, "deps", None), dict) else {}
    tool = MgrepSearchTool()
    result = tool.run(params)
    if result.success:
        return json.dumps(result.data)
    return json.dumps({"success": False, "error": result.error or "search failed"})


semantic_repo_search_tool = semantic_repo_search


registry.register("mgrep_index", MgrepIndexTool)
registry.register("mgrep_sync", MgrepSyncTool)
registry.register("mgrep_search", MgrepSearchTool)
registry.register("mgrep_stats", MgrepStatsTool)
