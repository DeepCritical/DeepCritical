import time
from unittest.mock import Mock, patch

import pytest

from DeepResearch.src.datatypes.agents import AgentType
from DeepResearch.src.datatypes.workflow_patterns import (
    InteractionPattern,
)
from DeepResearch.src.statemachines.workflow_pattern_statemachines import (
    ExecutePattern,
    InitializePattern,
    PatternError,
    SetupAgents,
    WorkflowPatternState,
)
from DeepResearch.src.utils.execution_status import ExecutionStatus
from DeepResearch.src.utils.workflow_patterns import (
    ConsensusAlgorithm,
    InteractionMetrics,
    MessageRoutingStrategy,
)


@pytest.fixture
def mock_context():
    """Create a mock GraphRunContext with all required state attributes."""
    ctx = Mock()
    ctx.state = Mock()
    ctx.state.interaction_pattern = "round_robin"
    ctx.state.agent_ids = ["agent1", "agent2"]
    ctx.state.agent_types = {"agent1": AgentType.EXECUTOR, "agent2": AgentType.EXECUTOR}
    ctx.state.agent_executors = {"agent1": Mock(), "agent2": Mock()}
    ctx.state.errors = []
    ctx.state.processing_steps = []
    ctx.state.execution_status = None
    ctx.state.interaction_state = None
    ctx.state.orchestrator = None
    return ctx


@pytest.fixture
def node():
    """Create InitializePattern node instance."""
    return InitializePattern()


@pytest.fixture
def mock_orchestrator():
    """Create a mock orchestrator."""
    orchestrator = Mock()
    orchestrator.register_agent_executor = Mock()
    return orchestrator


@pytest.fixture
def mock_interaction_state():
    """Create a mock interaction state."""
    return Mock()


