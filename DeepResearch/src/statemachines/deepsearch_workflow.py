"""
Deep Search workflow state machine for DeepCritical.

This module implements a Pydantic Graph-based workflow for deep search operations,
inspired by Jina AI DeepResearch patterns with iterative search, reflection, and synthesis.
"""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Annotated, TYPE_CHECKING
from enum import Enum

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

from ..datatypes.deepsearch import ActionType, EvaluationType
from ..utils.deepsearch_utils import (
    SearchContext,
    SearchOrchestrator,
    DeepSearchEvaluator,
    create_search_context,
    create_search_orchestrator,
    create_deep_search_evaluator,
)
from ..utils.execution_status import ExecutionStatus

if TYPE_CHECKING:
    pass


class DeepSearchPhase(str, Enum):
    """Phases of the deep search workflow."""

    INITIALIZATION = "initialization"
    SEARCH = "search"
    REFLECTION = "reflection"
    SYNTHESIS = "synthesis"
    EVALUATION = "evaluation"
    COMPLETION = "completion"


@dataclass
class DeepSearchState:
    """State for deep search workflow execution."""

    # Input
    question: str
    config: Optional[DictConfig] = None

    # Workflow state
    phase: DeepSearchPhase = DeepSearchPhase.INITIALIZATION
    current_step: int = 0
    max_steps: int = 20

    # Search context and orchestration
    search_context: Optional[SearchContext] = None
    orchestrator: Optional[SearchOrchestrator] = None
    evaluator: Optional[DeepSearchEvaluator] = None

    # Knowledge and results
    collected_knowledge: Dict[str, Any] = field(default_factory=dict)
    search_results: List[Dict[str, Any]] = field(default_factory=list)
    visited_urls: List[Dict[str, Any]] = field(default_factory=list)
    reflection_questions: List[str] = field(default_factory=list)

    # Evaluation results
    evaluation_results: Dict[str, Any] = field(default_factory=dict)
    quality_metrics: Dict[str, float] = field(default_factory=dict)

    # Final output
    final_answer: str = ""
    confidence_score: float = 0.0
    deepsearch_result: Optional[Dict[str, Any]] = None  # For agent results

    # Metadata
    processing_steps: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    execution_status: ExecutionStatus = ExecutionStatus.PENDING
    start_time: float = field(default_factory=time.time)
    end_time: Optional[float] = None


# --- Deep Search Workflow Nodes ---


@dataclass
class InitializeDeepSearch(BaseNode[DeepSearchState]):
    """Initialize the deep search workflow."""

    async def run(self, ctx: GraphRunContext[DeepSearchState]) -> "PlanSearchStrategy":
        """Initialize deep search components."""
        try:
            # Create search context
            config_dict = ctx.state.config.__dict__ if ctx.state.config else {}
            search_context = create_search_context(ctx.state.question, config_dict)
            ctx.state.search_context = search_context

            # Create orchestrator
            orchestrator = create_search_orchestrator(search_context)
            ctx.state.orchestrator = orchestrator

            # Create evaluator
            evaluator = create_deep_search_evaluator()
            ctx.state.evaluator = evaluator

            # Set initial phase
            ctx.state.phase = DeepSearchPhase.SEARCH
            ctx.state.execution_status = ExecutionStatus.RUNNING
            ctx.state.processing_steps.append("initialized_deep_search")

            return PlanSearchStrategy()

        except Exception as e:
            error_msg = f"Failed to initialize deep search: {str(e)}"
            ctx.state.errors.append(error_msg)
            ctx.state.execution_status = ExecutionStatus.FAILED
            return DeepSearchError()


