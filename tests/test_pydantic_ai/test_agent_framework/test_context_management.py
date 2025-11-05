"""Context propagation tests for agents."""

from __future__ import annotations

import json

import pytest


class TestContextManagement:
    """Ensure state is preserved across tool invocations."""

    @pytest.mark.asyncio
    @pytest.mark.pydantic_ai
    async def test_tool_execution_order(self, agent_bundle, agent_dependencies):
        await agent_bundle.agent.run("Order check", deps=agent_dependencies)
        assert [call[0] for call in agent_bundle.state["calls"]] == [
            "web_search",
            "calculator",
        ]

    @pytest.mark.asyncio
    @pytest.mark.pydantic_ai
    async def test_combined_context_updates(self, agent_bundle, agent_dependencies):
        result = await agent_bundle.agent.run("Combined", deps=agent_dependencies)
        payload = json.loads(result.output)

        assert "web_search" in payload
        assert "calculator" in payload
        assert agent_bundle.state["context"]["combined"], (
            "Combined context not captured"
        )
        last_entry = agent_bundle.state["context"]["combined"][0]
        assert "->" in last_entry
