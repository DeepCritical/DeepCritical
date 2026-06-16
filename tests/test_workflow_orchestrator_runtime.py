from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any

import pytest
from hydra import compose, initialize_config_dir
from omegaconf import OmegaConf
from pydantic_ai.exceptions import AgentRunError

from DeepResearch.app import PrimaryREACTWorkflow
from DeepResearch.src.agents.workflow_orchestrator import (
    PrimaryWorkflowOrchestrator,
    WorkflowSpawnRequest,
)
from DeepResearch.src.datatypes.workflow_orchestration import (
    WorkflowAdapterResult,
    WorkflowConfig,
    WorkflowOrchestrationConfig,
    WorkflowPlan,
    WorkflowRunContext,
    WorkflowStatus,
    WorkflowType,
)


class RecordingAdapter:
    def __init__(
        self,
        workflow_type: WorkflowType,
        calls: list[tuple[str, list[str]]],
        *,
        active_counter: dict[str, int] | None = None,
        always_fail: bool = False,
        delay: float = 0.0,
        fail_first: bool = False,
    ) -> None:
        self.workflow_type = workflow_type
        self.calls = calls
        self.active_counter = active_counter
        self.always_fail = always_fail
        self.delay = delay
        self.fail_first = fail_first
        self.attempts = 0

    async def execute(
        self, execution: Any, context: WorkflowRunContext
    ) -> WorkflowAdapterResult:
        self.attempts += 1
        self.calls.append(
            (
                execution.workflow_config.name,
                sorted(context.dependency_outputs.keys()),
            )
        )
        if self.active_counter is not None:
            self.active_counter["current"] += 1
            self.active_counter["max"] = max(
                self.active_counter["max"], self.active_counter["current"]
            )
        try:
            if self.delay:
                await asyncio.sleep(self.delay)
            if self.always_fail:
                return WorkflowAdapterResult(
                    success=False,
                    retryable=False,
                    error_message="permanent test failure",
                )
            if self.fail_first and self.attempts == 1:
                return WorkflowAdapterResult(
                    success=False,
                    retryable=True,
                    error_message="transient test failure",
                )
            return WorkflowAdapterResult(
                success=True,
                output_data={
                    "workflow": execution.workflow_config.name,
                    "dependencies": sorted(context.dependency_outputs.keys()),
                },
                metadata={"adapter": "recording"},
            )
        finally:
            if self.active_counter is not None:
                self.active_counter["current"] -= 1


@pytest.fixture
def config_dir() -> str:
    return str(Path(__file__).resolve().parents[1] / "configs")


@pytest.fixture
def no_primary_agent(monkeypatch: pytest.MonkeyPatch) -> None:
    def _fake_create_primary_agent(self: PrimaryWorkflowOrchestrator) -> None:
        self.primary_agent = None

    monkeypatch.setattr(
        PrimaryWorkflowOrchestrator,
        "_create_primary_agent",
        _fake_create_primary_agent,
    )


def make_orchestrator(workflows: list[WorkflowConfig]) -> PrimaryWorkflowOrchestrator:
    return PrimaryWorkflowOrchestrator(
        WorkflowOrchestrationConfig(
            primary_workflow=WorkflowConfig(
                workflow_type=WorkflowType.PRIMARY_REACT,
                name="main",
            ),
            sub_workflows=workflows,
            max_concurrent_workflows=2,
            global_timeout=5.0,
        )
    )


def test_orchestration_config_unwraps_hydra_groups(config_dir: str) -> None:
    with initialize_config_dir(version_base=None, config_dir=config_dir):
        cfg = compose(config_name="config")

    orchestration_config = PrimaryREACTWorkflow()._create_orchestration_config(
        cfg.workflow_orchestration
    )

    assert orchestration_config.primary_workflow.name == "main_research_workflow"
    assert len(orchestration_config.sub_workflows) >= 3
    assert len(orchestration_config.data_loaders) >= 1
    assert len(orchestration_config.multi_agent_systems) >= 1
    assert len(orchestration_config.judges) >= 1
    assert any(
        workflow.output_format != "default"
        for workflow in orchestration_config.sub_workflows
    )


def test_orchestration_config_accepts_flat_lists() -> None:
    raw_config = {
        "primary_workflow": {
            "workflow_type": "primary_react",
            "name": "main",
            "parameters": {"model_name": "test"},
        },
        "sub_workflows": [
            {
                "workflow_type": "search_workflow",
                "name": "search",
                "dependencies": [],
                "output_format": "search_results",
            }
        ],
        "data_loaders": [],
        "multi_agent_systems": [],
        "judges": [],
    }

    orchestration_config = PrimaryREACTWorkflow()._create_orchestration_config(
        raw_config
    )

    assert [workflow.name for workflow in orchestration_config.sub_workflows] == [
        "search"
    ]
    assert orchestration_config.sub_workflows[0].output_format == "search_results"