@dataclass
class PlanSearchStrategy(BaseNode[DeepSearchState]):
    """Plan the search strategy based on the question."""

    async def run(self, ctx: GraphRunContext[DeepSearchState]) -> "ExecuteSearchStep":
        """Plan search strategy and determine initial actions."""
        try:
            orchestrator = ctx.state.orchestrator
            if not orchestrator:
                raise RuntimeError("Orchestrator not initialized")

            # Analyze the question to determine search strategy
            question = ctx.state.question
            search_strategy = self._analyze_question(question)

            # Update context with strategy
            orchestrator.context.add_knowledge("search_strategy", search_strategy)
            orchestrator.context.add_knowledge("original_question", question)

            ctx.state.processing_steps.append("planned_search_strategy")
            ctx.state.phase = DeepSearchPhase.SEARCH

            return ExecuteSearchStep()

        except Exception as e:
            error_msg = f"Failed to plan search strategy: {str(e)}"
            ctx.state.errors.append(error_msg)
            ctx.state.execution_status = ExecutionStatus.FAILED
            return DeepSearchError()

    def _analyze_question(self, question: str) -> Dict[str, Any]:
        """Analyze the question to determine search strategy."""
        question_lower = question.lower()

        strategy = {
            "search_queries": [],
            "focus_areas": [],
            "expected_sources": [],
            "evaluation_criteria": [],
        }

        # Determine search queries
        if "how" in question_lower:
            strategy["search_queries"].append(f"how to {question}")
            strategy["focus_areas"].append("methodology")
        elif "what" in question_lower:
            strategy["search_queries"].append(f"what is {question}")
            strategy["focus_areas"].append("definition")
        elif "why" in question_lower:
            strategy["search_queries"].append(f"why {question}")
            strategy["focus_areas"].append("causation")
        elif "when" in question_lower:
            strategy["search_queries"].append(f"when {question}")
            strategy["focus_areas"].append("timeline")
        elif "where" in question_lower:
            strategy["search_queries"].append(f"where {question}")
            strategy["focus_areas"].append("location")

        # Add general search query
        strategy["search_queries"].append(question)

        # Determine expected sources
        if any(
            term in question_lower
            for term in ["research", "study", "paper", "academic"]
        ):
            strategy["expected_sources"].append("academic")
        if any(
            term in question_lower for term in ["news", "recent", "latest", "current"]
        ):
            strategy["expected_sources"].append("news")
        if any(term in question_lower for term in ["tutorial", "guide", "how to"]):
            strategy["expected_sources"].append("tutorial")

        # Set evaluation criteria
        strategy["evaluation_criteria"] = ["definitive", "completeness", "freshness"]

        return strategy


@dataclass
class ExecuteSearchStep(BaseNode[DeepSearchState]):
    """Execute a single search step."""

    async def run(self, ctx: GraphRunContext[DeepSearchState]) -> "CheckSearchProgress":
        """Execute the next search step using DeepSearchAgent."""
        try:
            # Import at runtime to avoid circular dependency
            from ...agents import DeepSearchAgent

            # Create DeepSearchAgent
            deepsearch_agent = DeepSearchAgent()
            await deepsearch_agent.initialize()

            # Check if we should continue
            orchestrator = ctx.state.orchestrator
            if not orchestrator or not orchestrator.should_continue_search():
                return SynthesizeResults()

            # Get next action
            next_action = orchestrator.get_next_action()
            if not next_action:
                return SynthesizeResults()

            # Prepare parameters for the action
            parameters = self._prepare_action_parameters(next_action, ctx.state)

            # Execute the action using agent
            agent_result = await deepsearch_agent.execute_search_step(
                next_action, parameters
            )

            if agent_result.success:
                # Update state with agent results
                self._update_state_with_agent_result(
                    ctx.state, next_action, agent_result.data
                )
                ctx.state.processing_steps.append(
                    f"executed_{next_action.value}_step_with_agent"
                )
            else:
                # Fallback to traditional orchestrator
                result = await orchestrator.execute_search_step(next_action, parameters)
                self._update_state_with_result(ctx.state, next_action, result)
                ctx.state.processing_steps.append(
                    f"executed_{next_action.value}_step_fallback"
                )

            # Move to next step
            orchestrator.context.next_step()
            ctx.state.current_step = orchestrator.context.current_step

            return CheckSearchProgress()

        except Exception as e:
            error_msg = f"Failed to execute search step: {str(e)}"
            ctx.state.errors.append(error_msg)
            ctx.state.execution_status = ExecutionStatus.FAILED
            return DeepSearchError()

    def _prepare_action_parameters(
        self, action: ActionType, state: DeepSearchState
    ) -> Dict[str, Any]:
        """Prepare parameters for the action."""
        if action == ActionType.SEARCH:
            # Get search queries from strategy
            strategy = state.search_context.collected_knowledge.get(
                "search_strategy", {}
            )
            queries = strategy.get("search_queries", [state.question])
            return {
                "query": queries[0] if queries else state.question,
                "max_results": 10,
            }

        elif action == ActionType.VISIT:
            # Get URLs from search results
            urls = [
                result.get("url")
                for result in state.search_results
                if result.get("url")
            ]
            return {
                "urls": urls[:5],  # Limit to 5 URLs
                "max_content_length": 5000,
            }

        elif action == ActionType.REFLECT:
            return {
                "original_question": state.question,
                "current_knowledge": str(state.collected_knowledge),
                "search_results": state.search_results,
            }

        elif action == ActionType.ANSWER:
            return {
                "original_question": state.question,
                "collected_knowledge": state.collected_knowledge,
                "search_results": state.search_results,
                "visited_urls": state.visited_urls,
            }

        else:
            return {}

    def _update_state_with_result(
        self, state: DeepSearchState, action: ActionType, result: Dict[str, Any]
    ) -> None:
        """Update state with action result."""
        if not result.get("success", False):
            return

        if action == ActionType.SEARCH:
            search_results = result.get("results", [])
            state.search_results.extend(search_results)

        elif action == ActionType.VISIT:
            visited_urls = result.get("visited_urls", [])
            state.visited_urls.extend(visited_urls)

        elif action == ActionType.REFLECT:
            reflection_questions = result.get("reflection_questions", [])
            state.reflection_questions.extend(reflection_questions)

        elif action == ActionType.ANSWER:
            answer = result.get("answer", "")
            state.final_answer = answer
            state.collected_knowledge["final_answer"] = answer

    def _update_state_with_agent_result(
        self, state: DeepSearchState, action: ActionType, agent_data: Dict[str, Any]
    ) -> None:
        """Update state with agent result."""
        # Store agent result
        state.deepsearch_result = agent_data

        if action == ActionType.SEARCH:
            search_results = agent_data.get("search_results", [])
            state.search_results.extend(search_results)

        elif action == ActionType.VISIT:
            visited_urls = agent_data.get("visited_urls", [])
            state.visited_urls.extend(visited_urls)

        elif action == ActionType.REFLECT:
            reflection_questions = agent_data.get("reflection_questions", [])
            state.reflection_questions.extend(reflection_questions)

        elif action == ActionType.ANSWER:
            answer = agent_data.get("answer", "")
            state.final_answer = answer
            state.collected_knowledge["final_answer"] = answer


