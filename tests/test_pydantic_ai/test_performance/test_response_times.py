"""Agent response time monitoring."""

from __future__ import annotations

import time

import pytest


class TestResponseTimes:
    """Ensure agent executions complete promptly."""

    @pytest.mark.asyncio
    @pytest.mark.pydantic_ai
    async def test_response_time_under_threshold(
        self, agent_bundle, agent_dependencies
    ):
        start = time.perf_counter()
        await agent_bundle.agent.run("Measure latency", deps=agent_dependencies)
        duration = time.perf_counter() - start
        assert duration < 0.5, f"Agent response exceeded threshold: {duration:.3f}s"
