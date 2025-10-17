"""Tool error handling tests."""

from __future__ import annotations

import pytest

from DeepResearch.src.datatypes.agents import AgentDependencies
from pydantic_ai import RunContext


class TestToolErrorHandling:
    """Verify agents surface tool failures cleanly."""

    @pytest.mark.asyncio
    @pytest.mark.pydantic_ai
    async def test_tool_exception_bubbles_up(self, make_test_agent):
        def register_unstable(agent, state):
            @agent.tool
            async def unstable(
                ctx: RunContext[AgentDependencies], trigger: bool
            ) -> dict[str, str]:
                state.setdefault("unstable_calls", 0)
                state["unstable_calls"] += 1
                raise RuntimeError("Simulated failure")

        bundle = make_test_agent(["unstable"], overrides={"unstable": register_unstable})

        with pytest.raises(RuntimeError):
            await bundle.agent.run("Trigger failure", deps=AgentDependencies())
        assert bundle.state["unstable_calls"] == 1

    @pytest.mark.asyncio
    @pytest.mark.pydantic_ai
    async def test_recovery_on_subsequent_run(self, make_test_agent):
        toggle = {"fail": True}

        def register_resilient(agent, state):
            @agent.tool
            async def resilient(
                ctx: RunContext[AgentDependencies], trigger: bool
            ) -> dict[str, str]:
                state.setdefault("resilient_calls", 0)
                state["resilient_calls"] += 1
                if toggle["fail"]:
                    toggle["fail"] = False
                    raise RuntimeError("First attempt fails")
                return {"status": "recovered"}

        bundle = make_test_agent(["resilient"], overrides={"resilient": register_resilient})

        with pytest.raises(RuntimeError):
            await bundle.agent.run("Attempt", deps=AgentDependencies())

        result = await bundle.agent.run("Retry", deps=AgentDependencies())
        assert "recovered" in result.output
        assert bundle.state["resilient_calls"] == 2
