from __future__ import annotations

import importlib
import re
from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING, Any

from . import deep_agent_graph

# Import agent prompts
from .agent import ACTIONS_WRAPPER, HEADER, AgentPrompts

if TYPE_CHECKING:
    from omegaconf import DictConfig


@dataclass
class PromptLoader:
    cfg: DictConfig

    def get(self, key: str, subkey: str | None = None) -> str:
        # 1) Prefer Python modules to enable code-side defaults and richer structures
        module_name = f"DeepResearch.src.prompts.{key}"
        try:
            mod = importlib.import_module(module_name)
            if subkey:
                # Map subkey to CONSTANT_NAME, default 'SYSTEM' if subkey == 'system'
                const_name = (
                    "SYSTEM"
                    if subkey.lower() == "system"
                    else re.sub(r"[^A-Za-z0-9]", "_", subkey).upper()
                )
                val = getattr(mod, const_name, None)
                if isinstance(val, str) and val:
                    return self._substitute(key, val)
            else:
                val = getattr(mod, "SYSTEM", None)
                if isinstance(val, str) and val:
                    return self._substitute(key, val)
        except Exception:
            pass

        # 2) Fallback to Hydra/YAML-configured prompts to keep configuration centralized
        block: dict[str, Any] = getattr(self.cfg, key, {})
        if subkey:
            return self._substitute(key, str(block.get(subkey, "")))
        return self._substitute(key, str(block.get("system", "")))

    def _substitute(self, key: str, template: str) -> str:
        if not template:
            return template
        # Collect variables: key-level vars, global prompt vars, and time vars
        vars_map: dict[str, Any] = {}
        try:
            block = getattr(self.cfg, key, {})
            vars_map.update(block.get("vars", {}) or {})  # type: ignore[attr-defined]
        except Exception:
            pass

        try:
            prompts_cfg = getattr(self.cfg, "prompts", {})
            globals_map = getattr(prompts_cfg, "globals", {})
            if isinstance(globals_map, dict):
                vars_map.update(globals_map)
        except Exception:
            pass

        from datetime import timezone

        now = datetime.now(timezone.utc)
        vars_map.setdefault(
            "current_date_utc", now.strftime("%a, %d %b %Y %H:%M:%S GMT")
        )
        vars_map.setdefault("current_time_iso", now.isoformat())
        vars_map.setdefault("current_year", str(now.year))
        vars_map.setdefault("current_month", str(now.month))

        def repl(match: re.Match[str]) -> str:
            name = match.group(1)
            val = vars_map.get(name)
            return "" if val is None else str(val)

        return re.sub(r"\$\{([A-Za-z0-9_]+)\}", repl, template)


__all__ = [
    "ACTIONS_WRAPPER",
    "HEADER",
    "AgentPrompts",
    "PromptLoader",
    "deep_agent_graph",
]