@pytest.mark.asyncio
async def test_execute_workflow_plan_honors_dependencies(
    no_primary_agent: None,
) -> None:
    workflows = [
        WorkflowConfig(
            workflow_type=WorkflowType.SEARCH_WORKFLOW,
            name="search",
            max_retries=0,
        ),
        WorkflowConfig(
            workflow_type=WorkflowType.REASONING_WORKFLOW,
            name="reason",
            dependencies=["search"],
            max_retries=0,
        ),
    ]
    orchestrator = make_orchestrator(workflows)
    calls: list[tuple[str, list[str]]] = []
    orchestrator.adapter_registry = {
        WorkflowType.SEARCH_WORKFLOW.value: RecordingAdapter(
            WorkflowType.SEARCH_WORKFLOW, calls
        ),
        WorkflowType.REASONING_WORKFLOW.value: RecordingAdapter(
            WorkflowType.REASONING_WORKFLOW, calls
        ),
    }

    result = await orchestrator.execute_workflow_plan(
        WorkflowPlan(user_input="question", workflow_names=["search", "reason"]),
        {"question": "question"},
        execution_mode="test",
    )

    assert result["success"] is True
    assert calls == [("search", []), ("reason", ["search"])]
    assert len(orchestrator.state.completed_executions) == 2
    assert orchestrator.state.active_executions == []


@pytest.mark.asyncio
async def test_execute_workflow_plan_retries_retryable_adapter_failure(
    no_primary_agent: None,
) -> None:
    workflow = WorkflowConfig(
        workflow_type=WorkflowType.SEARCH_WORKFLOW,
        name="search",
        max_retries=1,
    )
    orchestrator = make_orchestrator([workflow])
    calls: list[tuple[str, list[str]]] = []
    adapter = RecordingAdapter(WorkflowType.SEARCH_WORKFLOW, calls, fail_first=True)
    orchestrator.adapter_registry = {WorkflowType.SEARCH_WORKFLOW.value: adapter}

    result = await orchestrator.execute_workflow_plan(
        WorkflowPlan(user_input="question", workflow_names=["search"]),
        {"question": "question"},
        execution_mode="test",
    )

    assert result["success"] is True
    assert adapter.attempts == 2
    completed = orchestrator.state.completed_executions[0]
    assert completed.status == WorkflowStatus.COMPLETED
    assert completed.metadata["attempts"] == 2


@pytest.mark.asyncio
async def test_execute_workflow_plan_result_is_scoped_to_current_invocation(
    no_primary_agent: None,
) -> None:
    workflow = WorkflowConfig(
        workflow_type=WorkflowType.SEARCH_WORKFLOW,
        name="search",
        max_retries=0,
    )
    orchestrator = make_orchestrator([workflow])
    calls: list[tuple[str, list[str]]] = []
    orchestrator.adapter_registry = {
        WorkflowType.SEARCH_WORKFLOW.value: RecordingAdapter(
            WorkflowType.SEARCH_WORKFLOW, calls, always_fail=True
        )
    }

    first = await orchestrator.execute_workflow_plan(
        WorkflowPlan(user_input="question", workflow_names=["search"]),
        {"question": "question"},
        execution_mode="test",
    )
    assert first["success"] is False

    orchestrator.adapter_registry = {
        WorkflowType.SEARCH_WORKFLOW.value: RecordingAdapter(
            WorkflowType.SEARCH_WORKFLOW, calls
        )
    }
    second = await orchestrator.execute_workflow_plan(
        WorkflowPlan(user_input="question", workflow_names=["search"]),
        {"question": "question"},
        execution_mode="test",
    )

    assert second["success"] is True
    assert second["execution_metadata"]["total_executions"] == 1
    assert second["execution_metadata"]["failed_executions"] == 0
    assert len(second["completed_executions"]) == 1
    assert second["completed_executions"][0].status == WorkflowStatus.COMPLETED
    assert len(orchestrator.state.completed_executions) == 2


@pytest.mark.asyncio
async def test_execute_workflow_plan_skips_dependents_after_dependency_failure(
    no_primary_agent: None,
) -> None:
    workflows = [
        WorkflowConfig(
            workflow_type=WorkflowType.SEARCH_WORKFLOW,
            name="search",
            max_retries=0,
        ),
        WorkflowConfig(
            workflow_type=WorkflowType.REASONING_WORKFLOW,
            name="reason",
            dependencies=["search"],
            max_retries=0,
        ),
    ]
    orchestrator = make_orchestrator(workflows)
    calls: list[tuple[str, list[str]]] = []
    orchestrator.adapter_registry = {
        WorkflowType.SEARCH_WORKFLOW.value: RecordingAdapter(
            WorkflowType.SEARCH_WORKFLOW, calls, always_fail=True
        ),
        WorkflowType.REASONING_WORKFLOW.value: RecordingAdapter(
            WorkflowType.REASONING_WORKFLOW, calls
        ),
    }

    result = await orchestrator.execute_workflow_plan(
        WorkflowPlan(user_input="question", workflow_names=["search", "reason"]),
        {"question": "question"},
        execution_mode="test",
    )

    assert result["success"] is False
    assert calls == [("search", [])]
    statuses = {
        result.workflow_name: result.status
        for result in orchestrator.state.completed_executions
    }
    assert statuses == {
        "search": WorkflowStatus.FAILED,
        "reason": WorkflowStatus.CANCELLED,
    }
    skipped = next(
        result
        for result in orchestrator.state.completed_executions
        if result.workflow_name == "reason"
    )
    assert skipped.error_details is not None
    assert "dependencies" in skipped.error_details["error"]


