from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from pydantic import BaseModel, Field


class OrchestratorDependencies(BaseModel):
    """Dependencies for the agent orchestrator."""

    config: dict[str, Any] = Field(default_factory=dict)
    user_input: str = Field(..., description="User input/query")
    context: dict[str, Any] = Field(default_factory=dict)
    available_subgraphs: list[str] = Field(default_factory=list)
    available_agents: list[str] = Field(default_factory=list)
    current_iteration: int = Field(0, description="Current iteration number")
    parent_loop_id: str | None = Field(None, description="Parent loop ID if nested")


@dataclass
class Orchestrator:
    """Placeholder orchestrator that would sequence subflows based on config."""

    def build_plan(self, question: str, flows_cfg: dict[str, Any] | None) -> list[str]:
        enabled = [
            k
            for k, v in (flows_cfg or {}).items()
            if isinstance(v, dict) and v.get("enabled")
        ]
        return [f"flow:{name}" for name in enabled]
