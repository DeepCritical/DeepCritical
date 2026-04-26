import json

from DeepResearch.src.tools.workflow_pattern_tools import (
    CollaborativePatternTool,
    HierarchicalPatternTool,
    SequentialPatternTool,
    WorkflowOrchestrationTool,
)


def test_collaborative_pattern_tool_runs_real_runtime_in_development_mode():
    result = CollaborativePatternTool().run(
        {
            "agents": json.dumps(["agent_a", "agent_b"]),
            "input_data": json.dumps({"question": "agree?"}),
            "config": json.dumps({"development_mock": True}),
            "agent_executors": "{}",
        }
    )

    assert result.success is True
    assert result.data["pattern"] == "collaborative"
    assert "Collaborative Pattern Results" in result.data["result"]


def test_sequential_pattern_tool_runs_real_runtime_in_development_mode():
    result = SequentialPatternTool().run(
        {
            "agents": json.dumps(["first", "second"]),
            "input_data": json.dumps({"question": "sequence?"}),
            "config": json.dumps({"development_mock": True}),
            "agent_executors": "{}",
        }
    )

    assert result.success is True
    assert result.data["pattern"] == "sequential"
    assert "Sequential Pattern Results" in result.data["result"]


def test_hierarchical_pattern_tool_runs_real_runtime_in_development_mode():
    result = HierarchicalPatternTool().run(
        {
            "agents": json.dumps(
                [
                    {"id": "coordinator", "type": "orchestrator"},
                    {"id": "subordinate", "type": "executor"},
                ]
            ),
            "input_data": json.dumps({"question": "coordinate?"}),
            "config": json.dumps({"development_mock": True}),
            "agent_executors": "{}",
        }
    )

    assert result.success is True
    assert result.data["pattern"] == "hierarchical"
    assert "Hierarchical Pattern Results" in result.data["result"]


def test_pattern_tool_requires_explicit_executors_or_development_mode():
    result = CollaborativePatternTool().run(
        {
            "agents": json.dumps(["agent_a", "agent_b"]),
            "input_data": json.dumps({"question": "agree?"}),
            "config": "{}",
            "agent_executors": "{}",
        }
    )

    assert result.success is False
    assert "No agent executors provided" in result.error


def test_pattern_tool_rejects_non_object_input_data():
    result = CollaborativePatternTool().run(
        {
            "agents": json.dumps(["agent_a", "agent_b"]),
            "input_data": json.dumps(["not", "an", "object"]),
            "config": json.dumps({"development_mock": True}),
            "agent_executors": "{}",
        }
    )

    assert result.success is False
    assert result.error == "input_data must be a JSON object"


def test_default_tool_registry_bootstraps_workflow_pattern_tools():
    from DeepResearch.src.tools import registry

    registered = registry.list()
    assert "collaborative_pattern" in registered
    assert "sequential_pattern" in registered
    assert "hierarchical_pattern" in registered


def test_workflow_orchestration_tool_delegates_to_pattern_runtime():
    result = WorkflowOrchestrationTool().run(
        {
            "workflow_config": json.dumps(
                {"pattern": "collaborative", "agents": ["agent_a", "agent_b"]}
            ),
            "input_data": json.dumps({"question": "orchestrate?"}),
            "pattern_configs": json.dumps({"development_mock": True}),
        }
    )

    assert result.success is True
    assert "Collaborative Pattern Results" in result.data["final_result"]
    assert json.loads(result.data["execution_summary"]) == {
        "pattern": "collaborative",
        "agents": ["agent_a", "agent_b"],
    }
