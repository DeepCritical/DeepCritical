from unittest.mock import AsyncMock, Mock, patch

import pytest

from DeepResearch.src.datatypes.workflow_patterns import AgentType, InteractionPattern

# Adjust imports to match your project structure
from DeepResearch.src.statemachines.workflow_pattern_statemachines import (
    run_collaborative_pattern_workflow,
    run_hierarchical_pattern_workflow,
    run_pattern_workflow,
    run_sequential_pattern_workflow,
)


class TestRunCollaborativePatternWorkflow:
    """Test suite for run_collaborative_pattern_workflow function."""

    @pytest.fixture
    def basic_inputs(self):
        """Create basic inputs for workflow."""
        return {
            "question": "What is the best approach?",
            "agents": ["agent1", "agent2"],
            "agent_types": {
                "agent1": AgentType.EXECUTOR,
                "agent2": AgentType.EXECUTOR,
            },
            "agent_executors": {
                "agent1": Mock(),
                "agent2": Mock(),
            },
            "config": None,
        }

    @pytest.mark.asyncio
    async def test_returns_string_output(self, basic_inputs):
        """Test that workflow returns a string output."""
        with patch(
            "DeepResearch.src.statemachines.workflow_pattern_statemachines.create_collaborative_pattern_graph"
        ) as mock_graph_factory:
            mock_graph = Mock()
            mock_result = Mock()
            mock_result.output = "Test output"
            mock_graph.run = AsyncMock(return_value=mock_result)
            mock_graph_factory.return_value = mock_graph

            result = await run_collaborative_pattern_workflow(**basic_inputs)

            assert isinstance(result, str)
            assert result == "Test output"

    @pytest.mark.asyncio
    async def test_creates_collaborative_graph(self, basic_inputs):
        """Test that workflow creates a collaborative pattern graph."""
        with patch(
            "DeepResearch.src.statemachines.workflow_pattern_statemachines.create_collaborative_pattern_graph"
        ) as mock_graph_factory:
            mock_graph = Mock()
            mock_result = Mock()
            mock_result.output = "output"
            mock_graph.run = AsyncMock(return_value=mock_result)
            mock_graph_factory.return_value = mock_graph

            await run_collaborative_pattern_workflow(**basic_inputs)

            mock_graph_factory.assert_called_once()

    @pytest.mark.asyncio
    async def test_sets_collaborative_pattern_in_state(self, basic_inputs):
        """Test that workflow sets COLLABORATIVE pattern in state."""
        with patch(
            "DeepResearch.src.statemachines.workflow_pattern_statemachines.create_collaborative_pattern_graph"
        ) as mock_graph_factory:
            mock_graph = Mock()
            mock_result = Mock()
            mock_result.output = "output"
            mock_graph.run = AsyncMock(return_value=mock_result)
            mock_graph_factory.return_value = mock_graph

            await run_collaborative_pattern_workflow(**basic_inputs)

            call_args = mock_graph.run.call_args
            state = call_args.kwargs["state"]
            assert state.interaction_pattern == InteractionPattern.COLLABORATIVE

    @pytest.mark.asyncio
    async def test_passes_all_parameters_to_state(self, basic_inputs):
        """Test that all parameters are passed to workflow state."""
        with patch(
            "DeepResearch.src.statemachines.workflow_pattern_statemachines.create_collaborative_pattern_graph"
        ) as mock_graph_factory:
            mock_graph = Mock()
            mock_result = Mock()
            mock_result.output = "output"
            mock_graph.run = AsyncMock(return_value=mock_result)
            mock_graph_factory.return_value = mock_graph

            await run_collaborative_pattern_workflow(**basic_inputs)

            call_args = mock_graph.run.call_args
            state = call_args.kwargs["state"]

            assert state.question == "What is the best approach?"
            assert state.agent_ids == ["agent1", "agent2"]
            assert state.agent_types == basic_inputs["agent_types"]
            assert state.agent_executors == basic_inputs["agent_executors"]


