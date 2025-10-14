"""
Mock agent implementations for testing.
"""

from typing import Any


class MockPlannerAgent:
    """Mock planner agent for testing."""

    async def plan(
        self, query: str, state: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """Mock planning functionality."""
        return {
            "plan": f"Plan for: {query}",
            "steps": ["step1", "step2", "step3"],
            "tools": ["tool1", "tool2"],
        }


class MockExecutorAgent:
    """Mock executor agent for testing."""

    async def execute(
        self, plan: dict[str, Any], state: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """Mock execution functionality."""
        return {
            "result": f"Executed plan: {plan.get('plan', 'unknown')}",
            "outputs": ["output1", "output2"],
            "success": True,
        }


class MockEvaluatorAgent:
    """Mock evaluator agent for testing."""

    async def evaluate(
        self, result: dict[str, Any], query: str, state: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """Mock evaluation functionality."""
        return {
            "evaluation": f"Evaluated result for query: {query}",
            "score": 0.85,
            "feedback": "Good quality result",
        }


class MockSearchAgent:
    """Mock search agent for testing."""

    async def search(self, query: str) -> dict[str, Any]:
        """Mock search functionality."""
        return {
            "results": [f"Result {i} for {query}" for i in range(5)],
            "sources": ["source1", "source2", "source3"],
        }


class MockRAGAgent:
    """Mock RAG agent for testing."""

    async def query(self, question: str, context: str) -> dict[str, Any]:
        """Mock RAG query functionality."""
        return {
            "answer": f"RAG answer for: {question}",
            "sources": ["doc1", "doc2"],
            "confidence": 0.9,
        }