class TestWorkflowPatternState:
    def test_default_initialization_independent_fields(self):
        """Ensure that default lists/dicts are not shared across instances."""
        state1 = WorkflowPatternState(question="Q1")
        state2 = WorkflowPatternState(question="Q2")

        # Defaults are independent objects
        assert state1.agent_ids == []
        assert state2.agent_ids == []
        assert state1.agent_ids is not state2.agent_ids

        assert state1.agent_types == {}
        assert state1.agent_types is not state2.agent_types

        assert state1.processing_steps is not state2.processing_steps
        assert state1.errors is not state2.errors
        assert state1.execution_summary is not state2.execution_summary
        assert state1.agent_executors is not state2.agent_executors

    def test_default_enum_and_time_fields(self):
        """Check that default enum and timing fields are set correctly."""
        before = time.time()
        state = WorkflowPatternState(question="Timing test")
        after = time.time()

        assert state.interaction_pattern == InteractionPattern.COLLABORATIVE
        assert state.execution_status == ExecutionStatus.PENDING
        assert isinstance(state.metrics, InteractionMetrics)
        assert isinstance(state.start_time, float)
        # start_time should be close to creation time
        assert before <= state.start_time <= after
        assert state.end_time is None
        assert state.message_routing == MessageRoutingStrategy.DIRECT
        assert state.consensus_algorithm == ConsensusAlgorithm.SIMPLE_AGREEMENT

    def test_custom_initialization_with_full_arguments(self, mocker):
        """Provide all possible arguments and verify they're stored correctly."""
        mock_config = mocker.MagicMock()
        mock_interaction_state = mocker.MagicMock()
        mock_orchestrator = mocker.MagicMock()
        mock_metrics = mocker.MagicMock()
        agent_types = {
            "agent1": mocker.MagicMock(spec=AgentType),
            "agent2": mocker.MagicMock(spec=AgentType),
        }
        state = WorkflowPatternState(
            question="Test",
            config=mock_config,
            interaction_pattern=InteractionPattern.SEQUENTIAL,
            agent_ids=["agent1", "agent2"],
            agent_types=agent_types,
            interaction_state=mock_interaction_state,
            orchestrator=mock_orchestrator,
            metrics=mock_metrics,
            final_result="Success",
            execution_summary={"steps": 3},
            processing_steps=["init", "process"],
            errors=["minor error"],
            execution_status=ExecutionStatus.SUCCESS,
            start_time=123.456,
            end_time=789.0,
            agent_executors={"agent1": mocker.MagicMock()},
            message_routing=MessageRoutingStrategy.BROADCAST,
            consensus_algorithm=ConsensusAlgorithm.MAJORITY_VOTE,
        )

        assert state.question == "Test"
        assert state.config is mock_config
        assert state.interaction_pattern == InteractionPattern.SEQUENTIAL
        assert state.agent_ids == ["agent1", "agent2"]
        assert state.agent_types["agent1"] == agent_types["agent1"]
        assert state.interaction_state is mock_interaction_state
        assert state.orchestrator is mock_orchestrator
        assert state.metrics is mock_metrics
        assert state.final_result == "Success"
        assert state.execution_summary == {"steps": 3}
        assert state.errors == ["minor error"]
        assert state.execution_status == ExecutionStatus.SUCCESS
        assert state.start_time == 123.456
        assert state.end_time == 789.0
        assert state.message_routing == MessageRoutingStrategy.BROADCAST
        assert state.consensus_algorithm == ConsensusAlgorithm.MAJORITY_VOTE

    def test_mutability_and_state_progression(self):
        """Ensure that mutable fields behave and status updates are valid."""
        state = WorkflowPatternState(question="Mutability check")

        state.agent_ids.append("A1")
        state.errors.append("error A")
        state.processing_steps.extend(["step1", "step2"])
        state.execution_status = ExecutionStatus.RUNNING
        state.final_result = {"result": 42}
        state.end_time = time.time()

        assert state.agent_ids == ["A1"]
        assert state.errors == ["error A"]
        assert state.processing_steps == ["step1", "step2"]
        assert state.execution_status == ExecutionStatus.RUNNING
        assert isinstance(state.end_time, float)
        assert state.end_time >= state.start_time
        assert state.final_result is not None
        assert state.final_result["result"] == 42

    @pytest.mark.parametrize("question", ["", None])
    def test_question_accepts_any_value(self, question):
        """Even if question is None or empty, dataclass should still initialize."""
        state = WorkflowPatternState(question=question)
        assert state.question == question


