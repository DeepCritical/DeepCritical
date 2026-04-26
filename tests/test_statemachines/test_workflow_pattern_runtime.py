import pytest

from DeepResearch.src.datatypes.agents import AgentType
from DeepResearch.src.datatypes.workflow_patterns import (
    InteractionPattern,
    create_interaction_state,
)
from DeepResearch.src.statemachines.workflow_pattern_statemachines import (
    InitializePattern,
    WorkflowPatternState,
    create_collaborative_pattern_graph,
    create_hierarchical_pattern_graph,
    create_pattern_graph,
    create_sequential_pattern_graph,
    run_collaborative_pattern_workflow,
    run_hierarchical_pattern_workflow,
    run_sequential_pattern_workflow,
)
from DeepResearch.src.utils.workflow_patterns import InteractionMetrics


def test_interaction_state_defaults_agent_types_when_not_provided():
    state = create_interaction_state(
        pattern=InteractionPattern.COLLABORATIVE,
        agents=["agent_a", "agent_b"],
    )

    assert state.agents == {
        "agent_a": AgentType.EXECUTOR,
        "agent_b": AgentType.EXECUTOR,
    }


def test_supported_pattern_graphs_construct_without_patching():
    assert type(create_collaborative_pattern_graph()).__name__ == "Graph"
    assert type(create_sequential_pattern_graph()).__name__ == "Graph"
    assert type(create_hierarchical_pattern_graph()).__name__ == "Graph"


def test_unsupported_pattern_graph_fails_explicitly():
    with pytest.raises(ValueError, match="Unsupported workflow pattern"):
        create_pattern_graph(InteractionPattern.PEER_TO_PEER)


@pytest.mark.asyncio
async def test_collaborative_runtime_reaches_consensus_with_sync_one_arg_executors():
    result = await run_collaborative_pattern_workflow(
        question="Should we proceed?",
        agents=["agent_a", "agent_b"],
        agent_types={
            "agent_a": AgentType.EXECUTOR,
            "agent_b": AgentType.EXECUTOR,
        },
        agent_executors={
            "agent_a": lambda messages: {"answer": "yes"},
            "agent_b": lambda messages: {"answer": "yes"},
        },
    )

    assert "Collaborative Pattern Results" in result
    assert "Status: success" in result
    assert "Consensus Reached: True" in result


@pytest.mark.asyncio
async def test_collaborative_runtime_reports_non_consensus():
    result = await run_collaborative_pattern_workflow(
        question="Should we proceed?",
        agents=["agent_a", "agent_b"],
        agent_types={
            "agent_a": AgentType.EXECUTOR,
            "agent_b": AgentType.EXECUTOR,
        },
        agent_executors={
            "agent_a": lambda messages: {"answer": "yes"},
            "agent_b": lambda messages: {"answer": "no"},
        },
    )

    assert "Workflow Pattern Execution Failed" in result
    assert "Consensus was not reached" in result


@pytest.mark.asyncio
async def test_collaborative_runtime_fails_when_agent_executor_is_missing():
    result = await run_collaborative_pattern_workflow(
        question="Should we proceed?",
        agents=["agent_a", "agent_b"],
        agent_types={
            "agent_a": AgentType.EXECUTOR,
            "agent_b": AgentType.EXECUTOR,
        },
        agent_executors={
            "agent_a": lambda messages: {"answer": "yes"},
        },
    )

    assert "Workflow Pattern Execution Failed" in result
    assert "No executor for agent agent_b" in result
    assert result.count("No executor for agent agent_b") == 1


@pytest.mark.asyncio
async def test_graph_runtime_preserves_metrics_object_and_records_summary():
    state = WorkflowPatternState(
        question="Should we proceed?",
        interaction_pattern=InteractionPattern.COLLABORATIVE,
        agent_ids=["agent_a", "agent_b"],
        agent_types={
            "agent_a": AgentType.EXECUTOR,
            "agent_b": AgentType.EXECUTOR,
        },
        agent_executors={
            "agent_a": lambda messages: {"answer": "yes"},
            "agent_b": lambda messages: {"answer": "yes"},
        },
    )

    result = await create_collaborative_pattern_graph().run(
        InitializePattern(), state=state
    )

    assert "Status: success" in result.output
    assert isinstance(state.metrics, InteractionMetrics)
    assert state.interaction_summary["execution_status"] == "success"


@pytest.mark.asyncio
async def test_sequential_runtime_passes_previous_result_to_next_agent():
    seen_by_second = {}

    async def first_agent(messages, _state):
        assert messages[0].content == {"question": "build a plan"}
        return {"answer": "first result"}

    async def second_agent(messages, _state):
        seen_by_second["messages"] = messages
        return {"answer": "second result"}

    result = await run_sequential_pattern_workflow(
        question="build a plan",
        agents=["first", "second"],
        agent_types={
            "first": AgentType.EXECUTOR,
            "second": AgentType.EXECUTOR,
        },
        agent_executors={
            "first": first_agent,
            "second": second_agent,
        },
    )

    assert "Sequential Pattern Results" in result
    assert "Status: success" in result
    assert seen_by_second["messages"][0].content == {"answer": "first result"}


@pytest.mark.asyncio
async def test_hierarchical_runtime_runs_coordinator_and_subordinate():
    seen_by_subordinate = {}

    async def coordinator(messages, _state):
        assert messages[0].content == {"question": "coordinate this"}
        return {"answer": "coordinator result"}

    async def subordinate(messages, _state):
        seen_by_subordinate["messages"] = messages
        return {"answer": "subordinate result"}

    result = await run_hierarchical_pattern_workflow(
        question="coordinate this",
        coordinator_id="coordinator",
        subordinate_ids=["subordinate"],
        agent_types={
            "coordinator": AgentType.ORCHESTRATOR,
            "subordinate": AgentType.EXECUTOR,
        },
        agent_executors={
            "coordinator": coordinator,
            "subordinate": subordinate,
        },
    )

    assert "Hierarchical Pattern Results" in result
    assert "Status: success" in result
    assert seen_by_subordinate["messages"][0].content == {
        "answer": "coordinator result"
    }
