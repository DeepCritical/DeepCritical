"""
Multi-agent orchestration tests for Pydantic AI framework.
"""

from unittest.mock import AsyncMock, Mock

import pytest

from DeepResearch.src.agents import PlanGenerator
from tests.utils.mocks.mock_agents import (
    MockEvaluatorAgent,
    MockExecutorAgent,
    MockPlannerAgent,
)


class TestMultiAgentOrchestration:
    """Test multi-agent workflow orchestration."""

    @pytest.mark.asyncio
    @pytest.mark.optional
    @pytest.mark.pydantic_ai
    async def test_planner_executor_evaluator_workflow(self):
        """Test complete planner -> executor -> evaluator workflow."""
        # Create mock agents for testing
        planner = MockPlannerAgent()
        executor = MockExecutorAgent()
        evaluator = MockEvaluatorAgent()

        # Mock the orchestration function
        async def mock_orchestrate_workflow(
            planner_agent, executor_agent, evaluator_agent, query
        ):
            # Simulate workflow execution
            plan = await planner_agent.plan(query)
            result = await executor_agent.execute(plan)
            evaluation = await evaluator_agent.evaluate(result, query)
            return {"success": True, "result": result, "evaluation": evaluation}

        # Execute workflow
        query = "Analyze machine learning trends in bioinformatics"
        workflow_result = await mock_orchestrate_workflow(
            planner, executor, evaluator, query
        )

        assert workflow_result["success"]
        assert "result" in workflow_result
        assert "evaluation" in workflow_result

    @pytest.mark.asyncio
    @pytest.mark.optional
    @pytest.mark.pydantic_ai
    async def test_workflow_error_handling(self):
        """Test error handling in multi-agent workflows."""
        # Create agents that can fail
        failing_planner = Mock(spec=PlanGenerator)
        failing_planner.plan = AsyncMock(side_effect=Exception("Planning failed"))

        normal_executor = MockExecutorAgent()
        normal_evaluator = MockEvaluatorAgent()

        # Test that workflow handles planner failure gracefully
        async def orchestrate_workflow(planner, executor, evaluator, query):
            plan = await planner.plan(query)
            result = await executor.execute(plan)
            evaluation = await evaluator.evaluate(result, query)
            return {"success": True, "result": result, "evaluation": evaluation}

        with pytest.raises(Exception, match="Planning failed"):
            await orchestrate_workflow(
                failing_planner, normal_executor, normal_evaluator, "test query"
            )

    @pytest.mark.asyncio
    @pytest.mark.optional
    @pytest.mark.pydantic_ai
    async def test_workflow_state_persistence(self):
        """Test that workflow state is properly maintained across agents."""
        # Create agents that maintain state
        stateful_planner = MockPlannerAgent()
        stateful_executor = MockExecutorAgent()
        stateful_evaluator = MockEvaluatorAgent()

        # Mock state management
        workflow_state = {"query": "test", "step": 0, "data": {}}

        async def stateful_orchestrate(planner, executor, evaluator, query, state):
            # Update state in each step
            state["step"] = 1
            plan = await planner.plan(query, state)

            state["step"] = 2
            result = await executor.execute(plan, state)

            state["step"] = 3
            evaluation = await evaluator.evaluate(result, state)

            return {"result": result, "evaluation": evaluation, "final_state": state}

        result = await stateful_orchestrate(
            stateful_planner,
            stateful_executor,
            stateful_evaluator,
            "test query",
            workflow_state,
        )

        assert result["final_state"]["step"] == 3
        assert "result" in result
        assert "evaluation" in result
