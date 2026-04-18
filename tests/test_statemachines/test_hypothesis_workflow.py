from types import SimpleNamespace

import pytest
from omegaconf import OmegaConf

from DeepResearch.app import HypothesisRun, Plan, ResearchState
from DeepResearch.src.agents.workflow_orchestrator import PrimaryWorkflowOrchestrator
from DeepResearch.src.datatypes.workflow_orchestration import (
    WorkflowConfig,
    WorkflowOrchestrationConfig,
    WorkflowType,
)
from DeepResearch.src.statemachines.hypothesis_workflow import run_hypothesis_workflow


@pytest.mark.asyncio
async def test_hypothesis_workflow_generate_mode(monkeypatch):
    monkeypatch.setattr(
        "DeepResearch.src.tools.hypothesis_tools.GatherEvidenceTool._collect_external_evidence",
        lambda self, question, evidence_mode: [],
    )

    cfg = OmegaConf.create(
        {
            "workflow_orchestration": {"enabled": False},
            "flows": {
                "hypothesis_generation": {"enabled": True},
                "hypothesis_testing": {"enabled": False},
            },
            "hypothesis": {
                "mode": "generate",
                "max_hypotheses": 4,
                "top_k": 3,
                "evidence_mode": "search_only",
                "generate_testing_plans": False,
            },
        }
    )

    result = await run_hypothesis_workflow(
        "Why does spaced repetition improve long-term recall?", cfg
    )

    assert result["status"] == "success"
    assert len(result["ranked_hypotheses"]) == 3
    assert result["dataset"] is not None
    assert "Hypothesis Engine Report" in result["markdown_report"]


@pytest.mark.asyncio
async def test_hypothesis_workflow_testing_mode_returns_plans(monkeypatch):
    monkeypatch.setattr(
        "DeepResearch.src.tools.hypothesis_tools.GatherEvidenceTool._collect_external_evidence",
        lambda self, question, evidence_mode: [],
    )

    cfg = OmegaConf.create(
        {
            "workflow_orchestration": {"enabled": False},
            "flows": {
                "hypothesis_generation": {"enabled": False},
                "hypothesis_testing": {"enabled": True},
            },
            "hypothesis": {
                "mode": "generate_and_plan_tests",
                "max_hypotheses": 3,
                "top_k": 2,
                "evidence_mode": "search_only",
                "generate_testing_plans": True,
            },
        }
    )

    result = await run_hypothesis_workflow(
        "What mechanisms could explain how sleep quality affects memory?", cfg
    )

    assert result["status"] == "success"
    assert len(result["ranked_hypotheses"]) == 2
    assert len(result["test_plans"]) == 2
    assert len(result["testing_environments"]) == 2


@pytest.mark.asyncio
async def test_hypothesis_workflow_synthesis_failure_returns_structured_error(
    monkeypatch,
):
    monkeypatch.setattr(
        "DeepResearch.src.tools.hypothesis_tools.GatherEvidenceTool._collect_external_evidence",
        lambda self, question, evidence_mode: [],
    )

    def fail_format_report(self, question, mode, evidence, hypotheses, test_plans):
        raise RuntimeError("report formatter unavailable")

    monkeypatch.setattr(
        "DeepResearch.src.agents.hypothesis_agents.HypothesisPlannerAgent.format_report",
        fail_format_report,
    )

    cfg = OmegaConf.create(
        {
            "workflow_orchestration": {"enabled": False},
            "flows": {
                "hypothesis_generation": {"enabled": True},
                "hypothesis_testing": {"enabled": False},
            },
            "hypothesis": {
                "mode": "generate",
                "max_hypotheses": 3,
                "top_k": 2,
                "evidence_mode": "search_only",
                "generate_testing_plans": False,
            },
        }
    )

    result = await run_hypothesis_workflow(
        "Why does retrieval practice improve recall?", cfg
    )

    assert result["status"] == "failed"
    assert result["dataset"] is None
    assert result["testing_environments"] == []
    assert result["metadata"]["failure_stage"] == "report_synthesis"
    assert "Hypothesis report synthesis failed" in result["errors"][-1]
    assert "Hypothesis workflow failed" in result["markdown_report"]


