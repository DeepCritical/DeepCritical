from unittest.mock import AsyncMock, Mock

import pytest

from DeepResearch.src.statemachines.workflow_pattern_statemachines import (
    ExecuteCollaborativePattern,
    ExecuteHierarchicalPattern,
    ExecutePattern,
    ExecuteSequentialPattern,
    InteractionPattern,
    PatternError,
    ProcessCollaborativeResults,
    ProcessHierarchicalResults,
    ProcessSequentialResults,
)
from DeepResearch.src.utils.execution_status import ExecutionStatus


class TestExecuteCollaborativePattern:
    """Test suite for ExecuteCollaborativePattern node."""

    @pytest.fixture
    def mock_orchestrator(self):
        """Create a mock orchestrator."""
        orchestrator = Mock()
        orchestrator.execute_collaborative_pattern = AsyncMock()
        orchestrator.state = Mock()
        orchestrator.state.get_summary = Mock(
            return_value={"rounds": 3, "tokens": 1000}
        )
        return orchestrator

    @pytest.fixture
    def mock_context(self, mock_orchestrator):
        """Create a mock GraphRunContext."""
        ctx = Mock()
        ctx.state = Mock()
        ctx.state.orchestrator = mock_orchestrator
        ctx.state.final_result = None
        ctx.state.metrics = None
        ctx.state.errors = []
        ctx.state.processing_steps = []
        ctx.state.execution_status = None
        return ctx

    @pytest.fixture
    def node(self):
        """Create ExecuteCollaborativePattern node instance."""
        return ExecuteCollaborativePattern()

    @pytest.mark.asyncio
    async def test_successful_execution(self, node, mock_context, mock_orchestrator):
        """Test successful collaborative pattern execution."""
        mock_result = {"output": "collaborative result"}
        mock_orchestrator.execute_collaborative_pattern.return_value = mock_result

        result = await node.run(mock_context)

        assert isinstance(result, ProcessCollaborativeResults)
        assert mock_context.state.final_result == mock_result
        assert mock_context.state.metrics == {"rounds": 3, "tokens": 1000}
        assert "collaborative_pattern_executed" in mock_context.state.processing_steps
        assert len(mock_context.state.errors) == 0

    @pytest.mark.asyncio
    async def test_orchestrator_method_called(
        self, node, mock_context, mock_orchestrator
    ):
        """Test that orchestrator's execute method is called."""
        await node.run(mock_context)

        mock_orchestrator.execute_collaborative_pattern.assert_called_once()

    @pytest.mark.asyncio
    async def test_preserves_existing_processing_steps(self, node, mock_context):
        """Test that existing processing steps are preserved."""
        mock_context.state.processing_steps = ["step1", "step2"]

        await node.run(mock_context)

        assert mock_context.state.processing_steps == [
            "step1",
            "step2",
            "collaborative_pattern_executed",
        ]

    @pytest.mark.asyncio
    async def test_missing_orchestrator(self, node, mock_context):
        """Test handling when orchestrator is not initialized."""
        mock_context.state.orchestrator = None

        result = await node.run(mock_context)

        assert isinstance(result, PatternError)
        assert mock_context.state.execution_status == ExecutionStatus.FAILED
        assert "Collaborative pattern execution failed" in mock_context.state.errors[0]
        assert "Orchestrator not initialized" in mock_context.state.errors[0]

    @pytest.mark.asyncio
    async def test_execution_exception(self, node, mock_context, mock_orchestrator):
        """Test handling when execution raises an exception."""
        mock_orchestrator.execute_collaborative_pattern.side_effect = RuntimeError(
            "Execution failed"
        )

        result = await node.run(mock_context)

        assert isinstance(result, PatternError)
        assert mock_context.state.execution_status == ExecutionStatus.FAILED
        assert (
            "Collaborative pattern execution failed: Execution failed"
            in mock_context.state.errors[0]
        )

    @pytest.mark.asyncio
    async def test_metrics_retrieval_exception(
        self, node, mock_context, mock_orchestrator
    ):
        """Test handling when metrics retrieval fails."""
        mock_orchestrator.state.get_summary.side_effect = Exception("Metrics error")

        result = await node.run(mock_context)

        assert isinstance(result, PatternError)
        assert mock_context.state.execution_status == ExecutionStatus.FAILED

    @pytest.mark.asyncio
    async def test_error_appends_to_existing(self, node, mock_context):
        """Test that errors are appended to existing error list."""
        mock_context.state.errors = ["existing_error"]
        mock_context.state.orchestrator = None

        await node.run(mock_context)

        assert len(mock_context.state.errors) == 2
        assert mock_context.state.errors[0] == "existing_error"


