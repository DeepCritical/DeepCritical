"""
Agent data types for DeepCritical research workflows.

This module defines Pydantic models and data structures for agent operations
including agent types, statuses, dependencies, results, and execution history.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class AgentType(str, Enum):
    """Types of agents in the DeepCritical system."""

    PARSER = "parser"
    PLANNER = "planner"
    EXECUTOR = "executor"
    SEARCH = "search"
    RAG = "rag"
    BIOINFORMATICS = "bioinformatics"
    DEEPSEARCH = "deepsearch"
    ORCHESTRATOR = "orchestrator"
    EVALUATOR = "evaluator"
    # DeepAgent types
    DEEP_AGENT_PLANNING = "deep_agent_planning"
    DEEP_AGENT_FILESYSTEM = "deep_agent_filesystem"
    DEEP_AGENT_RESEARCH = "deep_agent_research"
    DEEP_AGENT_ORCHESTRATION = "deep_agent_orchestration"
    DEEP_AGENT_GENERAL = "deep_agent_general"


class AgentStatus(str, Enum):
    """Agent execution status."""

    IDLE = "idle"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    RETRYING = "retrying"


@dataclass
class AgentDependencies:
    """Dependencies for agent execution."""

    config: dict[str, Any] = field(default_factory=dict)
    tools: list[str] = field(default_factory=list)
    other_agents: list[str] = field(default_factory=list)
    data_sources: list[str] = field(default_factory=list)


@dataclass
class AgentResult:
    """Result from agent execution."""

    success: bool
    data: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)
    error: str | None = None
    execution_time: float = 0.0
    agent_type: AgentType = AgentType.EXECUTOR


@dataclass
class ExecutionHistory:
    """History of agent executions."""

    items: list[dict[str, Any]] = field(default_factory=list)

    def record(self, agent_type: AgentType, result: AgentResult, **kwargs):
        """Record an execution result."""
        self.items.append(
            {
                "timestamp": time.time(),
                "agent_type": agent_type.value,
                "success": result.success,
                "execution_time": result.execution_time,
                "error": result.error,
                **kwargs,
            }
        )
