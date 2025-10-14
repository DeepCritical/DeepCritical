from __future__ import annotations

from dataclasses import dataclass

from .base import ExecutionResult, ToolRunner, ToolSpec, registry


@dataclass
class SearchTool(ToolRunner):
    def __init__(self):
        super().__init__(
            ToolSpec(
                name="search",
                description="Retrieve snippets for a query (placeholder).",
                inputs={"query": "TEXT"},
                outputs={"snippets": "TEXT"},
            )
        )

    def run(self, params: dict[str, str]) -> ExecutionResult:
        ok, err = self.validate(params)
        if not ok:
            return ExecutionResult(success=False, error=err)
        q = params["query"].strip()
        if not q:
            return ExecutionResult(success=False, error="Empty query")
        return ExecutionResult(
            success=True, data={"snippets": f"Results for: {q}"}, metrics={"hits": 3}
        )


@dataclass
class SummarizeTool(ToolRunner):
    def __init__(self):
        super().__init__(
            ToolSpec(
                name="summarize",
                description="Summarize provided snippets (placeholder).",
                inputs={"snippets": "TEXT"},
                outputs={"summary": "TEXT"},
            )
        )

    def run(self, params: dict[str, str]) -> ExecutionResult:
        ok, err = self.validate(params)
        if not ok:
            return ExecutionResult(success=False, error=err)
        s = params["snippets"].strip()
        if not s:
            return ExecutionResult(success=False, error="Empty snippets")
        return ExecutionResult(success=True, data={"summary": f"Summary: {s[:60]}..."})


@dataclass
class MockTool(ToolRunner):
    """Base mock tool for testing purposes."""

    def __init__(self, name: str = "mock", description: str = "Mock tool for testing"):
        super().__init__(
            ToolSpec(
                name=name,
                description=description,
                inputs={"input": "TEXT"},
                outputs={"output": "TEXT"},
            )
        )

    def run(self, params: dict[str, str]) -> ExecutionResult:
        return ExecutionResult(
            success=True, data={"output": f"Mock result for: {params.get('input', '')}"}
        )


@dataclass
class MockWebSearchTool(ToolRunner):
    """Mock web search tool for testing."""

    def __init__(self):
        super().__init__(
            ToolSpec(
                name="mock_web_search",
                description="Mock web search tool for testing",
                inputs={"query": "TEXT"},
                outputs={"results": "TEXT"},
            )
        )

    def run(self, params: dict[str, str]) -> ExecutionResult:
        query = params.get("query", "")
        return ExecutionResult(
            success=True,
            data={"results": f"Mock search results for: {query}"},
            metrics={"hits": 5},
        )


@dataclass
class MockBioinformaticsTool(ToolRunner):
    """Mock bioinformatics tool for testing."""

    def __init__(self):
        super().__init__(
            ToolSpec(
                name="mock_bioinformatics",
                description="Mock bioinformatics tool for testing",
                inputs={"sequence": "TEXT"},
                outputs={"analysis": "TEXT"},
            )
        )

    def run(self, params: dict[str, str]) -> ExecutionResult:
        sequence = params.get("sequence", "")
        return ExecutionResult(
            success=True,
            data={"analysis": f"Mock bioinformatics analysis for: {sequence[:50]}..."},
            metrics={"length": len(sequence)},
        )


registry.register("search", SearchTool)
registry.register("summarize", SummarizeTool)
registry.register("mock", MockTool)
registry.register("mock_web_search", MockWebSearchTool)
registry.register("mock_bioinformatics", MockBioinformaticsTool)