@dataclass
class CheckSearchProgress(BaseNode[DeepSearchState]):
    """Check if search should continue or move to synthesis."""

    async def run(self, ctx: GraphRunContext[DeepSearchState]) -> "ExecuteSearchStep":
        """Check search progress and decide next step."""
        try:
            orchestrator = ctx.state.orchestrator
            if not orchestrator:
                raise RuntimeError("Orchestrator not initialized")

            # Check if we should continue searching
            if orchestrator.should_continue_search():
                return ExecuteSearchStep()
            else:
                return SynthesizeResults()

        except Exception as e:
            error_msg = f"Failed to check search progress: {str(e)}"
            ctx.state.errors.append(error_msg)
            ctx.state.execution_status = ExecutionStatus.FAILED
            return DeepSearchError()


@dataclass
class SynthesizeResults(BaseNode[DeepSearchState]):
    """Synthesize all collected information into a comprehensive answer."""

    async def run(self, ctx: GraphRunContext[DeepSearchState]) -> "EvaluateResults":
        """Synthesize results from all search activities."""
        try:
            ctx.state.phase = DeepSearchPhase.SYNTHESIS

            # If we don't have a final answer yet, generate one
            if not ctx.state.final_answer:
                ctx.state.final_answer = self._synthesize_answer(ctx.state)

            # Update knowledge with synthesis
            if ctx.state.orchestrator:
                ctx.state.orchestrator.knowledge_manager.add_knowledge(
                    key="synthesized_answer",
                    value=ctx.state.final_answer,
                    source="synthesis",
                    confidence=0.9,
                )

            ctx.state.processing_steps.append("synthesized_results")

            return EvaluateResults()

        except Exception as e:
            error_msg = f"Failed to synthesize results: {str(e)}"
            ctx.state.errors.append(error_msg)
            ctx.state.execution_status = ExecutionStatus.FAILED
            return DeepSearchError()

    def _synthesize_answer(self, state: DeepSearchState) -> str:
        """Synthesize a comprehensive answer from collected information."""
        answer_parts = []

        # Add question
        answer_parts.append(f"Question: {state.question}")
        answer_parts.append("")

        # Add main answer - prioritize agent results
        if state.deepsearch_result and state.deepsearch_result.get("answer"):
            answer_parts.append(f"Answer: {state.deepsearch_result['answer']}")
            confidence = state.deepsearch_result.get("confidence", 0.0)
            if confidence > 0:
                answer_parts.append(f"Confidence: {confidence:.3f}")
        elif state.collected_knowledge.get("final_answer"):
            answer_parts.append(f"Answer: {state.collected_knowledge['final_answer']}")
        else:
            # Generate answer from search results
            main_answer = self._generate_answer_from_results(state)
            answer_parts.append(f"Answer: {main_answer}")

        answer_parts.append("")

        # Add supporting information
        if state.search_results:
            answer_parts.append("Supporting Information:")
            for i, result in enumerate(state.search_results[:5], 1):
                answer_parts.append(f"{i}. {result.get('snippet', '')}")

        # Add sources
        if state.visited_urls:
            answer_parts.append("")
            answer_parts.append("Sources:")
            for i, url_result in enumerate(state.visited_urls[:3], 1):
                if url_result.get("success", False):
                    answer_parts.append(
                        f"{i}. {url_result.get('title', '')} - {url_result.get('url', '')}"
                    )

        return "\n".join(answer_parts)

    def _generate_answer_from_results(self, state: DeepSearchState) -> str:
        """Generate answer from search results."""
        if not state.search_results:
            return "Based on the available information, I was unable to find sufficient data to provide a comprehensive answer."

        # Extract key information from search results
        key_points = []
        for result in state.search_results[:3]:
            snippet = result.get("snippet", "")
            if snippet:
                key_points.append(snippet)

        if key_points:
            return " ".join(key_points)
        else:
            return "The search results provide some relevant information, but a more comprehensive answer would require additional research."


