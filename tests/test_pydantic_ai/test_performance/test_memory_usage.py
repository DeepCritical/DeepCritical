"""Memory usage monitoring tests."""

from __future__ import annotations

import tracemalloc

import pytest


class TestMemoryUsage:
    """Validate agent executions do not leak excessive memory."""

    @pytest.mark.asyncio
    @pytest.mark.pydantic_ai
    async def test_memory_delta_under_limit(self, agent_bundle, agent_dependencies):
        tracemalloc.start()
        snapshot_before = tracemalloc.take_snapshot()
        await agent_bundle.agent.run("Memory check", deps=agent_dependencies)
        snapshot_after = tracemalloc.take_snapshot()
        tracemalloc.stop()

        stats = snapshot_after.compare_to(snapshot_before, "lineno")
        allocated = sum(stat.size_diff for stat in stats)
        assert allocated < 1_000_000, (
            f"Excessive memory allocation detected: {allocated} bytes"
        )
