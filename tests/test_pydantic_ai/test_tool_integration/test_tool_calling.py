"""Tool calling tests using real Pydantic AI agents."""

from __future__ import annotations

import json

import pytest


class TestPydanticAIToolCalling:
    """Validate live tool invocations via ``TestModel``."""

    @pytest.mark.asyncio
    @pytest.mark.pydantic_ai
    async def test_registered_tools_execute(self, agent_bundle, agent_dependencies):
        result = await agent_bundle.agent.run("Execute tools", deps=agent_dependencies)
        payload = json.loads(result.output)

        assert payload["web_search"]["results"]
        assert payload["calculator"]["total"] >= 0
        assert agent_bundle.state["calls"] == [
            ("web_search", agent_bundle.state["context"]["queries"][0]),
            ("calculator", tuple(agent_bundle.state["context"]["numbers"][0])),
        ]

    @pytest.mark.asyncio
    @pytest.mark.pydantic_ai
    async def test_tool_calls_append_dependency_tracking(
        self, agent_bundle, agent_dependencies
    ):
        await agent_bundle.agent.run("Track deps", deps=agent_dependencies)
        assert len(agent_bundle.state["deps"]) == 2
        assert agent_dependencies.tools[-2:] == ["web_search", "calculator"]

    @pytest.mark.asyncio
    @pytest.mark.pydantic_ai
    async def test_sequential_runs_accumulate_results(
        self, agent_bundle, agent_dependencies
    ):
        await agent_bundle.agent.run("Run 1", deps=agent_dependencies)
        await agent_bundle.agent.run("Run 2", deps=agent_dependencies)
        assert len(agent_bundle.state["context"]["queries"]) == 2
        assert len(agent_bundle.state["context"]["numbers"]) == 2
