"""
Primary workflow orchestrator for DeepCritical's workflow-of-workflows architecture.

This module implements the main orchestrator that coordinates multiple specialized workflows
using Pydantic AI patterns and multi-agent systems.
"""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import TYPE_CHECKING, Any

from pydantic_ai import Agent, RunContext

from DeepResearch.src.datatypes.workflow_orchestration import (
    HypothesisDataset,
    HypothesisTestingEnvironment,
    JudgeEvaluationRequest,
    JudgeEvaluationResult,
    MultiAgentCoordinationRequest,
    MultiAgentCoordinationResult,
    OrchestrationState,
    OrchestratorDependencies,
    WorkflowComposition,
    WorkflowConfig,
    WorkflowExecution,
    WorkflowOrchestrationConfig,
    WorkflowResult,
    WorkflowSpawnRequest,
    WorkflowSpawnResult,
    WorkflowStatus,
    WorkflowType,
)
from DeepResearch.src.prompts.workflow_orchestrator import WorkflowOrchestratorPrompts

if TYPE_CHECKING:
    from collections.abc import Callable

    from omegaconf import DictConfig


@dataclass
class PrimaryWorkflowOrchestrator:
    """Primary orchestrator for workflow-of-workflows architecture."""

    config: WorkflowOrchestrationConfig
    state: OrchestrationState = field(default_factory=OrchestrationState)
    workflow_registry: dict[str, Callable] = field(default_factory=dict)
    agent_registry: dict[str, Any] = field(default_factory=dict)
    judge_registry: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        """Initialize the orchestrator with workflows, agents, and judges."""
        self._register_workflows()
        self._register_agents()
        self._register_judges()
        self._create_primary_agent()

    def _register_workflows(self):
        """Register available workflows."""
        self.workflow_registry = {
            "rag_workflow": self._execute_rag_workflow,
            "bioinformatics_workflow": self._execute_bioinformatics_workflow,
            "search_workflow": self._execute_search_workflow,
            "multi_agent_workflow": self._execute_multi_agent_workflow,
            "hypothesis_generation": self._execute_hypothesis_generation_workflow,
            "hypothesis_testing": self._execute_hypothesis_testing_workflow,
            "reasoning_workflow": self._execute_reasoning_workflow,
            "code_execution_workflow": self._execute_code_execution_workflow,
            "evaluation_workflow": self._execute_evaluation_workflow,
        }

    def _register_agents(self):
        """Register available agents."""
        # This would be populated with actual agent instances
        self.agent_registry = {
            "search_agent": None,  # Would be SearchAgent instance
            "bioinformatics_agent": None,  # Would be BioinformaticsAgent instance
            "research_agent": None,  # Would be ResearchAgent instance
            "code_agent": None,  # Would be CodeAgent instance
            "reasoning_agent": None,  # Would be ReasoningAgent instance
        }

    def _register_judges(self):
        """Register available judges."""
        # This would be populated with actual judge instances
        self.judge_registry = {
            "quality_judge": None,
            "scientific_validity_judge": None,
            "code_quality_judge": None,
            "research_impact_judge": None,
            "hypothesis_quality_judge": None,
            "reasoning_quality_judge": None,
            "bioinformatics_accuracy_judge": None,
            "coordination_quality_judge": None,
            "overall_system_judge": None,
        }

    def _create_primary_agent(self):
        """Create the primary REACT agent."""
        # Get prompts from the prompts module
        prompts = WorkflowOrchestratorPrompts()

        self.primary_agent = Agent(
            model=self.config.primary_workflow.parameters.get(
                "model_name", "anthropic:claude-sonnet-4-0"
            ),
            deps_type=OrchestratorDependencies,
            system_prompt=prompts.get_system_prompt(),
            instructions=prompts.get_instructions(),
        )
        self._register_primary_tools()

    def _register_primary_tools(self):
        """Register tools for the primary agent."""

        @self.primary_agent.tool
        def spawn_workflow(
            ctx: RunContext[OrchestratorDependencies],
            workflow_type: str,
            workflow_name: str,
            input_data: dict[str, Any],
            parameters: dict[str, Any] | None = None,
            priority: int = 0,
        ) -> WorkflowSpawnResult:
            """Spawn a new workflow execution."""
            try:
                request = WorkflowSpawnRequest(
                    workflow_type=WorkflowType(workflow_type),
                    workflow_name=workflow_name,
                    input_data=input_data,
                    parameters=parameters or {},
                    priority=priority,
                )
                return self._spawn_workflow(request)
            except Exception as e:
                return WorkflowSpawnResult(
                    success=False,
                    execution_id="",
                    workflow_name=workflow_name,
                    status=WorkflowStatus.FAILED,
                    error_message=str(e),
                )

        @self.primary_agent.tool
        def coordinate_multi_agent_system(
            ctx: RunContext[OrchestratorDependencies],
            system_id: str,
            task_description: str,
            input_data: dict[str, Any],
            coordination_strategy: str = "collaborative",
            max_rounds: int = 10,
        ) -> MultiAgentCoordinationResult:
            """Coordinate a multi-agent system."""
            try:
                request = MultiAgentCoordinationRequest(
                    system_id=system_id,
                    task_description=task_description,
                    input_data=input_data,
                    coordination_strategy=coordination_strategy,
                    max_rounds=max_rounds,
                )
                return self._coordinate_multi_agent_system(request)
            except Exception:
                return MultiAgentCoordinationResult(
                    success=False,
                    system_id=system_id,
                    final_result={},
                    coordination_rounds=0,
                    agent_results={},
                    consensus_score=0.0,
                    # error_message is not a field in MultiAgentCoordinationResult
                )

        @self.primary_agent.tool
        def evaluate_with_judge(
            ctx: RunContext[OrchestratorDependencies],
            judge_id: str,
            content_to_evaluate: dict[str, Any],
            evaluation_criteria: list[str],
            context: dict[str, Any] | None = None,
        ) -> JudgeEvaluationResult:
            """Evaluate content using a judge."""
            try:
                request = JudgeEvaluationRequest(
                    judge_id=judge_id,
                    content_to_evaluate=content_to_evaluate,
                    evaluation_criteria=evaluation_criteria,
                    context=context or {},
                )
                return self._evaluate_with_judge(request)
            except Exception as e:
                return JudgeEvaluationResult(
                    success=False,
                    judge_id=judge_id,
                    overall_score=0.0,
                    criterion_scores={},
                    feedback=f"Evaluation failed: {e!s}",
                    recommendations=[],
                )

        @self.primary_agent.tool
        def compose_workflows(
            ctx: RunContext[OrchestratorDependencies],
            user_input: str,
            selected_workflows: list[str],
            execution_strategy: str = "parallel",
        ) -> WorkflowComposition:
            """Compose workflows based on user input."""
            return self._compose_workflows(
                user_input, selected_workflows, execution_strategy
            )

        @self.primary_agent.tool
        def generate_hypothesis_dataset(
            ctx: RunContext[OrchestratorDependencies],
            name: str,
            description: str,
            hypotheses: list[dict[str, Any]],
            source_workflows: list[str],
        ) -> HypothesisDataset:
            """Generate a hypothesis dataset."""
            return HypothesisDataset(
                name=name,
                description=description,
                hypotheses=hypotheses,
                source_workflows=source_workflows,
            )

        @self.primary_agent.tool
        def create_testing_environment(
            ctx: RunContext[OrchestratorDependencies],
            name: str,
            hypothesis: dict[str, Any],
            test_configuration: dict[str, Any],
            expected_outcomes: list[str],
        ) -> HypothesisTestingEnvironment:
            """Create a hypothesis testing environment."""
            return HypothesisTestingEnvironment(
                name=name,
                hypothesis=hypothesis,
                test_configuration=test_configuration,
                expected_outcomes=expected_outcomes,
            )

    async def execute_primary_workflow(
        self, user_input: str, config: DictConfig
    ) -> dict[str, Any]:
        """Execute the primary REACT workflow."""
        # Create dependencies
        deps = OrchestratorDependencies(
            config=dict(config) if config else {},
            user_input=user_input,
            context={"execution_start": datetime.now().isoformat()},
            available_workflows=list(self.workflow_registry.keys()),
            available_agents=list(self.agent_registry.keys()),
            available_judges=list(self.judge_registry.keys()),
        )

        # Execute primary agent
        result = await self.primary_agent.run(user_input, deps=deps)

        # Update state
        self.state.last_updated = datetime.now()
        self.state.system_metrics["total_executions"] = len(
            self.state.completed_executions
        )

        return {
            "success": True,
            "result": result,
            "state": self.state,
            "execution_metadata": {
                "workflows_spawned": len(self.state.active_executions),
                "total_executions": len(self.state.completed_executions),
                "execution_time": time.time(),
            },
        }

    def _spawn_workflow(self, request: WorkflowSpawnRequest) -> WorkflowSpawnResult:
        """Spawn a new workflow execution."""
        try:
            # Create workflow execution
            execution = WorkflowExecution(
                workflow_config=self._get_workflow_config(
                    request.workflow_type, request.workflow_name
                ),
                input_data=request.input_data,
                status=WorkflowStatus.PENDING,
            )

            # Add to active executions
            self.state.active_executions.append(execution)

            # Execute workflow asynchronously
            asyncio.create_task(self._execute_workflow_async(execution))

            return WorkflowSpawnResult(
                success=True,
                execution_id=execution.execution_id,
                workflow_name=request.workflow_name,
                status=WorkflowStatus.PENDING,
            )
        except Exception as e:
            return WorkflowSpawnResult(
                success=False,
                execution_id="",
                workflow_name=request.workflow_name,
                status=WorkflowStatus.FAILED,
                error_message=str(e),
            )

    async def _execute_workflow_async(self, execution: WorkflowExecution):
        """Execute a workflow asynchronously."""
        try:
            execution.status = WorkflowStatus.RUNNING
            execution.start_time = datetime.now()

            # Get workflow function
            workflow_func = self.workflow_registry.get(
                execution.workflow_config.workflow_type.value
            )
            if not workflow_func:
                msg = (
                    f"Unknown workflow type: {execution.workflow_config.workflow_type}"
                )
                raise ValueError(msg)

            # Execute workflow
            result = await workflow_func(
                execution.input_data, execution.workflow_config.parameters
            )

            # Create workflow result
            workflow_result = WorkflowResult(
                execution_id=execution.execution_id,
                workflow_name=execution.workflow_config.name,
                status=WorkflowStatus.COMPLETED,
                output_data=result,
                execution_time=execution.duration or 0.0,
            )

            # Update state
            execution.status = WorkflowStatus.COMPLETED
            execution.end_time = datetime.now()
            execution.output_data = result

            self.state.active_executions.remove(execution)
            self.state.completed_executions.append(workflow_result)

        except Exception as e:
            execution.status = WorkflowStatus.FAILED
            execution.end_time = datetime.now()
            execution.error_message = str(e)

            # Create failed result
            workflow_result = WorkflowResult(
                execution_id=execution.execution_id,
                workflow_name=execution.workflow_config.name,
                status=WorkflowStatus.FAILED,
                output_data={},
                execution_time=execution.duration or 0.0,
                error_details={"error": str(e)},
            )

            self.state.active_executions.remove(execution)
            self.state.completed_executions.append(workflow_result)

    def _get_workflow_config(self, workflow_type: WorkflowType, workflow_name: str):
        """Get workflow configuration."""
        # This would return the appropriate workflow config from the orchestrator config
        for workflow_config in self.config.sub_workflows:
            if (
                workflow_config.workflow_type == workflow_type
                and workflow_config.name == workflow_name
            ):
                return workflow_config

        # Return default config if not found
        return WorkflowConfig(
            workflow_type=workflow_type, name=workflow_name, enabled=True
        )

    def _coordinate_multi_agent_system(
        self, request: MultiAgentCoordinationRequest
    ) -> MultiAgentCoordinationResult:
        """Coordinate a multi-agent system."""
        # This would implement actual multi-agent coordination
        # For now, return a placeholder result
        return MultiAgentCoordinationResult(
            success=True,
            system_id=request.system_id,
            final_result={"coordinated_result": "placeholder"},
            coordination_rounds=1,
            consensus_score=0.8,
        )

    def _evaluate_with_judge(
        self, request: JudgeEvaluationRequest
    ) -> JudgeEvaluationResult:
        """Evaluate content using a judge."""
        # This would implement actual judge evaluation
        # For now, return a placeholder result
        return JudgeEvaluationResult(
            success=True,
            judge_id=request.judge_id,
            overall_score=8.5,
            criterion_scores={"quality": 8.5, "accuracy": 8.0, "clarity": 9.0},
            feedback="Good quality output with room for improvement",
            recommendations=["Add more detail", "Improve clarity"],
        )

    def _compose_workflows(
        self, user_input: str, selected_workflows: list[str], execution_strategy: str
    ) -> WorkflowComposition:
        """Compose workflows based on user input."""
        return WorkflowComposition(
            user_input=user_input,
            selected_workflows=selected_workflows,
            execution_order=selected_workflows,  # Simple ordering for now
            composition_strategy=execution_strategy,
        )

    # Workflow execution methods (placeholders for now)
    async def _execute_rag_workflow(
        self, input_data: dict[str, Any], parameters: dict[str, Any]
    ) -> dict[str, Any]:
        """Execute RAG workflow."""
        # This would implement actual RAG workflow execution
        return {"rag_result": "placeholder", "documents_retrieved": 5}

    async def _execute_bioinformatics_workflow(
        self, input_data: dict[str, Any], parameters: dict[str, Any]
    ) -> dict[str, Any]:
        """Execute bioinformatics workflow."""
        # This would implement actual bioinformatics workflow execution
        return {
            "bioinformatics_result": "placeholder",
            "data_sources": ["GO", "PubMed"],
        }

    async def _execute_search_workflow(
        self, input_data: dict[str, Any], parameters: dict[str, Any]
    ) -> dict[str, Any]:
        """Execute search workflow."""
        # This would implement actual search workflow execution
        return {"search_result": "placeholder", "results_found": 10}

    async def _execute_multi_agent_workflow(
        self, input_data: dict[str, Any], parameters: dict[str, Any]
    ) -> dict[str, Any]:
        """Execute multi-agent workflow."""
        # This would implement actual multi-agent workflow execution
        return {"multi_agent_result": "placeholder", "agents_used": 3}

    async def _execute_hypothesis_generation_workflow(
        self, input_data: dict[str, Any], parameters: dict[str, Any]
    ) -> dict[str, Any]:
        """Execute hypothesis generation workflow."""
        # This would implement actual hypothesis generation
        return {"hypotheses": [{"hypothesis": "placeholder", "confidence": 0.8}]}

    async def _execute_hypothesis_testing_workflow(
        self, input_data: dict[str, Any], parameters: dict[str, Any]
    ) -> dict[str, Any]:
        """Execute hypothesis testing workflow."""
        # This would implement actual hypothesis testing
        return {"test_results": "placeholder", "success": True}

    async def _execute_reasoning_workflow(
        self, input_data: dict[str, Any], parameters: dict[str, Any]
    ) -> dict[str, Any]:
        """Execute reasoning workflow."""
        # This would implement actual reasoning
        return {"reasoning_result": "placeholder", "confidence": 0.9}

    async def _execute_code_execution_workflow(
        self, input_data: dict[str, Any], parameters: dict[str, Any]
    ) -> dict[str, Any]:
        """Execute code execution workflow."""
        # This would implement actual code execution
        return {"code_result": "placeholder", "execution_success": True}

    async def _execute_evaluation_workflow(
        self, input_data: dict[str, Any], parameters: dict[str, Any]
    ) -> dict[str, Any]:
        """Execute evaluation workflow."""
        # This would implement actual evaluation
        return {"evaluation_result": "placeholder", "score": 8.5}


# Alias for backward compatibility
WorkflowOrchestrator = PrimaryWorkflowOrchestrator