@pytest.mark.asyncio
async def test_plan_routes_to_hypothesis_before_orchestration():
    cfg = OmegaConf.create(
        {
            "workflow_orchestration": {"enabled": True},
            "flows": {
                "hypothesis_generation": {"enabled": True},
                "hypothesis_testing": {"enabled": False},
            },
        }
    )
    state = ResearchState(question="Test question", config=cfg)
    ctx = SimpleNamespace(state=state)

    next_node = await Plan().run(ctx)

    assert isinstance(next_node, HypothesisRun)


@pytest.mark.asyncio
async def test_orchestrator_generation_delegates_to_shared_workflow(monkeypatch):
    captured = {}

    async def fake_run(question, cfg, mode=None):
        captured["question"] = question
        captured["mode"] = mode
        captured["max_hypotheses"] = cfg.hypothesis.max_hypotheses
        return {"markdown_report": "ok"}

    monkeypatch.setattr(
        PrimaryWorkflowOrchestrator,
        "_create_primary_agent",
        lambda self: None,
    )
    monkeypatch.setattr(
        "DeepResearch.src.statemachines.hypothesis_workflow.run_hypothesis_workflow",
        fake_run,
    )

    orchestrator = PrimaryWorkflowOrchestrator(
        WorkflowOrchestrationConfig(
            primary_workflow=WorkflowConfig(
                workflow_type=WorkflowType.PRIMARY_REACT,
                name="main",
            )
        )
    )

    result = await orchestrator._execute_hypothesis_generation_workflow(
        {"question": "Why does spacing improve memory?"},
        {"max_hypotheses": 5},
    )

    assert result == {"markdown_report": "ok"}
    assert captured["question"] == "Why does spacing improve memory?"
    assert captured["mode"] == "generate"
    assert captured["max_hypotheses"] == 5


@pytest.mark.asyncio
async def test_orchestrator_testing_delegates_to_shared_workflow(monkeypatch):
    captured = {}

    async def fake_run(question, cfg, mode=None):
        captured["question"] = question
        captured["mode"] = mode
        captured["generate_testing_plans"] = cfg.hypothesis.generate_testing_plans
        return {"markdown_report": "ok"}

    monkeypatch.setattr(
        PrimaryWorkflowOrchestrator,
        "_create_primary_agent",
        lambda self: None,
    )
    monkeypatch.setattr(
        "DeepResearch.src.statemachines.hypothesis_workflow.run_hypothesis_workflow",
        fake_run,
    )

    orchestrator = PrimaryWorkflowOrchestrator(
        WorkflowOrchestrationConfig(
            primary_workflow=WorkflowConfig(
                workflow_type=WorkflowType.PRIMARY_REACT,
                name="main",
            )
        )
    )

    result = await orchestrator._execute_hypothesis_testing_workflow(
        {"question": "What mechanisms explain sleep and memory?"},
        {},
    )

    assert result == {"markdown_report": "ok"}
    assert captured["question"] == "What mechanisms explain sleep and memory?"
    assert captured["mode"] == "generate_and_plan_tests"
    assert captured["generate_testing_plans"] is True


@pytest.mark.asyncio
async def test_hypothesis_run_records_structured_failure_without_success_note(
    monkeypatch,
):
    async def fake_run(question, cfg, mode=None):
        return {
            "status": "failed",
            "errors": [
                "Hypothesis report synthesis failed: report formatter unavailable"
            ],
            "markdown_report": (
                "Hypothesis workflow failed: report formatter unavailable"
            ),
            "testing_environments": [],
            "dataset": None,
        }

    monkeypatch.setattr(
        "DeepResearch.src.statemachines.hypothesis_workflow.run_hypothesis_workflow",
        fake_run,
    )

    state = ResearchState(question="Test question", config=OmegaConf.create({}))
    ctx = SimpleNamespace(state=state)

    final = await HypothesisRun().run(ctx)

    assert final.data == "Hypothesis workflow failed: report formatter unavailable"
    assert state.answers[-1] == final.data
    assert not any(
        note == "Hypothesis workflow completed successfully" for note in state.notes
    )
    assert any("completed with failure status" in note for note in state.notes)
