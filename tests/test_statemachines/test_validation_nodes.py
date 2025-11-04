from unittest.mock import Mock

import pytest

from DeepResearch.src.datatypes.workflow_patterns import InteractionPattern
from DeepResearch.src.statemachines.workflow_pattern_statemachines import (
    ExecutionStatus,
    FinalizePattern,
    PatternError,
    ValidateConsensus,
    ValidateResults,
)


class TestValidateConsensus:
    """Test suite for ValidateConsensus node."""

    @pytest.fixture
    def mock_context(self):
        """Create a mock GraphRunContext."""
        ctx = Mock()
        ctx.state = Mock()
        ctx.state.execution_summary = {"consensus_reached": True}
        ctx.state.errors = []
        ctx.state.processing_steps = []
        ctx.state.execution_status = None
        return ctx

    @pytest.fixture
    def node(self):
        """Create ValidateConsensus node instance."""
        return ValidateConsensus()

    @pytest.mark.asyncio
    async def test_successful_validation_with_consensus(self, node, mock_context):
        """Test successful validation when consensus is reached."""
        result = await node.run(mock_context)

        assert isinstance(result, FinalizePattern)
        assert "consensus_validated" in mock_context.state.processing_steps
        assert len(mock_context.state.errors) == 0

    @pytest.mark.asyncio
    async def test_consensus_not_reached(self, node, mock_context):
        """Test validation failure when consensus is not reached."""
        mock_context.state.execution_summary = {"consensus_reached": False}

        result = await node.run(mock_context)

        assert isinstance(result, PatternError)
        assert mock_context.state.execution_status == ExecutionStatus.FAILED
        assert (
            "Consensus was not reached in collaborative pattern"
            in mock_context.state.errors[0]
        )

    @pytest.mark.asyncio
    async def test_consensus_key_missing(self, node, mock_context):
        """Test validation when consensus_reached key is missing."""
        mock_context.state.execution_summary = {}

        result = await node.run(mock_context)

        assert isinstance(result, PatternError)
        assert mock_context.state.execution_status == ExecutionStatus.FAILED
        assert "Consensus was not reached" in mock_context.state.errors[0]

    @pytest.mark.asyncio
    async def test_preserves_existing_processing_steps(self, node, mock_context):
        """Test that existing processing steps are preserved."""
        mock_context.state.processing_steps = ["step1", "step2"]

        await node.run(mock_context)

        assert mock_context.state.processing_steps == [
            "step1",
            "step2",
            "consensus_validated",
        ]

    @pytest.mark.asyncio
    async def test_execution_summary_access_exception(self, node, mock_context):
        """Test handling when execution_summary access fails."""
        # Replace execution_summary with a Mock that throws on .get()
        mock_summary = Mock()
        mock_summary.get = Mock(side_effect=Exception("Access error"))
        mock_context.state.execution_summary = mock_summary

        result = await node.run(mock_context)

        assert isinstance(result, PatternError)
        assert mock_context.state.execution_status == ExecutionStatus.FAILED
        assert (
            "Consensus validation failed: Access error" in mock_context.state.errors[0]
        )

    @pytest.mark.asyncio
    async def test_error_appends_to_existing(self, node, mock_context):
        """Test that errors are appended to existing error list."""
        mock_context.state.errors = ["existing_error"]
        mock_context.state.execution_summary = {"consensus_reached": False}

        await node.run(mock_context)

        assert len(mock_context.state.errors) == 2
        assert mock_context.state.errors[0] == "existing_error"

    @pytest.mark.asyncio
    async def test_no_validation_step_on_failure(self, node, mock_context):
        """Test that consensus_validated step is not added on failure."""
        mock_context.state.execution_summary = {"consensus_reached": False}

        await node.run(mock_context)

        assert "consensus_validated" not in mock_context.state.processing_steps


