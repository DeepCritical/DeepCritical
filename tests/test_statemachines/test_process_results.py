from unittest.mock import Mock, patch

import pytest

from DeepResearch.src.statemachines.workflow_pattern_statemachines import (
    ExecutionStatus,
    PatternError,
    ProcessCollaborativeResults,
    ProcessHierarchicalResults,
    ProcessSequentialResults,
    ValidateConsensus,
    ValidateResults,
)


class TestProcessCollaborativeResults:
    """Test suite for ProcessCollaborativeResults node."""

    @pytest.fixture
    def mock_consensus_result(self):
        """Create a mock consensus result."""
        result = Mock()
        result.consensus_reached = True
        result.confidence = 0.85
        result.algorithm_used = Mock()
        result.algorithm_used.value = "majority_vote"
        return result

    @pytest.fixture
    def mock_orchestrator(self):
        """Create a mock orchestrator with results."""
        orchestrator = Mock()
        orchestrator.state = Mock()
        orchestrator.state.results = {
            "agent1": {"output": "result1"},
            "agent2": {"output": "result2"},
        }
        return orchestrator

    @pytest.fixture
    def mock_interaction_state(self):
        """Create a mock interaction state."""
        state = Mock()
        state.current_round = 3
        state.active_agents = ["agent1", "agent2", "agent3"]
        return state

    @pytest.fixture
    def mock_context(self, mock_orchestrator, mock_interaction_state):
        """Create a mock GraphRunContext."""
        ctx = Mock()
        ctx.state = Mock()
        ctx.state.orchestrator = mock_orchestrator
        ctx.state.interaction_state = mock_interaction_state
        ctx.state.consensus_algorithm = "majority_vote"
        ctx.state.interaction_pattern = Mock()
        ctx.state.interaction_pattern.value = "collaborative"
        ctx.state.execution_summary = {}
        ctx.state.errors = []
        ctx.state.processing_steps = []
        ctx.state.execution_status = None
        return ctx

    @pytest.fixture
    def node(self):
        """Create ProcessCollaborativeResults node instance."""
        return ProcessCollaborativeResults()

    @pytest.mark.asyncio
    async def test_successful_processing(
        self, node, mock_context, mock_consensus_result
    ):
        """Test successful collaborative results processing."""
        with patch(
            "DeepResearch.src.statemachines.workflow_pattern_statemachines.WorkflowPatternUtils.compute_consensus",
            return_value=mock_consensus_result,
        ):
            result = await node.run(mock_context)

            assert isinstance(result, ValidateConsensus)
            assert (
                "collaborative_results_processed" in mock_context.state.processing_steps
            )
            assert len(mock_context.state.errors) == 0

    @pytest.mark.asyncio
    async def test_execution_summary_updated(
        self, node, mock_context, mock_consensus_result
    ):
        """Test that execution summary is updated correctly."""
        with patch(
            "DeepResearch.src.statemachines.workflow_pattern_statemachines.WorkflowPatternUtils.compute_consensus",
            return_value=mock_consensus_result,
        ):
            await node.run(mock_context)

            assert mock_context.state.execution_summary["pattern"] == "collaborative"
            assert mock_context.state.execution_summary["consensus_reached"]
            assert mock_context.state.execution_summary["consensus_confidence"] == 0.85
            assert (
                mock_context.state.execution_summary["algorithm_used"]
                == "majority_vote"
            )
            assert mock_context.state.execution_summary["total_rounds"] == 3
            assert mock_context.state.execution_summary["agents_participated"] == 3

    @pytest.mark.asyncio
    async def test_compute_consensus_called_with_correct_params(
        self, node, mock_context, mock_consensus_result
    ):
        """Test that compute_consensus is called with correct parameters."""
        with patch(
            "DeepResearch.src.statemachines.workflow_pattern_statemachines.WorkflowPatternUtils.compute_consensus",
            return_value=mock_consensus_result,
        ) as mock_compute:
            await node.run(mock_context)

            mock_compute.assert_called_once()
            call_args = mock_compute.call_args[0]
            assert len(call_args[0]) == 2  # Two results from orchestrator
            assert call_args[1] == "majority_vote"

    @pytest.mark.asyncio
    async def test_preserves_existing_processing_steps(
        self, node, mock_context, mock_consensus_result
    ):
        """Test that existing processing steps are preserved."""
        mock_context.state.processing_steps = ["step1", "step2"]

        with patch(
            "DeepResearch.src.statemachines.workflow_pattern_statemachines.WorkflowPatternUtils.compute_consensus",
            return_value=mock_consensus_result,
        ):
            await node.run(mock_context)

            assert mock_context.state.processing_steps == [
                "step1",
                "step2",
                "collaborative_results_processed",
            ]

    @pytest.mark.asyncio
    async def test_consensus_computation_exception(self, node, mock_context):
        """Test handling when consensus computation fails."""
        with patch(
            "DeepResearch.src.statemachines.workflow_pattern_statemachines.WorkflowPatternUtils.compute_consensus",
            side_effect=ValueError("Consensus error"),
        ):
            result = await node.run(mock_context)

            assert isinstance(result, PatternError)
            assert mock_context.state.execution_status == ExecutionStatus.FAILED
            assert (
                "Collaborative result processing failed: Consensus error"
                in mock_context.state.errors[0]
            )

    @pytest.mark.asyncio
    async def test_orchestrator_state_access_exception(self, node, mock_context):
        """Test handling when orchestrator state access fails."""
        mock_context.state.orchestrator.state.results = None

        with patch(
            "DeepResearch.src.statemachines.workflow_pattern_statemachines.WorkflowPatternUtils.compute_consensus",
            side_effect=AttributeError("State access error"),
        ):
            result = await node.run(mock_context)

            assert isinstance(result, PatternError)
            assert mock_context.state.execution_status == ExecutionStatus.FAILED

    @pytest.mark.asyncio
    async def test_error_appends_to_existing(self, node, mock_context):
        """Test that errors are appended to existing error list."""
        mock_context.state.errors = ["existing_error"]

        with patch(
            "DeepResearch.src.statemachines.workflow_pattern_statemachines.WorkflowPatternUtils.compute_consensus",
            side_effect=Exception("New error"),
        ):
            await node.run(mock_context)

            assert len(mock_context.state.errors) == 2
            assert mock_context.state.errors[0] == "existing_error"


