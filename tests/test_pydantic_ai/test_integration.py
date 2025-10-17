"""High-level Pydantic AI integration tests."""

from __future__ import annotations

import json

import pytest

from DeepResearch.src.datatypes.agents import AgentDependencies
from pydantic_ai import RunContext


@pytest.mark.asyncio
@pytest.mark.pydantic_ai
async def test_end_to_end_agent_run(agent_bundle, agent_dependencies):
    """End-to-end validation of agent workflow and outputs."""

    result = await agent_bundle.agent.run("Full integration", deps=agent_dependencies)
    payload = json.loads(result.output)

    assert isinstance(payload["web_search"]["query"], str)
    assert payload["web_search"]["query"]
    assert "total" in payload["calculator"]
    assert agent_bundle.state["calls"]


@pytest.mark.asyncio
@pytest.mark.pydantic_ai
async def test_custom_agent_configuration(make_test_agent):
    """Validate that custom tool combinations can be executed."""

    def register_formatter(agent, state):
        @agent.tool
        async def formatter(
            ctx: RunContext[AgentDependencies], values: list[int]
        ) -> dict[str, int]:
            state.setdefault("formatter_calls", 0)
            state["formatter_calls"] += 1
            return {"max": max(values), "min": min(values)}

    bundle = make_test_agent(["formatter"], overrides={"formatter": register_formatter})
    result = await bundle.agent.run("Format", deps=AgentDependencies())
    payload = json.loads(result.output)

    assert payload["formatter"]["max"] >= payload["formatter"]["min"]
    assert bundle.state["formatter_calls"] == 1
