"""Agent communication tests."""

from __future__ import annotations

from typing import Any, TypedDict

import pytest

from tests.utils.mocks.mock_agents import (
    MockEvaluatorAgent,
    MockExecutorAgent,
    MockPlannerAgent,
)


class SharedState(TypedDict):
    """Shared state exchanged between mock agents."""

    query: str
    history: list[dict[str, Any]]


class TestAgentCommunication:
    """Validate information exchange between agents."""

    @pytest.mark.asyncio
    @pytest.mark.pydantic_ai
    async def test_information_flow(self):
        planner = MockPlannerAgent()
        executor = MockExecutorAgent()
        evaluator = MockEvaluatorAgent()

        query = "Map protein folding techniques"
        plan = await planner.plan(query)
        result = await executor.execute(plan)
        evaluation = await evaluator.evaluate(result, query)

        assert "steps" in plan
        assert result["success"] is True
        assert evaluation["score"] > 0

    @pytest.mark.asyncio
    @pytest.mark.pydantic_ai
    async def test_shared_state_updates(self):
        planner = MockPlannerAgent()
        executor = MockExecutorAgent()
        evaluator = MockEvaluatorAgent()

        shared_state: SharedState = {
            "query": "Analyze gene expression",
            "history": [],
        }

        plan = await planner.plan(shared_state["query"], shared_state)
        shared_state["history"].append(plan)
        result = await executor.execute(plan, shared_state)
        shared_state["history"].append(result)
        evaluation = await evaluator.evaluate(
            result, shared_state["query"], shared_state
        )
        shared_state["history"].append(evaluation)

        assert len(shared_state["history"]) == 3
        assert shared_state["history"][0]["plan"].startswith("Plan for")
