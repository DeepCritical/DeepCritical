from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class PydAIToolsetBuilder:
    """Construct builtin tools and external toolsets for Pydantic AI based on cfg."""

    def build(self, cfg: dict[str, Any]) -> dict[str, list[Any]]:
        from DeepResearch.src.tools.pyd_ai_tools import (  # reuse helpers
            _build_builtin_tools,
            _build_toolsets,
        )

        builtin_tools = _build_builtin_tools(cfg)
        toolsets = _build_toolsets(cfg)
        return {"builtin_tools": builtin_tools, "toolsets": toolsets}
