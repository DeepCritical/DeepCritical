from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .execution_status import ExecutionStatus


@dataclass
class ExecutionItem:
    """Individual execution item in the history."""

    step_name: str
    tool: str
    status: ExecutionStatus
    result: dict[str, Any] | None = None
    error: str | None = None
    timestamp: float = field(
        default_factory=lambda: datetime.now(timezone.utc).timestamp()
    )
    parameters: dict[str, Any] | None = None
    duration: float | None = None
    retry_count: int = 0


@dataclass
class ExecutionStep:
    """Individual step in execution history."""

    step_id: str
    status: str
    start_time: float | None = None
    end_time: float | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class ExecutionHistory:
    """History of workflow execution for adaptive re-planning."""

    # Constants for success rate thresholds
    SUCCESS_RATE_THRESHOLD = 0.8

    items: list[ExecutionItem] = field(default_factory=list)
    start_time: float = field(
        default_factory=lambda: datetime.now(timezone.utc).timestamp()
    )
    end_time: float | None = None

    def add_item(self, item: ExecutionItem) -> None:
        """Add an execution item to the history."""
        self.items.append(item)

    def get_successful_steps(self) -> list[ExecutionItem]:
        """Get all successfully executed steps."""
        return [item for item in self.items if item.status == ExecutionStatus.SUCCESS]

    def get_failed_steps(self) -> list[ExecutionItem]:
        """Get all failed steps."""
        return [item for item in self.items if item.status == ExecutionStatus.FAILED]

    def get_step_by_name(self, step_name: str) -> ExecutionItem | None:
        """Get execution item by step name."""
        for item in self.items:
            if item.step_name == step_name:
                return item
        return None

    def get_tool_usage_count(self, tool_name: str) -> int:
        """Get the number of times a tool has been used."""
        return sum(1 for item in self.items if item.tool == tool_name)

    def get_failure_patterns(self) -> dict[str, int]:
        """Analyze failure patterns to inform re-planning."""
        failure_patterns = {}
        for item in self.get_failed_steps():
            error_type = self._categorize_error(item.error)
            failure_patterns[error_type] = failure_patterns.get(error_type, 0) + 1
        return failure_patterns

    def _categorize_error(self, error: str | None) -> str:
        """Categorize error types for pattern analysis."""
        if not error:
            return "unknown"

        error_lower = error.lower()
        if "timeout" in error_lower or "network" in error_lower:
            return "network_error"
        if "validation" in error_lower or "schema" in error_lower:
            return "validation_error"
        if "parameter" in error_lower or "config" in error_lower:
            return "parameter_error"
        if "success_criteria" in error_lower:
            return "criteria_failure"
        return "execution_error"

    def get_execution_summary(self) -> dict[str, Any]:
        """Get a summary of the execution history."""
        total_steps = len(self.items)
        successful_steps = len(self.get_successful_steps())
        failed_steps = len(self.get_failed_steps())

        duration = None
        if self.end_time:
            duration = self.end_time - self.start_time

        return {
            "total_steps": total_steps,
            "successful_steps": successful_steps,
            "failed_steps": failed_steps,
            "success_rate": successful_steps / total_steps if total_steps > 0 else 0,
            "duration": duration,
            "failure_patterns": self.get_failure_patterns(),
            "tools_used": list({item.tool for item in self.items}),
        }

    def finish(self) -> None:
        """Mark the execution as finished."""
        self.end_time = datetime.now(timezone.utc).timestamp()

    def to_dict(self) -> dict[str, Any]:
        """Convert history to dictionary for serialization."""
        return {
            "items": [
                {
                    "step_name": item.step_name,
                    "tool": item.tool,
                    "status": item.status.value,
                    "result": item.result,
                    "error": item.error,
                    "timestamp": item.timestamp,
                    "parameters": item.parameters,
                    "duration": item.duration,
                    "retry_count": item.retry_count,
                }
                for item in self.items
            ],
            "start_time": self.start_time,
            "end_time": self.end_time,
            "summary": self.get_execution_summary(),
        }

    def save_to_file(self, filepath: str) -> None:
        """Save execution history to a JSON file."""
        with Path(filepath).open("w") as f:
            json.dump(self.to_dict(), f, indent=2)

    @classmethod
    def load_from_file(cls, filepath: str) -> ExecutionHistory:
        """Load execution history from a JSON file."""
        with Path(filepath).open() as f:
            data = json.load(f)

        history = cls()
        history.start_time = data.get(
            "start_time", datetime.now(timezone.utc).timestamp()
        )
        history.end_time = data.get("end_time")

        for item_data in data.get("items", []):
            item = ExecutionItem(
                step_name=item_data["step_name"],
                tool=item_data["tool"],
                status=ExecutionStatus(item_data["status"]),
                result=item_data.get("result"),
                error=item_data.get("error"),
                timestamp=item_data.get(
                    "timestamp", datetime.now(timezone.utc).timestamp()
                ),
                parameters=item_data.get("parameters"),
                duration=item_data.get("duration"),
                retry_count=item_data.get("retry_count", 0),
            )
            history.items.append(item)

        return history


