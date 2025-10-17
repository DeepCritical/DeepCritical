"""Validate base agent construction and configuration."""

from __future__ import annotations

import pytest


class TestAgentInitialization:
    """Ensure agents are configured with expected defaults."""

    @pytest.mark.pydantic_ai
    def test_agent_configuration(self, agent_bundle, agent_dependencies):
        agent = agent_bundle.agent
        deps_cls = type(agent_dependencies)

        assert agent.model is not None, "Agent should have a backing model"
        assert agent.deps_type is deps_cls
        assert agent._function_toolset is not None
        assert set(agent._function_toolset.tools.keys()) == {"web_search", "calculator"}
        assert agent._instructions is not None
        assert agent._system_prompts == ("You are a reliable research copilot.",)

    @pytest.mark.pydantic_ai
    def test_state_tracking_attached(self, agent_bundle):
        agent = agent_bundle.agent
        assert hasattr(agent, "_test_state")
        state = agent._test_state  # type: ignore[attr-defined]
        assert state["calls"] == []
        assert state["context"] == {"queries": [], "numbers": [], "combined": []}
