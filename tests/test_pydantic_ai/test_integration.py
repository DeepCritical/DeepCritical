"""High-level Pydantic AI integration tests."""

from __future__ import annotations

import json

import pytest

try:
    from DeepResearch.src.datatypes.agents import AgentDependencies
except ImportError as exc:  # pragma: no cover - exercised in missing-deps envs
    pytest.skip(
        f"DeepResearch optional dependencies unavailable: {exc}",
        allow_module_level=True,
    )

try:
    from pydantic_ai import RunContext
except ModuleNotFoundError as exc:  # pragma: no cover - exercised in CI skips
    pytest.skip(
        f"pydantic_ai dependency unavailable: {exc}",
        allow_module_level=True,
    )


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
async def test_custom_agent_configuration(make_test_agent, agent_dependencies):
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
    deps_cls = type(agent_dependencies)
    result = await bundle.agent.run("Format", deps=deps_cls())
    payload = json.loads(result.output)

    assert payload["formatter"]["max"] >= payload["formatter"]["min"]
    assert bundle.state["formatter_calls"] == 1