class TestExecuteSequentialPattern:
    """Test suite for ExecuteSequentialPattern node."""

    @pytest.fixture
    def mock_orchestrator(self):
        """Create a mock orchestrator."""
        orchestrator = Mock()
        orchestrator.execute_sequential_pattern = AsyncMock()
        orchestrator.state = Mock()
        orchestrator.state.get_summary = Mock(return_value={"steps": 5, "time": 120})
        return orchestrator

    @pytest.fixture
    def mock_context(self, mock_orchestrator):
        """Create a mock GraphRunContext."""
        ctx = Mock()
        ctx.state = Mock()
        ctx.state.orchestrator = mock_orchestrator
        ctx.state.final_result = None
        ctx.state.metrics = None
        ctx.state.errors = []
        ctx.state.processing_steps = []
        ctx.state.execution_status = None
        return ctx

    @pytest.fixture
    def node(self):
        """Create ExecuteSequentialPattern node instance."""
        return ExecuteSequentialPattern()

    @pytest.mark.asyncio
    async def test_successful_execution(self, node, mock_context, mock_orchestrator):
        """Test successful sequential pattern execution."""
        mock_result = {"output": "sequential result"}
        mock_orchestrator.execute_sequential_pattern.return_value = mock_result

        result = await node.run(mock_context)

        assert isinstance(result, ProcessSequentialResults)
        assert mock_context.state.final_result == mock_result
        assert mock_context.state.metrics == {"steps": 5, "time": 120}
        assert "sequential_pattern_executed" in mock_context.state.processing_steps
        assert len(mock_context.state.errors) == 0

    @pytest.mark.asyncio
    async def test_orchestrator_method_called(
        self, node, mock_context, mock_orchestrator
    ):
        """Test that orchestrator's execute method is called."""
        await node.run(mock_context)

        mock_orchestrator.execute_sequential_pattern.assert_called_once()

    @pytest.mark.asyncio
    async def test_preserves_existing_processing_steps(self, node, mock_context):
        """Test that existing processing steps are preserved."""
        mock_context.state.processing_steps = ["step1", "step2"]

        await node.run(mock_context)

        assert mock_context.state.processing_steps == [
            "step1",
            "step2",
            "sequential_pattern_executed",
        ]

    @pytest.mark.asyncio
    async def test_missing_orchestrator(self, node, mock_context):
        """Test handling when orchestrator is not initialized."""
        mock_context.state.orchestrator = None

        result = await node.run(mock_context)

        assert isinstance(result, PatternError)
        assert mock_context.state.execution_status == ExecutionStatus.FAILED
        assert "Sequential pattern execution failed" in mock_context.state.errors[0]
        assert "Orchestrator not initialized" in mock_context.state.errors[0]

    @pytest.mark.asyncio
    async def test_execution_exception(self, node, mock_context, mock_orchestrator):
        """Test handling when execution raises an exception."""
        mock_orchestrator.execute_sequential_pattern.side_effect = ValueError(
            "Invalid sequence"
        )

        result = await node.run(mock_context)

        assert isinstance(result, PatternError)
        assert mock_context.state.execution_status == ExecutionStatus.FAILED
        assert (
            "Sequential pattern execution failed: Invalid sequence"
            in mock_context.state.errors[0]
        )

    @pytest.mark.asyncio
    async def test_metrics_retrieval_exception(
        self, node, mock_context, mock_orchestrator
    ):
        """Test handling when metrics retrieval fails."""
        mock_orchestrator.state.get_summary.side_effect = Exception("Metrics error")

        result = await node.run(mock_context)

        assert isinstance(result, PatternError)
        assert mock_context.state.execution_status == ExecutionStatus.FAILED

    @pytest.mark.asyncio
    async def test_error_appends_to_existing(self, node, mock_context):
        """Test that errors are appended to existing error list."""
        mock_context.state.errors = ["existing_error"]
        mock_context.state.orchestrator = None

        await node.run(mock_context)

        assert len(mock_context.state.errors) == 2
        assert mock_context.state.errors[0] == "existing_error"


