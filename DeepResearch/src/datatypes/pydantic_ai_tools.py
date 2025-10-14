"""
Pydantic AI tools data types for DeepCritical research workflows.

This module defines Pydantic AI specific tool runners and related data types
that integrate with the Pydantic AI framework.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from DeepResearch.src.utils.pydantic_ai_utils import build_agent as _build_agent
from DeepResearch.src.utils.pydantic_ai_utils import (
    build_builtin_tools as _build_builtin_tools,
)
from DeepResearch.src.utils.pydantic_ai_utils import build_toolsets as _build_toolsets

# Import utility functions from utils module
from DeepResearch.src.utils.pydantic_ai_utils import get_pydantic_ai_config as _get_cfg
from DeepResearch.src.utils.pydantic_ai_utils import run_agent_sync as _run_sync

# Import registry locally to avoid circular imports
# from ..tools.base import registry  # Commented out to avoid circular imports


@dataclass
class WebSearchBuiltinRunner:
    """Pydantic AI builtin web search wrapper."""

    def __init__(self):
        # Import base classes locally to avoid circular imports
        from DeepResearch.src.tools.base import ToolRunner, ToolSpec

        ToolRunner.__init__(
            self,
            ToolSpec(
                name="web_search",
                description="Pydantic AI builtin web search wrapper.",
                inputs={"query": "TEXT"},
                outputs={"results": "TEXT", "sources": "TEXT"},
            ),
        )

    def run(self, params: dict[str, Any]) -> dict[str, Any]:
        ok, err = self.validate(params)
        if not ok:
            return {"success": False, "error": err}

        q = str(params.get("query", "")).strip()
        if not q:
            return {"success": False, "error": "Empty query"}

        cfg = _get_cfg()
        builtin_tools = _build_builtin_tools(cfg)
        if not any(
            getattr(t, "__class__", object).__name__ == "WebSearchTool"
            for t in builtin_tools
        ):
            # Force add WebSearchTool if not already on
            try:
                from pydantic_ai import WebSearchTool

                builtin_tools.append(WebSearchTool())
            except Exception:
                return {"success": False, "error": "pydantic_ai not available"}

        toolsets = _build_toolsets(cfg)
        agent, _ = _build_agent(cfg, builtin_tools, toolsets)
        if agent is None:
            return {
                "success": False,
                "error": "pydantic_ai not available or misconfigured",
            }

        result = _run_sync(agent, q)
        if not result:
            return {"success": False, "error": "web search failed"}

        text = getattr(result, "output", "")
        # Best-effort extract sources when provider supports it; keep as string
        sources = ""
        try:
            parts = getattr(result, "parts", None)
            if parts:
                sources = "\n".join(
                    [str(p) for p in parts if "web_search" in str(p).lower()]
                )
        except Exception:
            pass

        return {"success": True, "data": {"results": text, "sources": sources}}


@dataclass
class CodeExecBuiltinRunner:
    """Pydantic AI builtin code execution wrapper."""

    def __init__(self):
        # Import base classes locally to avoid circular imports
        from DeepResearch.src.tools.base import ToolRunner, ToolSpec

        ToolRunner.__init__(
            self,
            ToolSpec(
                name="pyd_code_exec",
                description="Pydantic AI builtin code execution wrapper.",
                inputs={"code": "TEXT"},
                outputs={"output": "TEXT"},
            ),
        )

    def run(self, params: dict[str, Any]) -> dict[str, Any]:
        ok, err = self.validate(params)
        if not ok:
            return {"success": False, "error": err}

        code = str(params.get("code", "")).strip()
        if not code:
            return {"success": False, "error": "Empty code"}

        cfg = _get_cfg()
        builtin_tools = _build_builtin_tools(cfg)
        # Ensure CodeExecutionTool present
        if not any(
            getattr(t, "__class__", object).__name__ == "CodeExecutionTool"
            for t in builtin_tools
        ):
            try:
                from pydantic_ai import CodeExecutionTool

                builtin_tools.append(CodeExecutionTool())
            except Exception:
                return {"success": False, "error": "pydantic_ai not available"}

        toolsets = _build_toolsets(cfg)
        agent, _ = _build_agent(cfg, builtin_tools, toolsets)
        if agent is None:
            return {
                "success": False,
                "error": "pydantic_ai not available or misconfigured",
            }

        # Load system prompt from Hydra (if available)
        try:
            from DeepResearch.src.prompts import PromptLoader  # type: ignore

            # In this wrapper, cfg may be empty; PromptLoader expects DictConfig-like object
            loader = PromptLoader(cfg)  # type: ignore
            system_prompt = loader.get("code_exec")
            prompt = (
                system_prompt.replace("${code}", code)
                if system_prompt
                else f"Execute the following code and return ONLY the final output as plain text.\n\n{code}"
            )
        except Exception:
            prompt = f"Execute the following code and return ONLY the final output as plain text.\n\n{code}"

        result = _run_sync(agent, prompt)
        if not result:
            return {"success": False, "error": "code execution failed"}
        return {"success": True, "data": {"output": getattr(result, "output", "")}}


@dataclass
class UrlContextBuiltinRunner:
    """Pydantic AI builtin URL context wrapper."""

    def __init__(self):
        # Import base classes locally to avoid circular imports
        from DeepResearch.src.tools.base import ToolRunner, ToolSpec

        ToolRunner.__init__(
            self,
            ToolSpec(
                name="pyd_url_context",
                description="Pydantic AI builtin URL context wrapper.",
                inputs={"url": "TEXT"},
                outputs={"content": "TEXT"},
            ),
        )

    def run(self, params: dict[str, Any]) -> dict[str, Any]:
        ok, err = self.validate(params)
        if not ok:
            return {"success": False, "error": err}

        url = str(params.get("url", "")).strip()
        if not url:
            return {"success": False, "error": "Empty url"}

        cfg = _get_cfg()
        builtin_tools = _build_builtin_tools(cfg)
        # Ensure UrlContextTool present
        if not any(
            getattr(t, "__class__", object).__name__ == "UrlContextTool"
            for t in builtin_tools
        ):
            try:
                from pydantic_ai import UrlContextTool

                builtin_tools.append(UrlContextTool())
            except Exception:
                return {"success": False, "error": "pydantic_ai not available"}

        toolsets = _build_toolsets(cfg)
        agent, _ = _build_agent(cfg, builtin_tools, toolsets)
        if agent is None:
            return {
                "success": False,
                "error": "pydantic_ai not available or misconfigured",
            }

        prompt = (
            f"What is this? {url}\n\nExtract the main content or a concise summary."
        )
        result = _run_sync(agent, prompt)
        if not result:
            return {"success": False, "error": "url context failed"}
        return {"success": True, "data": {"content": getattr(result, "output", "")}}


# Registry overrides and additions

# Registry registrations (commented out to avoid circular imports)
# registry.register(
#     "web_search", WebSearchBuiltinRunner
# )  # override previous synthetic runner
# registry.register("pyd_code_exec", CodeExecBuiltinRunner)
# registry.register("pyd_url_context", UrlContextBuiltinRunner)
