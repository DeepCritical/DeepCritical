"""Single agent workflow tests."""

from __future__ import annotations

import json

import pytest


class TestSingleAgentWorkflow:
    """Validate that a single agent completes a full run."""

    @pytest.mark.asyncio
    @pytest.mark.pydantic_ai
    async def test_single_agent_completion(self, agent_bundle, agent_dependencies):
        result = await agent_bundle.agent.run("Run analysis", deps=agent_dependencies)
        payload = json.loads(result.output)

        assert payload["web_search"]["results"]
        assert payload["calculator"]["total"] >= 0
        assert agent_bundle.state["calls"]
        assert agent_dependencies.tools[-2:] == ["web_search", "calculator"]

    @pytest.mark.asyncio
    @pytest.mark.pydantic_ai
    async def test_multiple_runs_accumulate_history(
        self, agent_bundle, agent_dependencies
    ):
        await agent_bundle.agent.run("First run", deps=agent_dependencies)
        await agent_bundle.agent.run("Second run", deps=agent_dependencies)

        assert len(agent_bundle.state["calls"]) == 4
        assert agent_bundle.state["context"]["queries"]