class TestInitializePattern:
    """Comprehensive test suite for InitializePattern node."""

    @pytest.mark.asyncio
    async def test_basic_initialization(self, node, mock_context):
        """Test successful initialization with valid inputs."""
        mock_interaction_state = Mock()
        mock_orchestrator = Mock()

        with (
            patch(
                "DeepResearch.src.statemachines.workflow_pattern_statemachines.create_interaction_state",
                return_value=mock_interaction_state,
            ),
            patch(
                "DeepResearch.src.statemachines.workflow_pattern_statemachines.create_workflow_orchestrator",
                return_value=mock_orchestrator,
            ),
        ):
            result = await node.run(mock_context)

            assert isinstance(result, SetupAgents)
            assert mock_context.state.interaction_state == mock_interaction_state
            assert mock_context.state.orchestrator == mock_orchestrator
            assert mock_context.state.execution_status == ExecutionStatus.RUNNING
            assert "pattern_initialized" in mock_context.state.processing_steps
            assert len(mock_context.state.errors) == 0

    @pytest.mark.asyncio
    async def test_state_creation_with_correct_params(self, node, mock_context):
        """Test that interaction state is created with correct parameters."""
        with (
            patch(
                "DeepResearch.src.statemachines.workflow_pattern_statemachines.create_interaction_state"
            ) as mock_create_state,
            patch(
                "DeepResearch.src.statemachines.workflow_pattern_statemachines.create_workflow_orchestrator"
            ),
        ):
            await node.run(mock_context)

            mock_create_state.assert_called_once_with(
                pattern=mock_context.state.interaction_pattern,
                agents=mock_context.state.agent_ids,
                agent_types=mock_context.state.agent_types,
            )

    @pytest.mark.asyncio
    async def test_orchestrator_creation_with_correct_params(self, node, mock_context):
        """Test that orchestrator is created with correct parameters."""
        mock_interaction_state = Mock()

        with (
            patch(
                "DeepResearch.src.statemachines.workflow_pattern_statemachines.create_interaction_state",
                return_value=mock_interaction_state,
            ),
            patch(
                "DeepResearch.src.statemachines.workflow_pattern_statemachines.create_workflow_orchestrator"
            ) as mock_create_orch,
        ):
            await node.run(mock_context)

            mock_create_orch.assert_called_once_with(
                mock_interaction_state, mock_context.state.agent_executors
            )

    @pytest.mark.asyncio
    async def test_preserves_existing_processing_steps(self, node, mock_context):
        """Test that existing processing steps are preserved."""
        mock_context.state.processing_steps = ["step1", "step2"]

        with (
            patch(
                "DeepResearch.src.statemachines.workflow_pattern_statemachines.create_interaction_state"
            ),
            patch(
                "DeepResearch.src.statemachines.workflow_pattern_statemachines.create_workflow_orchestrator"
            ),
        ):
            await node.run(mock_context)

            assert mock_context.state.processing_steps == [
                "step1",
                "step2",
                "pattern_initialized",
            ]

    @pytest.mark.asyncio
    async def test_state_creation_failure(self, node, mock_context):
        """Test handling when interaction state creation fails."""
        with patch(
            "DeepResearch.src.statemachines.workflow_pattern_statemachines.create_interaction_state",
            side_effect=ValueError("Invalid pattern"),
        ):
            result = await node.run(mock_context)

            assert isinstance(result, PatternError)
            assert mock_context.state.execution_status == ExecutionStatus.FAILED
            assert len(mock_context.state.errors) == 1
            assert (
                "Pattern initialization failed: Invalid pattern"
                in mock_context.state.errors[0]
            )

    @pytest.mark.asyncio
    async def test_orchestrator_creation_failure(self, node, mock_context):
        """Test handling when orchestrator creation fails."""
        with (
            patch(
                "DeepResearch.src.statemachines.workflow_pattern_statemachines.create_interaction_state"
            ),
            patch(
                "DeepResearch.src.statemachines.workflow_pattern_statemachines.create_workflow_orchestrator",
                side_effect=RuntimeError("Orchestrator error"),
            ),
        ):
            result = await node.run(mock_context)

            assert isinstance(result, PatternError)
            assert mock_context.state.execution_status == ExecutionStatus.FAILED
            assert (
                "Pattern initialization failed: Orchestrator error"
                in mock_context.state.errors[0]
            )

    @pytest.mark.asyncio
    async def test_generic_exception_handling(self, node, mock_context):
        """Test handling of unexpected exceptions."""
        with patch(
            "DeepResearch.src.statemachines.workflow_pattern_statemachines.create_interaction_state",
            side_effect=Exception("Unexpected error"),
        ):
            result = await node.run(mock_context)

            assert isinstance(result, PatternError)
            assert mock_context.state.execution_status == ExecutionStatus.FAILED
            assert (
                "Pattern initialization failed: Unexpected error"
                in mock_context.state.errors[0]
            )

    @pytest.mark.asyncio
    async def test_error_appends_not_replaces(self, node, mock_context):
        """Test that errors are appended to existing error list."""
        mock_context.state.errors = ["existing_error"]

        with patch(
            "DeepResearch.src.statemachines.workflow_pattern_statemachines.create_interaction_state",
            side_effect=ValueError("New error"),
        ):
            await node.run(mock_context)

            assert len(mock_context.state.errors) == 2
            assert mock_context.state.errors[0] == "existing_error"
            assert (
                "Pattern initialization failed: New error"
                in mock_context.state.errors[1]
            )

    @pytest.mark.asyncio
    async def test_state_not_modified_on_failure(self, node, mock_context):
        """Test that state attributes remain unchanged when initialization fails."""
        with patch(
            "DeepResearch.src.statemachines.workflow_pattern_statemachines.create_interaction_state",
            side_effect=ValueError("Error"),
        ):
            await node.run(mock_context)

            assert mock_context.state.interaction_state is None
            assert mock_context.state.orchestrator is None
            assert len(mock_context.state.processing_steps) == 0

    @pytest.mark.asyncio
    async def test_empty_agent_list(self, node, mock_context):
        """Test initialization with empty agent list."""
        mock_context.state.agent_ids = []
        mock_context.state.agent_types = []

        with (
            patch(
                "DeepResearch.src.statemachines.workflow_pattern_statemachines.create_interaction_state"
            ) as mock_create,
            patch(
                "DeepResearch.src.statemachines.workflow_pattern_statemachines.create_workflow_orchestrator"
            ),
        ):
            await node.run(mock_context)

            mock_create.assert_called_once()
            assert mock_create.call_args[1]["agents"] == []

    @pytest.mark.asyncio
    async def test_single_agent(self, node, mock_context):
        """Test initialization with a single agent."""
        mock_context.state.agent_ids = ["solo_agent"]
        mock_context.state.agent_types = ["solo_type"]

        with (
            patch(
                "DeepResearch.src.statemachines.workflow_pattern_statemachines.create_interaction_state"
            ),
            patch(
                "DeepResearch.src.statemachines.workflow_pattern_statemachines.create_workflow_orchestrator"
            ),
        ):
            result = await node.run(mock_context)

            assert isinstance(result, SetupAgents)

    @pytest.mark.asyncio
    async def test_empty_executors_dict(self, node, mock_context):
        """Test initialization with empty executor dictionary."""
        mock_context.state.agent_executors = {}

        with (
            patch(
                "DeepResearch.src.statemachines.workflow_pattern_statemachines.create_interaction_state"
            ),
            patch(
                "DeepResearch.src.statemachines.workflow_pattern_statemachines.create_workflow_orchestrator"
            ) as mock_orch,
        ):
            await node.run(mock_context)

            assert mock_orch.call_args[0][1] == {}