class TestProcessSequentialResults:
    """Test suite for ProcessSequentialResults node."""

    @pytest.fixture
    def mock_orchestrator(self):
        """Create a mock orchestrator with sequential results."""
        orchestrator = Mock()
        orchestrator.state = Mock()
        orchestrator.state.results = {
            "agent1": {"success": True, "output": "result1"},
            "agent2": {"success": True, "output": "result2"},
            "agent3": {"success": False, "output": "failed"},
        }
        return orchestrator

    @pytest.fixture
    def mock_interaction_state(self):
        """Create a mock interaction state."""
        state = Mock()
        state.current_round = 5
        return state

    @pytest.fixture
    def mock_context(self, mock_orchestrator, mock_interaction_state):
        """Create a mock GraphRunContext."""
        ctx = Mock()
        ctx.state = Mock()
        ctx.state.orchestrator = mock_orchestrator
        ctx.state.interaction_state = mock_interaction_state
        ctx.state.interaction_pattern = Mock()
        ctx.state.interaction_pattern.value = "sequential"
        ctx.state.execution_summary = {}
        ctx.state.errors = []
        ctx.state.processing_steps = []
        ctx.state.execution_status = None
        return ctx

    @pytest.fixture
    def node(self):
        """Create ProcessSequentialResults node instance."""
        return ProcessSequentialResults()

    @pytest.mark.asyncio
    async def test_successful_processing(self, node, mock_context):
        """Test successful sequential results processing."""
        result = await node.run(mock_context)

        assert isinstance(result, ValidateResults)
        assert "sequential_results_processed" in mock_context.state.processing_steps
        assert len(mock_context.state.errors) == 0

    @pytest.mark.asyncio
    async def test_execution_summary_updated(self, node, mock_context):
        """Test that execution summary is updated correctly."""
        await node.run(mock_context)

        assert mock_context.state.execution_summary["pattern"] == "sequential"
        assert mock_context.state.execution_summary["sequential_steps"] == 3
        assert (
            mock_context.state.execution_summary["agents_executed"] == 2
        )  # Only successful ones
        assert mock_context.state.execution_summary["total_rounds"] == 5

    @pytest.mark.asyncio
    async def test_counts_only_successful_agents(self, node, mock_context):
        """Test that only successful agents are counted."""
        await node.run(mock_context)

        # 2 out of 3 agents have success=True
        assert mock_context.state.execution_summary["agents_executed"] == 2

    @pytest.mark.asyncio
    async def test_preserves_existing_processing_steps(self, node, mock_context):
        """Test that existing processing steps are preserved."""
        mock_context.state.processing_steps = ["step1", "step2"]

        await node.run(mock_context)

        assert mock_context.state.processing_steps == [
            "step1",
            "step2",
            "sequential_results_processed",
        ]

    @pytest.mark.asyncio
    async def test_empty_results(self, node, mock_context):
        """Test processing with empty results."""
        mock_context.state.orchestrator.state.results = {}

        result = await node.run(mock_context)

        assert isinstance(result, ValidateResults)
        assert mock_context.state.execution_summary["sequential_steps"] == 0
        assert mock_context.state.execution_summary["agents_executed"] == 0

    @pytest.mark.asyncio
    async def test_results_access_exception(self, node, mock_context):
        """Test handling when results access fails."""
        mock_context.state.orchestrator.state.results = None

        result = await node.run(mock_context)

        assert isinstance(result, PatternError)
        assert mock_context.state.execution_status == ExecutionStatus.FAILED
        assert "Sequential result processing failed" in mock_context.state.errors[0]

    @pytest.mark.asyncio
    async def test_summary_update_exception(self, node, mock_context):
        """Test handling when summary update fails."""
        # Make execution_summary a Mock that raises on update
        mock_summary = Mock()
        mock_summary.update = Mock(side_effect=Exception("Update error"))
        mock_context.state.execution_summary = mock_summary

        result = await node.run(mock_context)

        assert isinstance(result, PatternError)
        assert mock_context.state.execution_status == ExecutionStatus.FAILED

    @pytest.mark.asyncio
    async def test_error_appends_to_existing(self, node, mock_context):
        """Test that errors are appended to existing error list."""
        mock_context.state.errors = ["existing_error"]
        mock_context.state.orchestrator.state.results = None

        await node.run(mock_context)

        assert len(mock_context.state.errors) == 2
        assert mock_context.state.errors[0] == "existing_error"


