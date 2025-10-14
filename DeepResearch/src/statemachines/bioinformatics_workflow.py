"""
Bioinformatics workflow nodes for Pydantic Graph.

This module implements stateful nodes for bioinformatics data fusion and reasoning
workflows using Pydantic Graph and agent-to-agent communication.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import Annotated, Any

# Optional import for pydantic_graph
try:
    from pydantic_graph import BaseNode, Edge, End, Graph, GraphRunContext
except ImportError:
    # Create placeholder classes for when pydantic_graph is not available
    from typing import Generic, TypeVar

    T = TypeVar("T")

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


from DeepResearch.src.datatypes.bioinformatics import (
    DataFusionRequest,
    EvidenceCode,
    FusedDataset,
    GOAnnotation,
    PubMedPaper,
    ReasoningTask,
)


@dataclass
class BioinformaticsState:
    """State for bioinformatics workflows."""

    # Input
    question: str
    fusion_request: DataFusionRequest | None = None
    reasoning_task: ReasoningTask | None = None

    # Processing state
    go_annotations: list[GOAnnotation] = field(default_factory=list)
    pubmed_papers: list[PubMedPaper] = field(default_factory=list)
    fused_dataset: FusedDataset | None = None
    quality_metrics: dict[str, float] = field(default_factory=dict)

    # Results
    reasoning_result: dict[str, Any] | None = None
    final_answer: str = ""

    # Metadata
    notes: list[str] = field(default_factory=list)
    processing_steps: list[str] = field(default_factory=list)
    config: dict[str, Any] | None = None


@dataclass
class ParseBioinformaticsQuery(BaseNode[BioinformaticsState]):  # type: ignore[unsupported-base]
    """Parse bioinformatics query and determine workflow type."""

    async def run(self, ctx: GraphRunContext[BioinformaticsState]) -> FuseDataSources:
        """Parse the query and create appropriate fusion request using the new agent system."""

        question = ctx.state.question
        ctx.state.notes.append(f"Parsing bioinformatics query: {question}")

        try:
            # Use the new ParserAgent for better query understanding
            from DeepResearch.agents import ParserAgent

            parser = ParserAgent()
            parsed_result = parser.parse(question)

            # Extract workflow type from parsed result
            workflow_type = parsed_result.get("domain", "general_bioinformatics")
            if workflow_type == "bioinformatics":
                # Further refine based on specific bioinformatics domains
                fusion_type = self._determine_fusion_type(question)
            else:
                fusion_type = parsed_result.get("intent", "MultiSource")

            source_databases = self._identify_data_sources(question)

            # Create fusion request from config
            fusion_request = DataFusionRequest.from_config(
                config=ctx.state.config or {},
                request_id=f"fusion_{asyncio.get_event_loop().time()}",
                fusion_type=fusion_type,
                source_databases=source_databases,
                filters=self._extract_filters(question),
            )

            ctx.state.fusion_request = fusion_request
            ctx.state.notes.append(f"Created fusion request: {fusion_type}")
            ctx.state.notes.append(
                f"Parsed entities: {parsed_result.get('entities', [])}"
            )

            return FuseDataSources()

        except Exception as e:
            ctx.state.notes.append(f"Error in parsing: {e!s}")
            # Fallback to original logic
            fusion_type = self._determine_fusion_type(question)
            source_databases = self._identify_data_sources(question)

            fusion_request = DataFusionRequest.from_config(
                config=ctx.state.config or {},
                request_id=f"fusion_{asyncio.get_event_loop().time()}",
                fusion_type=fusion_type,
                source_databases=source_databases,
                filters=self._extract_filters(question),
            )

            ctx.state.fusion_request = fusion_request
            ctx.state.notes.append(f"Created fusion request (fallback): {fusion_type}")

            return FuseDataSources()

    def _determine_fusion_type(self, question: str) -> str:
        """Determine the type of data fusion needed."""
        question_lower = question.lower()

        if "go" in question_lower and "pubmed" in question_lower:
            return "GO+PubMed"
        if "geo" in question_lower and "cmap" in question_lower:
            return "GEO+CMAP"
        if "drugbank" in question_lower and "ttd" in question_lower:
            return "DrugBank+TTD+CMAP"
        if "pdb" in question_lower and "intact" in question_lower:
            return "PDB+IntAct"
        return "MultiSource"

    def _identify_data_sources(self, question: str) -> list[str]:
        """Identify relevant data sources from the question."""
        question_lower = question.lower()
        sources = []

        if any(
            term in question_lower for term in ["go", "gene ontology", "annotation"]
        ):
            sources.append("GO")
        if any(term in question_lower for term in ["pubmed", "paper", "publication"]):
            sources.append("PubMed")
        if any(term in question_lower for term in ["geo", "expression", "microarray"]):
            sources.append("GEO")
        if any(term in question_lower for term in ["drug", "compound", "drugbank"]):
            sources.append("DrugBank")
        if any(term in question_lower for term in ["structure", "pdb", "protein"]):
            sources.append("PDB")
        if any(term in question_lower for term in ["interaction", "intact"]):
            sources.append("IntAct")

        return sources if sources else ["GO", "PubMed"]

    def _extract_filters(self, question: str) -> dict[str, Any]:
        """Extract filtering criteria from the question."""
        filters = {}
        question_lower = question.lower()

        # Evidence code filters
        if "ida" in question_lower or "gold standard" in question_lower:
            filters["evidence_codes"] = ["IDA"]
        elif "experimental" in question_lower:
            filters["evidence_codes"] = ["IDA", "EXP"]

        # Year filters
        if "recent" in question_lower or "2022" in question_lower:
            filters["year_min"] = 2022

        return filters


@dataclass
class FuseDataSources(BaseNode[BioinformaticsState]):  # type: ignore[unsupported-base]
    """Fuse data from multiple bioinformatics sources."""

    async def run(self, ctx: GraphRunContext[BioinformaticsState]) -> AssessDataQuality:
        """Fuse data from multiple sources using the new agent system."""

        fusion_request = ctx.state.fusion_request
        if not fusion_request:
            ctx.state.notes.append("No fusion request found, skipping data fusion")
            return AssessDataQuality()

        ctx.state.notes.append(
            f"Fusing data from: {', '.join(fusion_request.source_databases)}"
        )
        ctx.state.processing_steps.append("Data fusion")

        try:
            # Use the new BioinformaticsAgent
            from DeepResearch.agents import BioinformaticsAgent

            bioinformatics_agent = BioinformaticsAgent()

            # Fuse data using the new agent
            fused_dataset = await bioinformatics_agent.fuse_data(fusion_request)

            ctx.state.fused_dataset = fused_dataset
            ctx.state.quality_metrics = fused_dataset.quality_metrics
            ctx.state.notes.append(
                f"Fused dataset created with {fused_dataset.total_entities} entities"
            )

        except Exception as e:
            ctx.state.notes.append(f"Data fusion failed: {e!s}")
            # Create empty dataset for continuation
            ctx.state.fused_dataset = FusedDataset(
                dataset_id="empty",
                name="Empty Dataset",
                description="Empty dataset due to fusion failure",
                source_databases=fusion_request.source_databases,
            )

        return AssessDataQuality()


@dataclass
class AssessDataQuality(BaseNode[BioinformaticsState]):  # type: ignore[unsupported-base]
    """Assess quality of fused dataset."""

    async def run(
        self, ctx: GraphRunContext[BioinformaticsState]
    ) -> CreateReasoningTask:
        """Assess data quality and determine next steps."""

        fused_dataset = ctx.state.fused_dataset
        if not fused_dataset:
            ctx.state.notes.append("No fused dataset to assess")
            return CreateReasoningTask()

        ctx.state.notes.append("Assessing data quality")
        ctx.state.processing_steps.append("Quality assessment")

        # Check if we have sufficient data for reasoning (from config)
        bioinformatics_config = (ctx.state.config or {}).get("bioinformatics", {})
        limits_config = bioinformatics_config.get("limits", {})
        min_entities = limits_config.get("minimum_entities_for_reasoning", 10)

        if fused_dataset.total_entities < min_entities:
            ctx.state.notes.append(
                f"Insufficient data: {fused_dataset.total_entities} < {min_entities}"
            )
            return CreateReasoningTask()

        # Log quality metrics
        for metric, value in ctx.state.quality_metrics.items():
            ctx.state.notes.append(f"Quality metric {metric}: {value:.3f}")

        return CreateReasoningTask()


@dataclass
class CreateReasoningTask(BaseNode[BioinformaticsState]):  # type: ignore[unsupported-base]
    """Create reasoning task based on original question and fused data."""

    async def run(self, ctx: GraphRunContext[BioinformaticsState]) -> PerformReasoning:
        """Create reasoning task from the original question."""

        question = ctx.state.question
        fused_dataset = ctx.state.fused_dataset

        ctx.state.notes.append("Creating reasoning task")
        ctx.state.processing_steps.append("Task creation")

        # Create reasoning task
        reasoning_task = ReasoningTask(
            task_id=f"reasoning_{asyncio.get_event_loop().time()}",
            task_type=self._determine_task_type(question),
            question=question,
            context={
                "fusion_type": (
                    ctx.state.fusion_request.fusion_type
                    if ctx.state.fusion_request
                    else "unknown"
                ),
                "data_sources": (
                    ctx.state.fusion_request.source_databases
                    if ctx.state.fusion_request
                    else []
                ),
                "quality_metrics": ctx.state.quality_metrics,
            },
            difficulty_level=self._assess_difficulty(question),
            required_evidence=(
                [EvidenceCode.IDA, EvidenceCode.EXP] if fused_dataset else []
            ),
        )

        ctx.state.reasoning_task = reasoning_task
        ctx.state.notes.append(f"Created reasoning task: {reasoning_task.task_type}")

        return PerformReasoning()

    def _determine_task_type(self, question: str) -> str:
        """Determine the type of reasoning task."""
        question_lower = question.lower()

        if any(term in question_lower for term in ["function", "role", "purpose"]):
            return "gene_function_prediction"
        if any(
            term in question_lower for term in ["interaction", "binding", "complex"]
        ):
            return "protein_interaction_prediction"
        if any(term in question_lower for term in ["drug", "compound", "inhibitor"]):
            return "drug_target_prediction"
        if any(
            term in question_lower
            for term in ["expression", "regulation", "transcript"]
        ):
            return "expression_analysis"
        if any(term in question_lower for term in ["structure", "fold", "domain"]):
            return "structure_function_analysis"
        return "general_reasoning"

    def _assess_difficulty(self, question: str) -> str:
        """Assess the difficulty level of the reasoning task."""
        question_lower = question.lower()

        if any(
            term in question_lower
            for term in ["complex", "multiple", "integrate", "combine"]
        ):
            return "hard"
        if any(term in question_lower for term in ["simple", "basic", "direct"]):
            return "easy"
        return "medium"


@dataclass
class PerformReasoning(BaseNode[BioinformaticsState]):  # type: ignore[unsupported-base]
    """Perform integrative reasoning using fused bioinformatics data."""

    async def run(self, ctx: GraphRunContext[BioinformaticsState]) -> SynthesizeResults:
        """Perform reasoning using the new agent system."""

        reasoning_task = ctx.state.reasoning_task
        fused_dataset = ctx.state.fused_dataset

        if not reasoning_task or not fused_dataset:
            ctx.state.notes.append(
                "Missing reasoning task or dataset, skipping reasoning"
            )
            return SynthesizeResults()

        ctx.state.notes.append("Performing integrative reasoning")
        ctx.state.processing_steps.append("Reasoning")

        try:
            # Use the new BioinformaticsAgent
            from DeepResearch.agents import BioinformaticsAgent

            bioinformatics_agent = BioinformaticsAgent()

            # Perform reasoning using the new agent
            reasoning_result = await bioinformatics_agent.perform_reasoning(
                reasoning_task, fused_dataset
            )

            ctx.state.reasoning_result = reasoning_result
            confidence = reasoning_result.get("confidence", 0.0)
            ctx.state.notes.append(
                f"Reasoning completed with confidence: {confidence:.3f}"
            )

        except Exception as e:
            ctx.state.notes.append(f"Reasoning failed: {e!s}")
            # Create fallback result
            ctx.state.reasoning_result = {
                "success": False,
                "answer": f"Reasoning failed: {e!s}",
                "confidence": 0.0,
                "supporting_evidence": [],
                "reasoning_chain": ["Error occurred during reasoning"],
            }

        return SynthesizeResults()


@dataclass
class SynthesizeResults(BaseNode[BioinformaticsState]):  # type: ignore[unsupported-base]
    """Synthesize final results from reasoning and data fusion."""

    async def run(
        self, ctx: GraphRunContext[BioinformaticsState]
    ) -> Annotated[End[str], Edge(label="done")]:
        """Synthesize final answer from all processing steps."""

        ctx.state.notes.append("Synthesizing final results")
        ctx.state.processing_steps.append("Synthesis")

        # Build final answer
        answer_parts = []

        # Add question
        answer_parts.append(f"Question: {ctx.state.question}")
        answer_parts.append("")

        # Add processing summary
        answer_parts.append("Processing Summary:")
        for step in ctx.state.processing_steps:
            answer_parts.append(f"- {step}")
        answer_parts.append("")

        # Add data fusion results
        if ctx.state.fused_dataset:
            answer_parts.append("Data Fusion Results:")
            answer_parts.append(f"- Dataset: {ctx.state.fused_dataset.name}")
            answer_parts.append(
                f"- Sources: {', '.join(ctx.state.fused_dataset.source_databases)}"
            )
            answer_parts.append(
                f"- Total Entities: {ctx.state.fused_dataset.total_entities}"
            )
            answer_parts.append("")

        # Add quality metrics
        if ctx.state.quality_metrics:
            answer_parts.append("Quality Metrics:")
            for metric, value in ctx.state.quality_metrics.items():
                answer_parts.append(f"- {metric}: {value:.3f}")
            answer_parts.append("")

        # Add reasoning results
        if ctx.state.reasoning_result and ctx.state.reasoning_result.get(
            "success", False
        ):
            answer_parts.append("Reasoning Results:")
            answer_parts.append(
                f"- Answer: {ctx.state.reasoning_result.get('answer', 'No answer')}"
            )
            answer_parts.append(
                f"- Confidence: {ctx.state.reasoning_result.get('confidence', 0.0):.3f}"
            )
            supporting_evidence = ctx.state.reasoning_result.get(
                "supporting_evidence", []
            )
            answer_parts.append(
                f"- Supporting Evidence: {len(supporting_evidence)} items"
            )

            reasoning_chain = ctx.state.reasoning_result.get("reasoning_chain", [])
            if reasoning_chain:
                answer_parts.append("- Reasoning Chain:")
                for i, step in enumerate(reasoning_chain, 1):
                    answer_parts.append(f"  {i}. {step}")
        else:
            answer_parts.append("Reasoning Results:")
            answer_parts.append("- Reasoning could not be completed successfully")

        # Add notes
        if ctx.state.notes:
            answer_parts.append("")
            answer_parts.append("Processing Notes:")
            for note in ctx.state.notes:
                answer_parts.append(f"- {note}")

        final_answer = "\n".join(answer_parts)
        ctx.state.final_answer = final_answer

        return End(final_answer)


# Create the bioinformatics workflow graph
bioinformatics_workflow = Graph(
    nodes=(
        ParseBioinformaticsQuery(),
        FuseDataSources(),
        AssessDataQuality(),
        CreateReasoningTask(),
        PerformReasoning(),
        SynthesizeResults(),
    ),
    state_type=BioinformaticsState,
)


def run_bioinformatics_workflow(
    question: str, config: dict[str, Any] | None = None
) -> str:
    """Run the bioinformatics workflow for a given question."""

    state = BioinformaticsState(question=question, config=config or {})

    result = asyncio.run(
        bioinformatics_workflow.run(ParseBioinformaticsQuery(), state=state)  # type: ignore
    )
    return result.output or ""
