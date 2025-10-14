from __future__ import annotations

from dataclasses import dataclass

from .base import ExecutionResult, ToolRunner, ToolSpec, registry

# Lightweight workflow tools mirroring the JS example tools with placeholder logic


@dataclass
class RewriteTool(ToolRunner):
    def __init__(self):
        super().__init__(
            ToolSpec(
                name="rewrite",
                description="Rewrite a raw question into an optimized search query (placeholder).",
                inputs={"query": "TEXT"},
                outputs={"queries": "TEXT"},
            )
        )

    def run(self, params: dict[str, str]) -> ExecutionResult:
        ok, err = self.validate(params)
        if not ok:
            return ExecutionResult(success=False, error=err)
        q = params.get("query", "").strip()
        if not q:
            return ExecutionResult(success=False, error="Empty query")
        # Very naive rewrite
        return ExecutionResult(success=True, data={"queries": f"{q} best sources"})


@dataclass
class WebSearchTool(ToolRunner):
    def __init__(self):
        super().__init__(
            ToolSpec(
                name="web_search",
                description="Perform a web search and return synthetic snippets (placeholder).",
                inputs={"query": "TEXT"},
                outputs={"results": "TEXT"},
            )
        )

    def run(self, params: dict[str, str]) -> ExecutionResult:
        ok, err = self.validate(params)
        if not ok:
            return ExecutionResult(success=False, error=err)
        q = params.get("query", "").strip()
        if not q:
            return ExecutionResult(success=False, error="Empty query")
        # Return a deterministic synthetic result
        return ExecutionResult(
            success=True,
            data={
                "results": f"Top 3 snippets for: {q}. [1] Snippet A. [2] Snippet B. [3] Snippet C."
            },
        )


@dataclass
class ReadTool(ToolRunner):
    def __init__(self):
        super().__init__(
            ToolSpec(
                name="read",
                description="Read a URL and return text content (placeholder).",
                inputs={"url": "TEXT"},
                outputs={"content": "TEXT"},
            )
        )

    def run(self, params: dict[str, str]) -> ExecutionResult:
        ok, err = self.validate(params)
        if not ok:
            return ExecutionResult(success=False, error=err)
        url = params.get("url", "").strip()
        if not url:
            return ExecutionResult(success=False, error="Empty url")
        return ExecutionResult(success=True, data={"content": f"<content from {url}>"})


@dataclass
class FinalizeTool(ToolRunner):
    def __init__(self):
        super().__init__(
            ToolSpec(
                name="finalize",
                description="Polish a draft answer into a final version (placeholder).",
                inputs={"draft": "TEXT"},
                outputs={"final": "TEXT"},
            )
        )

    def run(self, params: dict[str, str]) -> ExecutionResult:
        ok, err = self.validate(params)
        if not ok:
            return ExecutionResult(success=False, error=err)
        draft = params.get("draft", "").strip()
        if not draft:
            return ExecutionResult(success=False, error="Empty draft")
        final = draft.replace("  ", " ").strip()
        return ExecutionResult(success=True, data={"final": final})


@dataclass
class ReferencesTool(ToolRunner):
    def __init__(self):
        super().__init__(
            ToolSpec(
                name="references",
                description="Attach simple reference markers to an answer using provided web text (placeholder).",
                inputs={"answer": "TEXT", "web": "TEXT"},
                outputs={"answer_with_refs": "TEXT"},
            )
        )

    def run(self, params: dict[str, str]) -> ExecutionResult:
        ok, err = self.validate(params)
        if not ok:
            return ExecutionResult(success=False, error=err)
        ans = params.get("answer", "").strip()
        web = params.get("web", "").strip()
        if not ans:
            return ExecutionResult(success=False, error="Empty answer")
        suffix = " [^1]" if web else ""
        return ExecutionResult(success=True, data={"answer_with_refs": ans + suffix})