class TestProcessHierarchicalResults:
    """Test suite for ProcessHierarchicalResults node."""

    @pytest.fixture
    def mock_orchestrator(self):
        """Create a mock orchestrator with hierarchical results."""
        orchestrator = Mock()
        orchestrator.state = Mock()
        orchestrator.state.results = {
            "coordinator": {"output": "coordinated result"},
            "subordinate1": {"output": "sub result 1"},
            "subordinate2": {"output": "sub result 2"},
        }
        return orchestrator

    @pytest.fixture
    def mock_interaction_state(self):
        """Create a mock interaction state."""
        state = Mock()
        state.current_round = 4
        return state

    @pytest.fixture
    def mock_context(self, mock_orchestrator, mock_interaction_state):
        """Create a mock GraphRunContext."""
        ctx = Mock()
        ctx.state = Mock()
        ctx.state.orchestrator = mock_orchestrator
        ctx.state.interaction_state = mock_interaction_state
        ctx.state.interaction_pattern = Mock()
        ctx.state.interaction_pattern.value = "hierarchical"
        ctx.state.execution_summary = {}
        ctx.state.errors = []
        ctx.state.processing_steps = []
        ctx.state.execution_status = None
        return ctx

    @pytest.fixture
    def node(self):
        """Create ProcessHierarchicalResults node instance."""
        return ProcessHierarchicalResults()

    @pytest.mark.asyncio
    async def test_successful_processing(self, node, mock_context):
        """Test successful hierarchical results processing."""
        result = await node.run(mock_context)

        assert isinstance(result, ValidateResults)
        assert "hierarchical_results_processed" in mock_context.state.processing_steps
        assert len(mock_context.state.errors) == 0

    @pytest.mark.asyncio
    async def test_execution_summary_updated(self, node, mock_context):
        """Test that execution summary is updated correctly."""
        await node.run(mock_context)

        assert mock_context.state.execution_summary["pattern"] == "hierarchical"
        assert mock_context.state.execution_summary["coordinator_executed"]
        assert mock_context.state.execution_summary["subordinates_executed"] == 2
        assert mock_context.state.execution_summary["total_rounds"] == 4

    @pytest.mark.asyncio
    async def test_coordinator_not_present(self, node, mock_context):
        """Test processing when coordinator is not in results."""
        mock_context.state.orchestrator.state.results = {
            "subordinate1": {"output": "sub result 1"},
            "subordinate2": {"output": "sub result 2"},
        }

        await node.run(mock_context)

        assert not mock_context.state.execution_summary["coordinator_executed"]
        assert mock_context.state.execution_summary["subordinates_executed"] == 2

    @pytest.mark.asyncio
    async def test_only_coordinator_present(self, node, mock_context):
        """Test processing with only coordinator results."""
        mock_context.state.orchestrator.state.results = {
            "coordinator": {"output": "coordinated result"}
        }

        await node.run(mock_context)

        assert mock_context.state.execution_summary["coordinator_executed"]
        assert mock_context.state.execution_summary["subordinates_executed"] == 0

    @pytest.mark.asyncio
    async def test_preserves_existing_processing_steps(self, node, mock_context):
        """Test that existing processing steps are preserved."""
        mock_context.state.processing_steps = ["step1", "step2"]

        await node.run(mock_context)

        assert mock_context.state.processing_steps == [
            "step1",
            "step2",
            "hierarchical_results_processed",
        ]

    @pytest.mark.asyncio
    async def test_empty_results(self, node, mock_context):
        """Test processing with empty results."""
        mock_context.state.orchestrator.state.results = {}

        result = await node.run(mock_context)

        assert isinstance(result, ValidateResults)
        assert not mock_context.state.execution_summary["coordinator_executed"]
        assert mock_context.state.execution_summary["subordinates_executed"] == 0

    @pytest.mark.asyncio
    async def test_results_access_exception(self, node, mock_context):
        """Test handling when results access fails."""
        mock_context.state.orchestrator.state.results = None

        result = await node.run(mock_context)

        assert isinstance(result, PatternError)
        assert mock_context.state.execution_status == ExecutionStatus.FAILED
        assert "Hierarchical result processing failed" in mock_context.state.errors[0]

    @pytest.mark.asyncio
    async def test_summary_update_exception(self, node, mock_context):
        """Test handling when summary update fails."""
        # Make execution_summary a Mock that raises on update
        mock_summary = Mock()
        mock_summary.update = Mock(side_effect=Exception("Update error"))
        mock_context.state.execution_summary = mock_summary

        result = await node.run(mock_context)

        assert isinstance(result, PatternError)
        assert mock_context.state.execution_status == ExecutionStatus.FAILED

    @pytest.mark.asyncio
    async def test_error_appends_to_existing(self, node, mock_context):
        """Test that errors are appended to existing error list."""
        mock_context.state.errors = ["existing_error"]
        mock_context.state.orchestrator.state.results = None

        await node.run(mock_context)

        assert len(mock_context.state.errors) == 2
        assert mock_context.state.errors[0] == "existing_error"
