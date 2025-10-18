"""Tool execution result validation tests."""

from __future__ import annotations

import json

import pytest


class TestToolExecutionResults:
    """Validate tool outputs are surfaced correctly."""

    @pytest.mark.asyncio
    @pytest.mark.pydantic_ai
    async def test_tool_outputs_propagate(self, agent_bundle, agent_dependencies):
        result = await agent_bundle.agent.run("Gather data", deps=agent_dependencies)
        payload = json.loads(result.output)
        assert payload["web_search"]["source_count"] == 1
        assert payload["calculator"]["count"] >= 1

    @pytest.mark.asyncio
    @pytest.mark.pydantic_ai
    async def test_stateful_output_accumulation(self, agent_bundle, agent_dependencies):
        await agent_bundle.agent.run("First", deps=agent_dependencies)
        await agent_bundle.agent.run("Second", deps=agent_dependencies)

        totals = [
            entry[1]
            for entry in agent_bundle.state["calls"]
            if entry[0] == "calculator"
        ]
        assert len(totals) == 2