@dataclass
class EvaluatorTool(ToolRunner):
    def __init__(self):
        super().__init__(
            ToolSpec(
                name="evaluator",
                description="Evaluate an answer for definitiveness (placeholder).",
                inputs={"question": "TEXT", "answer": "TEXT"},
                outputs={"pass": "TEXT", "feedback": "TEXT"},
            )
        )

    def run(self, params: dict[str, str]) -> ExecutionResult:
        ok, err = self.validate(params)
        if not ok:
            return ExecutionResult(success=False, error=err)
        answer = params.get("answer", "")
        is_definitive = all(
            x not in answer.lower() for x in ["i don't know", "not sure", "unable"]
        )
        return ExecutionResult(
            success=True,
            data={
                "pass": "true" if is_definitive else "false",
                "feedback": (
                    "Looks clear." if is_definitive else "Avoid uncertainty language."
                ),
            },
        )


@dataclass
class ErrorAnalyzerTool(ToolRunner):
    def __init__(self):
        super().__init__(
            ToolSpec(
                name="error_analyzer",
                description="Analyze a sequence of steps and suggest improvements (placeholder).",
                inputs={"steps": "TEXT"},
                outputs={"recap": "TEXT", "blame": "TEXT", "improvement": "TEXT"},
            )
        )

    def run(self, params: dict[str, str]) -> ExecutionResult:
        ok, err = self.validate(params)
        if not ok:
            return ExecutionResult(success=False, error=err)
        steps = params.get("steps", "").strip()
        if not steps:
            return ExecutionResult(success=False, error="Empty steps")
        return ExecutionResult(
            success=True,
            data={
                "recap": "Reviewed steps.",
                "blame": "Repetitive search pattern.",
                "improvement": "Diversify queries and visit authoritative sources.",
            },
        )


@dataclass
class ReducerTool(ToolRunner):
    def __init__(self):
        super().__init__(
            ToolSpec(
                name="reducer",
                description="Merge multiple candidate answers into a coherent article (placeholder).",
                inputs={"answers": "TEXT"},
                outputs={"reduced": "TEXT"},
            )
        )

    def run(self, params: dict[str, str]) -> ExecutionResult:
        ok, err = self.validate(params)
        if not ok:
            return ExecutionResult(success=False, error=err)
        answers = params.get("answers", "").strip()
        if not answers:
            return ExecutionResult(success=False, error="Empty answers")
        # Simple merge: collapse duplicate whitespace and join
        reduced = " ".join(
            part.strip() for part in answers.split("\n\n") if part.strip()
        )
        return ExecutionResult(success=True, data={"reduced": reduced})


# Register all tools
registry.register("rewrite", RewriteTool)


@dataclass
class WorkflowTool(ToolRunner):
    """Tool for managing workflow execution."""

    def __init__(self):
        super().__init__(
            ToolSpec(
                name="workflow",
                description="Execute workflow operations",
                inputs={"workflow": "TEXT", "parameters": "TEXT"},
                outputs={"result": "TEXT"},
            )
        )

    def run(self, params: dict[str, str]) -> ExecutionResult:
        workflow = params.get("workflow", "")
        parameters = params.get("parameters", "")
        return ExecutionResult(
            success=True,
            data={
                "result": f"Workflow '{workflow}' executed with parameters: {parameters}"
            },
            metrics={"steps": 3},
        )


@dataclass
class WorkflowStepTool(ToolRunner):
    """Tool for executing individual workflow steps."""

    def __init__(self):
        super().__init__(
            ToolSpec(
                name="workflow_step",
                description="Execute a single workflow step",
                inputs={"step": "TEXT", "context": "TEXT"},
                outputs={"result": "TEXT"},
            )
        )

    def run(self, params: dict[str, str]) -> ExecutionResult:
        step = params.get("step", "")
        context = params.get("context", "")
        return ExecutionResult(
            success=True,
            data={"result": f"Step '{step}' completed with context: {context}"},
            metrics={"duration": 1.2},
        )


registry.register("web_search", WebSearchTool)
registry.register("read", ReadTool)
registry.register("finalize", FinalizeTool)
registry.register("references", ReferencesTool)
registry.register("evaluator", EvaluatorTool)
registry.register("error_analyzer", ErrorAnalyzerTool)
registry.register("reducer", ReducerTool)
registry.register("workflow", WorkflowTool)
registry.register("workflow_step", WorkflowStepTool)