@dataclass
class EvaluateResults(BaseNode[DeepSearchState]):
    """Evaluate the quality and completeness of the results."""

    async def run(self, ctx: GraphRunContext[DeepSearchState]) -> "CompleteDeepSearch":
        """Evaluate the results and calculate quality metrics."""
        try:
            ctx.state.phase = DeepSearchPhase.EVALUATION

            evaluator = ctx.state.evaluator
            orchestrator = ctx.state.orchestrator

            if not evaluator or not orchestrator:
                raise RuntimeError("Evaluator or orchestrator not initialized")

            # Evaluate answer quality
            evaluation_results = {}
            for eval_type in [
                EvaluationType.DEFINITIVE,
                EvaluationType.COMPLETENESS,
                EvaluationType.FRESHNESS,
            ]:
                result = evaluator.evaluate_answer_quality(
                    ctx.state.question, ctx.state.final_answer, eval_type
                )
                evaluation_results[eval_type.value] = result

            ctx.state.evaluation_results = evaluation_results

            # Evaluate search progress
            progress_evaluation = evaluator.evaluate_search_progress(
                orchestrator.context, orchestrator.knowledge_manager
            )

            ctx.state.quality_metrics = {
                "progress_score": progress_evaluation["progress_score"],
                "progress_percentage": progress_evaluation["progress_percentage"],
                "knowledge_score": progress_evaluation["knowledge_score"],
                "search_diversity": progress_evaluation["search_diversity"],
                "url_coverage": progress_evaluation["url_coverage"],
                "reflection_score": progress_evaluation["reflection_score"],
                "answer_score": progress_evaluation["answer_score"],
            }

            # Calculate overall confidence
            ctx.state.confidence_score = self._calculate_confidence_score(ctx.state)

            ctx.state.processing_steps.append("evaluated_results")

            return CompleteDeepSearch()

        except Exception as e:
            error_msg = f"Failed to evaluate results: {str(e)}"
            ctx.state.errors.append(error_msg)
            ctx.state.execution_status = ExecutionStatus.FAILED
            return DeepSearchError()

    def _calculate_confidence_score(self, state: DeepSearchState) -> float:
        """Calculate overall confidence score."""
        confidence_factors = []

        # Evaluation results confidence
        for eval_result in state.evaluation_results.values():
            if eval_result.get("pass", False):
                confidence_factors.append(0.8)
            else:
                confidence_factors.append(0.4)

        # Quality metrics confidence
        if state.quality_metrics:
            progress_percentage = state.quality_metrics.get("progress_percentage", 0)
            confidence_factors.append(progress_percentage / 100)

        # Knowledge completeness confidence
        knowledge_items = len(state.collected_knowledge)
        knowledge_confidence = min(knowledge_items / 10, 1.0)
        confidence_factors.append(knowledge_confidence)

        # Calculate average confidence
        return (
            sum(confidence_factors) / len(confidence_factors)
            if confidence_factors
            else 0.5
        )