class TestSetupAgents:
    """Comprehensive test suite for SetupAgents node."""

    @pytest.fixture
    def mock_orchestrator(self):
        """Create a mock orchestrator."""
        orchestrator = Mock()
        orchestrator.register_agent_executor = Mock()
        return orchestrator

    @pytest.fixture
    def mock_interaction_state(self):
        """Create a mock interaction state."""
        return Mock()

    @pytest.fixture
    def mock_context(self, mock_orchestrator, mock_interaction_state):
        """Create a mock GraphRunContext with all required state attributes."""
        ctx = Mock()
        ctx.state = Mock()
        ctx.state.orchestrator = mock_orchestrator
        ctx.state.interaction_state = mock_interaction_state
        ctx.state.agent_executors = {
            "agent1": Mock(),
            "agent2": Mock(),
        }
        ctx.state.errors = []
        ctx.state.processing_steps = []
        ctx.state.execution_status = None
        return ctx

    @pytest.fixture
    def node(self):
        """Create SetupAgents node instance."""
        return SetupAgents()

    @pytest.mark.asyncio
    async def test_successful_setup(self, node, mock_context, mock_orchestrator):
        """Test successful agent setup with valid state."""
        with patch(
            "DeepResearch.src.statemachines.workflow_pattern_statemachines.WorkflowPatternUtils.validate_interaction_state",
            return_value=[],
        ):
            result = await node.run(mock_context)

            assert isinstance(result, ExecutePattern)
            assert "agents_setup" in mock_context.state.processing_steps
            assert len(mock_context.state.errors) == 0
            assert mock_orchestrator.register_agent_executor.call_count == 2

    @pytest.mark.asyncio
    async def test_registers_all_executors(self, node, mock_context, mock_orchestrator):
        """Test that all agent executors are registered correctly."""
        executor1 = Mock()
        executor2 = Mock()
        mock_context.state.agent_executors = {
            "agent1": executor1,
            "agent2": executor2,
        }

        with patch(
            "DeepResearch.src.statemachines.workflow_pattern_statemachines.WorkflowPatternUtils.validate_interaction_state",
            return_value=[],
        ):
            await node.run(mock_context)

            mock_orchestrator.register_agent_executor.assert_any_call(
                "agent1", executor1
            )
            mock_orchestrator.register_agent_executor.assert_any_call(
                "agent2", executor2
            )

    @pytest.mark.asyncio
    async def test_validation_calls_with_correct_state(
        self, node, mock_context, mock_interaction_state
    ):
        """Test that validation is called with the correct interaction state."""
        with patch(
            "DeepResearch.src.statemachines.workflow_pattern_statemachines.WorkflowPatternUtils.validate_interaction_state"
        ) as mock_validate:
            mock_validate.return_value = []

            await node.run(mock_context)

            mock_validate.assert_called_once_with(mock_interaction_state)

    @pytest.mark.asyncio
    async def test_preserves_existing_processing_steps(self, node, mock_context):
        """Test that existing processing steps are preserved."""
        mock_context.state.processing_steps = ["step1", "step2"]

        with patch(
            "DeepResearch.src.statemachines.workflow_pattern_statemachines.WorkflowPatternUtils.validate_interaction_state",
            return_value=[],
        ):
            await node.run(mock_context)

            assert mock_context.state.processing_steps == [
                "step1",
                "step2",
                "agents_setup",
            ]

    @pytest.mark.asyncio
    async def test_missing_orchestrator(self, node, mock_context):
        """Test handling when orchestrator is not initialized."""
        mock_context.state.orchestrator = None

        result = await node.run(mock_context)

        assert isinstance(result, PatternError)
        assert mock_context.state.execution_status == ExecutionStatus.FAILED
        assert len(mock_context.state.errors) == 1
        assert "Agent setup failed" in mock_context.state.errors[0]
        assert (
            "Orchestrator or interaction state not initialized"
            in mock_context.state.errors[0]
        )

    @pytest.mark.asyncio
    async def test_missing_interaction_state(self, node, mock_context):
        """Test handling when interaction state is not initialized."""
        mock_context.state.interaction_state = None

        result = await node.run(mock_context)

        assert isinstance(result, PatternError)
        assert mock_context.state.execution_status == ExecutionStatus.FAILED
        assert (
            "Orchestrator or interaction state not initialized"
            in mock_context.state.errors[0]
        )

    @pytest.mark.asyncio
    async def test_both_orchestrator_and_state_missing(self, node, mock_context):
        """Test handling when both orchestrator and interaction state are missing."""
        mock_context.state.orchestrator = None
        mock_context.state.interaction_state = None

        result = await node.run(mock_context)

        assert isinstance(result, PatternError)
        assert mock_context.state.execution_status == ExecutionStatus.FAILED

    @pytest.mark.asyncio
    async def test_validation_errors_returns_pattern_error(self, node, mock_context):
        """Test that validation errors result in PatternError."""
        validation_errors = ["Error 1", "Error 2"]

        with patch(
            "DeepResearch.src.statemachines.workflow_pattern_statemachines.WorkflowPatternUtils.validate_interaction_state",
            return_value=validation_errors,
        ):
            result = await node.run(mock_context)

            assert isinstance(result, PatternError)
            assert validation_errors[0] in mock_context.state.errors
            assert validation_errors[1] in mock_context.state.errors

    @pytest.mark.asyncio
    async def test_validation_errors_extend_existing_errors(self, node, mock_context):
        """Test that validation errors are appended to existing errors."""
        mock_context.state.errors = ["existing_error"]
        validation_errors = ["validation_error_1", "validation_error_2"]

        with patch(
            "DeepResearch.src.statemachines.workflow_pattern_statemachines.WorkflowPatternUtils.validate_interaction_state",
            return_value=validation_errors,
        ):
            await node.run(mock_context)

            assert len(mock_context.state.errors) == 3
            assert mock_context.state.errors[0] == "existing_error"
            assert "validation_error_1" in mock_context.state.errors
            assert "validation_error_2" in mock_context.state.errors

    @pytest.mark.asyncio
    async def test_validation_errors_no_agents_setup_step(self, node, mock_context):
        """Test that agents_setup step is not added when validation fails."""
        with patch(
            "DeepResearch.src.statemachines.workflow_pattern_statemachines.WorkflowPatternUtils.validate_interaction_state",
            return_value=["validation_error"],
        ):
            await node.run(mock_context)

            assert "agents_setup" not in mock_context.state.processing_steps

    @pytest.mark.asyncio
    async def test_executor_registration_exception(
        self, node, mock_context, mock_orchestrator
    ):
        """Test handling when executor registration raises an exception."""
        mock_orchestrator.register_agent_executor.side_effect = RuntimeError(
            "Registration failed"
        )

        result = await node.run(mock_context)

        assert isinstance(result, PatternError)
        assert mock_context.state.execution_status == ExecutionStatus.FAILED
        assert "Agent setup failed: Registration failed" in mock_context.state.errors[0]

    @pytest.mark.asyncio
    async def test_validation_exception(self, node, mock_context):
        """Test handling when validation raises an exception."""
        with patch(
            "DeepResearch.src.statemachines.workflow_pattern_statemachines.WorkflowPatternUtils.validate_interaction_state",
            side_effect=Exception("Validation crashed"),
        ):
            result = await node.run(mock_context)

            assert isinstance(result, PatternError)
            assert mock_context.state.execution_status == ExecutionStatus.FAILED
            assert (
                "Agent setup failed: Validation crashed" in mock_context.state.errors[0]
            )

    @pytest.mark.asyncio
    async def test_empty_agent_executors(self, node, mock_context, mock_orchestrator):
        """Test setup with no agent executors."""
        mock_context.state.agent_executors = {}

        with patch(
            "DeepResearch.src.statemachines.workflow_pattern_statemachines.WorkflowPatternUtils.validate_interaction_state",
            return_value=[],
        ):
            result = await node.run(mock_context)

            assert isinstance(result, ExecutePattern)
            mock_orchestrator.register_agent_executor.assert_not_called()
            assert "agents_setup" in mock_context.state.processing_steps

    @pytest.mark.asyncio
    async def test_single_agent_executor(self, node, mock_context, mock_orchestrator):
        """Test setup with a single agent executor."""
        single_executor = Mock()
        mock_context.state.agent_executors = {"agent1": single_executor}

        with patch(
            "DeepResearch.src.statemachines.workflow_pattern_statemachines.WorkflowPatternUtils.validate_interaction_state",
            return_value=[],
        ):
            result = await node.run(mock_context)

            assert isinstance(result, ExecutePattern)
            mock_orchestrator.register_agent_executor.assert_called_once_with(
                "agent1", single_executor
            )

    @pytest.mark.asyncio
    async def test_error_appends_not_replaces(self, node, mock_context):
        """Test that errors are appended to existing error list."""
        mock_context.state.errors = ["previous_error"]
        mock_context.state.orchestrator = None

        await node.run(mock_context)

        assert len(mock_context.state.errors) == 2
        assert mock_context.state.errors[0] == "previous_error"
        assert "Agent setup failed" in mock_context.state.errors[1]

    @pytest.mark.asyncio
    async def test_execution_status_set_on_exception(
        self, node, mock_context, mock_orchestrator
    ):
        """Test that execution status is set to FAILED on exception."""
        mock_orchestrator.register_agent_executor.side_effect = Exception("Boom")

        await node.run(mock_context)

        assert mock_context.state.execution_status == ExecutionStatus.FAILED

    @pytest.mark.asyncio
    async def test_execution_status_unchanged_on_success(self, node, mock_context):
        """Test that execution status is not modified on successful setup."""
        initial_status = Mock()
        mock_context.state.execution_status = initial_status

        with patch(
            "DeepResearch.src.statemachines.workflow_pattern_statemachines.WorkflowPatternUtils.validate_interaction_state",
            return_value=[],
        ):
            await node.run(mock_context)

            assert mock_context.state.execution_status == initial_status