class TestRunSequentialPatternWorkflow:
    """Test suite for run_sequential_pattern_workflow function."""

    @pytest.fixture
    def basic_inputs(self):
        """Create basic inputs for workflow."""
        return {
            "question": "What is the sequence?",
            "agents": ["agent1", "agent2", "agent3"],
            "agent_types": {
                "agent1": AgentType.EXECUTOR,
                "agent2": AgentType.EXECUTOR,
                "agent3": AgentType.EXECUTOR,
            },
            "agent_executors": {
                "agent1": Mock(),
                "agent2": Mock(),
                "agent3": Mock(),
            },
            "config": None,
        }

    @pytest.mark.asyncio
    async def test_returns_string_output(self, basic_inputs):
        """Test that workflow returns a string output."""
        with patch(
            "DeepResearch.src.statemachines.workflow_pattern_statemachines.create_sequential_pattern_graph"
        ) as mock_graph_factory:
            mock_graph = Mock()
            mock_result = Mock()
            mock_result.output = "Sequential output"
            mock_graph.run = AsyncMock(return_value=mock_result)
            mock_graph_factory.return_value = mock_graph

            result = await run_sequential_pattern_workflow(**basic_inputs)

            assert isinstance(result, str)
            assert result == "Sequential output"

    @pytest.mark.asyncio
    async def test_creates_sequential_graph(self, basic_inputs):
        """Test that workflow creates a sequential pattern graph."""
        with patch(
            "DeepResearch.src.statemachines.workflow_pattern_statemachines.create_sequential_pattern_graph"
        ) as mock_graph_factory:
            mock_graph = Mock()
            mock_result = Mock()
            mock_result.output = "output"
            mock_graph.run = AsyncMock(return_value=mock_result)
            mock_graph_factory.return_value = mock_graph

            await run_sequential_pattern_workflow(**basic_inputs)

            mock_graph_factory.assert_called_once()

    @pytest.mark.asyncio
    async def test_sets_sequential_pattern_in_state(self, basic_inputs):
        """Test that workflow sets SEQUENTIAL pattern in state."""
        with patch(
            "DeepResearch.src.statemachines.workflow_pattern_statemachines.create_sequential_pattern_graph"
        ) as mock_graph_factory:
            mock_graph = Mock()
            mock_result = Mock()
            mock_result.output = "output"
            mock_graph.run = AsyncMock(return_value=mock_result)
            mock_graph_factory.return_value = mock_graph

            await run_sequential_pattern_workflow(**basic_inputs)

            call_args = mock_graph.run.call_args
            state = call_args.kwargs["state"]
            assert state.interaction_pattern == InteractionPattern.SEQUENTIAL

    @pytest.mark.asyncio
    async def test_passes_all_parameters_to_state(self, basic_inputs):
        """Test that all parameters are passed to workflow state."""
        with patch(
            "DeepResearch.src.statemachines.workflow_pattern_statemachines.create_sequential_pattern_graph"
        ) as mock_graph_factory:
            mock_graph = Mock()
            mock_result = Mock()
            mock_result.output = "output"
            mock_graph.run = AsyncMock(return_value=mock_result)
            mock_graph_factory.return_value = mock_graph

            await run_sequential_pattern_workflow(**basic_inputs)

            call_args = mock_graph.run.call_args
            state = call_args.kwargs["state"]

            assert state.question == "What is the sequence?"
            assert state.agent_ids == ["agent1", "agent2", "agent3"]
            assert state.agent_types == basic_inputs["agent_types"]
            assert state.agent_executors == basic_inputs["agent_executors"]