@dataclass
class CompleteDeepSearch(BaseNode[DeepSearchState]):
    """Complete the deep search workflow."""

    async def run(
        self, ctx: GraphRunContext[DeepSearchState]
    ) -> Annotated[End[str], Edge(label="done")]:
        """Complete the workflow and return final results."""
        try:
            ctx.state.phase = DeepSearchPhase.COMPLETION
            ctx.state.execution_status = ExecutionStatus.COMPLETED
            ctx.state.end_time = time.time()

            # Create final output
            final_output = self._create_final_output(ctx.state)

            ctx.state.processing_steps.append("completed_deep_search")

            return End(final_output)

        except Exception as e:
            error_msg = f"Failed to complete deep search: {str(e)}"
            ctx.state.errors.append(error_msg)
            ctx.state.execution_status = ExecutionStatus.FAILED
            return DeepSearchError()

    def _create_final_output(self, state: DeepSearchState) -> str:
        """Create the final output with all results."""
        output_parts = []

        # Header
        output_parts.append("=== Deep Search Results ===")
        output_parts.append("")

        # Question and answer
        output_parts.append(f"Question: {state.question}")
        output_parts.append("")
        output_parts.append(f"Answer: {state.final_answer}")
        output_parts.append("")

        # Quality metrics
        if state.quality_metrics:
            output_parts.append("Quality Metrics:")
            for metric, value in state.quality_metrics.items():
                if isinstance(value, float):
                    output_parts.append(f"- {metric}: {value:.2f}")
                else:
                    output_parts.append(f"- {metric}: {value}")
            output_parts.append("")

        # Confidence score
        output_parts.append(f"Confidence Score: {state.confidence_score:.2%}")
        output_parts.append("")

        # Processing summary
        output_parts.append("Processing Summary:")
        output_parts.append(f"- Total Steps: {state.current_step}")
        output_parts.append(f"- Search Results: {len(state.search_results)}")
        output_parts.append(f"- Visited URLs: {len(state.visited_urls)}")
        output_parts.append(
            f"- Reflection Questions: {len(state.reflection_questions)}"
        )
        output_parts.append(
            f"- Processing Time: {state.end_time - state.start_time:.2f}s"
        )
        output_parts.append("")

        # Steps completed
        if state.processing_steps:
            output_parts.append("Steps Completed:")
            for step in state.processing_steps:
                output_parts.append(f"- {step}")
            output_parts.append("")

        # Errors (if any)
        if state.errors:
            output_parts.append("Errors Encountered:")
            for error in state.errors:
                output_parts.append(f"- {error}")

        return "\n".join(output_parts)


@dataclass
class DeepSearchError(BaseNode[DeepSearchState]):
    """Handle deep search workflow errors."""

    async def run(
        self, ctx: GraphRunContext[DeepSearchState]
    ) -> Annotated[End[str], Edge(label="error")]:
        """Handle errors and return error response."""
        ctx.state.execution_status = ExecutionStatus.FAILED
        ctx.state.end_time = time.time()

        error_response = [
            "Deep Search Workflow Failed",
            "",
            f"Question: {ctx.state.question}",
            "",
            "Errors:",
        ]

        for error in ctx.state.errors:
            error_response.append(f"- {error}")

        error_response.extend(
            [
                "",
                f"Steps Completed: {ctx.state.current_step}",
                f"Processing Time: {ctx.state.end_time - ctx.state.start_time:.2f}s",
                f"Status: {ctx.state.execution_status.value}",
            ]
        )

        return End("\n".join(error_response))


# --- Deep Search Workflow Graph ---

deepsearch_workflow_graph = Graph(
    nodes=(
        InitializeDeepSearch,
        PlanSearchStrategy,
        ExecuteSearchStep,
        CheckSearchProgress,
        SynthesizeResults,
        EvaluateResults,
        CompleteDeepSearch,
        DeepSearchError,
    ),
    state_type=DeepSearchState,
)


def run_deepsearch_workflow(question: str, config: Optional[DictConfig] = None) -> str:
    """Run the complete deep search workflow."""
    state = DeepSearchState(question=question, config=config)
    result = asyncio.run(
        deepsearch_workflow_graph.run(InitializeDeepSearch(), state=state)
    )
    return result.output