class TestPatternError:
    """Test suite for PatternError node."""

    @pytest.fixture
    def mock_context(self):
        """Create a mock GraphRunContext."""
        ctx = Mock()
        ctx.state = Mock()
        ctx.state.start_time = time.time() - 5.0  # 5 seconds ago
        ctx.state.end_time = None
        ctx.state.question = "What went wrong?"
        ctx.state.interaction_pattern = InteractionPattern.COLLABORATIVE
        ctx.state.errors = ["Error 1", "Error 2"]
        ctx.state.processing_steps = ["step1", "step2"]
        ctx.state.execution_status = None
        return ctx

    @pytest.fixture
    def node(self):
        """Create PatternError node instance."""
        return PatternError()

    @pytest.mark.asyncio
    async def test_returns_end_node(self, node, mock_context):
        """Test that PatternError returns an End node."""
        result = await node.run(mock_context)

        assert hasattr(result, "data")
        assert isinstance(result.data, str)

    @pytest.mark.asyncio
    async def test_sets_end_time(self, node, mock_context):
        """Test that end_time is set."""
        before_time = time.time()
        await node.run(mock_context)
        after_time = time.time()

        assert mock_context.state.end_time is not None
        assert before_time <= mock_context.state.end_time <= after_time

    @pytest.mark.asyncio
    async def test_sets_execution_status_to_failed(self, node, mock_context):
        """Test that execution status is set to FAILED."""
        await node.run(mock_context)

        assert mock_context.state.execution_status == ExecutionStatus.FAILED

    @pytest.mark.asyncio
    async def test_output_contains_title(self, node, mock_context):
        """Test that output contains error title."""
        result = await node.run(mock_context)
        output = result.data

        assert "Workflow Pattern Execution Failed" in output

    @pytest.mark.asyncio
    async def test_output_contains_question(self, node, mock_context):
        """Test that output contains the question."""
        result = await node.run(mock_context)
        output = result.data

        assert "Question: What went wrong?" in output

    @pytest.mark.asyncio
    async def test_output_contains_pattern(self, node, mock_context):
        """Test that output contains the pattern type."""
        result = await node.run(mock_context)
        output = result.data

        assert "Pattern: collaborative" in output

    @pytest.mark.asyncio
    async def test_output_contains_errors_section(self, node, mock_context):
        """Test that output contains errors section."""
        result = await node.run(mock_context)
        output = result.data

        assert "Errors:" in output
        assert "- Error 1" in output
        assert "- Error 2" in output

    @pytest.mark.asyncio
    async def test_output_contains_steps_completed(self, node, mock_context):
        """Test that output contains steps completed count."""
        result = await node.run(mock_context)
        output = result.data

        assert "Steps Completed: 2" in output

    @pytest.mark.asyncio
    async def test_output_contains_execution_time(self, node, mock_context):
        """Test that output contains execution time."""
        result = await node.run(mock_context)
        output = result.data

        assert "Execution Time:" in output
        assert "s" in output

    @pytest.mark.asyncio
    async def test_output_contains_failed_status(self, node, mock_context):
        """Test that output contains failed status."""
        result = await node.run(mock_context)
        output = result.data

        assert "Status: failed" in output

    @pytest.mark.asyncio
    async def test_single_error(self, node, mock_context):
        """Test output with a single error."""
        mock_context.state.errors = ["Single error"]
        result = await node.run(mock_context)
        output = result.data

        assert "- Single error" in output

    @pytest.mark.asyncio
    async def test_multiple_errors(self, node, mock_context):
        """Test output with multiple errors."""
        mock_context.state.errors = ["Error 1", "Error 2", "Error 3", "Error 4"]
        result = await node.run(mock_context)
        output = result.data

        assert "- Error 1" in output
        assert "- Error 2" in output
        assert "- Error 3" in output
        assert "- Error 4" in output

    @pytest.mark.asyncio
    async def test_empty_errors_list(self, node, mock_context):
        """Test output with no errors."""
        mock_context.state.errors = []
        result = await node.run(mock_context)
        output = result.data

        assert "Errors:" in output
        # No error items, just the header

    @pytest.mark.asyncio
    async def test_no_processing_steps(self, node, mock_context):
        """Test output with no processing steps."""
        mock_context.state.processing_steps = []
        result = await node.run(mock_context)
        output = result.data

        assert "Steps Completed: 0" in output

    @pytest.mark.asyncio
    async def test_many_processing_steps(self, node, mock_context):
        """Test output with many processing steps."""
        mock_context.state.processing_steps = [f"step{i}" for i in range(10)]
        result = await node.run(mock_context)
        output = result.data

        assert "Steps Completed: 10" in output

    @pytest.mark.asyncio
    async def test_sequential_pattern(self, node, mock_context):
        """Test error output for sequential pattern."""
        mock_context.state.interaction_pattern = InteractionPattern.SEQUENTIAL
        result = await node.run(mock_context)
        output = result.data

        assert "Pattern: sequential" in output

    @pytest.mark.asyncio
    async def test_hierarchical_pattern(self, node, mock_context):
        """Test error output for hierarchical pattern."""
        mock_context.state.interaction_pattern = InteractionPattern.HIERARCHICAL
        result = await node.run(mock_context)
        output = result.data

        assert "Pattern: hierarchical" in output

    @pytest.mark.asyncio
    async def test_execution_time_calculation(self, node, mock_context):
        """Test that execution time is calculated correctly."""
        mock_context.state.start_time = time.time() - 10.5
        result = await node.run(mock_context)
        output = result.data

        # Should be around 10.5 seconds
        assert "10." in output or "11." in output  # Allow for slight timing variations

    @pytest.mark.asyncio
    async def test_zero_execution_time(self, node, mock_context):
        """Test output when execution time is very short."""
        mock_context.state.start_time = time.time()
        result = await node.run(mock_context)
        output = result.data

        assert "0.0" in output or "0.00" in output

    @pytest.mark.asyncio
    async def test_output_format_structure(self, node, mock_context):
        """Test that output has all expected sections in correct order."""
        result = await node.run(mock_context)
        output = result.data

        lines = output.split("\n")
        assert lines[0] == "Workflow Pattern Execution Failed"
        assert lines[1] == ""  # Empty line
        assert lines[2].startswith("Question:")
        assert lines[3].startswith("Pattern:")

    @pytest.mark.asyncio
    async def test_long_error_messages(self, node, mock_context):
        """Test output with very long error messages."""
        long_error = "This is a very long error message " * 10
        mock_context.state.errors = [long_error]
        result = await node.run(mock_context)
        output = result.data

        assert long_error in output

    @pytest.mark.asyncio
    async def test_special_characters_in_errors(self, node, mock_context):
        """Test that special characters in errors are handled."""
        mock_context.state.errors = [
            "Error with 'quotes'",
            'Error with "double quotes"',
            "Error with\nnewline",
        ]
        result = await node.run(mock_context)
        output = result.data

        assert "Error with 'quotes'" in output
        assert 'Error with "double quotes"' in output

    @pytest.mark.asyncio
    async def test_special_characters_in_question(self, node, mock_context):
        """Test that special characters in question are handled."""
        mock_context.state.question = "What's the 'best' approach?"
        result = await node.run(mock_context)
        output = result.data

        assert "What's the 'best' approach?" in output

    @pytest.mark.asyncio
    async def test_all_fields_present(self, node, mock_context):
        """Test that all expected fields are present in error output."""
        result = await node.run(mock_context)
        output = result.data

        expected_fields = [
            "Workflow Pattern Execution Failed",
            "Question:",
            "Pattern:",
            "Errors:",
            "Steps Completed:",
            "Execution Time:",
            "Status:",
        ]

        for field in expected_fields:
            assert field in output, f"Missing field: {field}"
