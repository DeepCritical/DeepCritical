"""Validate base agent construction and configuration."""

from __future__ import annotations

import pytest

from DeepResearch.src.datatypes.agents import AgentDependencies


class TestAgentInitialization:
    """Ensure agents are configured with expected defaults."""

    @pytest.mark.pydantic_ai
    def test_agent_configuration(self, agent_bundle):
        agent = agent_bundle.agent

        assert agent.model is not None, "Agent should have a backing model"
        assert agent.deps_type is AgentDependencies
        assert agent._function_toolset is not None  # noqa: SLF001
        assert set(agent._function_toolset.tools.keys()) == {"web_search", "calculator"}  # noqa: SLF001
        assert agent._instructions is not None  # noqa: SLF001
        assert agent._system_prompts == ("You are a reliable research copilot.",)  # noqa: SLF001

    @pytest.mark.pydantic_ai
    def test_state_tracking_attached(self, agent_bundle):
        agent = agent_bundle.agent
        assert hasattr(agent, "_test_state")  # noqa: SLF001
        state = agent._test_state  # type: ignore[attr-defined]  # noqa: SLF001
        assert state["calls"] == []
        assert state["context"] == {"queries": [], "numbers": [], "combined": []}