class ExecutionTracker:
    """Utility class for tracking execution metrics and performance."""

    def __init__(self):
        self.metrics = {
            "total_executions": 0,
            "successful_executions": 0,
            "failed_executions": 0,
            "average_duration": 0,
            "tool_performance": {},
            "error_frequency": {},
        }

    def update_metrics(self, history: ExecutionHistory) -> None:
        """Update metrics based on execution history."""
        summary = history.get_execution_summary()

        self.metrics["total_executions"] += 1
        if (
            summary["success_rate"] > self.SUCCESS_RATE_THRESHOLD
        ):  # Consider successful if >80% success rate
            self.metrics["successful_executions"] += 1
        else:
            self.metrics["failed_executions"] += 1

        # Update average duration
        if summary["duration"]:
            total_duration = self.metrics["average_duration"] * (
                self.metrics["total_executions"] - 1
            )
            self.metrics["average_duration"] = (
                total_duration + summary["duration"]
            ) / self.metrics["total_executions"]

        # Update tool performance
        for tool in summary["tools_used"]:
            if tool not in self.metrics["tool_performance"]:
                self.metrics["tool_performance"][tool] = {"uses": 0, "successes": 0}

            self.metrics["tool_performance"][tool]["uses"] += 1
            if summary["success_rate"] > self.SUCCESS_RATE_THRESHOLD:
                self.metrics["tool_performance"][tool]["successes"] += 1

        # Update error frequency
        for error_type, count in summary["failure_patterns"].items():
            self.metrics["error_frequency"][error_type] = (
                self.metrics["error_frequency"].get(error_type, 0) + count
            )

    def get_tool_reliability(self, tool_name: str) -> float:
        """Get reliability score for a specific tool."""
        if tool_name not in self.metrics["tool_performance"]:
            return 0.0

        perf = self.metrics["tool_performance"][tool_name]
        if perf["uses"] == 0:
            return 0.0

        return perf["successes"] / perf["uses"]

    def get_most_reliable_tools(self, limit: int = 5) -> list[tuple[str, float]]:
        """Get the most reliable tools based on historical performance."""
        tool_scores = [
            (tool, self.get_tool_reliability(tool))
            for tool in self.metrics["tool_performance"]
        ]
        tool_scores.sort(key=lambda x: x[1], reverse=True)
        return tool_scores[:limit]

    def get_common_failure_modes(self) -> list[tuple[str, int]]:
        """Get the most common failure modes."""
        failure_modes = list(self.metrics["error_frequency"].items())
        failure_modes.sort(key=lambda x: x[1], reverse=True)
        return failure_modes


@dataclass
class ExecutionMetrics:
    """Metrics for execution performance tracking."""

    total_steps: int = 0
    successful_steps: int = 0
    failed_steps: int = 0
    total_duration: float = 0.0
    avg_step_duration: float = 0.0
    tool_usage_count: dict[str, int] = field(default_factory=dict)
    error_frequency: dict[str, int] = field(default_factory=dict)

    def add_step_result(self, step_name: str, success: bool, duration: float) -> None:
        """Add a step result to the metrics."""
        self.total_steps += 1
        if success:
            self.successful_steps += 1
        else:
            self.failed_steps += 1

        self.total_duration += duration
        if self.total_steps > 0:
            self.avg_step_duration = self.total_duration / self.total_steps

        # Track tool usage
        if step_name not in self.tool_usage_count:
            self.tool_usage_count[step_name] = 0
        self.tool_usage_count[step_name] += 1

    def add_error(self, error_type: str) -> None:
        """Add an error occurrence."""
        if error_type not in self.error_frequency:
            self.error_frequency[error_type] = 0
        self.error_frequency[error_type] += 1