@pytest.mark.asyncio
async def test_execute_workflow_plan_respects_max_concurrent_workflows(
    no_primary_agent: None,
) -> None:
    workflows = [
        WorkflowConfig(
            workflow_type=WorkflowType.SEARCH_WORKFLOW,
            name=f"search_{index}",
            max_retries=0,
        )
        for index in range(3)
    ]
    orchestrator = make_orchestrator(workflows)
    orchestrator.config.max_concurrent_workflows = 1
    calls: list[tuple[str, list[str]]] = []
    active_counter = {"current": 0, "max": 0}
    orchestrator.adapter_registry = {
        WorkflowType.SEARCH_WORKFLOW.value: RecordingAdapter(
            WorkflowType.SEARCH_WORKFLOW,
            calls,
            active_counter=active_counter,
            delay=0.01,
        )
    }

    result = await orchestrator.execute_workflow_plan(
        WorkflowPlan(
            user_input="question",
            workflow_names=["search_0", "search_1", "search_2"],
            execution_strategy="parallel",
        ),
        {"question": "question"},
        execution_mode="test",
    )

    assert result["success"] is True
    assert active_counter["max"] == 1
    assert len(calls) == 3


@pytest.mark.asyncio
async def test_spawned_workflows_are_drained_before_completion(
    no_primary_agent: None,
) -> None:
    workflow = WorkflowConfig(
        workflow_type=WorkflowType.SEARCH_WORKFLOW,
        name="search",
        max_retries=0,
    )
    orchestrator = make_orchestrator([workflow])
    calls: list[tuple[str, list[str]]] = []
    orchestrator.adapter_registry = {
        WorkflowType.SEARCH_WORKFLOW.value: RecordingAdapter(
            WorkflowType.SEARCH_WORKFLOW, calls
        )
    }

    spawn = orchestrator._spawn_workflow(
        WorkflowSpawnRequest(
            workflow_type=WorkflowType.SEARCH_WORKFLOW,
            workflow_name="search",
            input_data={"question": "question"},
        )
    )
    assert spawn.success is True
    assert orchestrator.state.active_executions

    await orchestrator._drain_workflows()

    assert orchestrator.state.active_executions == []
    assert len(orchestrator.state.completed_executions) == 1
    assert orchestrator.state.completed_executions[0].status == WorkflowStatus.COMPLETED


@pytest.mark.asyncio
async def test_execute_primary_workflow_failure_metadata_reflects_drained_workflows(
    no_primary_agent: None,
) -> None:
    workflow = WorkflowConfig(
        workflow_type=WorkflowType.SEARCH_WORKFLOW,
        name="search",
        max_retries=0,
    )
    orchestrator = make_orchestrator([workflow])
    calls: list[tuple[str, list[str]]] = []
    orchestrator.adapter_registry = {
        WorkflowType.SEARCH_WORKFLOW.value: RecordingAdapter(
            WorkflowType.SEARCH_WORKFLOW, calls
        )
    }

    class FailingPrimaryAgent:
        async def run(self, *_args: Any, **_kwargs: Any) -> None:
            orchestrator._spawn_workflow(
                WorkflowSpawnRequest(
                    workflow_type=WorkflowType.SEARCH_WORKFLOW,
                    workflow_name="search",
                    input_data={"question": "question"},
                )
            )
            raise AgentRunError("model unavailable")

    orchestrator.primary_agent = FailingPrimaryAgent()

    result = await orchestrator.execute_primary_workflow(
        "question", OmegaConf.create({})
    )

    assert result["success"] is False
    assert result["execution_metadata"]["failure_kind"] == "agent_run_error"
    assert result["execution_metadata"]["workflows_spawned"] == 1
    assert result["execution_metadata"]["active_executions"] == 0
    assert result["execution_metadata"]["total_executions"] == 1
    assert orchestrator.state.active_executions == []
    assert len(orchestrator.state.completed_executions) == 1
    assert orchestrator.state.completed_executions[0].status == WorkflowStatus.COMPLETED


@pytest.mark.asyncio
async def test_execute_workflow_plan_rejects_dependency_cycles(
    no_primary_agent: None,
) -> None:
    workflows = [
        WorkflowConfig(
            workflow_type=WorkflowType.SEARCH_WORKFLOW,
            name="a",
            dependencies=["b"],
        ),
        WorkflowConfig(
            workflow_type=WorkflowType.REASONING_WORKFLOW,
            name="b",
            dependencies=["a"],
        ),
    ]
    orchestrator = make_orchestrator(workflows)

    with pytest.raises(ValueError, match="cycle"):
        await orchestrator.execute_workflow_plan(
            WorkflowPlan(user_input="question", workflow_names=["a", "b"]),
            {"question": "question"},
            execution_mode="test",
        )
