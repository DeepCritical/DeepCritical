"""
Pydantic AI utilities for DeepCritical research workflows.

This module provides utility functions for Pydantic AI integration,
including configuration management, tool building, and agent creation.
"""

from __future__ import annotations

import contextlib
from typing import Any


def get_pydantic_ai_config() -> dict[str, Any]:
    """Get configuration from Hydra or environment."""
    try:
        # Lazy import Hydra/OmegaConf if available via app context; fall back to env-less defaults
        # In this lightweight wrapper, we don't have direct cfg access; return empty
        return {}
    except Exception:
        return {}


def build_builtin_tools(cfg: dict[str, Any]) -> list[Any]:
    """Build Pydantic AI builtin tools from configuration."""
    try:
        # Import from Pydantic AI (exported at package root)
        from pydantic_ai import CodeExecutionTool, UrlContextTool, WebSearchTool
    except Exception:
        return []

    pyd_cfg = (cfg or {}).get("pyd_ai", {})
    builtin_cfg = pyd_cfg.get("builtin_tools", {})

    tools: list[Any] = []

    # Web Search
    ws_cfg = builtin_cfg.get("web_search", {})
    if ws_cfg.get("enabled", True):
        kwargs: dict[str, Any] = {}
        if ws_cfg.get("search_context_size"):
            kwargs["search_context_size"] = ws_cfg.get("search_context_size")
        if ws_cfg.get("user_location"):
            kwargs["user_location"] = ws_cfg.get("user_location")
        if ws_cfg.get("blocked_domains"):
            kwargs["blocked_domains"] = ws_cfg.get("blocked_domains")
        if ws_cfg.get("allowed_domains"):
            kwargs["allowed_domains"] = ws_cfg.get("allowed_domains")
        if ws_cfg.get("max_uses") is not None:
            kwargs["max_uses"] = ws_cfg.get("max_uses")
        try:
            tools.append(WebSearchTool(**kwargs))
        except Exception:
            tools.append(WebSearchTool())

    # Code Execution
    ce_cfg = builtin_cfg.get("code_execution", {})
    if ce_cfg.get("enabled", False):
        with contextlib.suppress(Exception):
            tools.append(CodeExecutionTool())

    # URL Context
    uc_cfg = builtin_cfg.get("url_context", {})
    if uc_cfg.get("enabled", False):
        with contextlib.suppress(Exception):
            tools.append(UrlContextTool())

    return tools


def build_toolsets(cfg: dict[str, Any]) -> list[Any]:
    """Build Pydantic AI toolsets from configuration."""
    toolsets: list[Any] = []
    pyd_cfg = (cfg or {}).get("pyd_ai", {})
    ts_cfg = pyd_cfg.get("toolsets", {})

    # LangChain toolset (optional)
    lc_cfg = ts_cfg.get("langchain", {})
    if lc_cfg.get("enabled"):
        try:
            from pydantic_ai.ext.langchain import LangChainToolset

            # Expect user to provide instantiated tools or a toolkit provider name; here we do nothing dynamic
            tools = []  # placeholder if user later wires concrete LangChain tools
            toolsets.append(LangChainToolset(tools))
        except Exception:
            pass

    # ACI toolset (optional)
    aci_cfg = ts_cfg.get("aci", {})
    if aci_cfg.get("enabled"):
        try:
            from pydantic_ai.ext.aci import ACIToolset

            toolsets.append(
                ACIToolset(
                    aci_cfg.get("tools", []),
                    linked_account_owner_id=aci_cfg.get("linked_account_owner_id"),
                )
            )
        except Exception:
            pass

    return toolsets


def build_agent(
    cfg: dict[str, Any],
    builtin_tools: list[Any] | None = None,
    toolsets: list[Any] | None = None,
):
    """Build Pydantic AI agent from configuration."""
    try:
        from pydantic_ai import Agent
        from pydantic_ai.models.openai import OpenAIResponsesModelSettings
    except Exception:
        return None, None

    pyd_cfg = (cfg or {}).get("pyd_ai", {})
    model_name = pyd_cfg.get("model", "anthropic:claude-sonnet-4-0")

    settings = None
    # OpenAI Responses specific settings (include web search sources)
    if model_name.startswith("openai-responses:"):
        ws_include = (
            (pyd_cfg.get("builtin_tools", {}) or {}).get("web_search", {}) or {}
        ).get("openai_include_sources", False)
        try:
            settings = OpenAIResponsesModelSettings(
                openai_include_web_search_sources=bool(ws_include)
            )
        except Exception:
            settings = None

    agent = Agent(
        model=model_name,
        builtin_tools=builtin_tools or [],
        toolsets=toolsets or [],
        model_settings=settings,
    )

    return agent, pyd_cfg


def run_agent_sync(agent, prompt: str) -> Any | None:
    """Run agent synchronously and return result."""
    try:
        return agent.run_sync(prompt)
    except Exception:
        return None
