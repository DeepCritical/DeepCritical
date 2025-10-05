"""
Workflow pattern state machines for DeepCritical agent interaction design patterns.

This module implements Pydantic Graph-based state machines for various agent
interaction patterns including collaborative, sequential, hierarchical, and
consensus-based coordination strategies.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Annotated

# Optional import for pydantic_graph
try:
    from pydantic_graph import BaseNode, End, Graph, GraphRunContext, Edge
except ImportError:
    # Create placeholder classes for when pydantic_graph is not available
    from typing import TypeVar, Generic
    
    T = TypeVar('T')
    
    class BaseNode(Generic[T]):
        def __init__(self, *args, **kwargs):
            pass
    
    class End:
        def __init__(self, *args, **kwargs):
            pass
    
    class Graph:
        def __init__(self, *args, **kwargs):
            pass
    
    class GraphRunContext:
        def __init__(self, *args, **kwargs):
            pass
    
    class Edge:
        def __init__(self, *args, **kwargs):
            pass
from omegaconf import DictConfig

# Import existing DeepCritical types
from ..datatypes.workflow_patterns import (
    InteractionPattern,
    WorkflowOrchestrator,
    create_workflow_orchestrator,
    AgentInteractionState,
    create_interaction_state,
)
from ..datatypes.agents import AgentType
from ..utils.execution_status import ExecutionStatus
from ..utils.workflow_patterns import (
    ConsensusAlgorithm,
    MessageRoutingStrategy,
    InteractionMetrics,
    WorkflowPatternUtils,
)


@dataclass
class WorkflowPatternState:
    """State for workflow pattern execution."""

    # Input
    question: str
    config: Optional[DictConfig] = None

    # Pattern configuration
    interaction_pattern: InteractionPattern = InteractionPattern.COLLABORATIVE
    agent_ids: List[str] = field(default_factory=list)
    agent_types: Dict[str, AgentType] = field(default_factory=dict)

    # Execution state
    interaction_state: Optional[AgentInteractionState] = None
    orchestrator: Optional[WorkflowOrchestrator] = None
    metrics: InteractionMetrics = field(default_factory=InteractionMetrics)

    # Results
    final_result: Optional[Any] = None
    execution_summary: Dict[str, Any] = field(default_factory=dict)

    # Metadata
    processing_steps: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    execution_status: ExecutionStatus = ExecutionStatus.PENDING
    start_time: float = field(default_factory=time.time)
    end_time: Optional[float] = None

    # Context for Pydantic Graph
    agent_executors: Dict[str, Any] = field(default_factory=dict)
    message_routing: MessageRoutingStrategy = MessageRoutingStrategy.DIRECT
    consensus_algorithm: ConsensusAlgorithm = ConsensusAlgorithm.SIMPLE_AGREEMENT


# --- Base Pattern Nodes ---

@dataclass
class InitializePattern(BaseNode[WorkflowPatternState]):
    """Initialize workflow pattern execution."""

    async def run(self, ctx: GraphRunContext[WorkflowPatternState]) -> "SetupAgents":
        """Initialize the interaction pattern."""
        try:
            # Create interaction state
            interaction_state = create_interaction_state(
                pattern=ctx.state.interaction_pattern,
                agents=ctx.state.agent_ids,
                agent_types=ctx.state.agent_types,
            )

            # Create orchestrator
            orchestrator = create_workflow_orchestrator(
                interaction_state, ctx.state.agent_executors
            )

            # Update state
            ctx.state.interaction_state = interaction_state
            ctx.state.orchestrator = orchestrator
            ctx.state.execution_status = ExecutionStatus.RUNNING
            ctx.state.processing_steps.append("pattern_initialized")

            return SetupAgents()

        except Exception as e:
            ctx.state.errors.append(f"Pattern initialization failed: {str(e)}")
            ctx.state.execution_status = ExecutionStatus.FAILED
            return PatternError()


@dataclass
class SetupAgents(BaseNode[WorkflowPatternState]):
    """Set up agents for interaction."""

    async def run(self, ctx: GraphRunContext[WorkflowPatternState]) -> "ExecutePattern":
        """Set up agents and prepare for execution."""
        try:
            orchestrator = ctx.state.orchestrator
            interaction_state = ctx.state.interaction_state

            if not orchestrator or not interaction_state:
                raise RuntimeError("Orchestrator or interaction state not initialized")

            # Set up agent executors
            for agent_id, executor in ctx.state.agent_executors.items():
                orchestrator.register_agent_executor(agent_id, executor)

            # Validate setup
            validation_errors = WorkflowPatternUtils.validate_interaction_state(interaction_state)
            if validation_errors:
                ctx.state.errors.extend(validation_errors)
                return PatternError()

            ctx.state.processing_steps.append("agents_setup")

            return ExecutePattern()

        except Exception as e:
            ctx.state.errors.append(f"Agent setup failed: {str(e)}")
            ctx.state.execution_status = ExecutionStatus.FAILED
            return PatternError()


# --- Pattern-Specific Nodes ---

@dataclass
class ExecuteCollaborativePattern(BaseNode[WorkflowPatternState]):
    """Execute collaborative interaction pattern."""

    async def run(self, ctx: GraphRunContext[WorkflowPatternState]) -> "ProcessCollaborativeResults":
        """Execute collaborative pattern."""
        try:
            orchestrator = ctx.state.orchestrator
            if not orchestrator:
                raise RuntimeError("Orchestrator not initialized")

            # Execute collaborative pattern
            result = await orchestrator.execute_collaborative_pattern()

            # Update state
            ctx.state.final_result = result
            ctx.state.metrics = orchestrator.state.get_summary()
            ctx.state.processing_steps.append("collaborative_pattern_executed")

            return ProcessCollaborativeResults()

        except Exception as e:
            ctx.state.errors.append(f"Collaborative pattern execution failed: {str(e)}")
            ctx.state.execution_status = ExecutionStatus.FAILED
            return PatternError()


@dataclass
class ExecuteSequentialPattern(BaseNode[WorkflowPatternState]):
    """Execute sequential interaction pattern."""

    async def run(self, ctx: GraphRunContext[WorkflowPatternState]) -> "ProcessSequentialResults":
        """Execute sequential pattern."""
        try:
            orchestrator = ctx.state.orchestrator
            if not orchestrator:
                raise RuntimeError("Orchestrator not initialized")

            # Execute sequential pattern
            result = await orchestrator.execute_sequential_pattern()

            # Update state
            ctx.state.final_result = result
            ctx.state.metrics = orchestrator.state.get_summary()
            ctx.state.processing_steps.append("sequential_pattern_executed")

            return ProcessSequentialResults()

        except Exception as e:
            ctx.state.errors.append(f"Sequential pattern execution failed: {str(e)}")
            ctx.state.execution_status = ExecutionStatus.FAILED
            return PatternError()


@dataclass
class ExecuteHierarchicalPattern(BaseNode[WorkflowPatternState]):
    """Execute hierarchical interaction pattern."""

    async def run(self, ctx: GraphRunContext[WorkflowPatternState]) -> "ProcessHierarchicalResults":
        """Execute hierarchical pattern."""
        try:
            orchestrator = ctx.state.orchestrator
            if not orchestrator:
                raise RuntimeError("Orchestrator not initialized")

            # Execute hierarchical pattern
            result = await orchestrator.execute_hierarchical_pattern()

            # Update state
            ctx.state.final_result = result
            ctx.state.metrics = orchestrator.state.get_summary()
            ctx.state.processing_steps.append("hierarchical_pattern_executed")

            return ProcessHierarchicalResults()

        except Exception as e:
            ctx.state.errors.append(f"Hierarchical pattern execution failed: {str(e)}")
            ctx.state.execution_status = ExecutionStatus.FAILED
            return PatternError()


# --- Result Processing Nodes ---

@dataclass
class ProcessCollaborativeResults(BaseNode[WorkflowPatternState]):
    """Process results from collaborative pattern."""

    async def run(self, ctx: GraphRunContext[WorkflowPatternState]) -> "ValidateConsensus":
        """Process collaborative results."""
        try:
            # Compute consensus metrics
            consensus_result = WorkflowPatternUtils.compute_consensus(
                list(ctx.state.orchestrator.state.results.values()),
                ctx.state.consensus_algorithm,
            )

            # Update execution summary
            ctx.state.execution_summary.update({
                "pattern": ctx.state.interaction_pattern.value,
                "consensus_reached": consensus_result.consensus_reached,
                "consensus_confidence": consensus_result.confidence,
                "algorithm_used": consensus_result.algorithm_used.value,
                "total_rounds": ctx.state.interaction_state.current_round,
                "agents_participated": len(ctx.state.interaction_state.active_agents),
            })

            ctx.state.processing_steps.append("collaborative_results_processed")

            return ValidateConsensus()

        except Exception as e:
            ctx.state.errors.append(f"Collaborative result processing failed: {str(e)}")
            ctx.state.execution_status = ExecutionStatus.FAILED
            return PatternError()


@dataclass
class ProcessSequentialResults(BaseNode[WorkflowPatternState]):
    """Process results from sequential pattern."""

    async def run(self, ctx: GraphRunContext[WorkflowPatternState]) -> "ValidateResults":
        """Process sequential results."""
        try:
            # Sequential results are already in the correct format
            sequential_results = ctx.state.orchestrator.state.results

            # Update execution summary
            ctx.state.execution_summary.update({
                "pattern": ctx.state.interaction_pattern.value,
                "sequential_steps": len(sequential_results),
                "agents_executed": len([r for r in sequential_results.values() if r.get("success", False)]),
                "total_rounds": ctx.state.interaction_state.current_round,
            })

            ctx.state.processing_steps.append("sequential_results_processed")

            return ValidateResults()

        except Exception as e:
            ctx.state.errors.append(f"Sequential result processing failed: {str(e)}")
            ctx.state.execution_status = ExecutionStatus.FAILED
            return PatternError()


@dataclass
class ProcessHierarchicalResults(BaseNode[WorkflowPatternState]):
    """Process results from hierarchical pattern."""

    async def run(self, ctx: GraphRunContext[WorkflowPatternState]) -> "ValidateResults":
        """Process hierarchical results."""
        try:
            # Hierarchical results contain coordinator and subordinate results
            hierarchical_results = ctx.state.orchestrator.state.results

            # Update execution summary
            ctx.state.execution_summary.update({
                "pattern": ctx.state.interaction_pattern.value,
                "coordinator_executed": "coordinator" in hierarchical_results,
                "subordinates_executed": len([k for k in hierarchical_results.keys() if k != "coordinator"]),
                "total_rounds": ctx.state.interaction_state.current_round,
            })

            ctx.state.processing_steps.append("hierarchical_results_processed")

            return ValidateResults()

        except Exception as e:
            ctx.state.errors.append(f"Hierarchical result processing failed: {str(e)}")
            ctx.state.execution_status = ExecutionStatus.FAILED
            return PatternError()


# --- Validation Nodes ---

@dataclass
class ValidateConsensus(BaseNode[WorkflowPatternState]):
    """Validate consensus results."""

    async def run(self, ctx: GraphRunContext[WorkflowPatternState]) -> "FinalizePattern":
        """Validate consensus was achieved."""
        try:
            consensus_reached = ctx.state.execution_summary.get("consensus_reached", False)

            if not consensus_reached:
                ctx.state.errors.append("Consensus was not reached in collaborative pattern")
                ctx.state.execution_status = ExecutionStatus.FAILED
                return PatternError()

            ctx.state.processing_steps.append("consensus_validated")

            return FinalizePattern()

        except Exception as e:
            ctx.state.errors.append(f"Consensus validation failed: {str(e)}")
            ctx.state.execution_status = ExecutionStatus.FAILED
            return PatternError()


@dataclass
class ValidateResults(BaseNode[WorkflowPatternState]):
    """Validate pattern execution results."""

    async def run(self, ctx: GraphRunContext[WorkflowPatternState]) -> "FinalizePattern":
        """Validate pattern execution was successful."""
        try:
            final_result = ctx.state.final_result

            if final_result is None:
                ctx.state.errors.append("No final result generated")
                ctx.state.execution_status = ExecutionStatus.FAILED
                return PatternError()

            # Validate result format based on pattern
            if ctx.state.interaction_pattern == InteractionPattern.SEQUENTIAL:
                if not isinstance(final_result, dict):
                    ctx.state.errors.append("Sequential pattern should return dict result")
                    ctx.state.execution_status = ExecutionStatus.FAILED
                    return PatternError()

            elif ctx.state.interaction_pattern == InteractionPattern.HIERARCHICAL:
                if not isinstance(final_result, dict) or "coordinator" not in final_result:
                    ctx.state.errors.append("Hierarchical pattern should return dict with coordinator")
                    ctx.state.execution_status = ExecutionStatus.FAILED
                    return PatternError()

            ctx.state.processing_steps.append("results_validated")

            return FinalizePattern()

        except Exception as e:
            ctx.state.errors.append(f"Result validation failed: {str(e)}")
            ctx.state.execution_status = ExecutionStatus.FAILED
            return PatternError()


# --- Finalization Nodes ---

@dataclass
class FinalizePattern(BaseNode[WorkflowPatternState]):
    """Finalize pattern execution."""

    async def run(self, ctx: GraphRunContext[WorkflowPatternState]) -> Annotated[End[str], Edge(label="done")]:
        """Finalize the pattern execution."""
        try:
            # Update final metrics
            ctx.state.end_time = time.time()
            total_time = ctx.state.end_time - ctx.state.start_time

            # Create comprehensive execution summary
            final_summary = {
                "pattern": ctx.state.interaction_pattern.value,
                "question": ctx.state.question,
                "execution_status": ctx.state.execution_status.value,
                "total_time": total_time,
                "steps_executed": len(ctx.state.processing_steps),
                "errors_count": len(ctx.state.errors),
                "agents_involved": len(ctx.state.agent_ids),
                "interaction_summary": ctx.state.interaction_state.get_summary() if ctx.state.interaction_state else {},
                "metrics": ctx.state.metrics.__dict__,
                "execution_summary": ctx.state.execution_summary,
            }

            # Format final output
            output_parts = [
                f"=== {ctx.state.interaction_pattern.value.title()} Pattern Results ===",
                "",
                f"Question: {ctx.state.question}",
                f"Pattern: {ctx.state.interaction_pattern.value}",
                f"Status: {ctx.state.execution_status.value}",
                f"Execution Time: {total_time:.2f}s",
                f"Steps Completed: {len(ctx.state.processing_steps)}",
                "",
            ]

            if ctx.state.final_result:
                output_parts.extend([
                    "Final Result:",
                    str(ctx.state.final_result),
                    "",
                ])

            if ctx.state.execution_summary:
                output_parts.extend([
                    "Execution Summary:",
                    f"- Total Rounds: {ctx.state.execution_summary.get('total_rounds', 0)}",
                    f"- Agents Participated: {ctx.state.execution_summary.get('agents_participated', 0)}",
                ])

                if ctx.state.interaction_pattern == InteractionPattern.COLLABORATIVE:
                    output_parts.extend([
                        f"- Consensus Reached: {ctx.state.execution_summary.get('consensus_reached', False)}",
                        f"- Consensus Confidence: {ctx.state.execution_summary.get('consensus_confidence', 0):.3f}",
                    ])

                output_parts.append("")

            if ctx.state.processing_steps:
                output_parts.extend([
                    "Processing Steps:",
                    "\n".join(f"- {step}" for step in ctx.state.processing_steps),
                    "",
                ])

            if ctx.state.errors:
                output_parts.extend([
                    "Errors Encountered:",
                    "\n".join(f"- {error}" for error in ctx.state.errors),
                ])

            final_output = "\n".join(output_parts)
            ctx.state.processing_steps.append("pattern_finalized")

            return End(final_output)

        except Exception as e:
            ctx.state.errors.append(f"Pattern finalization failed: {str(e)}")
            ctx.state.execution_status = ExecutionStatus.FAILED
            return PatternError()


@dataclass
class PatternError(BaseNode[WorkflowPatternState]):
    """Handle pattern execution errors."""

    async def run(self, ctx: GraphRunContext[WorkflowPatternState]) -> Annotated[End[str], Edge(label="error")]:
        """Handle errors and return error response."""
        ctx.state.end_time = time.time()
        ctx.state.execution_status = ExecutionStatus.FAILED

        error_response = [
            "Workflow Pattern Execution Failed",
            "",
            f"Question: {ctx.state.question}",
            f"Pattern: {ctx.state.interaction_pattern.value}",
            "",
            "Errors:",
        ]

        for error in ctx.state.errors:
            error_response.append(f"- {error}")

        error_response.extend([
            "",
            f"Steps Completed: {len(ctx.state.processing_steps)}",
            f"Execution Time: {ctx.state.end_time - ctx.state.start_time:.2f}s",
            f"Status: {ctx.state.execution_status.value}",
        ])

        return End("\n".join(error_response))


# --- Pattern-Specific Execution Nodes ---

@dataclass
class ExecutePattern(BaseNode[WorkflowPatternState]):
    """Execute the appropriate pattern based on configuration."""

    async def run(self, ctx: GraphRunContext[WorkflowPatternState]) -> Any:
        """Execute the configured interaction pattern."""
        pattern = ctx.state.interaction_pattern

        if pattern == InteractionPattern.COLLABORATIVE:
            return ExecuteCollaborativePattern()
        elif pattern == InteractionPattern.SEQUENTIAL:
            return ExecuteSequentialPattern()
        elif pattern == InteractionPattern.HIERARCHICAL:
            return ExecuteHierarchicalPattern()
        else:
            ctx.state.errors.append(f"Unsupported pattern: {pattern}")
            return PatternError()


# --- Workflow Graph Creation ---

def create_collaborative_pattern_graph() -> Graph[WorkflowPatternState]:
    """Create a Pydantic Graph for collaborative pattern execution."""
    return Graph(
        nodes=[
            InitializePattern(),
            SetupAgents(),
            ExecuteCollaborativePattern(),
            ProcessCollaborativeResults(),
            ValidateConsensus(),
            FinalizePattern(),
            PatternError(),
        ],
        state_type=WorkflowPatternState,
    )


def create_sequential_pattern_graph() -> Graph[WorkflowPatternState]:
    """Create a Pydantic Graph for sequential pattern execution."""
    return Graph(
        nodes=[
            InitializePattern(),
            SetupAgents(),
            ExecuteSequentialPattern(),
            ProcessSequentialResults(),
            ValidateResults(),
            FinalizePattern(),
            PatternError(),
        ],
        state_type=WorkflowPatternState,
    )


def create_hierarchical_pattern_graph() -> Graph[WorkflowPatternState]:
    """Create a Pydantic Graph for hierarchical pattern execution."""
    return Graph(
        nodes=[
            InitializePattern(),
            SetupAgents(),
            ExecuteHierarchicalPattern(),
            ProcessHierarchicalResults(),
            ValidateResults(),
            FinalizePattern(),
            PatternError(),
        ],
        state_type=WorkflowPatternState,
    )


def create_pattern_graph(pattern: InteractionPattern) -> Graph[WorkflowPatternState]:
    """Create a Pydantic Graph for the given interaction pattern."""

    if pattern == InteractionPattern.COLLABORATIVE:
        return create_collaborative_pattern_graph()
    elif pattern == InteractionPattern.SEQUENTIAL:
        return create_sequential_pattern_graph()
    elif pattern == InteractionPattern.HIERARCHICAL:
        return create_hierarchical_pattern_graph()
    else:
        # Default to collaborative
        return create_collaborative_pattern_graph()


# --- Workflow Execution Functions ---

async def run_collaborative_pattern_workflow(
    question: str,
    agents: List[str],
    agent_types: Dict[str, AgentType],
    agent_executors: Dict[str, Any],
    config: Optional[DictConfig] = None,
) -> str:
    """Run collaborative pattern workflow."""

    state = WorkflowPatternState(
        question=question,
        config=config,
        interaction_pattern=InteractionPattern.COLLABORATIVE,
        agent_ids=agents,
        agent_types=agent_types,
        agent_executors=agent_executors,
    )

    graph = create_collaborative_pattern_graph()
    result = await graph.run(InitializePattern(), state=state)
    return result.output


async def run_sequential_pattern_workflow(
    question: str,
    agents: List[str],
    agent_types: Dict[str, AgentType],
    agent_executors: Dict[str, Any],
    config: Optional[DictConfig] = None,
) -> str:
    """Run sequential pattern workflow."""

    state = WorkflowPatternState(
        question=question,
        config=config,
        interaction_pattern=InteractionPattern.SEQUENTIAL,
        agent_ids=agents,
        agent_types=agent_types,
        agent_executors=agent_executors,
    )

    graph = create_sequential_pattern_graph()
    result = await graph.run(InitializePattern(), state=state)
    return result.output


async def run_hierarchical_pattern_workflow(
    question: str,
    coordinator_id: str,
    subordinate_ids: List[str],
    agent_types: Dict[str, AgentType],
    agent_executors: Dict[str, Any],
    config: Optional[DictConfig] = None,
) -> str:
    """Run hierarchical pattern workflow."""

    all_agents = [coordinator_id] + subordinate_ids
    state = WorkflowPatternState(
        question=question,
        config=config,
        interaction_pattern=InteractionPattern.HIERARCHICAL,
        agent_ids=all_agents,
        agent_types=agent_types,
        agent_executors=agent_executors,
    )

    graph = create_hierarchical_pattern_graph()
    result = await graph.run(InitializePattern(), state=state)
    return result.output


async def run_pattern_workflow(
    question: str,
    pattern: InteractionPattern,
    agents: List[str],
    agent_types: Dict[str, AgentType],
    agent_executors: Dict[str, Any],
    config: Optional[DictConfig] = None,
) -> str:
    """Run workflow with the specified interaction pattern."""

    state = WorkflowPatternState(
        question=question,
        config=config,
        interaction_pattern=pattern,
        agent_ids=agents,
        agent_types=agent_types,
        agent_executors=agent_executors,
    )

    graph = create_pattern_graph(pattern)
    result = await graph.run(InitializePattern(), state=state)
    return result.output


# Export all components
__all__ = [
    "WorkflowPatternState",
    "InitializePattern",
    "SetupAgents",
    "ExecuteCollaborativePattern",
    "ExecuteSequentialPattern",
    "ExecuteHierarchicalPattern",
    "ProcessCollaborativeResults",
    "ProcessSequentialResults",
    "ProcessHierarchicalResults",
    "ValidateConsensus",
    "ValidateResults",
    "FinalizePattern",
    "PatternError",
    "ExecutePattern",
    "create_collaborative_pattern_graph",
    "create_sequential_pattern_graph",
    "create_hierarchical_pattern_graph",
    "create_pattern_graph",
    "run_collaborative_pattern_workflow",
    "run_sequential_pattern_workflow",
    "run_hierarchical_pattern_workflow",
    "run_pattern_workflow",
]
