"""
Bioinformatics tools for DeepCritical research workflows.

This module implements deferred tools for bioinformatics data processing,
integration with Pydantic AI, and agent-to-agent communication.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field

# Note: defer decorator is not available in current pydantic-ai version

from .base import ToolSpec, ToolRunner, ExecutionResult, registry
from ..datatypes.bioinformatics import (
    GOAnnotation,
    PubMedPaper,
    GEOSeries,
    DrugTarget,
    ProteinStructure,
    FusedDataset,
    ReasoningTask,
    DataFusionRequest,
)
from ..agents.bioinformatics_agents import DataFusionResult, ReasoningResult
from ..statemachines.bioinformatics_workflow import run_bioinformatics_workflow


class BioinformaticsToolDeps(BaseModel):
    """Dependencies for bioinformatics tools."""

    config: Dict[str, Any] = Field(default_factory=dict)
    model_name: str = Field(
        "anthropic:claude-sonnet-4-0", description="Model to use for AI agents"
    )
    quality_threshold: float = Field(
        0.8, ge=0.0, le=1.0, description="Quality threshold for data fusion"
    )

    @classmethod
    def from_config(cls, config: Dict[str, Any], **kwargs) -> "BioinformaticsToolDeps":
        """Create tool dependencies from configuration."""
        bioinformatics_config = config.get("bioinformatics", {})
        model_config = bioinformatics_config.get("model", {})
        quality_config = bioinformatics_config.get("quality", {})

        return cls(
            config=config,
            model_name=model_config.get("default", "anthropic:claude-sonnet-4-0"),
            quality_threshold=quality_config.get("default_threshold", 0.8),
            **kwargs,
        )


# Deferred tool definitions for bioinformatics data processing
# @defer - not available in current pydantic-ai version
def go_annotation_processor(
    annotations: List[Dict[str, Any]],
    papers: List[Dict[str, Any]],
    evidence_codes: Optional[List[str]] = None,
) -> List[GOAnnotation]:
    """Process GO annotations with PubMed paper context."""
    # This would be implemented with actual data processing logic
    # For now, return mock data structure
    return []


# @defer - not available in current pydantic-ai version
def pubmed_paper_retriever(
    query: str, max_results: int = 100, year_min: Optional[int] = None
) -> List[PubMedPaper]:
    """Retrieve PubMed papers based on query."""
    # This would be implemented with actual PubMed API calls
    # For now, return mock data structure
    return []


# @defer - not available in current pydantic-ai version
def geo_data_retriever(
    series_ids: List[str], include_expression: bool = True
) -> List[GEOSeries]:
    """Retrieve GEO data for specified series."""
    # This would be implemented with actual GEO API calls
    # For now, return mock data structure
    return []


# @defer - not available in current pydantic-ai version
def drug_target_mapper(
    drug_ids: List[str], target_types: Optional[List[str]] = None
) -> List[DrugTarget]:
    """Map drugs to their targets from DrugBank and TTD."""
    # This would be implemented with actual database queries
    # For now, return mock data structure
    return []


# @defer - not available in current pydantic-ai version
def protein_structure_retriever(
    pdb_ids: List[str], include_interactions: bool = True
) -> List[ProteinStructure]:
    """Retrieve protein structures from PDB."""
    # This would be implemented with actual PDB API calls
    # For now, return mock data structure
    return []


# @defer - not available in current pydantic-ai version
def data_fusion_engine(
    fusion_request: DataFusionRequest, deps: BioinformaticsToolDeps
) -> DataFusionResult:
    """Fuse data from multiple bioinformatics sources."""
    # This would orchestrate the actual data fusion process
    # For now, return mock result
    return DataFusionResult(
        success=True,
        fused_dataset=FusedDataset(
            dataset_id="mock_fusion",
            name="Mock Fused Dataset",
            description="Mock dataset for testing",
            source_databases=fusion_request.source_databases,
        ),
        quality_metrics={"overall_quality": 0.85},
    )


# @defer - not available in current pydantic-ai version
def reasoning_engine(
    task: ReasoningTask, dataset: FusedDataset, deps: BioinformaticsToolDeps
) -> ReasoningResult:
    """Perform reasoning on fused bioinformatics data."""
    # This would perform the actual reasoning
    # For now, return mock result
    return ReasoningResult(
        success=True,
        answer="Mock reasoning result based on integrated data sources",
        confidence=0.8,
        supporting_evidence=["evidence1", "evidence2"],
        reasoning_chain=[
            "Step 1: Analyze data",
            "Step 2: Apply reasoning",
            "Step 3: Generate answer",
        ],
    )


# Tool runners for integration with the existing registry system
@dataclass
class BioinformaticsFusionTool(ToolRunner):
    """Tool for bioinformatics data fusion."""

    def __init__(self):
        super().__init__(
            ToolSpec(
                name="bioinformatics_fusion",
                description="Fuse data from multiple bioinformatics sources (GO, PubMed, GEO, etc.)",
                inputs={
                    "fusion_type": "TEXT",
                    "source_databases": "TEXT",
                    "filters": "TEXT",
                    "quality_threshold": "FLOAT",
                },
                outputs={
                    "fused_dataset": "JSON",
                    "quality_metrics": "JSON",
                    "success": "BOOLEAN",
                },
            )
        )

    def run(self, params: Dict[str, Any]) -> ExecutionResult:
        """Execute bioinformatics data fusion."""
        try:
            # Extract parameters
            fusion_type = params.get("fusion_type", "MultiSource")
            source_databases = params.get("source_databases", "GO,PubMed").split(",")
            filters = params.get("filters", {})
            quality_threshold = float(params.get("quality_threshold", 0.8))

            # Create fusion request
            fusion_request = DataFusionRequest(
                request_id=f"fusion_{asyncio.get_event_loop().time()}",
                fusion_type=fusion_type,
                source_databases=source_databases,
                filters=filters,
                quality_threshold=quality_threshold,
            )

            # Create tool dependencies from config
            deps = BioinformaticsToolDeps.from_config(
                config=params.get("config", {}), quality_threshold=quality_threshold
            )

            # Execute fusion using deferred tool
            fusion_result = data_fusion_engine(fusion_request, deps)

            return ExecutionResult(
                success=fusion_result.success,
                data={
                    "fused_dataset": (
                        fusion_result.fused_dataset.model_dump()
                        if fusion_result.fused_dataset
                        else None
                    ),
                    "quality_metrics": fusion_result.quality_metrics,
                    "success": fusion_result.success,
                },
                error=(
                    None if fusion_result.success else "; ".join(fusion_result.errors)
                ),
            )

        except Exception as e:
            return ExecutionResult(
                success=False, data={}, error=f"Bioinformatics fusion failed: {str(e)}"
            )


@dataclass
class BioinformaticsReasoningTool(ToolRunner):
    """Tool for bioinformatics reasoning tasks."""

    def __init__(self):
        super().__init__(
            ToolSpec(
                name="bioinformatics_reasoning",
                description="Perform integrative reasoning on bioinformatics data",
                inputs={
                    "question": "TEXT",
                    "task_type": "TEXT",
                    "dataset": "JSON",
                    "difficulty_level": "TEXT",
                },
                outputs={
                    "answer": "TEXT",
                    "confidence": "FLOAT",
                    "supporting_evidence": "JSON",
                    "reasoning_chain": "JSON",
                },
            )
        )

    def run(self, params: Dict[str, Any]) -> ExecutionResult:
        """Execute bioinformatics reasoning."""
        try:
            # Extract parameters
            question = params.get("question", "")
            task_type = params.get("task_type", "general_reasoning")
            dataset_data = params.get("dataset", {})
            difficulty_level = params.get("difficulty_level", "medium")

            # Create reasoning task
            reasoning_task = ReasoningTask(
                task_id=f"reasoning_{asyncio.get_event_loop().time()}",
                task_type=task_type,
                question=question,
                difficulty_level=difficulty_level,
            )

            # Create fused dataset from provided data
            fused_dataset = FusedDataset(**dataset_data) if dataset_data else None

            if not fused_dataset:
                return ExecutionResult(
                    success=False, data={}, error="No dataset provided for reasoning"
                )

            # Create tool dependencies from config
            deps = BioinformaticsToolDeps.from_config(config=params.get("config", {}))

            # Execute reasoning using deferred tool
            reasoning_result = reasoning_engine(reasoning_task, fused_dataset, deps)

            return ExecutionResult(
                success=reasoning_result.success,
                data={
                    "answer": reasoning_result.answer,
                    "confidence": reasoning_result.confidence,
                    "supporting_evidence": reasoning_result.supporting_evidence,
                    "reasoning_chain": reasoning_result.reasoning_chain,
                },
                error=None if reasoning_result.success else "Reasoning failed",
            )

        except Exception as e:
            return ExecutionResult(
                success=False,
                data={},
                error=f"Bioinformatics reasoning failed: {str(e)}",
            )


@dataclass
class BioinformaticsWorkflowTool(ToolRunner):
    """Tool for running complete bioinformatics workflows."""

    def __init__(self):
        super().__init__(
            ToolSpec(
                name="bioinformatics_workflow",
                description="Run complete bioinformatics workflow with data fusion and reasoning",
                inputs={"question": "TEXT", "config": "JSON"},
                outputs={
                    "final_answer": "TEXT",
                    "processing_steps": "JSON",
                    "quality_metrics": "JSON",
                    "reasoning_result": "JSON",
                },
            )
        )

    def run(self, params: Dict[str, Any]) -> ExecutionResult:
        """Execute complete bioinformatics workflow."""
        try:
            # Extract parameters
            question = params.get("question", "")
            config = params.get("config", {})

            if not question:
                return ExecutionResult(
                    success=False,
                    data={},
                    error="No question provided for bioinformatics workflow",
                )

            # Run the complete workflow
            final_answer = run_bioinformatics_workflow(question, config)

            return ExecutionResult(
                success=True,
                data={
                    "final_answer": final_answer,
                    "processing_steps": [
                        "Parse",
                        "Fuse",
                        "Assess",
                        "Create",
                        "Reason",
                        "Synthesize",
                    ],
                    "quality_metrics": {"workflow_completion": 1.0},
                    "reasoning_result": {"success": True, "answer": final_answer},
                },
                error=None,
            )

        except Exception as e:
            return ExecutionResult(
                success=False,
                data={},
                error=f"Bioinformatics workflow failed: {str(e)}",
            )


@dataclass
class GOAnnotationTool(ToolRunner):
    """Tool for processing GO annotations with PubMed context."""

    def __init__(self):
        super().__init__(
            ToolSpec(
                name="go_annotation_processor",
                description="Process GO annotations with PubMed paper context for reasoning tasks",
                inputs={
                    "annotations": "JSON",
                    "papers": "JSON",
                    "evidence_codes": "TEXT",
                },
                outputs={
                    "processed_annotations": "JSON",
                    "quality_score": "FLOAT",
                    "annotation_count": "INTEGER",
                },
            )
        )

    def run(self, params: Dict[str, Any]) -> ExecutionResult:
        """Process GO annotations with PubMed context."""
        try:
            # Extract parameters
            annotations = params.get("annotations", [])
            papers = params.get("papers", [])
            evidence_codes = params.get("evidence_codes", "IDA,EXP").split(",")

            # Process annotations using deferred tool
            processed_annotations = go_annotation_processor(
                annotations, papers, evidence_codes
            )

            # Calculate quality score based on evidence codes
            quality_score = 0.9 if "IDA" in evidence_codes else 0.7

            return ExecutionResult(
                success=True,
                data={
                    "processed_annotations": [
                        ann.model_dump() for ann in processed_annotations
                    ],
                    "quality_score": quality_score,
                    "annotation_count": len(processed_annotations),
                },
                error=None,
            )

        except Exception as e:
            return ExecutionResult(
                success=False,
                data={},
                error=f"GO annotation processing failed: {str(e)}",
            )


@dataclass
class PubMedRetrievalTool(ToolRunner):
    """Tool for retrieving PubMed papers."""

    def __init__(self):
        super().__init__(
            ToolSpec(
                name="pubmed_retriever",
                description="Retrieve PubMed papers based on query with full text for open access papers",
                inputs={
                    "query": "TEXT",
                    "max_results": "INTEGER",
                    "year_min": "INTEGER",
                },
                outputs={
                    "papers": "JSON",
                    "total_found": "INTEGER",
                    "open_access_count": "INTEGER",
                },
            )
        )

    def run(self, params: Dict[str, Any]) -> ExecutionResult:
        """Retrieve PubMed papers."""
        try:
            # Extract parameters
            query = params.get("query", "")
            max_results = int(params.get("max_results", 100))
            year_min = params.get("year_min")

            if not query:
                return ExecutionResult(
                    success=False,
                    data={},
                    error="No query provided for PubMed retrieval",
                )

            # Retrieve papers using deferred tool
            papers = pubmed_paper_retriever(query, max_results, year_min)

            # Count open access papers
            open_access_count = sum(1 for paper in papers if paper.is_open_access)

            return ExecutionResult(
                success=True,
                data={
                    "papers": [paper.model_dump() for paper in papers],
                    "total_found": len(papers),
                    "open_access_count": open_access_count,
                },
                error=None,
            )

        except Exception as e:
            return ExecutionResult(
                success=False, data={}, error=f"PubMed retrieval failed: {str(e)}"
            )


# Register all bioinformatics tools
registry.register("bioinformatics_fusion", BioinformaticsFusionTool)
registry.register("bioinformatics_reasoning", BioinformaticsReasoningTool)
registry.register("bioinformatics_workflow", BioinformaticsWorkflowTool)
registry.register("go_annotation_processor", GOAnnotationTool)
registry.register("pubmed_retriever", PubMedRetrievalTool)
