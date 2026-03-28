from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Callable


@dataclass
class ToolSpec:
    name: str
    description: str = ""
    inputs: dict[str, str] = field(default_factory=dict)  # param: type
    outputs: dict[str, str] = field(default_factory=dict)  # key: type


@dataclass
class ExecutionResult:
    success: bool
    data: dict[str, Any] = field(default_factory=dict)
    metrics: dict[str, Any] = field(default_factory=dict)
    error: str | None = None


class ToolRunner:
    spec: ToolSpec

    def __init__(self, spec: ToolSpec):
        self.spec = spec

    @staticmethod
    def _normalize_input_spec(spec_type: str) -> tuple[str, bool]:
        normalized = spec_type.split("(", 1)[0].strip()
        return normalized, "(optional" in spec_type.lower()

    def validate(self, params: dict[str, Any]) -> tuple[bool, str | None]:
        for k, t in self.spec.inputs.items():
            normalized_type, is_optional = self._normalize_input_spec(t)
            if k not in params:
                if is_optional:
                    continue
                return False, f"Missing required param: {k}"
            # basic type gate (string types only for placeholder)
            if normalized_type.endswith(("PATH", "ID")) or normalized_type in {
                "TEXT",
                "AA SEQUENCE",
            }:
                if not isinstance(params[k], str):
                    return (
                        False,
                        f"Invalid type for {k}: expected str for {normalized_type}",
                    )
        return True, None

    def run(self, params: dict[str, Any]) -> ExecutionResult:
        raise NotImplementedError


class ToolRegistry:
    def __init__(self):
        self._tools: dict[str, Callable[[], ToolRunner]] = {}

    def register(self, name: str, factory: Callable[[], ToolRunner]):
        self._tools[name] = factory

    def make(self, name: str) -> ToolRunner:
        if name not in self._tools:
            msg = f"Tool not found: {name}"
            raise KeyError(msg)
        return self._tools[name]()

    def list(self):
        return list(self._tools.keys())


registry = ToolRegistry()
