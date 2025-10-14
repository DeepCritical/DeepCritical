"""
Execution-related data types for DeepCritical's workflow orchestration.

This module defines data structures for workflow execution including
workflow steps, DAGs, execution contexts, and execution history.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from DeepResearch.src.utils.execution_history import ExecutionHistory


@dataclass
class WorkflowStep:
    """A single step in a computational workflow."""

    tool: str
    parameters: dict[str, Any]
    inputs: dict[str, str]  # Maps input names to data sources
    outputs: dict[str, str]  # Maps output names to data destinations
    success_criteria: dict[str, Any]
    retry_config: dict[str, Any] = field(default_factory=dict)


@dataclass
class WorkflowDAG:
    """Directed Acyclic Graph representing a computational workflow."""

    steps: list[WorkflowStep]
    dependencies: dict[str, list[str]]  # Maps step names to their dependencies
    execution_order: list[str]  # Topological sort of step names
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class ExecutionContext:
    """Context for workflow execution."""

    workflow: WorkflowDAG
    history: ExecutionHistory
    data_bag: dict[str, Any] = field(default_factory=dict)
    current_step: int = 0
    max_retries: int = 3
    manual_confirmation: bool = False
    adaptive_replanning: bool = True
