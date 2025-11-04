"""Tool error handling tests."""

from __future__ import annotations

from typing import Any

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


class TestToolErrorHandling:
    """Verify agents surface tool failures cleanly."""

    @pytest.mark.asyncio
    @pytest.mark.pydantic_ai
    async def test_tool_exception_bubbles_up(
        self, make_test_agent, agent_dependencies
    ) -> None:
        def register_unstable(agent, state: dict[str, Any]):
            @agent.tool
            async def unstable(
                ctx: RunContext[AgentDependencies], trigger: bool
            ) -> dict[str, str]:
                state.setdefault("unstable_calls", 0)
                state["unstable_calls"] += 1
                raise RuntimeError("Simulated failure")

        bundle = make_test_agent(
            ["unstable"], overrides={"unstable": register_unstable}
        )

        deps_cls = type(agent_dependencies)

        with pytest.raises(RuntimeError):
            await bundle.agent.run("Trigger failure", deps=deps_cls())
        assert bundle.state["unstable_calls"] == 1

    @pytest.mark.asyncio
    @pytest.mark.pydantic_ai
    async def test_recovery_on_subsequent_run(
        self, make_test_agent, agent_dependencies
    ) -> None:
        toggle = {"fail": True}

        def register_resilient(agent, state: dict[str, Any]):
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

        bundle = make_test_agent(
            ["resilient"], overrides={"resilient": register_resilient}
        )

        deps_cls = type(agent_dependencies)

        with pytest.raises(RuntimeError):
            await bundle.agent.run("Attempt", deps=deps_cls())

        result = await bundle.agent.run("Retry", deps=deps_cls())
        assert "recovered" in result.output
        assert bundle.state["resilient_calls"] == 2
