"""Error recovery performance tests."""

from __future__ import annotations

import pytest

from DeepResearch.src.datatypes.agents import AgentDependencies
from pydantic_ai import RunContext


class TestErrorRecovery:
    """Ensure agents can recover from transient failures."""

    @pytest.mark.asyncio
    @pytest.mark.pydantic_ai
    async def test_retry_success_after_failure(self, make_test_agent):
        execution_counts = {"invocations": 0}

        def register_flaky(agent, state):
            @agent.tool
            async def flaky(
                ctx: RunContext[AgentDependencies], attempt: int
            ) -> dict[str, str]:
                state.setdefault("failures", 0)
                execution_counts["invocations"] += 1
                if execution_counts["invocations"] == 1:
                    state["failures"] += 1
                    raise RuntimeError("Flaky tool failure")
                return {"status": "stable", "attempt": attempt}

        bundle = make_test_agent(["flaky"], overrides={"flaky": register_flaky})

        with pytest.raises(RuntimeError):
            await bundle.agent.run("Initial", deps=AgentDependencies())

        result = await bundle.agent.run("Second", deps=AgentDependencies())
        assert "stable" in result.output
        assert execution_counts["invocations"] == 2
        assert bundle.state["failures"] == 1
