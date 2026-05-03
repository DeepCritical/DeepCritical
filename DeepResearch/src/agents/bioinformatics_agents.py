"""
Bioinformatics agents for data fusion and reasoning tasks.

This module implements specialized agents using Pydantic AI for bioinformatics
data processing, fusion, and reasoning tasks.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from pydantic_ai import Agent

from DeepResearch.src.datatypes.bioinformatics import (
    BioinformaticsAgentDeps,
    DataFusionRequest,
    DataFusionResult,
    FusedDataset,
    GOAnnotation,
    PubMedPaper,
    ReasoningResult,
    ReasoningTask,
)
from DeepResearch.src.prompts.bioinformatics_agents import BioinformaticsAgentPrompts
from DeepResearch.src.utils.model_registry import resolve_pydantic_ai_model


class DataFusionAgent:
    """Agent for fusing bioinformatics data from multiple sources."""

    def __init__(
        self,
        model_name: str | None = None,
        model_role: str = "bioinformatics_reasoning",
        config: dict[str, Any] | None = None,
    ):
        self.model_name = model_name or resolve_pydantic_ai_model(config, model_role)
        self.model_role = model_role
        self.config = config or {}
        self.agent: Agent[BioinformaticsAgentDeps, DataFusionResult] = (
            self._create_agent()
        )

    def _create_agent(self) -> Agent[BioinformaticsAgentDeps, DataFusionResult]:
        """Create the data fusion agent."""
        # Get model from config or use default
        bioinformatics_config = self.config.get("bioinformatics", {})
        agents_config = bioinformatics_config.get("agents", {})
        data_fusion_config = agents_config.get("data_fusion", {})

        model = data_fusion_config.get("model", self.model_name)

        # Get system prompt from config or use default
        system_prompt = data_fusion_config.get(
            "system_prompt",
            BioinformaticsAgentPrompts.DATA_FUSION_SYSTEM,
        )

        return Agent[BioinformaticsAgentDeps, DataFusionResult](
            model=model,
            deps_type=BioinformaticsAgentDeps,
            output_type=DataFusionResult,
            system_prompt=system_prompt,
        )

    async def fuse_data(
        self, request: DataFusionRequest, deps: BioinformaticsAgentDeps
    ) -> DataFusionResult:
        """Fuse data from multiple sources based on the request."""

        fusion_prompt = BioinformaticsAgentPrompts.PROMPTS["data_fusion"].format(
            fusion_type=request.fusion_type,
            source_databases=", ".join(request.source_databases),
            filters=request.filters,
            quality_threshold=request.quality_threshold,
            max_entities=request.max_entities,
        )

        result = await self.agent.run(fusion_prompt, deps=deps)
        return result.output


class GOAnnotationAgent:
    """Agent for processing GO annotations with PubMed context."""

    def __init__(
        self,
        model_name: str | None = None,
        model_role: str = "bioinformatics_reasoning",
        config: Mapping[str, Any] | None = None,
    ):
        self.model_name = model_name or resolve_pydantic_ai_model(config, model_role)
        self.agent: Agent[BioinformaticsAgentDeps, list[GOAnnotation]] = (
            self._create_agent()
        )

    def _create_agent(self) -> Agent[BioinformaticsAgentDeps, list[GOAnnotation]]:
        """Create the GO annotation agent."""
        return Agent[BioinformaticsAgentDeps, list[GOAnnotation]](
            model=self.model_name,
            deps_type=BioinformaticsAgentDeps,
            output_type=list[GOAnnotation],
            system_prompt=BioinformaticsAgentPrompts.GO_ANNOTATION_SYSTEM,
        )

    async def process_annotations(
        self,
        annotations: list[dict[str, Any]],
        papers: list[PubMedPaper],
        deps: BioinformaticsAgentDeps,
    ) -> list[GOAnnotation]:
        """Process GO annotations with PubMed context."""

        processing_prompt = BioinformaticsAgentPrompts.PROMPTS[
            "go_annotation_processing"
        ].format(
            annotation_count=len(annotations),
            paper_count=len(papers),
        )

        result = await self.agent.run(processing_prompt, deps=deps)
        return result.output


class ReasoningAgent:
    """Agent for performing reasoning tasks on fused bioinformatics data."""

    def __init__(
        self,
        model_name: str | None = None,
        model_role: str = "bioinformatics_reasoning",
        config: Mapping[str, Any] | None = None,
    ):
        self.model_name = model_name or resolve_pydantic_ai_model(config, model_role)
        self.agent: Agent[BioinformaticsAgentDeps, ReasoningResult] = (
            self._create_agent()
        )

    def _create_agent(self) -> Agent[BioinformaticsAgentDeps, ReasoningResult]:
        """Create the reasoning agent."""
        return Agent[BioinformaticsAgentDeps, ReasoningResult](
            model=self.model_name,
            deps_type=BioinformaticsAgentDeps,
            output_type=ReasoningResult,
            system_prompt=BioinformaticsAgentPrompts.REASONING_SYSTEM,
        )

    async def perform_reasoning(
        self, task: ReasoningTask, dataset: FusedDataset, deps: BioinformaticsAgentDeps
    ) -> ReasoningResult:
        """Perform reasoning task on fused dataset."""

        reasoning_prompt = BioinformaticsAgentPrompts.PROMPTS["reasoning_task"].format(
            task_type=task.task_type,
            question=task.question,
            difficulty_level=task.difficulty_level,
            required_evidence=[code.value for code in task.required_evidence],
            total_entities=dataset.total_entities,
            source_databases=", ".join(dataset.source_databases),
            go_annotations_count=len(dataset.go_annotations),
            pubmed_papers_count=len(dataset.pubmed_papers),
            gene_expression_profiles_count=len(dataset.gene_expression_profiles),
            drug_targets_count=len(dataset.drug_targets),
            protein_structures_count=len(dataset.protein_structures),
            protein_interactions_count=len(dataset.protein_interactions),
        )

        result = await self.agent.run(reasoning_prompt, deps=deps)
        return result.output


class DataQualityAgent:
    """Agent for assessing data quality and consistency."""

    def __init__(
        self,
        model_name: str | None = None,
        model_role: str = "bioinformatics_reasoning",
        config: Mapping[str, Any] | None = None,
    ):
        self.model_name = model_name or resolve_pydantic_ai_model(config, model_role)
        self.agent: Agent[BioinformaticsAgentDeps, dict[str, float]] = (
            self._create_agent()
        )

    def _create_agent(self) -> Agent[BioinformaticsAgentDeps, dict[str, float]]:
        """Create the data quality agent."""
        return Agent[BioinformaticsAgentDeps, dict[str, float]](
            model=self.model_name,
            deps_type=BioinformaticsAgentDeps,
            output_type=dict[str, float],
            system_prompt=BioinformaticsAgentPrompts.DATA_QUALITY_SYSTEM,
        )

    async def assess_quality(
        self, dataset: FusedDataset, deps: BioinformaticsAgentDeps
    ) -> dict[str, float]:
        """Assess quality of fused dataset."""

        quality_prompt = BioinformaticsAgentPrompts.PROMPTS[
            "data_quality_assessment"
        ].format(
            total_entities=dataset.total_entities,
            source_databases=", ".join(dataset.source_databases),
            go_annotations_count=len(dataset.go_annotations),
            pubmed_papers_count=len(dataset.pubmed_papers),
            gene_expression_profiles_count=len(dataset.gene_expression_profiles),
            drug_targets_count=len(dataset.drug_targets),
            protein_structures_count=len(dataset.protein_structures),
            protein_interactions_count=len(dataset.protein_interactions),
        )

        result = await self.agent.run(quality_prompt, deps=deps)
        return result.output


class BioinformaticsAgent:
    """Main bioinformatics agent that coordinates all bioinformatics operations."""

    def __init__(
        self,
        model_name: str | None = None,
        model_role: str = "bioinformatics_reasoning",
        config: Mapping[str, Any] | None = None,
    ):
        self.model_name = model_name or resolve_pydantic_ai_model(config, model_role)
        self.orchestrator = AgentOrchestrator(
            self.model_name, model_role=model_role, config=config
        )

    async def process_request(
        self, request: DataFusionRequest, deps: BioinformaticsAgentDeps
    ) -> tuple[FusedDataset, ReasoningResult, dict[str, float]]:
        """Process a complete bioinformatics request end-to-end."""
        # Create reasoning dataset
        dataset, quality_metrics = await self.orchestrator.create_reasoning_dataset(
            request, deps
        )

        # Create a reasoning task for the request
        reasoning_task = ReasoningTask(
            task_id="main_task",
            task_type="integrative_analysis",
            question=getattr(request, "reasoning_question", None)
            or "Analyze the fused dataset",
            difficulty_level="moderate",
            required_evidence=[],  # Will use default evidence requirements
        )

        # Perform reasoning
        reasoning_result = await self.orchestrator.perform_integrative_reasoning(
            reasoning_task, dataset, deps
        )

        return dataset, reasoning_result, quality_metrics


class AgentOrchestrator:
    """Orchestrator for coordinating multiple bioinformatics agents."""

    def __init__(
        self,
        model_name: str | None = None,
        model_role: str = "bioinformatics_reasoning",
        config: Mapping[str, Any] | None = None,
    ):
        self.model_name = model_name or resolve_pydantic_ai_model(config, model_role)
        self.fusion_agent = DataFusionAgent(
            self.model_name, model_role=model_role, config=dict(config or {})
        )
        self.go_agent = GOAnnotationAgent(
            self.model_name, model_role=model_role, config=config
        )
        self.reasoning_agent = ReasoningAgent(
            self.model_name, model_role=model_role, config=config
        )
        self.quality_agent = DataQualityAgent(
            self.model_name, model_role=model_role, config=config
        )

    async def create_reasoning_dataset(
        self, request: DataFusionRequest, deps: BioinformaticsAgentDeps
    ) -> tuple[FusedDataset, dict[str, float]]:
        """Create a reasoning dataset by fusing multiple data sources."""

        # Step 1: Fuse data from multiple sources
        fusion_result = await self.fusion_agent.fuse_data(request, deps)

        if not fusion_result.success:
            msg = "Data fusion failed"
            raise ValueError(msg)

        # Step 2: Construct dataset from fusion result
        if fusion_result.fused_dataset is None:
            msg = "Fused dataset is None"
            raise ValueError(msg)
        dataset = fusion_result.fused_dataset

        # Step 3: Assess data quality
        quality_metrics = await self.quality_agent.assess_quality(dataset, deps)

        return dataset, quality_metrics

    async def perform_integrative_reasoning(
        self,
        reasoning_task: ReasoningTask,
        dataset: FusedDataset,
        deps: BioinformaticsAgentDeps,
    ) -> ReasoningResult:
        """Perform integrative reasoning using fused data and task."""
        return await self.reasoning_agent.perform_reasoning(
            reasoning_task, dataset, deps
        )
