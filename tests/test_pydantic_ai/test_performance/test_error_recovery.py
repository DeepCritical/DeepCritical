"""Error recovery performance tests."""

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


class TestErrorRecovery:
    """Ensure agents can recover from transient failures."""

    @pytest.mark.asyncio
    @pytest.mark.pydantic_ai
    async def test_retry_success_after_failure(
        self, make_test_agent, agent_dependencies
    ) -> None:
        execution_counts: dict[str, int] = {"invocations": 0}

        def register_flaky(agent, state: dict[str, Any]):
            @agent.tool
            async def flaky(
                ctx: RunContext[AgentDependencies], attempt: int
            ) -> dict[str, int | str]:
                state.setdefault("failures", 0)
                execution_counts["invocations"] += 1
                if execution_counts["invocations"] == 1:
                    state["failures"] += 1
                    raise RuntimeError("Flaky tool failure")
                return {"status": "stable", "attempt": attempt}

        bundle = make_test_agent(["flaky"], overrides={"flaky": register_flaky})

        deps_cls = type(agent_dependencies)

        with pytest.raises(RuntimeError):
            await bundle.agent.run("Initial", deps=deps_cls())

        result = await bundle.agent.run("Second", deps=deps_cls())
        assert "stable" in result.output
        assert execution_counts["invocations"] == 2
        assert bundle.state["failures"] == 1