class TestExecuteHierarchicalPattern:
    """Test suite for ExecuteHierarchicalPattern node."""

    @pytest.fixture
    def mock_orchestrator(self):
        """Create a mock orchestrator."""
        orchestrator = Mock()
        orchestrator.execute_hierarchical_pattern = AsyncMock()
        orchestrator.state = Mock()
        orchestrator.state.get_summary = Mock(return_value={"levels": 3, "agents": 7})
        return orchestrator

    @pytest.fixture
    def mock_context(self, mock_orchestrator):
        """Create a mock GraphRunContext."""
        ctx = Mock()
        ctx.state = Mock()
        ctx.state.orchestrator = mock_orchestrator
        ctx.state.final_result = None
        ctx.state.metrics = None
        ctx.state.errors = []
        ctx.state.processing_steps = []
        ctx.state.execution_status = None
        return ctx

    @pytest.fixture
    def node(self):
        """Create ExecuteHierarchicalPattern node instance."""
        return ExecuteHierarchicalPattern()

    @pytest.mark.asyncio
    async def test_successful_execution(self, node, mock_context, mock_orchestrator):
        """Test successful hierarchical pattern execution."""
        mock_result = {"output": "hierarchical result"}
        mock_orchestrator.execute_hierarchical_pattern.return_value = mock_result

        result = await node.run(mock_context)

        assert isinstance(result, ProcessHierarchicalResults)
        assert mock_context.state.final_result == mock_result
        assert mock_context.state.metrics == {"levels": 3, "agents": 7}
        assert "hierarchical_pattern_executed" in mock_context.state.processing_steps
        assert len(mock_context.state.errors) == 0

    @pytest.mark.asyncio
    async def test_orchestrator_method_called(
        self, node, mock_context, mock_orchestrator
    ):
        """Test that orchestrator's execute method is called."""
        await node.run(mock_context)

        mock_orchestrator.execute_hierarchical_pattern.assert_called_once()

    @pytest.mark.asyncio
    async def test_preserves_existing_processing_steps(self, node, mock_context):
        """Test that existing processing steps are preserved."""
        mock_context.state.processing_steps = ["step1", "step2"]

        await node.run(mock_context)

        assert mock_context.state.processing_steps == [
            "step1",
            "step2",
            "hierarchical_pattern_executed",
        ]

    @pytest.mark.asyncio
    async def test_missing_orchestrator(self, node, mock_context):
        """Test handling when orchestrator is not initialized."""
        mock_context.state.orchestrator = None

        result = await node.run(mock_context)

        assert isinstance(result, PatternError)
        assert mock_context.state.execution_status == ExecutionStatus.FAILED
        assert "Hierarchical pattern execution failed" in mock_context.state.errors[0]
        assert "Orchestrator not initialized" in mock_context.state.errors[0]

    @pytest.mark.asyncio
    async def test_execution_exception(self, node, mock_context, mock_orchestrator):
        """Test handling when execution raises an exception."""
        mock_orchestrator.execute_hierarchical_pattern.side_effect = TypeError(
            "Invalid hierarchy"
        )

        result = await node.run(mock_context)

        assert isinstance(result, PatternError)
        assert mock_context.state.execution_status == ExecutionStatus.FAILED
        assert (
            "Hierarchical pattern execution failed: Invalid hierarchy"
            in mock_context.state.errors[0]
        )

    @pytest.mark.asyncio
    async def test_metrics_retrieval_exception(
        self, node, mock_context, mock_orchestrator
    ):
        """Test handling when metrics retrieval fails."""
        mock_orchestrator.state.get_summary.side_effect = Exception("Metrics error")

        result = await node.run(mock_context)

        assert isinstance(result, PatternError)
        assert mock_context.state.execution_status == ExecutionStatus.FAILED

    @pytest.mark.asyncio
    async def test_error_appends_to_existing(self, node, mock_context):
        """Test that errors are appended to existing error list."""
        mock_context.state.errors = ["existing_error"]
        mock_context.state.orchestrator = None

        await node.run(mock_context)

        assert len(mock_context.state.errors) == 2
        assert mock_context.state.errors[0] == "existing_error"


