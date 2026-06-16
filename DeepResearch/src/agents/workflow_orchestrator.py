"""
Primary workflow orchestrator for DeepCritical's workflow-of-workflows architecture.

This module implements the main orchestrator that coordinates multiple specialized workflows
using Pydantic AI patterns and multi-agent systems.
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Protocol

from omegaconf import DictConfig
from pydantic_ai import Agent, RunContext
from pydantic_ai.exceptions import AgentRunError

from DeepResearch.src.agents.multi_agent_coordinator import MultiAgentCoordinator
from DeepResearch.src.agents.workflow_judge import run_llm_judge
from DeepResearch.src.agents.workflow_supervisor import WorkflowSupervisor
from DeepResearch.src.datatypes.llm_models import DEFAULT_PYDANTIC_AI_MODEL
from DeepResearch.src.datatypes.workflow_orchestration import (
    HypothesisDataset,
    HypothesisTestingEnvironment,
    JudgeConfig,
    JudgeEvaluationRequest,
    JudgeEvaluationResult,
    MultiAgentCoordinationRequest,
    MultiAgentCoordinationResult,
    OrchestrationState,
    OrchestratorDependencies,
    WorkflowAdapterResult,
    WorkflowComposition,
    WorkflowConfig,
    WorkflowExecution,
    WorkflowOrchestrationConfig,
    WorkflowPlan,
    WorkflowResult,
    WorkflowRunContext,
    WorkflowSpawnRequest,
    WorkflowSpawnResult,
    WorkflowStatus,
    WorkflowType,
)
from DeepResearch.src.prompts.workflow_orchestrator import WorkflowOrchestratorPrompts
from DeepResearch.src.tools.registry import canonical_registry
from DeepResearch.src.utils.model_registry import resolve_pydantic_ai_model

logger = logging.getLogger(__name__)


def _hypothesis_generation_return_payload(
    *,
    dataset: Any,
    meta: dict[str, Any],
    judge_payload: dict[str, Any] | None,
    run_quality_judge: bool,
    fail_on_judge_failure: bool = False,
) -> dict[str, Any]:
    """Shared response shape for hypothesis pipelines (primary tool + spawned workflow).

    When ``run_quality_judge`` is True and ``fail_on_judge_failure`` is True,
    ``success`` is False if the judge fails or returns no result.
    """
    answer_lines: list[str] = []
    for i, row in enumerate(dataset.hypotheses, start=1):
        stmt = row.get("statement") if isinstance(row, dict) else None
        answer_lines.append(f"{i}. {stmt or row!s}")
    pipeline_success = True
    judge_ok: bool | None = None
    if run_quality_judge:
        if judge_payload is None:
            judge_ok = False
        else:
            judge_ok = bool(judge_payload.get("success"))
        if fail_on_judge_failure and judge_ok is not True:
            pipeline_success = False

    out: dict[str, Any] = {
        "success": pipeline_success,
        "hypothesis_dataset": dataset.model_dump(),
        "hypotheses": dataset.hypotheses,
        "answer": "\n".join(answer_lines),
        "metadata": meta,
        "judge": judge_payload,
    }
    if run_quality_judge:
        if judge_payload is None:
            out["quality_judge_ok"] = False
            out["quality_judge_error"] = "Quality judge did not return a result"
        else:
            ok = bool(judge_payload.get("success"))
            out["quality_judge_ok"] = ok
            if not ok:
                out["quality_judge_error"] = (
                    judge_payload.get("error_message")
                    or judge_payload.get("feedback")
                    or "Quality judge evaluation failed"
                )
    return out


class WorkflowAdapter(Protocol):
    """Minimal adapter contract for executable workflow units."""

    workflow_type: WorkflowType

    async def execute(
        self, execution: WorkflowExecution, context: WorkflowRunContext
    ) -> WorkflowAdapterResult:
        """Execute a workflow and return a normalized adapter result."""


@dataclass
class FunctionWorkflowAdapter:
    """Adapter wrapper around the current ``_execute_*_workflow`` methods."""

    workflow_type: WorkflowType
    workflow_func: Callable[[dict[str, Any], dict[str, Any]], Awaitable[Any]]

    async def execute(
        self, execution: WorkflowExecution, context: WorkflowRunContext
    ) -> WorkflowAdapterResult:
        output = await self.workflow_func(
            execution.input_data, execution.workflow_config.parameters
        )
        if isinstance(output, WorkflowAdapterResult):
            return output
        if not isinstance(output, dict):
            output = {"result": output}
        success = bool(output.get("success", True))
        error_message = output.get("error") or output.get("error_message")
        return WorkflowAdapterResult(
            success=success,
            output_data=output,
            metadata={
                "workflow_type": execution.workflow_config.workflow_type.value,
                "workflow_name": execution.workflow_config.name,
                "execution_mode": context.execution_mode,
            },
            retryable=bool(output.get("retryable", False)),
            degraded=bool(output.get("degraded", False)),
            error_message=str(error_message) if error_message else None,
        )


@dataclass
class PrimaryWorkflowOrchestrator:
    """Primary orchestrator for workflow-of-workflows architecture."""

    config: WorkflowOrchestrationConfig
    state: OrchestrationState = field(default_factory=OrchestrationState)
    workflow_registry: dict[str, Callable[..., Any]] = field(default_factory=dict)
    adapter_registry: dict[str, WorkflowAdapter] = field(default_factory=dict)
    agent_registry: dict[str, Any] = field(default_factory=dict)
    judge_registry: dict[str, Any] = field(default_factory=dict)
    _tasks_by_execution_id: dict[str, asyncio.Task[Any]] = field(
        default_factory=dict, init=False
    )
    _executions_by_id: dict[str, WorkflowExecution] = field(
        default_factory=dict, init=False
    )

    def __post_init__(self):
        """Initialize the orchestrator with workflows, agents, and judges."""
        self._register_workflows()
        self._register_agents()
        self._register_judges()
        self._create_primary_agent()
        self._supervisor = WorkflowSupervisor(self.state)

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
        self.adapter_registry = {
            workflow_type: FunctionWorkflowAdapter(
                workflow_type=WorkflowType(workflow_type),
                workflow_func=workflow_func,
            )
            for workflow_type, workflow_func in self.workflow_registry.items()
        }

    def _register_agents(self):
        """Register agent metadata from multi-agent system configs (MVP)."""
        self.agent_registry = {
            "multi_agent_system_ids": [
                s.system_id for s in self.config.multi_agent_systems if s.enabled
            ],
            "configured_agent_ids": [
                ac.agent_id
                for s in self.config.multi_agent_systems
                for ac in s.agents
                if s.enabled and ac.enabled
            ],
        }

    def _register_judges(self):
        """Register enabled judges from config; ensure at least one default judge."""
        self.judge_registry = {}
        for jc in self.config.judges:
            if jc.enabled:
                self.judge_registry[jc.judge_id] = jc
        if not self.judge_registry:
            raw_model = self.config.primary_workflow.parameters.get(
                "model_name", DEFAULT_PYDANTIC_AI_MODEL
            )
            # JudgeConfig expects a provider id string; primary may use TestModel.
            default_model = (
                raw_model if isinstance(raw_model, str) else DEFAULT_PYDANTIC_AI_MODEL
            )
            qj = JudgeConfig(
                judge_id="quality_judge",
                name="Default quality judge",
                model_name=default_model,
                evaluation_criteria=["quality", "accuracy", "clarity"],
            )
            self.judge_registry["quality_judge"] = qj
        # Pipeline defaults use this id; alias when omitted from config.
        if "hypothesis_quality_judge" not in self.judge_registry:
            base = self.judge_registry.get("quality_judge")
            if base is None and self.judge_registry:
                base = next(iter(self.judge_registry.values()))
            if base is not None:
                self.judge_registry["hypothesis_quality_judge"] = base.model_copy(
                    update={
                        "judge_id": "hypothesis_quality_judge",
                        "name": "Hypothesis quality judge",
                        "evaluation_criteria": [
                            "testability",
                            "falsifiability",
                            "evidence_support",
                        ],
                    }
                )

    def _create_primary_agent(self):
        """Create the primary REACT agent."""
        prompts = WorkflowOrchestratorPrompts()
        parameters = self.config.primary_workflow.parameters
        model = parameters.get("model_name") or parameters.get("model")
        if not model:
            model = resolve_pydantic_ai_model(
                parameters,
                parameters.get("model_role", "workflow_orchestration"),
            )

        instr = prompts.get_instructions()
        instr_str = "\n".join(instr) if isinstance(instr, list) else str(instr)

        self.primary_agent = Agent[OrchestratorDependencies, str](
            model=model,
            deps_type=OrchestratorDependencies,
            system_prompt=prompts.get_system_prompt(),
            instructions=instr_str,
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
        async def coordinate_multi_agent_system(
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
                return await self._coordinate_multi_agent_system(request)
            except Exception as e:
                return MultiAgentCoordinationResult(
                    success=False,
                    system_id=system_id,
                    final_result={},
                    coordination_rounds=0,
                    agent_results={},
                    consensus_score=0.0,
                    error_message=str(e),
                )

        @self.primary_agent.tool
        async def evaluate_with_judge(
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
                return await self._evaluate_with_judge(request)
            except Exception as e:
                return JudgeEvaluationResult(
                    success=False,
                    judge_id=judge_id,
                    overall_score=0.0,
                    criterion_scores={},
                    feedback=f"Evaluation failed: {e!s}",
                    recommendations=[],
                    error_message=str(e),
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
            """Package caller-supplied hypothesis dicts into a HypothesisDataset.

            Prefer structured fields per DeepResearch.src.datatypes.hypothesis_generation.HypothesisCandidate
            (statement, hypothesis_type, mechanism_or_rationale, predictions, evidence, confidence, etc.).
            For end-to-end generation from evidence, use ``run_hypothesis_generation`` instead.
            """
            return HypothesisDataset(
                name=name,
                description=description,
                hypotheses=hypotheses,
                source_workflows=source_workflows,
            )

        @self.primary_agent.tool
        async def run_hypothesis_generation(
            ctx: RunContext[OrchestratorDependencies],
            name: str,
            description: str,
            research_question: str,
            parameters: dict[str, Any] | None = None,
        ) -> dict[str, Any]:
            """Run the full evidence-grounded hypothesis generation pipeline."""
            from DeepResearch.src.agents.hypothesis_generation_agent import (
                run_hypothesis_generation_pipeline,
            )

            merged = dict(parameters or {})
            pm = self.config.primary_workflow.parameters.get("model_name")
            if pm and "model_name" not in merged:
                merged["model_name"] = pm
            input_data: dict[str, Any] = {
                "question": research_question,
                "dataset_name": name,
                "dataset_description": description,
                "workflow_name": "primary_react_hypothesis_generation",
            }
            try:
                dataset, meta = await run_hypothesis_generation_pipeline(
                    input_data,
                    merged,
                    default_model=str(pm) if pm else None,
                )
            except Exception as e:
                return {"success": False, "error": str(e)}
            judge_payload: dict[str, Any] | None = None
            if merged.get("run_quality_judge"):
                req = JudgeEvaluationRequest(
                    judge_id=str(merged.get("judge_id", "hypothesis_quality_judge")),
                    content_to_evaluate={"hypothesis_dataset": dataset.model_dump()},
                    evaluation_criteria=list(
                        merged.get(
                            "evaluation_criteria",
                            [
                                "testability",
                                "falsifiability",
                                "evidence_support",
                            ],
                        )
                    ),
                    context={"pipeline_metadata": meta},
                )
                jr = await self._evaluate_with_judge(req)
                judge_payload = jr.model_dump()
            return _hypothesis_generation_return_payload(
                dataset=dataset,
                meta=meta,
                judge_payload=judge_payload,
                run_quality_judge=bool(merged.get("run_quality_judge")),
                fail_on_judge_failure=bool(merged.get("fail_on_judge_failure")),
            )

        @self.primary_agent.tool
        def create_testing_environment(
            ctx: RunContext[OrchestratorDependencies],
            name: str,
            hypothesis: dict[str, Any],
            test_configuration: dict[str, Any],
            expected_outcomes: list[str],
            success_criteria: dict[str, Any] | None = None,
        ) -> HypothesisTestingEnvironment:
            """Create a hypothesis testing environment."""
            return HypothesisTestingEnvironment(
                name=name,
                hypothesis=hypothesis,
                test_configuration=test_configuration,
                expected_outcomes=expected_outcomes,
                success_criteria=success_criteria or {"criteria": expected_outcomes},
            )

    async def execute_primary_workflow(
        self, user_input: str, config: DictConfig
    ) -> dict[str, Any]:
        """Execute the primary REACT workflow."""
        start_ts = time.perf_counter()
        completed_before = len(self.state.completed_executions)
        cfg_dict = self._config_to_dict(config)
        configured_ids = list(self.agent_registry.get("configured_agent_ids", []))
        system_ids = list(self.agent_registry.get("multi_agent_system_ids", []))
        agent_hints = configured_ids + [
            f"multi_agent_system:{sid}" for sid in system_ids
        ]
        deps = OrchestratorDependencies(
            config=cfg_dict,
            user_input=user_input,
            context={"execution_start": datetime.now().isoformat()},
            available_workflows=list(self.workflow_registry.keys()),
            available_agents=agent_hints,
            available_judges=list(self.judge_registry.keys()),
        )

        run_result: Any = None
        error: str | None = None
        failure_kind: str | None = None
        try:
            run_result = await self.primary_agent.run(user_input, deps=deps)
        except AgentRunError as e:
            error = str(e)
            failure_kind = "agent_run_error"
        except Exception as e:
            error = str(e)
            failure_kind = "unexpected_error"
            logger.exception("Primary workflow agent.run failed")
        finally:
            await self._drain_workflows()
            self.state.last_updated = datetime.now()
            self.state.system_metrics["total_executions"] = len(
                self.state.completed_executions
            )
            self.state.system_metrics["active_executions"] = len(
                self.state.active_executions
            )

        completed_this_run = len(self.state.completed_executions) - completed_before
        elapsed = time.perf_counter() - start_ts
        if error is not None:
            return {
                "success": False,
                "error": error,
                "result": {"output": None, "usage": None},
                "state": self.state,
                "execution_metadata": {
                    "workflows_spawned": completed_this_run,
                    "active_executions": len(self.state.active_executions),
                    "total_executions": len(self.state.completed_executions),
                    "elapsed_seconds": elapsed,
                    "failure_kind": failure_kind,
                },
            }

        out = getattr(run_result, "output", None)
        usage = getattr(run_result, "usage", None)
        usage_payload: Any = None
        if usage is not None and hasattr(usage, "model_dump"):
            usage_payload = usage.model_dump()
        elif usage is not None:
            usage_payload = str(usage)

        return {
            "success": True,
            "result": {"output": out, "usage": usage_payload},
            "state": self.state,
            "execution_metadata": {
                "workflows_spawned": completed_this_run,
                "active_executions": len(self.state.active_executions),
                "total_executions": len(self.state.completed_executions),
                "elapsed_seconds": elapsed,
            },
        }

    async def execute_workflow_plan(
        self,
        plan: WorkflowPlan | WorkflowComposition,
        input_data: dict[str, Any] | None = None,
        root_config: dict[str, Any] | None = None,
        execution_mode: str = "production",
    ) -> dict[str, Any]:
        """Execute a deterministic workflow composition without LLM tool calls."""
        start_time = time.monotonic()
        completed_before = len(self.state.completed_executions)
        input_payload = dict(input_data or {})
        workflow_names = self._plan_workflow_names(plan)
        dependency_map = self._plan_dependency_map(plan, workflow_names)
        batches = self._topological_batches(workflow_names, dependency_map)
        dependency_outputs: dict[str, dict[str, Any]] = {}
        strategy = (
            getattr(plan, "execution_strategy", None) or self.config.execution_strategy
        )
        max_parallel = max(1, self.config.max_concurrent_workflows)

        for batch in batches:
            ordered_batch = sorted(
                batch,
                key=lambda n: self._get_workflow_config_by_name_or_type(n).priority,
                reverse=True,
            )
            workflow_chunks = (
                [[workflow_name] for workflow_name in ordered_batch]
                if strategy == "sequential"
                else [
                    ordered_batch[index : index + max_parallel]
                    for index in range(0, len(ordered_batch), max_parallel)
                ]
            )
            for workflow_chunk in workflow_chunks:
                batch_tasks: list[tuple[str, WorkflowExecution, asyncio.Task[Any]]] = []
                for workflow_name in workflow_chunk:
                    dependencies = dependency_map.get(workflow_name, [])
                    workflow_config = self._copy_workflow_config(
                        self._get_workflow_config_by_name_or_type(workflow_name),
                        {"dependencies": dependencies},
                    )
                    missing_dependencies = [
                        dep for dep in dependencies if dep not in dependency_outputs
                    ]
                    if missing_dependencies:
                        self._record_skipped_execution(
                            workflow_config,
                            "Skipped because dependencies did not complete "
                            f"successfully: {missing_dependencies}",
                        )
                        continue

                    dependency_payload = {
                        dep: dependency_outputs[dep] for dep in dependencies
                    }
                    execution = WorkflowExecution(
                        workflow_config=workflow_config,
                        input_data={
                            **input_payload,
                            "dependency_outputs": dependency_payload,
                        },
                        status=WorkflowStatus.PENDING,
                    )
                    context = WorkflowRunContext(
                        user_input=getattr(plan, "user_input", "") or "",
                        root_config=dict(root_config or {}),
                        dependency_outputs=dependency_payload,
                        execution_mode=execution_mode,
                    )
                    task = self._start_execution(execution, context)
                    batch_tasks.append((workflow_name, execution, task))

                if not batch_tasks:
                    continue
                await asyncio.gather(
                    *(task for _, _, task in batch_tasks), return_exceptions=True
                )
                self._clear_finished_tasks()
                for workflow_name, execution, _task in batch_tasks:
                    result = self._completed_result_for(execution.execution_id)
                    if result and result.status == WorkflowStatus.COMPLETED:
                        dependency_outputs[workflow_name] = result.output_data

        self.state.last_updated = datetime.now()
        self.state.system_metrics["total_executions"] = len(
            self.state.completed_executions
        )
        self.state.system_metrics["active_executions"] = len(
            self.state.active_executions
        )
        plan_results = self.state.completed_executions[completed_before:]
        failed = [
            result
            for result in plan_results
            if result.status != WorkflowStatus.COMPLETED
        ]
        return {
            "success": not failed,
            "state": self.state,
            "completed_executions": plan_results,
            "execution_metadata": {
                "total_executions": len(plan_results),
                "failed_executions": len(failed),
                "execution_time": time.monotonic() - start_time,
            },
        }

    def compose_workflow_plan(
        self,
        user_input: str,
        selected_workflows: list[str] | None = None,
        execution_strategy: str | None = None,
    ) -> WorkflowPlan:
        """Create a deterministic plan from selected or configured workflows."""
        workflow_names = selected_workflows or [
            workflow.name for workflow in self.config.sub_workflows if workflow.enabled
        ]
        dependencies = {
            workflow.name: list(workflow.dependencies)
            for workflow in self.config.sub_workflows
            if workflow.name in workflow_names and workflow.dependencies
        }
        return WorkflowPlan(
            user_input=user_input,
            workflow_names=workflow_names,
            workflow_dependencies=dependencies,
            execution_strategy=execution_strategy or self.config.execution_strategy,
            expected_outputs={
                workflow.name: workflow.output_format
                for workflow in self.config.sub_workflows
                if workflow.name in workflow_names
            },
        )

    def _config_to_dict(self, config: Any) -> dict[str, Any]:
        """Convert DictConfig or mapping-like config into a plain dict."""
        if config is None:
            return {}
        try:
            from omegaconf import OmegaConf

            if isinstance(config, DictConfig):
                data = OmegaConf.to_container(config, resolve=True)
                if not isinstance(data, dict):
                    return {}
                return {str(k): v for k, v in data.items()}
        except Exception:
            pass
        if isinstance(config, dict):
            return {str(k): v for k, v in config.items()}
        return {}

    def _copy_workflow_config(
        self, workflow_config: WorkflowConfig, update: dict[str, Any]
    ) -> WorkflowConfig:
        """Copy a workflow config (Pydantic v2)."""
        return workflow_config.model_copy(update=update)

    def _spawn_workflow(self, request: WorkflowSpawnRequest) -> WorkflowSpawnResult:
        """Spawn a new workflow execution."""
        try:
            workflow_config = self._get_workflow_config(
                request.workflow_type, request.workflow_name
            )
            params = request.parameters or {}
            if request.parameters or request.dependencies:
                workflow_config = self._copy_workflow_config(
                    workflow_config,
                    {
                        "parameters": {**workflow_config.parameters, **params},
                        "dependencies": request.dependencies
                        or workflow_config.dependencies,
                    },
                )
            execution = WorkflowExecution(
                workflow_config=workflow_config,
                input_data=request.input_data,
                status=WorkflowStatus.PENDING,
            )

            context = WorkflowRunContext(
                user_input=str(
                    request.input_data.get("question")
                    or request.input_data.get("query")
                    or ""
                ),
                dependency_outputs={},
                execution_mode=str(params.get("execution_mode", "production")),
            )
            task = self._start_execution(execution, context)

            def _log_task_failure(t: asyncio.Task[Any]) -> None:
                try:
                    t.result()
                except asyncio.CancelledError:
                    pass
                except Exception:
                    logger.exception(
                        "Spawned workflow execution failed (execution_id=%s)",
                        getattr(execution, "execution_id", "?"),
                    )

            task.add_done_callback(_log_task_failure)

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

    async def _execute_workflow_async(self, execution: WorkflowExecution) -> None:
        """Execute a workflow asynchronously."""
        context = WorkflowRunContext()
        await self._execute_workflow_task(execution, context)

    async def _execute_workflow_task(
        self, execution: WorkflowExecution, context: WorkflowRunContext
    ) -> None:
        """Execute a workflow task and record exactly one terminal result."""
        workflow_result: WorkflowResult
        try:
            workflow_result = await self._run_execution_with_retries(execution, context)
        except asyncio.CancelledError:
            execution.status = WorkflowStatus.CANCELLED
            execution.end_time = datetime.now()
            workflow_result = WorkflowResult(
                execution_id=execution.execution_id,
                workflow_name=execution.workflow_config.name,
                status=WorkflowStatus.CANCELLED,
                output_data={},
                execution_time=execution.duration or 0.0,
                error_details={"error": "Workflow execution cancelled"},
            )
            self._finish_execution(execution, workflow_result)
            raise
        except Exception as e:
            execution.status = WorkflowStatus.FAILED
            execution.end_time = datetime.now()
            execution.error_message = str(e)
            workflow_result = WorkflowResult(
                execution_id=execution.execution_id,
                workflow_name=execution.workflow_config.name,
                status=WorkflowStatus.FAILED,
                output_data={},
                execution_time=execution.duration or 0.0,
                error_details={"error": str(e)},
            )
        self._finish_execution(execution, workflow_result)

    async def _run_execution_with_retries(
        self, execution: WorkflowExecution, context: WorkflowRunContext
    ) -> WorkflowResult:
        """Run one workflow with timeout and retry semantics."""
        started = time.monotonic()
        adapter = self.adapter_registry.get(
            execution.workflow_config.workflow_type.value
        )
        if adapter is None:
            execution.status = WorkflowStatus.FAILED
            execution.end_time = datetime.now()
            execution.error_message = (
                f"Unknown workflow type: {execution.workflow_config.workflow_type}"
            )
            return WorkflowResult(
                execution_id=execution.execution_id,
                workflow_name=execution.workflow_config.name,
                status=WorkflowStatus.FAILED,
                output_data={},
                execution_time=time.monotonic() - started,
                error_details={"error": execution.error_message},
            )
        if not execution.workflow_config.enabled:
            execution.status = WorkflowStatus.CANCELLED
            execution.end_time = datetime.now()
            execution.error_message = "Workflow is disabled"
            return WorkflowResult(
                execution_id=execution.execution_id,
                workflow_name=execution.workflow_config.name,
                status=WorkflowStatus.CANCELLED,
                output_data={},
                execution_time=time.monotonic() - started,
                error_details={"error": execution.error_message},
            )

        max_attempts = max(1, execution.workflow_config.max_retries + 1)
        last_error: str | None = None
        for attempt_index in range(max_attempts):
            execution.retry_count = attempt_index
            execution.status = WorkflowStatus.RUNNING
            if execution.start_time is None:
                execution.start_time = datetime.now()
            try:
                coro = adapter.execute(execution, context)
                if execution.workflow_config.timeout:
                    adapter_result = await asyncio.wait_for(
                        coro, timeout=execution.workflow_config.timeout
                    )
                else:
                    adapter_result = await coro
            except TimeoutError:
                last_error = "Workflow execution timed out"
                if attempt_index + 1 < max_attempts:
                    continue
                break
            except Exception as e:
                last_error = str(e)
                if attempt_index + 1 < max_attempts:
                    continue
                break

            if adapter_result.success:
                execution.status = WorkflowStatus.COMPLETED
                execution.end_time = datetime.now()
                execution.output_data = adapter_result.output_data
                return WorkflowResult(
                    execution_id=execution.execution_id,
                    workflow_name=execution.workflow_config.name,
                    status=WorkflowStatus.COMPLETED,
                    output_data=adapter_result.output_data,
                    metadata={
                        **adapter_result.metadata,
                        "attempts": attempt_index + 1,
                        "degraded": adapter_result.degraded,
                    },
                    execution_time=time.monotonic() - started,
                )

            last_error = adapter_result.error_message or "Workflow adapter failed"
            if not adapter_result.retryable or attempt_index + 1 >= max_attempts:
                break

        execution.status = WorkflowStatus.FAILED
        execution.end_time = datetime.now()
        execution.error_message = last_error or "Workflow execution failed"
        return WorkflowResult(
            execution_id=execution.execution_id,
            workflow_name=execution.workflow_config.name,
            status=WorkflowStatus.FAILED,
            output_data={},
            metadata={"attempts": execution.retry_count + 1},
            execution_time=time.monotonic() - started,
            error_details={"error": execution.error_message},
        )

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

    def _get_workflow_config_by_name_or_type(
        self, workflow_name: str
    ) -> WorkflowConfig:
        """Resolve workflow config by configured name or workflow type value."""
        for workflow_config in self.config.sub_workflows:
            if workflow_name in {
                workflow_config.name,
                workflow_config.workflow_type.value,
            }:
                return workflow_config
        try:
            workflow_type = WorkflowType(workflow_name)
        except ValueError as e:
            known = [workflow.name for workflow in self.config.sub_workflows] + list(
                self.workflow_registry.keys()
            )
            raise ValueError(
                f"Unknown workflow {workflow_name!r}. Known workflows: {known}"
            ) from e
        return WorkflowConfig(workflow_type=workflow_type, name=workflow_name)

    def _start_execution(
        self, execution: WorkflowExecution, context: WorkflowRunContext
    ) -> asyncio.Task[Any]:
        """Register and start an execution task owned by this orchestrator."""
        self.state.active_executions.append(execution)
        self._executions_by_id[execution.execution_id] = execution
        task = asyncio.create_task(self._execute_workflow_task(execution, context))
        self._tasks_by_execution_id[execution.execution_id] = task
        return task

    async def _drain_workflows(self) -> None:
        """Wait for all spawned tasks, cancelling them on global timeout."""
        pending = [
            task for task in self._tasks_by_execution_id.values() if not task.done()
        ]
        if not pending:
            self._clear_finished_tasks()
            return
        gather = asyncio.gather(*pending, return_exceptions=True)
        try:
            if self.config.global_timeout:
                await asyncio.wait_for(gather, timeout=self.config.global_timeout)
            else:
                await gather
        except TimeoutError:
            for task in pending:
                if not task.done():
                    task.cancel()
            await asyncio.gather(*pending, return_exceptions=True)
        finally:
            self._clear_finished_tasks()

    def _finish_execution(
        self, execution: WorkflowExecution, workflow_result: WorkflowResult
    ) -> None:
        """Move an execution from active state to terminal results once."""
        if execution in self.state.active_executions:
            self.state.active_executions.remove(execution)
        self._executions_by_id.pop(execution.execution_id, None)
        if not self._completed_result_for(workflow_result.execution_id):
            self.state.completed_executions.append(workflow_result)

    def _record_skipped_execution(
        self, workflow_config: WorkflowConfig, reason: str
    ) -> WorkflowExecution:
        """Record a workflow that cannot run because its prerequisites failed."""
        now = datetime.now()
        execution = WorkflowExecution(
            workflow_config=workflow_config,
            status=WorkflowStatus.CANCELLED,
            start_time=now,
            end_time=now,
            error_message=reason,
        )
        workflow_result = WorkflowResult(
            execution_id=execution.execution_id,
            workflow_name=workflow_config.name,
            status=WorkflowStatus.CANCELLED,
            output_data={},
            execution_time=0.0,
            error_details={"error": reason},
        )
        self._finish_execution(execution, workflow_result)
        return execution

    def _completed_result_for(self, execution_id: str) -> WorkflowResult | None:
        """Return a completed result by execution id."""
        for result in self.state.completed_executions:
            if result.execution_id == execution_id:
                return result
        return None

    def _clear_finished_tasks(self) -> None:
        """Drop task handles that have reached a terminal state."""
        for execution_id, task in list(self._tasks_by_execution_id.items()):
            if task.done():
                self._tasks_by_execution_id.pop(execution_id, None)

    def _plan_workflow_names(
        self, plan: WorkflowPlan | WorkflowComposition
    ) -> list[str]:
        """Extract workflow names from supported plan models."""
        workflow_names = getattr(plan, "workflow_names", None)
        if workflow_names is None:
            workflow_names = getattr(plan, "selected_workflows", [])
        return list(workflow_names)

    def _plan_dependency_map(
        self, plan: WorkflowPlan | WorkflowComposition, workflow_names: list[str]
    ) -> dict[str, list[str]]:
        """Merge explicit plan dependencies with configured workflow dependencies."""
        explicit = dict(getattr(plan, "workflow_dependencies", {}) or {})
        dependency_map: dict[str, list[str]] = {}
        for workflow_name in workflow_names:
            config = self._get_workflow_config_by_name_or_type(workflow_name)
            dependency_map[workflow_name] = list(
                explicit.get(workflow_name, config.dependencies)
            )
        return dependency_map

    def _topological_batches(
        self, workflow_names: list[str], dependency_map: dict[str, list[str]]
    ) -> list[list[str]]:
        """Return dependency-ordered workflow batches."""
        workflow_set = set(workflow_names)
        for workflow_name, dependencies in dependency_map.items():
            unknown = [dep for dep in dependencies if dep not in workflow_set]
            if unknown:
                raise ValueError(
                    f"Workflow {workflow_name!r} depends on unknown workflows: {unknown}"
                )

        remaining = set(workflow_names)
        completed: set[str] = set()
        batches: list[list[str]] = []
        while remaining:
            ready = sorted(
                workflow_name
                for workflow_name in remaining
                if all(
                    dep in completed for dep in dependency_map.get(workflow_name, [])
                )
            )
            if not ready:
                raise ValueError(
                    f"Workflow dependencies contain a cycle: {dependency_map}"
                )
            batches.append(ready)
            completed.update(ready)
            remaining.difference_update(ready)
        return batches

    async def _coordinate_multi_agent_system(
        self, request: MultiAgentCoordinationRequest
    ) -> MultiAgentCoordinationResult:
        """Run multi-agent coordination for a configured system_id."""
        sys_cfg = next(
            (
                s
                for s in self.config.multi_agent_systems
                if s.system_id == request.system_id
            ),
            None,
        )
        if sys_cfg is None:
            known = [s.system_id for s in self.config.multi_agent_systems]
            return MultiAgentCoordinationResult(
                success=False,
                system_id=request.system_id,
                final_result={},
                coordination_rounds=0,
                agent_results={},
                consensus_score=0.0,
                error_message=(
                    f"No multi_agent_system with system_id={request.system_id!r}. "
                    f"Known: {known}"
                ),
            )
        if not sys_cfg.enabled:
            return MultiAgentCoordinationResult(
                success=False,
                system_id=request.system_id,
                final_result={},
                coordination_rounds=0,
                agent_results={},
                consensus_score=0.0,
                error_message="Multi-agent system is disabled in configuration.",
            )
        merged = sys_cfg.model_copy(
            update={
                "coordination_strategy": request.coordination_strategy
                or sys_cfg.coordination_strategy
            }
        )
        if not merged.agents:
            return MultiAgentCoordinationResult(
                success=False,
                system_id=request.system_id,
                final_result={},
                coordination_rounds=0,
                agent_results={},
                consensus_score=0.0,
                error_message="Multi-agent system has no agents configured.",
            )
        coordinator = MultiAgentCoordinator(merged)
        cr = await coordinator.coordinate(
            request.task_description,
            request.input_data,
            request.max_rounds,
        )
        return MultiAgentCoordinationResult(
            success=cr.success,
            system_id=request.system_id,
            final_result=cr.final_result,
            coordination_rounds=cr.total_rounds,
            agent_results=dict(cr.agent_results),
            consensus_score=cr.consensus_score,
            error_message=cr.error_message,
        )

    async def _evaluate_with_judge(
        self, request: JudgeEvaluationRequest
    ) -> JudgeEvaluationResult:
        """LLM rubric judge using configured JudgeConfig."""
        jc = self.judge_registry.get(request.judge_id)
        if jc is None:
            return JudgeEvaluationResult(
                success=False,
                judge_id=request.judge_id,
                overall_score=0.0,
                criterion_scores={},
                feedback="",
                recommendations=[],
                error_message=f"Unknown judge_id: {request.judge_id!r}",
            )
        return await run_llm_judge(jc, request)

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

    async def _execute_rag_workflow_via_tools(
        self, question: str, parameters: dict[str, Any]
    ) -> dict[str, Any]:
        """Neo4j + rag.ingest / rag.retrieve / rag.generate (canonical tools)."""
        emb = parameters.get("embeddings_config")
        vs = parameters.get("vector_store_config")
        llm = parameters.get("llm_config")
        if (
            not isinstance(emb, dict)
            or not isinstance(vs, dict)
            or not isinstance(llm, dict)
        ):
            return {
                "success": False,
                "error": (
                    "RAG tools path requires embeddings_config, vector_store_config, "
                    "and llm_config as dicts in workflow parameters"
                ),
                "rag_path": "tools",
            }

        docs = parameters.get("documents")
        if docs is None:
            chunk_res = await canonical_registry.aexecute(
                "chunked_search",
                {
                    "query": question,
                    "search_type": parameters.get("search_type", "search"),
                    "num_results": parameters.get("num_results", 4),
                    "chunk_size": parameters.get("chunk_size", 1000),
                    "chunk_overlap": parameters.get("chunk_overlap", 0),
                    "heading_level": parameters.get("heading_level", 3),
                    "min_characters_per_chunk": parameters.get(
                        "min_characters_per_chunk", 50
                    ),
                    "max_characters_per_section": parameters.get(
                        "max_characters_per_section", 4000
                    ),
                    "clean_text": parameters.get("clean_text", True),
                },
            )
            chunks: list[dict[str, Any]] = []
            if chunk_res.success:
                raw = chunk_res.data.get("chunks", [])
                if isinstance(raw, list):
                    chunks = raw
            texts: list[str] = []
            for c in chunks:
                if isinstance(c, dict):
                    t = str(c.get("text") or c.get("content") or "").strip()
                    if t:
                        texts.append(t)
            docs = [{"content": t} for t in texts]

        if not docs:
            return {
                "success": False,
                "error": "No documents to ingest for RAG tools path",
                "rag_path": "tools",
            }

        ingest = await canonical_registry.aexecute(
            "rag.ingest",
            {
                "documents": json.dumps(docs),
                "embeddings_config": json.dumps(emb),
                "vector_store_config": json.dumps(vs),
                "llm_config": json.dumps(llm),
            },
        )
        if not ingest.success:
            return {
                "success": False,
                "error": ingest.error or "rag.ingest failed",
                "rag_path": "tools",
            }

        retr = await canonical_registry.aexecute(
            "rag.retrieve",
            {
                "query": question,
                "top_k": int(parameters.get("top_k", 5)),
                "search_type": str(parameters.get("rag_search_type", "similarity")),
                "filters": json.dumps(parameters.get("filters", {})),
                "embeddings_config": json.dumps(emb),
                "vector_store_config": json.dumps(vs),
                "llm_config": json.dumps(llm),
            },
        )
        if not retr.success:
            return {
                "success": False,
                "error": retr.error or "rag.retrieve failed",
                "rag_path": "tools",
            }

        gen_params: dict[str, Any] = {
            "query": question,
            "retrieved_documents": json.dumps(retr.data.get("results", [])),
            "llm_config": json.dumps(llm),
        }
        if parameters.get("max_tokens") is not None:
            gen_params["max_tokens"] = parameters.get("max_tokens")
        if parameters.get("temperature") is not None:
            gen_params["temperature"] = parameters.get("temperature")

        gen = await canonical_registry.aexecute("rag.generate", gen_params)
        if not gen.success:
            return {
                "success": False,
                "error": gen.error or "rag.generate failed",
                "rag_path": "tools",
            }

        return {
            "success": True,
            "answer": gen.data.get("answer", ""),
            "documents_retrieved": int(retr.data.get("count", 0) or 0),
            "rag_path": "tools",
            "degraded": False,
        }

    async def _execute_rag_workflow(
        self, input_data: dict[str, Any], parameters: dict[str, Any]
    ) -> dict[str, Any]:
        """Execute RAG workflow."""
        question = str(
            input_data.get("question") or input_data.get("query") or ""
        ).strip()
        if not question:
            return {"success": False, "error": "Missing question for RAG workflow"}

        vs_raw = parameters.get("vector_store_config")
        store_type = ""
        if isinstance(vs_raw, dict):
            st = vs_raw.get("store_type", "")
            store_type = (st.value if hasattr(st, "value") else str(st)).lower()
        use_rag_tools = bool(parameters.get("use_rag_tools")) or store_type == "neo4j"
        if use_rag_tools and isinstance(vs_raw, dict):
            try:
                return await self._execute_rag_workflow_via_tools(question, parameters)
            except Exception as e:
                return {
                    "success": False,
                    "error": str(e),
                    "rag_path": "tools",
                }

        # Retrieve source text via chunked web search when available.
        chunks: list[dict[str, Any]] = []
        chunk_res = await canonical_registry.aexecute(
            "chunked_search",
            {
                "query": question,
                "search_type": parameters.get("search_type", "search"),
                "num_results": parameters.get("num_results", 4),
                "chunk_size": parameters.get("chunk_size", 1000),
                "chunk_overlap": parameters.get("chunk_overlap", 0),
                "heading_level": parameters.get("heading_level", 3),
                "min_characters_per_chunk": parameters.get(
                    "min_characters_per_chunk", 50
                ),
                "max_characters_per_section": parameters.get(
                    "max_characters_per_section", 4000
                ),
                "clean_text": parameters.get("clean_text", True),
            },
        )
        if chunk_res.success:
            raw = chunk_res.data.get("chunks", [])
            if isinstance(raw, list):
                chunks = raw

        # Build an in-memory vector store for this workflow run.
        # This is production-safe as a fallback; a persistent vector store can
        # be layered in later via configuration.
        from DeepResearch.src.datatypes.rag import (
            EmbeddingsConfig,
            RAGQuery,
            SearchType,
            VectorStoreConfig,
            VectorStoreType,
        )
        from DeepResearch.src.datatypes.vllm_integration import VLLMLLMProvider
        from DeepResearch.src.prompts.rag import RAGPrompts
        from DeepResearch.src.utils.sentence_transformers_embeddings import (
            SentenceTransformersEmbeddings,
        )
        from DeepResearch.src.vector_stores.in_memory_vector_store import (
            InMemoryVectorStore,
        )

        embeddings_cfg = EmbeddingsConfig(
            model_type=parameters.get("embedding_model_type", "sentence_transformers"),
            model_name=parameters.get(
                "embedding_model_name", "sentence-transformers/all-MiniLM-L6-v2"
            ),
            num_dimensions=int(parameters.get("embedding_dimensions", 384)),
        )
        embeddings = SentenceTransformersEmbeddings(embeddings_cfg)
        vs_cfg = VectorStoreConfig(
            store_type=VectorStoreType.FAISS,  # treated as in-memory fallback here
            embedding_dimension=embeddings_cfg.num_dimensions,
            collection_name="inmem",
        )
        vector_store = InMemoryVectorStore(vs_cfg, embeddings)

        # Ingest chunks into store.
        texts = []
        for c in chunks:
            if isinstance(c, dict):
                text = str(c.get("text") or c.get("content") or "").strip()
                if text:
                    texts.append(text)
        if texts:
            await vector_store.add_document_text_chunks(texts)

        # Retrieve and generate answer (best-effort LLM).
        rag_query = RAGQuery(text=question, search_type=SearchType.SIMILARITY, top_k=5)
        retrieved = await vector_store.search(
            query=rag_query.text,
            search_type=rag_query.search_type,
            top_k=rag_query.top_k,
        )
        context = "\n\n".join(
            [f"Document {r.rank}: {r.document.content}" for r in retrieved]
        )
        prompt = RAGPrompts.get_rag_query_prompt(question, context)

        generated_answer: str | None = None
        llm_cfg = parameters.get("llm_config")
        llm_used_ok = False
        if isinstance(llm_cfg, dict):
            try:
                from DeepResearch.src.datatypes.rag import LLMModelType, VLLMConfig

                llm_config = VLLMConfig(
                    model_type=LLMModelType(llm_cfg.get("model_type", "custom")),
                    model_name=str(llm_cfg.get("model_name", "unknown")),
                    host=str(llm_cfg.get("host", "localhost")),
                    port=int(llm_cfg.get("port", 8000)),
                    api_key=llm_cfg.get("api_key"),
                )
                llm = VLLMLLMProvider(llm_config)
                generated_answer = await llm.generate(prompt, context=context)
                llm_used_ok = bool(generated_answer and str(generated_answer).strip())
            except Exception:
                generated_answer = None
                llm_used_ok = False

        if not generated_answer:
            # Degraded mode: return context-based synthesis without LLM.
            generated_answer = context[:2000] if context else "No context retrieved."

        return {
            "success": True,
            "answer": generated_answer,
            "documents_retrieved": len(retrieved),
            "degraded": not llm_used_ok,
            "rag_path": "in_memory",
        }

    async def _execute_bioinformatics_workflow(
        self, input_data: dict[str, Any], parameters: dict[str, Any]
    ) -> dict[str, Any]:
        """Execute bioinformatics workflow."""
        question = str(
            input_data.get("question") or input_data.get("query") or ""
        ).strip()
        if not question:
            return {
                "success": False,
                "error": "Missing question for bioinformatics workflow",
            }

        res = await canonical_registry.aexecute(
            "bioinformatics_workflow",
            {"question": question, "config": parameters.get("config", {})},
        )
        if not res.success:
            return {
                "success": False,
                "error": res.error or "bioinformatics_workflow failed",
            }
        return {
            "success": True,
            "final_answer": res.data.get("final_answer", ""),
            "processing_steps": res.data.get("processing_steps", []),
            "quality_metrics": res.data.get("quality_metrics", {}),
        }

    async def _execute_search_workflow(
        self, input_data: dict[str, Any], parameters: dict[str, Any]
    ) -> dict[str, Any]:
        """Execute search workflow."""
        query = str(input_data.get("query") or input_data.get("question") or "").strip()
        if not query:
            return {"success": False, "error": "Missing query for search workflow"}

        res = await canonical_registry.aexecute(
            "web_search",
            {
                "query": query,
                "search_type": parameters.get("search_type", "search"),
                "num_results": parameters.get("num_results", 4),
            },
        )
        if not res.success:
            return {"success": False, "error": res.error or "web_search failed"}
        return {
            "success": True,
            "content": res.data.get("content", ""),
            "results_found": parameters.get("num_results", 4),
        }

    async def _execute_multi_agent_workflow(
        self, input_data: dict[str, Any], parameters: dict[str, Any]
    ) -> dict[str, Any]:
        """Execute multi-agent workflow via configured systems."""
        task = str(
            input_data.get("task_description")
            or input_data.get("question")
            or input_data.get("query")
            or ""
        ).strip()
        if not task:
            return {"success": False, "error": "Missing task_description or question"}
        systems = [s for s in self.config.multi_agent_systems if s.enabled]
        if not systems:
            return {
                "success": False,
                "error": "No enabled multi_agent_systems in orchestration config",
            }
        sid = str(parameters.get("system_id") or systems[0].system_id)
        req = MultiAgentCoordinationRequest(
            system_id=sid,
            task_description=task,
            input_data=dict(input_data),
            coordination_strategy=str(
                parameters.get("coordination_strategy", "collaborative")
            ),
            max_rounds=int(parameters.get("max_rounds", 10)),
        )
        coord_res = await self._coordinate_multi_agent_system(req)
        return {
            "success": coord_res.success,
            "coordination": coord_res.model_dump(),
        }

    async def _execute_hypothesis_generation_workflow(
        self, input_data: dict[str, Any], parameters: dict[str, Any]
    ) -> dict[str, Any]:
        """Execute hypothesis generation workflow."""
        from DeepResearch.src.statemachines.hypothesis_workflow import (
            run_hypothesis_workflow,
        )

        question = (
            input_data.get("question")
            or input_data.get("user_input")
            or input_data.get("query")
            or input_data.get("research_question")
            or ""
        )
        cfg = self._build_hypothesis_config(parameters, testing_enabled=False)
        workflow_kwargs: dict[str, Any] = {"mode": "generate"}
        if input_data.get("existing_hypotheses") is not None:
            workflow_kwargs["existing_hypotheses"] = input_data["existing_hypotheses"]
        return await run_hypothesis_workflow(question, cfg, **workflow_kwargs)

    async def _execute_hypothesis_testing_workflow(
        self, input_data: dict[str, Any], parameters: dict[str, Any]
    ) -> dict[str, Any]:
        """Execute hypothesis testing workflow."""
        from DeepResearch.src.statemachines.hypothesis_workflow import (
            run_hypothesis_workflow,
        )

        question = (
            input_data.get("question")
            or input_data.get("user_input")
            or input_data.get("query")
            or input_data.get("research_question")
            or ""
        )
        cfg = self._build_hypothesis_config(parameters, testing_enabled=True)
        workflow_kwargs: dict[str, Any] = {"mode": "testing"}
        if input_data.get("existing_hypotheses") is not None:
            workflow_kwargs["existing_hypotheses"] = input_data["existing_hypotheses"]
        return await run_hypothesis_workflow(question, cfg, **workflow_kwargs)

    def _build_hypothesis_config(
        self, parameters: dict[str, Any], *, testing_enabled: bool
    ) -> DictConfig:
        """Build a minimal config for delegating hypothesis workflows."""
        from omegaconf import DictConfig

        mode = "testing" if testing_enabled else "generate"
        cfg = DictConfig(
            {
                "workflow_orchestration": {"enabled": False},
                "flows": {
                    "hypothesis_generation": {"enabled": not testing_enabled},
                    "hypothesis_testing": {"enabled": testing_enabled},
                },
                "hypothesis": {
                    "mode": mode,
                    "max_hypotheses": parameters.get("max_hypotheses", 3),
                    "top_k": parameters.get("top_k", 3),
                    "evidence_mode": parameters.get("evidence_mode", "search_only"),
                    "generate_testing_plans": testing_enabled
                    or parameters.get("generate_testing_plans", False),
                    "score_weights": parameters.get("score_weights", {}),
                    "existing_hypotheses": parameters.get("existing_hypotheses", []),
                },
            }
        )
        return cfg

    async def _execute_reasoning_workflow(
        self, input_data: dict[str, Any], parameters: dict[str, Any]
    ) -> dict[str, Any]:
        """Execute reasoning workflow."""
        return {
            "success": False,
            "error": "reasoning_workflow is not implemented in MVP",
        }

    async def _execute_code_execution_workflow(
        self, input_data: dict[str, Any], parameters: dict[str, Any]
    ) -> dict[str, Any]:
        """Execute code execution workflow."""
        code = input_data.get("code")
        language = input_data.get("language", "python")
        if not code:
            return {
                "success": False,
                "error": "Missing code for code execution workflow",
            }

        tool_name = "docker_sandbox"
        exec_params = {
            "language": language,
            "code": code,
            "timeout": str(parameters.get("timeout", 60)),
            "max_retries": str(parameters.get("max_retries", 0)),
            "env": json.dumps(parameters.get("env", {})),
        }
        res = await canonical_registry.aexecute(tool_name, exec_params)
        if not res.success:
            return {"success": False, "error": res.error or "docker_sandbox failed"}
        return {"success": True, "result": res.data}

    async def _execute_evaluation_workflow(
        self, input_data: dict[str, Any], parameters: dict[str, Any]
    ) -> dict[str, Any]:
        """Execute evaluation workflow via LLM judge."""
        answer = str(input_data.get("answer", "")).strip()
        if not answer:
            return {"success": False, "error": "Missing answer for evaluation workflow"}
        judge_id = str(parameters.get("judge_id", "quality_judge"))
        criteria = list(
            parameters.get("evaluation_criteria", ["quality", "accuracy", "clarity"])
        )
        content = {"answer": answer}
        for k, v in input_data.items():
            if k != "answer":
                content[k] = v
        req = JudgeEvaluationRequest(
            judge_id=judge_id,
            content_to_evaluate=content,
            evaluation_criteria=criteria,
            context=dict(parameters.get("context", {})),
        )
        jr = await self._evaluate_with_judge(req)
        return {
            "success": jr.success,
            "score": jr.overall_score,
            "feedback": jr.feedback,
            "criterion_scores": jr.criterion_scores,
            "recommendations": jr.recommendations,
            "error": jr.error_message,
        }


# Alias for backward compatibility
WorkflowOrchestrator = PrimaryWorkflowOrchestrator
