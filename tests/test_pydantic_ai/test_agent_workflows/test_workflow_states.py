"""Workflow state transition tests."""

from __future__ import annotations

from typing import TypedDict

import pytest

from tests.utils.mocks.mock_agents import (
    MockEvaluatorAgent,
    MockExecutorAgent,
    MockPlannerAgent,
)


class WorkflowState(TypedDict):
    """Structured workflow state used during orchestration."""

    step: int
    log: list[str]


class TestWorkflowStates:
    """Ensure workflow state handling remains consistent."""

    @pytest.mark.asyncio
    @pytest.mark.pydantic_ai
    async def test_state_transition_sequence(self):
        planner = MockPlannerAgent()
        executor = MockExecutorAgent()
        evaluator = MockEvaluatorAgent()

        state: WorkflowState = {"step": 0, "log": []}

        async def orchestrate(query: str) -> dict[str, str]:
            state["step"] = 1
            plan = await planner.plan(query, state)
            state["log"].append("planned")
            state["step"] = 2
            result = await executor.execute(plan, state)
            state["log"].append("executed")
            state["step"] = 3
            evaluation = await evaluator.evaluate(result, query, state)
            state["log"].append("evaluated")
            return {"plan": plan["plan"], "evaluation": evaluation["evaluation"]}

        outcome = await orchestrate("Profile research workflow")
        assert outcome["plan"].startswith("Plan for")
        assert outcome["evaluation"].startswith("Evaluated result")
        assert state["step"] == 3
        assert state["log"] == ["planned", "executed", "evaluated"]
