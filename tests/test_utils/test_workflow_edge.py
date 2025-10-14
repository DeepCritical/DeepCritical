# tests/test_utils/test_workflow_edge.py

from unittest.mock import patch

import pytest

from DeepResearch.src.utils.workflow_edge import (
    Edge,
    EdgeGroup,
    FanInEdgeGroup,
    FanOutEdgeGroup,
    SwitchCaseEdgeGroup,
    SwitchCaseEdgeGroupCase,
    SwitchCaseEdgeGroupDefault,
)


class TestWorkflowEdge:
    def test_edge_creation(self):
        """Test normal Edge instantiation and basic properties."""

        def always_true(x):
            return True

        edge = Edge("source_1", "target_1", condition=always_true)

        assert edge.source_id == "source_1"
        assert edge.target_id == "target_1"
        assert edge.condition_name == "always_true"
        assert edge.id == "source_1->target_1"
        assert edge.should_route({}) is True

        # Now test the EdgeGroup Creation
        edges_list = []
        for index in range(3):
            edge = Edge(
                f"source_{index + 1}", f"target_{index + 1}", condition=always_true
            )
            edges_list.append(edge)
        edges_group = EdgeGroup(edges=edges_list, id="Test", type="Test")
        assert edges_group.id == "Test"
        assert edges_group.type == "Test"
        assert edges_group.edges != []
        assert isinstance(edges_group.edges, list)
        # Test source_executor_ids(self) -> list[str]:
        assert edges_group.source_executor_ids != []
        assert isinstance(edges_group.source_executor_ids, list)
        # Test target_executor_ids(self) -> list[str]:
        assert edges_group.target_executor_ids != []
        assert isinstance(edges_group.target_executor_ids, list)
        # Test to_dict(self) -> dict[str, Any]:
        assert list(edges_group.to_dict().keys()) == ["id", "type", "edges"]
        # Test from_dict(cls, data: dict[str, Any]) -> EdgeGroup:
        get_dict = edges_group.to_dict()
        assert isinstance(edges_group.from_dict(get_dict), EdgeGroup)

    def test_fan_in_fan_out_edge_groups(self):
        """Test normal FanOutEdgeGroup instantiation and basic properties."""
        fan_out_edge_group = FanOutEdgeGroup(
            source_id="target_1", target_ids=["target_2", "target_3"]
        )
        assert len(fan_out_edge_group.target_ids) == 2
        assert fan_out_edge_group.selection_func is None
        assert isinstance(fan_out_edge_group.to_dict(), dict)
        # Test a fan-out mapping from a single source to less than 2 targets.
        with pytest.raises(
            ValueError, match="FanOutEdgeGroup must contain at least two targets"
        ):
            FanOutEdgeGroup(source_id="target_1", target_ids=["target_2"])
        """Test normal FanInEdgeGroup instantiation and basic properties."""
        fan_in_edge_group = FanInEdgeGroup(
            source_ids=["target_1", "target_2"], target_id="target_3"
        )
        assert len(fan_in_edge_group.source_executor_ids) == 2
        assert isinstance(fan_in_edge_group.to_dict(), dict)
        # Test a fan-in mapping from nothing to a single target.
        with pytest.raises(
            ValueError, match="Edge source_id must be a non-empty string"
        ):
            FanOutEdgeGroup(source_id="", target_ids="target_2")

    def test_switch_case_edges_group_case(self):
        """Test initialization with conditions - named functions, lambdas, explicit names."""

        # Named function
        def my_predicate(x):
            return x > 5

        case1 = SwitchCaseEdgeGroupCase(condition=my_predicate, target_id="node_1")
        assert case1.target_id == "node_1"
        assert case1.type == "Case"
        assert case1.condition_name == "my_predicate"
        assert case1.condition(10) is True
        assert case1.condition(3) is False

        # Lambda
        case2 = SwitchCaseEdgeGroupCase(condition=lambda x: x < 0, target_id="node_2")
        assert case2.condition_name == "<lambda>"
        assert case2.condition(-5) is True

        # Explicit name is ignored when condition exists
        case3 = SwitchCaseEdgeGroupCase(
            condition=my_predicate, target_id="node_3", condition_name="custom"
        )
        assert case3.condition_name == "my_predicate"

        """Test initialization with None condition - missing callable placeholder."""
        # No name provided
        case1 = SwitchCaseEdgeGroupCase(condition=None, target_id="node_4")
        assert case1.condition_name is None
        with pytest.raises(RuntimeError):
            case1.condition("anything")

        # Name provided
        case2 = SwitchCaseEdgeGroupCase(
            condition=None, target_id="node_5", condition_name="saved_condition"
        )
        assert case2.condition_name == "saved_condition"
        with pytest.raises(RuntimeError):
            case2.condition("anything")

        """Test target_id validation."""
        with pytest.raises(ValueError, match="target_id"):
            SwitchCaseEdgeGroupCase(condition=lambda x: True, target_id="")

        with pytest.raises(
            ValueError, match="SwitchCaseEdgeGroupCase requires a target_id"
        ):
            SwitchCaseEdgeGroupCase(condition=lambda x: True, target_id="")

        """Test to_dict/from_dict round-trip and edge cases."""
        # With condition name
        case1 = SwitchCaseEdgeGroupCase(condition=lambda x: x > 10, target_id="node_6")
        dict1 = case1.to_dict()
        assert dict1["target_id"] == "node_6"
        assert dict1["type"] == "Case"
        assert dict1["condition_name"] == "<lambda>"
        assert "_condition" not in dict1

        # Without condition name
        case2 = SwitchCaseEdgeGroupCase(condition=None, target_id="node_7")
        dict2 = case2.to_dict()
        assert "condition_name" not in dict2

        # Round-trip
        restored = SwitchCaseEdgeGroupCase.from_dict(dict1)
        assert restored.target_id == "node_6"
        assert restored.condition_name == "<lambda>"
        assert restored.type == "Case"
        with pytest.raises(RuntimeError):
            restored.condition("test")

        # From dict without condition_name
        restored2 = SwitchCaseEdgeGroupCase.from_dict({"target_id": "node_8"})
        assert restored2.condition_name is None

        """Test repr exclusion and equality comparison behaviors."""

        def func1(x):
            return x > 5

        case1 = SwitchCaseEdgeGroupCase(func1, "node_9")
        case2 = SwitchCaseEdgeGroupCase(func1, "node_9")
        case3 = SwitchCaseEdgeGroupCase(func1, "node_10")

        # Repr excludes _condition
        assert "_condition" not in repr(case1)
        assert "target_id" in repr(case1)

        # Equality ignores _condition (compare=False)
        assert case1 == case2
        assert case1 != case3

    def test_switch_case_edges_group_default(self):
        """Test initialization, validation, serialization, and dataclass behaviors."""
        # Valid initialization
        default1 = SwitchCaseEdgeGroupDefault(target_id="fallback_node")
        assert default1.target_id == "fallback_node"
        assert default1.type == "Default"

        # Empty target_id validation
        with pytest.raises(ValueError, match="target_id"):
            SwitchCaseEdgeGroupDefault(target_id="")

        # None target_id validation
        with pytest.raises(
            ValueError, match="SwitchCaseEdgeGroupDefault requires a target_id"
        ):
            SwitchCaseEdgeGroupDefault(target_id="")

        # Serialization
        dict1 = default1.to_dict()
        assert dict1["target_id"] == "fallback_node"
        assert dict1["type"] == "Default"
        assert len(dict1) == 2

        # Deserialization
        restored = SwitchCaseEdgeGroupDefault.from_dict({"target_id": "restored_node"})
        assert restored.target_id == "restored_node"
        assert restored.type == "Default"

        # Round-trip
        dict2 = restored.to_dict()
        restored2 = SwitchCaseEdgeGroupDefault.from_dict(dict2)
        assert restored2.target_id == restored.target_id
        assert restored2.type == "Default"

        # Equality - same target_id means equal
        default2 = SwitchCaseEdgeGroupDefault("node_a")
        default3 = SwitchCaseEdgeGroupDefault("node_a")
        default4 = SwitchCaseEdgeGroupDefault("node_b")
        assert default2 == default3
        assert default2 != default4

        # Repr contains target_id
        assert "target_id" in repr(default1)
        assert "fallback_node" in repr(default1)

    def test_switch_case_edges_group(self):
        """Test initialization, validation, routing logic, and serialization."""
        # Valid initialization with cases and default
        case1 = SwitchCaseEdgeGroupCase(condition=lambda x: x > 10, target_id="high")
        case2 = SwitchCaseEdgeGroupCase(condition=lambda x: x < 5, target_id="low")
        default = SwitchCaseEdgeGroupDefault(target_id="fallback")

        group = SwitchCaseEdgeGroup(source_id="start", cases=[case1, case2, default])

        assert group._target_ids == ["high", "low", "fallback"]
        assert len(group.cases) == 3
        assert group.cases[0] == case1
        assert group.cases[1] == case2
        assert group.cases[2] == default
        assert group.type == "SwitchCaseEdgeGroup"
        assert len(group._target_ids) == 3
        assert "high" in group._target_ids
        assert "low" in group._target_ids
        assert "fallback" in group._target_ids

        # Custom id
        group2 = SwitchCaseEdgeGroup(
            source_id="start", cases=[case1, default], id="custom_id"
        )
        assert group2.id == "custom_id"

        # Fewer than 2 cases validation
        with pytest.raises(ValueError, match="at least two cases"):
            SwitchCaseEdgeGroup(source_id="start", cases=[default])

        # No default case validation
        with pytest.raises(ValueError, match="exactly one default"):
            SwitchCaseEdgeGroup(source_id="start", cases=[case1, case2])

        # Multiple default cases validation
        default2 = SwitchCaseEdgeGroupDefault(target_id="another_fallback")
        with pytest.raises(ValueError, match="exactly one default"):
            SwitchCaseEdgeGroup(source_id="start", cases=[case1, default, default2])

        # Warning when default is not last
        with patch("logging.Logger.warning") as mock_warning:
            _ = SwitchCaseEdgeGroup(source_id="start", cases=[default, case1])
            mock_warning.assert_called_once()
            assert "not the last case" in mock_warning.call_args[0][0]

        # Selection logic - first matching condition
        targets = ["high", "low", "fallback"]
        assert group._selection_func is not None
        result1 = group._selection_func(15, targets)
        assert result1 == ["high"]

        result2 = group._selection_func(3, targets)
        assert group._selection_func is not None
        assert result2 == ["low"]

        # Selection logic - no match, goes to default
        result3 = group._selection_func(7, targets)
        assert group._selection_func is not None
        assert result3 == ["fallback"]

        # Selection logic - condition raises exception, skips to next
        case_error = SwitchCaseEdgeGroupCase(
            condition=lambda x: x.missing_attr, target_id="error_node"
        )
        group4 = SwitchCaseEdgeGroup(source_id="start", cases=[case_error, default])
        with patch("logging.Logger.warning") as mock_warning:
            assert group4._selection_func is not None
            result4 = group4._selection_func(10, ["error_node", "fallback"])
            assert result4 == ["fallback"]
            mock_warning.assert_called_once()
            assert "Error evaluating condition" in mock_warning.call_args[0][0]

        # Serialization
        dict1 = group.to_dict()
        assert dict1["type"] == "SwitchCaseEdgeGroup"
        assert "cases" in dict1
        assert len(dict1["cases"]) == 3
        assert dict1["cases"][0]["target_id"] == "high"
        assert dict1["cases"][1]["target_id"] == "low"
        assert dict1["cases"][2]["target_id"] == "fallback"
        assert dict1["cases"][2]["type"] == "Default"

        # Edge creation
        assert len(group.edges) == 3
        assert all(edge.source_id == "start" for edge in group.edges)
        edge_targets = {edge.target_id for edge in group.edges}
        assert edge_targets == {"high", "low", "fallback"}

    def test_edge_validation(self):
        """Test that Edge enforces non-empty source_id and target_id."""
        # Valid cases
        Edge("a", "b")  # should not raise

        # Invalid cases
        with pytest.raises(ValueError, match="source_id must be a non-empty string"):
            Edge("", "target")

        with pytest.raises(ValueError, match="target_id must be a non-empty string"):
            Edge("source", "")

        with pytest.raises(ValueError, match="source_id must be a non-empty string"):
            Edge("", "")

    def test_edge_traversal(self):
        """Test the should_route method with and without conditions."""
        # Edge without condition → always routes
        edge_no_cond = Edge("src", "dst")
        assert edge_no_cond.should_route({}) is True
        assert edge_no_cond.should_route(None) is True
        assert edge_no_cond.should_route({"key": "value"}) is True

        # Edge with condition
        def is_positive(data):
            return data.get("value", 0) > 0

        edge_with_cond = Edge("src", "dst", condition=is_positive)
        assert edge_with_cond.should_route({"value": 5}) is True
        assert edge_with_cond.should_route({"value": -1}) is False
        assert edge_with_cond.should_route({}) is False  # default 0 not > 0

    def test_edge_error_handling(self):
        """Test robustness when condition raises an exception."""

        def faulty_condition(data):
            raise ValueError("Oops!")

        edge = Edge("src", "dst", condition=faulty_condition)

        # should_route should propagate the exception (no internal try/except in Edge)
        with pytest.raises(ValueError, match="Oops!"):
            edge.should_route({"test": 1})

        # Also test serialization round-trip preserves condition_name
        edge_dict = edge.to_dict()
        assert edge_dict == {
            "source_id": "src",
            "target_id": "dst",
            "condition_name": "faulty_condition",
        }

        # Deserialized edge has no callable, but retains name
        restored = Edge.from_dict(edge_dict)
        assert restored.source_id == "src"
        assert restored.target_id == "dst"
        assert restored.condition_name == "faulty_condition"
        assert restored._condition is None
        assert restored.should_route({}) is True  # falls back to unconditional
