"""Concurrent agent execution tests."""

from __future__ import annotations

import asyncio
import json

import pytest

from DeepResearch.src.datatypes.agents import AgentDependencies


class TestConcurrentExecution:
    """Ensure multiple agent runs succeed concurrently."""

    @pytest.mark.asyncio
    @pytest.mark.pydantic_ai
    async def test_parallel_runs(self, make_test_agent):
        bundle = make_test_agent()

        async def _run(idx: int):
            deps = AgentDependencies(
                config={"run": idx},
                tools=[],
                other_agents=["planner"],
                data_sources=["kb"],
            )
            return await bundle.agent.run(f"Concurrent run {idx}", deps=deps)

        results = await asyncio.gather(*[_run(idx) for idx in range(5)])
        totals = [json.loads(result.output)["calculator"]["total"] for result in results]
        assert len(totals) == 5
        assert all(total >= 0 for total in totals)
