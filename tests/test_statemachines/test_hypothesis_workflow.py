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
from DeepResearch.src.statemachines.hypothesis_workflow import (
    _build_testing_environments,
    _section_get,
    run_hypothesis_workflow,
)
from DeepResearch.src.tools.base import ExecutionResult


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
                "mode": "testing",
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
    assert all(
        environment["status"] == "pending"
        for environment in result["testing_environments"]
    )


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
    assert captured["mode"] == "testing"
    assert captured["generate_testing_plans"] is True


@pytest.mark.asyncio
async def test_hypothesis_workflow_can_rank_provided_hypotheses(monkeypatch):
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
                "mode": "testing",
                "top_k": 2,
                "generate_testing_plans": True,
            },
        }
    )

    provided_hypotheses = [
        {
            "id": "hyp-1",
            "statement": "Targeted feedback improves retention by reinforcing retrieval cues.",
            "rationale": "Grounded in retrieval-practice evidence.",
            "assumptions": ["Feedback timing is measurable."],
            "predictions": ["Retention improves when feedback is timely."],
            "supporting_evidence": ["ev-1", "ev-2"],
            "counter_evidence": ["No retention change would weaken the hypothesis."],
            "keywords": ["targeted feedback", "retention"],
        },
        {
            "id": "hyp-2",
            "statement": "Targeted feedback reduces confusion by clarifying misconceptions.",
            "rationale": "Grounded in misconception-correction evidence.",
            "assumptions": ["Confusion can be measured."],
            "predictions": ["Learners make fewer repeated mistakes."],
            "supporting_evidence": ["ev-3"],
            "counter_evidence": ["No change in mistakes would weaken the hypothesis."],
            "keywords": ["targeted feedback", "misconceptions"],
        },
    ]

    result = await run_hypothesis_workflow(
        "",
        cfg,
        mode="testing",
        existing_hypotheses=provided_hypotheses,
    )

    assert result["status"] == "success"
    assert result["metadata"]["used_provided_hypotheses"] is True
    assert len(result["ranked_hypotheses"]) == 2
    assert len(result["test_plans"]) == 2


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


def test_section_get_supports_none_dict_and_broken_getters():
    class BrokenGetter:
        hypothesis_mode = "testing"

        def get(self, key, default=None):
            raise RuntimeError("getter failed")

    assert _section_get(None, "missing", "fallback") == "fallback"
    assert _section_get({"mode": "generate"}, "mode", "fallback") == "generate"
    assert _section_get(BrokenGetter(), "hypothesis_mode", "fallback") == "testing"


@pytest.mark.asyncio
async def test_hypothesis_workflow_rejects_blank_question_without_hypotheses():
    result = await run_hypothesis_workflow("", OmegaConf.create({}))

    assert result["status"] == "failed"
    assert result["metadata"]["failure_stage"] == "request_parsing"
    assert "Question cannot be empty" in result["errors"][-1]


@pytest.mark.asyncio
async def test_hypothesis_workflow_records_evidence_gathering_failure(monkeypatch):
    monkeypatch.setattr(
        "DeepResearch.src.statemachines.hypothesis_workflow.GatherEvidenceTool.run",
        lambda self, params: ExecutionResult(
            success=False, error="evidence unavailable"
        ),
    )

    result = await run_hypothesis_workflow(
        "Why does retrieval practice improve memory?", OmegaConf.create({})
    )

    assert result["status"] == "failed"
    assert result["metadata"]["failure_stage"] == "evidence_gathering"


@pytest.mark.asyncio
async def test_hypothesis_workflow_records_generation_failure(monkeypatch):
    monkeypatch.setattr(
        "DeepResearch.src.agents.hypothesis_agents.HypothesisGeneratorAgent.generate",
        lambda self, question, evidence, max_hypotheses: (_ for _ in ()).throw(
            RuntimeError("generator unavailable")
        ),
    )

    result = await run_hypothesis_workflow(
        "Why does retrieval practice improve memory?", OmegaConf.create({})
    )

    assert result["status"] == "failed"
    assert result["metadata"]["failure_stage"] == "hypothesis_generation"