class TestValidateResults:
    """Test suite for ValidateResults node."""

    @pytest.fixture
    def mock_context(self):
        """Create a mock GraphRunContext."""
        ctx = Mock()
        ctx.state = Mock()
        ctx.state.final_result = {"output": "some result"}
        ctx.state.interaction_pattern = InteractionPattern.SEQUENTIAL
        ctx.state.errors = []
        ctx.state.processing_steps = []
        ctx.state.execution_status = None
        return ctx

    @pytest.fixture
    def node(self):
        """Create ValidateResults node instance."""
        return ValidateResults()

    @pytest.mark.asyncio
    async def test_successful_validation_sequential(self, node, mock_context):
        """Test successful validation for sequential pattern."""
        mock_context.state.interaction_pattern = InteractionPattern.SEQUENTIAL
        mock_context.state.final_result = {"agent1": "result1", "agent2": "result2"}

        result = await node.run(mock_context)

        assert isinstance(result, FinalizePattern)
        assert "results_validated" in mock_context.state.processing_steps
        assert len(mock_context.state.errors) == 0

    @pytest.mark.asyncio
    async def test_successful_validation_hierarchical(self, node, mock_context):
        """Test successful validation for hierarchical pattern."""
        mock_context.state.interaction_pattern = InteractionPattern.HIERARCHICAL
        mock_context.state.final_result = {
            "coordinator": "coord_result",
            "subordinate1": "sub1_result",
        }

        result = await node.run(mock_context)

        assert isinstance(result, FinalizePattern)
        assert "results_validated" in mock_context.state.processing_steps
        assert len(mock_context.state.errors) == 0

    @pytest.mark.asyncio
    async def test_successful_validation_collaborative(self, node, mock_context):
        """Test successful validation for collaborative pattern (no specific format check)."""
        mock_context.state.interaction_pattern = InteractionPattern.COLLABORATIVE
        mock_context.state.final_result = "any result format"

        result = await node.run(mock_context)

        assert isinstance(result, FinalizePattern)
        assert "results_validated" in mock_context.state.processing_steps

    @pytest.mark.asyncio
    async def test_final_result_is_none(self, node, mock_context):
        """Test validation failure when final_result is None."""
        mock_context.state.final_result = None

        result = await node.run(mock_context)

        assert isinstance(result, PatternError)
        assert mock_context.state.execution_status == ExecutionStatus.FAILED
        assert "No final result generated" in mock_context.state.errors[0]

    @pytest.mark.asyncio
    async def test_sequential_pattern_invalid_format(self, node, mock_context):
        """Test validation failure when sequential pattern returns non-dict."""
        mock_context.state.interaction_pattern = InteractionPattern.SEQUENTIAL
        mock_context.state.final_result = "not a dict"

        result = await node.run(mock_context)

        assert isinstance(result, PatternError)
        assert mock_context.state.execution_status == ExecutionStatus.FAILED
        assert (
            "Sequential pattern should return dict result"
            in mock_context.state.errors[0]
        )

    @pytest.mark.asyncio
    async def test_hierarchical_pattern_not_dict(self, node, mock_context):
        """Test validation failure when hierarchical pattern returns non-dict."""
        mock_context.state.interaction_pattern = InteractionPattern.HIERARCHICAL
        mock_context.state.final_result = ["list", "not", "dict"]

        result = await node.run(mock_context)

        assert isinstance(result, PatternError)
        assert mock_context.state.execution_status == ExecutionStatus.FAILED
        assert (
            "Hierarchical pattern should return dict with coordinator"
            in mock_context.state.errors[0]
        )

    @pytest.mark.asyncio
    async def test_hierarchical_pattern_missing_coordinator(self, node, mock_context):
        """Test validation failure when hierarchical pattern dict lacks coordinator."""
        mock_context.state.interaction_pattern = InteractionPattern.HIERARCHICAL
        mock_context.state.final_result = {
            "subordinate1": "sub1_result",
            "subordinate2": "sub2_result",
        }

        result = await node.run(mock_context)

        assert isinstance(result, PatternError)
        assert mock_context.state.execution_status == ExecutionStatus.FAILED
        assert (
            "Hierarchical pattern should return dict with coordinator"
            in mock_context.state.errors[0]
        )

    @pytest.mark.asyncio
    async def test_preserves_existing_processing_steps(self, node, mock_context):
        """Test that existing processing steps are preserved."""
        mock_context.state.processing_steps = ["step1", "step2"]

        await node.run(mock_context)

        assert mock_context.state.processing_steps == [
            "step1",
            "step2",
            "results_validated",
        ]

    @pytest.mark.asyncio
    async def test_validation_exception(self, node, mock_context):
        """Test handling when validation logic raises an exception."""
        # Cause an exception by making final_result access fail
        type(mock_context.state).final_result = property(
            lambda self: (_ for _ in ()).throw(Exception("Pattern error"))
        )

        result = await node.run(mock_context)

        assert isinstance(result, PatternError)
        assert mock_context.state.execution_status == ExecutionStatus.FAILED
        assert "Result validation failed" in mock_context.state.errors[0]

    @pytest.mark.asyncio
    async def test_error_appends_to_existing(self, node, mock_context):
        """Test that errors are appended to existing error list."""
        mock_context.state.errors = ["existing_error"]
        mock_context.state.final_result = None

        await node.run(mock_context)

        assert len(mock_context.state.errors) == 2
        assert mock_context.state.errors[0] == "existing_error"

    @pytest.mark.asyncio
    async def test_no_validation_step_on_failure(self, node, mock_context):
        """Test that results_validated step is not added on failure."""
        mock_context.state.final_result = None

        await node.run(mock_context)

        assert "results_validated" not in mock_context.state.processing_steps

    @pytest.mark.asyncio
    async def test_sequential_empty_dict_is_valid(self, node, mock_context):
        """Test that empty dict is valid for sequential pattern."""
        mock_context.state.interaction_pattern = InteractionPattern.SEQUENTIAL
        mock_context.state.final_result = {}

        result = await node.run(mock_context)

        assert isinstance(result, FinalizePattern)

    @pytest.mark.asyncio
    async def test_hierarchical_empty_dict_invalid(self, node, mock_context):
        """Test that empty dict is invalid for hierarchical pattern (no coordinator)."""
        mock_context.state.interaction_pattern = InteractionPattern.HIERARCHICAL
        mock_context.state.final_result = {}

        result = await node.run(mock_context)

        assert isinstance(result, PatternError)
        assert "coordinator" in mock_context.state.errors[0]