class TestRunHierarchicalPatternWorkflow:
    """Test suite for run_hierarchical_pattern_workflow function."""

    @pytest.fixture
    def basic_inputs(self):
        """Create basic inputs for workflow."""
        return {
            "question": "What is the hierarchy?",
            "coordinator_id": "PLANNER",
            "subordinate_ids": ["sub1", "sub2"],
            "agent_types": {
                "PLANNER": AgentType.PLANNER,
                "sub1": AgentType.EXECUTOR,
                "sub2": AgentType.EXECUTOR,
            },
            "agent_executors": {
                "PLANNER": Mock(),
                "sub1": Mock(),
                "sub2": Mock(),
            },
            "config": None,
        }

    @pytest.mark.asyncio
    async def test_returns_string_output(self, basic_inputs):
        """Test that workflow returns a string output."""
        with patch(
            "DeepResearch.src.statemachines.workflow_pattern_statemachines.create_hierarchical_pattern_graph"
        ) as mock_graph_factory:
            mock_graph = Mock()
            mock_result = Mock()
            mock_result.output = "Hierarchical output"
            mock_graph.run = AsyncMock(return_value=mock_result)
            mock_graph_factory.return_value = mock_graph

            result = await run_hierarchical_pattern_workflow(**basic_inputs)

            assert isinstance(result, str)
            assert result == "Hierarchical output"

    @pytest.mark.asyncio
    async def test_creates_hierarchical_graph(self, basic_inputs):
        """Test that workflow creates a hierarchical pattern graph."""
        with patch(
            "DeepResearch.src.statemachines.workflow_pattern_statemachines.create_hierarchical_pattern_graph"
        ) as mock_graph_factory:
            mock_graph = Mock()
            mock_result = Mock()
            mock_result.output = "output"
            mock_graph.run = AsyncMock(return_value=mock_result)
            mock_graph_factory.return_value = mock_graph

            await run_hierarchical_pattern_workflow(**basic_inputs)

            mock_graph_factory.assert_called_once()

    @pytest.mark.asyncio
    async def test_sets_hierarchical_pattern_in_state(self, basic_inputs):
        """Test that workflow sets HIERARCHICAL pattern in state."""
        with patch(
            "DeepResearch.src.statemachines.workflow_pattern_statemachines.create_hierarchical_pattern_graph"
        ) as mock_graph_factory:
            mock_graph = Mock()
            mock_result = Mock()
            mock_result.output = "output"
            mock_graph.run = AsyncMock(return_value=mock_result)
            mock_graph_factory.return_value = mock_graph

            await run_hierarchical_pattern_workflow(**basic_inputs)

            call_args = mock_graph.run.call_args
            state = call_args.kwargs["state"]
            assert state.interaction_pattern == InteractionPattern.HIERARCHICAL

    @pytest.mark.asyncio
    async def test_combines_PLANNER_and_subordinates(self, basic_inputs):
        """Test that PLANNER and subordinates are combined into agent_ids."""
        with patch(
            "DeepResearch.src.statemachines.workflow_pattern_statemachines.create_hierarchical_pattern_graph"
        ) as mock_graph_factory:
            mock_graph = Mock()
            mock_result = Mock()
            mock_result.output = "output"
            mock_graph.run = AsyncMock(return_value=mock_result)
            mock_graph_factory.return_value = mock_graph

            await run_hierarchical_pattern_workflow(**basic_inputs)

            call_args = mock_graph.run.call_args
            state = call_args.kwargs["state"]

            assert state.agent_ids == ["PLANNER", "sub1", "sub2"]
            assert state.agent_ids[0] == "PLANNER"  # PLANNER is first

    @pytest.mark.asyncio
    async def test_passes_all_parameters_to_state(self, basic_inputs):
        """Test that all parameters are passed to workflow state."""
        with patch(
            "DeepResearch.src.statemachines.workflow_pattern_statemachines.create_hierarchical_pattern_graph"
        ) as mock_graph_factory:
            mock_graph = Mock()
            mock_result = Mock()
            mock_result.output = "output"
            mock_graph.run = AsyncMock(return_value=mock_result)
            mock_graph_factory.return_value = mock_graph

            await run_hierarchical_pattern_workflow(**basic_inputs)

            call_args = mock_graph.run.call_args
            state = call_args.kwargs["state"]

            assert state.question == "What is the hierarchy?"
            assert state.agent_types == basic_inputs["agent_types"]
            assert state.agent_executors == basic_inputs["agent_executors"]

    @pytest.mark.asyncio
    async def test_handles_empty_subordinates(self, basic_inputs):
        """Test workflow with no subordinates."""
        with patch(
            "DeepResearch.src.statemachines.workflow_pattern_statemachines.create_hierarchical_pattern_graph"
        ) as mock_graph_factory:
            mock_graph = Mock()
            mock_result = Mock()
            mock_result.output = "output"
            mock_graph.run = AsyncMock(return_value=mock_result)
            mock_graph_factory.return_value = mock_graph

            basic_inputs["subordinate_ids"] = []

            await run_hierarchical_pattern_workflow(**basic_inputs)

            call_args = mock_graph.run.call_args
            state = call_args.kwargs["state"]
            assert state.agent_ids == ["PLANNER"]

    @pytest.mark.asyncio
    async def test_handles_many_subordinates(self, basic_inputs):
        """Test workflow with many subordinates."""
        with patch(
            "DeepResearch.src.statemachines.workflow_pattern_statemachines.create_hierarchical_pattern_graph"
        ) as mock_graph_factory:
            mock_graph = Mock()
            mock_result = Mock()
            mock_result.output = "output"
            mock_graph.run = AsyncMock(return_value=mock_result)
            mock_graph_factory.return_value = mock_graph

            subordinates = [f"sub{i}" for i in range(10)]
            basic_inputs["subordinate_ids"] = subordinates

            await run_hierarchical_pattern_workflow(**basic_inputs)

            call_args = mock_graph.run.call_args
            state = call_args.kwargs["state"]
            assert len(state.agent_ids) == 11
            assert state.agent_ids[0] == "PLANNER"