@pytest.mark.asyncio
async def test_hypothesis_workflow_records_ranking_failure(monkeypatch):
    monkeypatch.setattr(
        "DeepResearch.src.tools.hypothesis_tools.GatherEvidenceTool._collect_external_evidence",
        lambda self, question, evidence_mode: [],
    )
    monkeypatch.setattr(
        "DeepResearch.src.agents.hypothesis_agents.HypothesisEvaluatorAgent.rank",
        lambda self, candidates, top_k, score_weights=None: (_ for _ in ()).throw(
            RuntimeError("ranking unavailable")
        ),
    )

    result = await run_hypothesis_workflow(
        "Why does retrieval practice improve memory?", OmegaConf.create({})
    )

    assert result["status"] == "failed"
    assert result["metadata"]["failure_stage"] == "hypothesis_ranking"


@pytest.mark.asyncio
async def test_hypothesis_workflow_records_test_plan_failure(monkeypatch):
    monkeypatch.setattr(
        "DeepResearch.src.tools.hypothesis_tools.GatherEvidenceTool._collect_external_evidence",
        lambda self, question, evidence_mode: [],
    )
    monkeypatch.setattr(
        "DeepResearch.src.agents.hypothesis_agents.HypothesisPlannerAgent.create_test_plans",
        lambda self, candidates: (_ for _ in ()).throw(
            RuntimeError("planner unavailable")
        ),
    )

    cfg = OmegaConf.create({"hypothesis": {"mode": "testing"}})
    result = await run_hypothesis_workflow(
        "Why does retrieval practice improve memory?", cfg
    )

    assert result["status"] == "failed"
    assert result["metadata"]["failure_stage"] == "test_plan_creation"


def test_build_testing_environments_skips_unmatched_plans():
    state = SimpleNamespace(
        test_plans=[
            SimpleNamespace(
                hypothesis_id="missing-hypothesis",
                test_type="comparative validation study",
                method="Do the experiment",
                required_inputs=["input"],
                success_criteria=["criterion"],
            )
        ],
        ranked_candidates=[],
    )

    assert _build_testing_environments(state) == []


@pytest.mark.asyncio
async def test_run_hypothesis_workflow_raises_on_non_dict_output(monkeypatch):
    class FakeGraph:
        async def run(self, *args, **kwargs):
            return SimpleNamespace(output="not-a-dict")

    monkeypatch.setattr(
        "DeepResearch.src.statemachines.hypothesis_workflow.create_hypothesis_workflow",
        lambda: FakeGraph(),
    )

    with pytest.raises(RuntimeError, match="structured output"):
        await run_hypothesis_workflow(
            "Why does spacing help memory?", OmegaConf.create({})
        )


@pytest.mark.asyncio
async def test_hypothesis_run_uses_default_messages_and_exception_fallback(
    monkeypatch,
):
    async def no_report_success(question, cfg, mode=None):
        return {
            "status": "success",
            "errors": [],
            "dataset": None,
            "testing_environments": [],
        }

    monkeypatch.setattr(
        "DeepResearch.src.statemachines.hypothesis_workflow.run_hypothesis_workflow",
        no_report_success,
    )

    success_state = ResearchState(question="Test question", config=OmegaConf.create({}))
    success_ctx = SimpleNamespace(state=success_state)
    success_final = await HypothesisRun().run(success_ctx)

    assert success_final.data == "Hypothesis analysis completed."
    assert success_state.answers[-1] == "Hypothesis analysis completed."

    async def no_report_failure(question, cfg, mode=None):
        return {
            "status": "failed",
            "errors": ["ranker offline"],
            "dataset": None,
            "testing_environments": [],
        }

    monkeypatch.setattr(
        "DeepResearch.src.statemachines.hypothesis_workflow.run_hypothesis_workflow",
        no_report_failure,
    )

    failure_state = ResearchState(question="Test question", config=OmegaConf.create({}))
    failure_ctx = SimpleNamespace(state=failure_state)
    failure_final = await HypothesisRun().run(failure_ctx)

    assert failure_final.data == "Hypothesis workflow failed: ranker offline"
    assert any(
        "completed with failure status: ranker offline" in note
        for note in failure_state.notes
    )

    async def raise_error(question, cfg, mode=None):
        raise RuntimeError("executor blew up")

    monkeypatch.setattr(
        "DeepResearch.src.statemachines.hypothesis_workflow.run_hypothesis_workflow",
        raise_error,
    )

    error_state = ResearchState(question="Test question", config=OmegaConf.create({}))
    error_ctx = SimpleNamespace(state=error_state)
    error_final = await HypothesisRun().run(error_ctx)

    assert error_final.data == "Error: Hypothesis workflow failed: executor blew up"
    assert error_state.answers[-1] == error_final.data
