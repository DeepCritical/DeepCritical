"""Dependency injection behaviour tests."""

from __future__ import annotations

import pytest


class TestDependencyInjection:
    """Verify dependencies flow through agent executions."""

    @pytest.mark.asyncio
    @pytest.mark.pydantic_ai
    async def test_dependencies_passed_to_tools(self, agent_bundle, agent_dependencies):
        agent = agent_bundle.agent
        state = agent_bundle.state

        result = await agent.run("Collect insights", deps=agent_dependencies)

        assert result.output
        assert all(dep is agent_dependencies for dep in state["deps"])
        assert agent_dependencies.tools.count("web_search") >= 1
        assert agent_dependencies.tools.count("calculator") >= 1

    @pytest.mark.asyncio
    @pytest.mark.pydantic_ai
    async def test_dependency_configuration_persists(
        self, agent_bundle, agent_dependencies
    ):
        agent_dependencies.config["timeout"] = 45
        await agent_bundle.agent.run("Check timeout", deps=agent_dependencies)

        observed_timeouts = {
            dep.config["timeout"] for dep in agent_bundle.state["deps"]
        }
        assert observed_timeouts == {45}