class TestRunPatternWorkflow:
    """Test suite for run_pattern_workflow function."""

    @pytest.fixture
    def basic_inputs(self):
        """Create basic inputs for workflow."""
        return {
            "question": "Generic question?",
            "pattern": InteractionPattern.COLLABORATIVE,
            "agents": ["agent1", "agent2"],
            "agent_types": {
                "agent1": AgentType.EXECUTOR,
                "agent2": AgentType.EXECUTOR,
            },
            "agent_executors": {
                "agent1": Mock(),
                "agent2": Mock(),
            },
            "config": None,
        }

    @pytest.mark.asyncio
    async def test_returns_string_output(self, basic_inputs):
        """Test that workflow returns a string output."""
        with patch(
            "DeepResearch.src.statemachines.workflow_pattern_statemachines.create_pattern_graph"
        ) as mock_graph_factory:
            mock_graph = Mock()
            mock_result = Mock()
            mock_result.output = "Pattern output"
            mock_graph.run = AsyncMock(return_value=mock_result)
            mock_graph_factory.return_value = mock_graph

            result = await run_pattern_workflow(**basic_inputs)

            assert isinstance(result, str)
            assert result == "Pattern output"

    @pytest.mark.asyncio
    async def test_creates_graph_for_specified_pattern(self, basic_inputs):
        """Test that workflow creates graph for the specified pattern."""
        with patch(
            "DeepResearch.src.statemachines.workflow_pattern_statemachines.create_pattern_graph"
        ) as mock_graph_factory:
            mock_graph = Mock()
            mock_result = Mock()
            mock_result.output = "output"
            mock_graph.run = AsyncMock(return_value=mock_result)
            mock_graph_factory.return_value = mock_graph

            await run_pattern_workflow(**basic_inputs)

            mock_graph_factory.assert_called_once_with(InteractionPattern.COLLABORATIVE)

    @pytest.mark.asyncio
    async def test_handles_collaborative_pattern(self, basic_inputs):
        """Test workflow with COLLABORATIVE pattern."""
        with patch(
            "DeepResearch.src.statemachines.workflow_pattern_statemachines.create_pattern_graph"
        ) as mock_graph_factory:
            mock_graph = Mock()
            mock_result = Mock()
            mock_result.output = "output"
            mock_graph.run = AsyncMock(return_value=mock_result)
            mock_graph_factory.return_value = mock_graph

            basic_inputs["pattern"] = InteractionPattern.COLLABORATIVE

            await run_pattern_workflow(**basic_inputs)

            call_args = mock_graph.run.call_args
            state = call_args.kwargs["state"]
            assert state.interaction_pattern == InteractionPattern.COLLABORATIVE

    @pytest.mark.asyncio
    async def test_handles_sequential_pattern(self, basic_inputs):
        """Test workflow with SEQUENTIAL pattern."""
        with patch(
            "DeepResearch.src.statemachines.workflow_pattern_statemachines.create_pattern_graph"
        ) as mock_graph_factory:
            mock_graph = Mock()
            mock_result = Mock()
            mock_result.output = "output"
            mock_graph.run = AsyncMock(return_value=mock_result)
            mock_graph_factory.return_value = mock_graph

            basic_inputs["pattern"] = InteractionPattern.SEQUENTIAL

            await run_pattern_workflow(**basic_inputs)

            call_args = mock_graph.run.call_args
            state = call_args.kwargs["state"]
            assert state.interaction_pattern == InteractionPattern.SEQUENTIAL

    @pytest.mark.asyncio
    async def test_handles_hierarchical_pattern(self, basic_inputs):
        """Test workflow with HIERARCHICAL pattern."""
        with patch(
            "DeepResearch.src.statemachines.workflow_pattern_statemachines.create_pattern_graph"
        ) as mock_graph_factory:
            mock_graph = Mock()
            mock_result = Mock()
            mock_result.output = "output"
            mock_graph.run = AsyncMock(return_value=mock_result)
            mock_graph_factory.return_value = mock_graph

            basic_inputs["pattern"] = InteractionPattern.HIERARCHICAL

            await run_pattern_workflow(**basic_inputs)

            call_args = mock_graph.run.call_args
            state = call_args.kwargs["state"]
            assert state.interaction_pattern == InteractionPattern.HIERARCHICAL

    @pytest.mark.asyncio
    async def test_passes_all_parameters_to_state(self, basic_inputs):
        """Test that all parameters are passed to workflow state."""
        with patch(
            "DeepResearch.src.statemachines.workflow_pattern_statemachines.create_pattern_graph"
        ) as mock_graph_factory:
            mock_graph = Mock()
            mock_result = Mock()
            mock_result.output = "output"
            mock_graph.run = AsyncMock(return_value=mock_result)
            mock_graph_factory.return_value = mock_graph

            await run_pattern_workflow(**basic_inputs)

            call_args = mock_graph.run.call_args
            state = call_args.kwargs["state"]

            assert state.question == "Generic question?"
            assert state.agent_ids == ["agent1", "agent2"]
            assert state.agent_types == basic_inputs["agent_types"]
            assert state.agent_executors == basic_inputs["agent_executors"]
            assert state.interaction_pattern == InteractionPattern.COLLABORATIVE

    @pytest.mark.asyncio
    async def test_passes_config_to_state(self, basic_inputs):
        """Test that config is passed to workflow state."""
        with patch(
            "DeepResearch.src.statemachines.workflow_pattern_statemachines.create_pattern_graph"
        ) as mock_graph_factory:
            mock_graph = Mock()
            mock_result = Mock()
            mock_result.output = "output"
            mock_graph.run = AsyncMock(return_value=mock_result)
            mock_graph_factory.return_value = mock_graph

            custom_config = Mock()
            basic_inputs["config"] = custom_config

            await run_pattern_workflow(**basic_inputs)

            call_args = mock_graph.run.call_args
            state = call_args.kwargs["state"]
            assert state.config == custom_config
