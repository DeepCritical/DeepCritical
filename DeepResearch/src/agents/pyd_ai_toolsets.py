from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List


@dataclass
class PydAIToolsetBuilder:
    """Construct builtin tools and external toolsets for Pydantic AI based on cfg."""

    def build(self, cfg: Dict[str, Any]) -> Dict[str, List[Any]]:
        from ..tools.pyd_ai_tools import (
            _build_builtin_tools,
            _build_toolsets,
        )  # reuse helpers

        builtin_tools = _build_builtin_tools(cfg)
        toolsets = _build_toolsets(cfg)
        return {"builtin_tools": builtin_tools, "toolsets": toolsets}