class TestExecutePattern:
    """Test suite for ExecutePattern node."""

    @pytest.fixture
    def mock_context(self):
        """Create a mock GraphRunContext."""
        ctx = Mock()
        ctx.state = Mock()
        ctx.state.interaction_pattern = InteractionPattern.COLLABORATIVE
        ctx.state.errors = []
        return ctx

    @pytest.fixture
    def node(self):
        """Create ExecutePattern node instance."""
        return ExecutePattern()

    @pytest.mark.asyncio
    async def test_returns_collaborative_pattern_node(self, node, mock_context):
        """Test that collaborative pattern returns ExecuteCollaborativePattern."""
        mock_context.state.interaction_pattern = InteractionPattern.COLLABORATIVE

        result = await node.run(mock_context)

        assert isinstance(result, ExecuteCollaborativePattern)
        assert len(mock_context.state.errors) == 0

    @pytest.mark.asyncio
    async def test_returns_sequential_pattern_node(self, node, mock_context):
        """Test that sequential pattern returns ExecuteSequentialPattern."""
        mock_context.state.interaction_pattern = InteractionPattern.SEQUENTIAL

        result = await node.run(mock_context)

        assert isinstance(result, ExecuteSequentialPattern)
        assert len(mock_context.state.errors) == 0

    @pytest.mark.asyncio
    async def test_returns_hierarchical_pattern_node(self, node, mock_context):
        """Test that hierarchical pattern returns ExecuteHierarchicalPattern."""
        mock_context.state.interaction_pattern = InteractionPattern.HIERARCHICAL

        result = await node.run(mock_context)

        assert isinstance(result, ExecuteHierarchicalPattern)
        assert len(mock_context.state.errors) == 0

    @pytest.mark.asyncio
    async def test_unsupported_pattern_returns_error(self, node, mock_context):
        """Test that unsupported pattern returns PatternError."""
        # Create a mock pattern that's not in the supported list
        mock_context.state.interaction_pattern = Mock()
        mock_context.state.interaction_pattern.__eq__ = lambda self, other: False

        result = await node.run(mock_context)

        assert isinstance(result, PatternError)
        assert len(mock_context.state.errors) == 1
        assert "Unsupported pattern:" in mock_context.state.errors[0]

    @pytest.mark.asyncio
    async def test_unsupported_pattern_appends_error(self, node, mock_context):
        """Test that unsupported pattern error is appended to existing errors."""
        mock_context.state.errors = ["existing_error"]
        mock_context.state.interaction_pattern = Mock()
        mock_context.state.interaction_pattern.__eq__ = lambda self, other: False

        await node.run(mock_context)

        assert len(mock_context.state.errors) == 2
        assert mock_context.state.errors[0] == "existing_error"
        assert "Unsupported pattern:" in mock_context.state.errors[1]

    @pytest.mark.asyncio
    async def test_none_pattern_returns_error(self, node, mock_context):
        """Test that None pattern returns PatternError."""
        mock_context.state.interaction_pattern = None

        result = await node.run(mock_context)

        assert isinstance(result, PatternError)
        assert len(mock_context.state.errors) == 1

    @pytest.mark.asyncio
    async def test_all_enum_values_supported(self, node, mock_context):
        """Test that all InteractionPattern enum values are supported."""
        patterns = [
            (InteractionPattern.COLLABORATIVE, ExecuteCollaborativePattern),
            (InteractionPattern.SEQUENTIAL, ExecuteSequentialPattern),
            (InteractionPattern.HIERARCHICAL, ExecuteHierarchicalPattern),
        ]

        for pattern, expected_node_type in patterns:
            mock_context.state.interaction_pattern = pattern
            mock_context.state.errors = []

            result = await node.run(mock_context)

            assert isinstance(result, expected_node_type), (
                f"Pattern {pattern} should return {expected_node_type.__name__}"
            )
            assert len(mock_context.state.errors) == 0, (
                f"Pattern {pattern} should not generate errors"
            )

    @pytest.mark.asyncio
    async def test_collaborative_returns_new_instance(self, node, mock_context):
        """Test that each call returns a new instance."""
        mock_context.state.interaction_pattern = InteractionPattern.COLLABORATIVE

        result1 = await node.run(mock_context)
        result2 = await node.run(mock_context)

        assert isinstance(result1, ExecuteCollaborativePattern)
        assert isinstance(result2, ExecuteCollaborativePattern)
        assert result1 is not result2  # Different instances

    @pytest.mark.asyncio
    async def test_sequential_returns_new_instance(self, node, mock_context):
        """Test that sequential pattern returns new instance each time."""
        mock_context.state.interaction_pattern = InteractionPattern.SEQUENTIAL

        result1 = await node.run(mock_context)
        result2 = await node.run(mock_context)

        assert result1 is not result2

    @pytest.mark.asyncio
    async def test_hierarchical_returns_new_instance(self, node, mock_context):
        """Test that hierarchical pattern returns new instance each time."""
        mock_context.state.interaction_pattern = InteractionPattern.HIERARCHICAL

        result1 = await node.run(mock_context)
        result2 = await node.run(mock_context)

        assert result1 is not result2

    @pytest.mark.asyncio
    async def test_error_returns_new_instance(self, node, mock_context):
        """Test that error case returns new PatternError instance each time."""
        mock_context.state.interaction_pattern = None

        result1 = await node.run(mock_context)
        result2 = await node.run(mock_context)

        assert isinstance(result1, PatternError)
        assert isinstance(result2, PatternError)
        assert result1 is not result2
