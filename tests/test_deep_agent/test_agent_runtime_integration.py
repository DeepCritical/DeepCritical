from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from pydantic_ai.models.test import TestModel

from DeepResearch.src.agents.deep_agent_implementations import (
    AgentConfig,
    PlanningAgent,
)
from DeepResearch.src.datatypes.deep_agent_runtime import DeepAgentDeps
from DeepResearch.src.datatypes.deep_agent_state import DeepAgentState
from DeepResearch.src.datatypes.deep_agent_types import AgentCapability
from DeepResearch.src.prompts.deep_agent_graph import AgentBuilder, AgentBuilderConfig
from DeepResearch.src.tools.deep_agent_middleware import (
    FilesystemMiddleware,
    PlanningMiddleware,
    SubAgentMiddleware,
    create_default_middleware_pipeline,
)


class _FakeAgent:
    pass


def test_deep_agent_wrapper_uses_runtime_deps(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test")

    planning_agent = PlanningAgent(
        AgentConfig(
            name="planning-agent",
            model_name=TestModel(),
            system_prompt=(
                "You are a planning specialist focused on breaking down complex "
                "tasks into manageable steps."
            ),
            tools=["write_todos"],
            capabilities=[AgentCapability.PLANNING],
        )
    )

    assert planning_agent.agent is not None
    assert set(planning_agent.agent._function_toolset.tools) == {"write_todos"}
    assert planning_agent.agent._deps_type is DeepAgentDeps


@pytest.mark.asyncio
async def test_deep_agent_wrapper_executes_state_backed_tool() -> None:
    state = DeepAgentState(session_id="agent-execute")
    planning_agent = PlanningAgent(
        AgentConfig(
            name="planning-agent",
            model_name=TestModel(),
            tools=["write_todos"],
            retry_attempts=0,
        )
    )

    result = await planning_agent.execute("Create one todo", state)

    assert result.success
    assert result.error is None
    assert isinstance(result.result, dict)
    assert "write_todos" in result.result["output"]
    assert len(state.todos) == 1
    assert state.todos[0].content


def test_deep_agent_wrapper_rejects_unknown_tools() -> None:
    config = AgentConfig(name="invalid-agent", tools=["missing_tool"])

    with pytest.raises(ValueError, match="missing_tool"):
        PlanningAgent(config)


def test_agent_builder_accepts_model_instances() -> None:
    agent = AgentBuilder(
        AgentBuilderConfig(model_name=TestModel(), tools=["write_todos"])
    ).build_agent()

    assert set(agent._function_toolset.tools) == {"write_todos"}
    assert agent._deps_type is DeepAgentDeps


def test_agent_builder_rejects_unknown_tools() -> None:
    builder = AgentBuilder(AgentBuilderConfig(tools=["missing_tool"]))

    with pytest.raises(ValueError, match="missing_tool"):
        builder.build_agent()


@pytest.mark.asyncio
async def test_middleware_accepts_raw_deep_agent_state() -> None:
    state = DeepAgentState(session_id="middleware")

    planning_result = await PlanningMiddleware().process(_FakeAgent(), state)
    filesystem_result = await FilesystemMiddleware().process(_FakeAgent(), state)

    assert planning_result.success
    assert filesystem_result.success


@pytest.mark.asyncio
async def test_default_middleware_pipeline_accepts_raw_deep_agent_state() -> None:
    state = DeepAgentState(session_id="default-pipeline")
    pipeline = create_default_middleware_pipeline()

    results = await pipeline.process(_FakeAgent(), state)

    assert results
    assert all(result.success for result in results)
    assert "subagent_registry" in state.shared_state


@pytest.mark.asyncio
async def test_subagent_middleware_exposes_registry_to_state() -> None:
    state = DeepAgentState(session_id="subagent-middleware")
    middleware = SubAgentMiddleware()
    subagent = MagicMock()
    subagent.run = AsyncMock(return_value=SimpleNamespace(output={"ok": True}))
    middleware._agent_registry["research"] = subagent

    result = await middleware.process(_FakeAgent(), state)

    assert result.success
    assert state.shared_state["subagent_registry"]["research"] is subagent
