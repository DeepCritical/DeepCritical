from __future__ import annotations

import importlib
import inspect
from typing import Any

from DeepResearch.src.datatypes.tool_specs import ToolCategory, ToolSpec

# Import core tool types from datatypes
from DeepResearch.src.datatypes.tools import ExecutionResult, MockToolRunner, ToolRunner


class ToolRegistry:
    """Registry for managing and executing tools in the PRIME ecosystem."""

    def __init__(self):
        self.tools: dict[str, ToolSpec] = {}
        self.runners: dict[str, ToolRunner] = {}
        self.mock_mode = True  # Default to mock mode for development

    def register_tool(
        self, tool_spec: ToolSpec, runner_class: type[ToolRunner] | None = None
    ) -> None:
        """Register a tool with its specification and runner."""
        self.tools[tool_spec.name] = tool_spec

        if runner_class:
            self.runners[tool_spec.name] = runner_class(tool_spec)
        elif self.mock_mode:
            self.runners[tool_spec.name] = MockToolRunner(tool_spec)

    def get_tool_spec(self, tool_name: str) -> ToolSpec | None:
        """Get tool specification by name."""
        return self.tools.get(tool_name)

    def list_tools(self) -> list[str]:
        """List all registered tool names."""
        return list(self.tools.keys())

    def list_tools_by_category(self, category: ToolCategory) -> list[str]:
        """List tools by category."""
        return [name for name, spec in self.tools.items() if spec.category == category]

    def execute_tool(
        self, tool_name: str, parameters: dict[str, Any]
    ) -> ExecutionResult:
        """Execute a tool with given parameters."""
        if tool_name not in self.tools:
            return ExecutionResult(success=False, error=f"Tool not found: {tool_name}")

        if tool_name not in self.runners:
            return ExecutionResult(
                success=False, error=f"No runner registered for tool: {tool_name}"
            )

        runner = self.runners[tool_name]
        return runner.run(parameters)

    def validate_tool_execution(
        self, tool_name: str, parameters: dict[str, Any]
    ) -> ExecutionResult:
        """Validate tool execution without running it."""
        if tool_name not in self.tools:
            return ExecutionResult(success=False, error=f"Tool not found: {tool_name}")

        if tool_name not in self.runners:
            return ExecutionResult(
                success=False, error=f"No runner registered for tool: {tool_name}"
            )

        runner = self.runners[tool_name]
        return runner.validate_inputs(parameters)

    def get_tool_dependencies(self, tool_name: str) -> list[str]:
        """Get dependencies for a tool."""
        if tool_name not in self.tools:
            return []

        return self.tools[tool_name].dependencies

    def check_dependency_availability(self, tool_name: str) -> dict[str, bool]:
        """Check if all dependencies for a tool are available."""
        dependencies = self.get_tool_dependencies(tool_name)
        availability = {}

        for dep in dependencies:
            availability[dep] = dep in self.tools

        return availability

    def enable_mock_mode(self) -> None:
        """Enable mock mode for all tools."""
        self.mock_mode = True
        # Re-register all tools with mock runners
        for tool_name, tool_spec in self.tools.items():
            if tool_name not in self.runners:
                self.runners[tool_name] = MockToolRunner(tool_spec)

    def disable_mock_mode(self) -> None:
        """Disable mock mode (requires real runners to be registered)."""
        self.mock_mode = False

    def load_tools_from_module(self, module_name: str) -> None:
        """Load tool specifications and runners from a Python module."""
        try:
            module = importlib.import_module(module_name)

            # Look for tool specifications
            for _name, obj in inspect.getmembers(module):
                if isinstance(obj, ToolSpec):
                    self.register_tool(obj)

            # Look for tool runner classes
            for _name, obj in inspect.getmembers(module):
                if (
                    inspect.isclass(obj)
                    and issubclass(obj, ToolRunner)
                    and obj != ToolRunner
                ):
                    # Find corresponding tool spec
                    tool_name = getattr(obj, "tool_name", None)
                    if tool_name and tool_name in self.tools:
                        self.register_tool(self.tools[tool_name], obj)

        except ImportError:
            pass

    def get_registry_summary(self) -> dict[str, Any]:
        """Get a summary of the tool registry."""
        categories = {}
        for tool_name, tool_spec in self.tools.items():
            category = tool_spec.category.value
            if category not in categories:
                categories[category] = []
            categories[category].append(tool_name)

        return {
            "total_tools": len(self.tools),
            "tools_with_runners": len(self.runners),
            "mock_mode": self.mock_mode,
            "categories": categories,
            "available_tools": list(self.tools.keys()),
        }


# Global registry instance
registry = ToolRegistry()
