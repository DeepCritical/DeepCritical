import time
from unittest.mock import Mock

import pytest

from DeepResearch.src.datatypes.workflow_patterns import InteractionPattern

# Adjust imports to match your project structure
from DeepResearch.src.statemachines.workflow_pattern_statemachines import (
    ExecutionStatus,
    FinalizePattern,
    PatternError,
)


class TestFinalizePattern:
    """Test suite for FinalizePattern node."""

    @pytest.fixture
    def mock_context(self):
        """Create a mock GraphRunContext."""
        ctx = Mock()
        ctx.state = Mock()
        ctx.state.start_time = time.time() - 10.0  # 10 seconds ago
        ctx.state.end_time = None
        ctx.state.interaction_pattern = InteractionPattern.COLLABORATIVE
        ctx.state.question = "What is the best approach?"
        ctx.state.execution_status = ExecutionStatus.RUNNING
        ctx.state.processing_steps = ["step1", "step2", "step3"]
        ctx.state.errors = []
        ctx.state.agent_ids = ["agent1", "agent2", "agent3"]
        ctx.state.final_result = {"output": "final answer"}
        ctx.state.execution_summary = {
            "total_rounds": 3,
            "agents_participated": 3,
            "consensus_reached": True,
            "consensus_confidence": 0.92,
        }
        ctx.state.interaction_state = Mock()
        ctx.state.interaction_state.get_summary = Mock(return_value={})
        ctx.state.metrics = Mock()
        ctx.state.metrics.__dict__ = {"token_count": 1500}
        return ctx

    @pytest.fixture
    def node(self):
        """Create FinalizePattern node instance."""
        return FinalizePattern()

    @pytest.mark.asyncio
    async def test_successful_finalization(self, node, mock_context):
        """Test successful pattern finalization."""
        result = await node.run(mock_context)

        # End object stores the value in .data
        assert isinstance(result.data, str)
        assert mock_context.state.end_time is not None
        assert "pattern_finalized" in mock_context.state.processing_steps
        assert len(mock_context.state.errors) == 0

    @pytest.mark.asyncio
    async def test_end_time_set(self, node, mock_context):
        """Test that end_time is set during finalization."""
        before_time = time.time()
        await node.run(mock_context)
        after_time = time.time()

        assert mock_context.state.end_time is not None
        assert before_time <= mock_context.state.end_time <= after_time

    @pytest.mark.asyncio
    async def test_output_contains_pattern_info(self, node, mock_context):
        """Test that output contains pattern information."""
        result = await node.run(mock_context)
        output = result.data

        assert "Collaborative Pattern Results" in output
        assert "What is the best approach?" in output
        assert "collaborative" in output
        assert "Status:" in output

    @pytest.mark.asyncio
    async def test_output_contains_execution_time(self, node, mock_context):
        """Test that output contains execution time."""
        result = await node.run(mock_context)
        output = result.data

        assert "Execution Time:" in output
        assert "s" in output  # seconds indicator

    @pytest.mark.asyncio
    async def test_output_contains_steps_completed(self, node, mock_context):
        """Test that output contains steps completed count."""
        result = await node.run(mock_context)
        output = result.data

        assert "Steps Completed: 3" in output

    @pytest.mark.asyncio
    async def test_output_contains_final_result(self, node, mock_context):
        """Test that output contains final result."""
        result = await node.run(mock_context)
        output = result.data

        assert "Final Result:" in output
        assert "final answer" in output

    @pytest.mark.asyncio
    async def test_output_contains_execution_summary(self, node, mock_context):
        """Test that output contains execution summary."""
        result = await node.run(mock_context)
        output = result.data

        assert "Execution Summary:" in output
        assert "Total Rounds: 3" in output
        assert "Agents Participated: 3" in output

    @pytest.mark.asyncio
    async def test_output_contains_consensus_info_for_collaborative(
        self, node, mock_context
    ):
        """Test that output contains consensus info for collaborative pattern."""
        mock_context.state.interaction_pattern = InteractionPattern.COLLABORATIVE
        result = await node.run(mock_context)
        output = result.data

        assert "Consensus Reached: True" in output
        assert "Consensus Confidence: 0.920" in output

    @pytest.mark.asyncio
    async def test_output_no_consensus_info_for_sequential(self, node, mock_context):
        """Test that output doesn't contain consensus info for sequential pattern."""
        mock_context.state.interaction_pattern = InteractionPattern.SEQUENTIAL
        result = await node.run(mock_context)
        output = result.data

        assert "Consensus Reached" not in output
        assert "Consensus Confidence" not in output

    @pytest.mark.asyncio
    async def test_output_contains_processing_steps(self, node, mock_context):
        """Test that output contains processing steps."""
        result = await node.run(mock_context)
        output = result.data

        assert "Processing Steps:" in output
        assert "- step1" in output
        assert "- step2" in output
        assert "- step3" in output

    @pytest.mark.asyncio
    async def test_output_contains_errors_when_present(self, node, mock_context):
        """Test that output contains errors when they exist."""
        mock_context.state.errors = ["error1", "error2"]
        result = await node.run(mock_context)
        output = result.data

        assert "Errors Encountered:" in output
        assert "- error1" in output
        assert "- error2" in output

    @pytest.mark.asyncio
    async def test_output_no_errors_section_when_empty(self, node, mock_context):
        """Test that output doesn't contain errors section when no errors."""
        mock_context.state.errors = []
        result = await node.run(mock_context)
        output = result.data

        assert "Errors Encountered:" not in output

    @pytest.mark.asyncio
    async def test_no_final_result_section_when_none(self, node, mock_context):
        """Test that final result section is omitted when None."""
        mock_context.state.final_result = None
        result = await node.run(mock_context)
        output = result.data

        assert "Final Result:" not in output

    @pytest.mark.asyncio
    async def test_empty_execution_summary(self, node, mock_context):
        """Test finalization with empty execution summary."""
        mock_context.state.execution_summary = {}
        result = await node.run(mock_context)
        output = result.data

        # Empty execution summary means no "Execution Summary:" section at all
        assert "Execution Summary:" not in output

    @pytest.mark.asyncio
    async def test_empty_processing_steps(self, node, mock_context):
        """Test finalization with empty processing steps."""
        mock_context.state.processing_steps = []

        _ = await node.run(mock_context)

        # Empty list gets pattern_finalized appended
        assert len(mock_context.state.processing_steps) == 1
        assert mock_context.state.processing_steps[0] == "pattern_finalized"

    @pytest.mark.asyncio
    async def test_preserves_existing_processing_steps(self, node, mock_context):
        """Test that existing processing steps are preserved."""
        initial_steps = ["step1", "step2", "step3"]
        mock_context.state.processing_steps = initial_steps.copy()

        await node.run(mock_context)

        assert mock_context.state.processing_steps == initial_steps + [
            "pattern_finalized"
        ]

    @pytest.mark.asyncio
    async def test_hierarchical_pattern_output(self, node, mock_context):
        """Test finalization for hierarchical pattern."""
        mock_context.state.interaction_pattern = InteractionPattern.HIERARCHICAL
        result = await node.run(mock_context)
        output = result.data

        assert "Hierarchical Pattern Results" in output
        assert "hierarchical" in output

    @pytest.mark.asyncio
    async def test_sequential_pattern_output(self, node, mock_context):
        """Test finalization for sequential pattern."""
        mock_context.state.interaction_pattern = InteractionPattern.SEQUENTIAL
        result = await node.run(mock_context)
        output = result.data

        assert "Sequential Pattern Results" in output
        assert "sequential" in output

    @pytest.mark.asyncio
    async def test_time_calculation_exception(self, node, mock_context):
        """Test handling when time calculation fails."""
        mock_context.state.start_time = "invalid"

        result = await node.run(mock_context)

        assert isinstance(result, PatternError)
        assert mock_context.state.execution_status == ExecutionStatus.FAILED
        assert "Pattern finalization failed" in mock_context.state.errors[0]

    @pytest.mark.asyncio
    async def test_output_formatting_exception(self, node, mock_context):
        """Test handling when output formatting fails."""
        # Cause exception by making question access fail
        type(mock_context.state).question = property(
            lambda self: (_ for _ in ()).throw(Exception("Format error"))
        )

        result = await node.run(mock_context)

        assert isinstance(result, PatternError)
        assert mock_context.state.execution_status == ExecutionStatus.FAILED

    @pytest.mark.asyncio
    async def test_error_appends_to_existing(self, node, mock_context):
        """Test that errors are appended to existing error list."""
        mock_context.state.errors = ["existing_error"]
        mock_context.state.start_time = None  # Cause an error

        await node.run(mock_context)

        assert len(mock_context.state.errors) == 2
        assert mock_context.state.errors[0] == "existing_error"

    @pytest.mark.asyncio
    async def test_execution_status_set_on_exception(self, node, mock_context):
        """Test that execution status is set to FAILED on exception."""
        mock_context.state.start_time = None

        await node.run(mock_context)

        assert mock_context.state.execution_status == ExecutionStatus.FAILED

    @pytest.mark.asyncio
    async def test_all_fields_present_in_output(self, node, mock_context):
        """Test that all expected fields are present in successful output."""
        result = await node.run(mock_context)
        output = result.data

        expected_fields = [
            "Pattern Results",
            "Question:",
            "Pattern:",
            "Status:",
            "Execution Time:",
            "Steps Completed:",
            "Final Result:",
            "Execution Summary:",
            "Processing Steps:",
        ]

        for field in expected_fields:
            assert field in output, f"Missing field: {field}"
