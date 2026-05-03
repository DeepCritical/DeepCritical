import pytest

from DeepResearch.src.agents.hypothesis_agents import (
    HypothesisEvaluatorAgent,
    HypothesisGeneratorAgent,
    HypothesisPlannerAgent,
)
from DeepResearch.src.datatypes.hypothesis import (
    HypothesisCandidate,
    HypothesisEvidence,
)
from DeepResearch.src.tools.base import ExecutionResult


def _sample_evidence() -> list[HypothesisEvidence]:
    return [
        HypothesisEvidence(
            source_id="ev-1",
            source_type="question",
            title="Question framing",
            summary="The question ties a plausible driver to a measurable outcome.",
            relevance=0.9,
        )
    ]


def _sample_candidate() -> HypothesisCandidate:
    return HypothesisCandidate(
        id="hyp-1",
        statement="Spacing study sessions improves long-term recall.",
        rationale="The intervention and outcome are both measurable.",
        assumptions=["Spacing is measurable."],
        predictions=["Recall improves after spaced practice."],
        supporting_evidence=["ev-1"],
        counter_evidence=["No recall gain after spacing."],
        keywords=["spacing", "long-term recall", "practice"],
    )


def test_hypothesis_generator_agent_raises_default_error_on_tool_failure(monkeypatch):
    monkeypatch.setattr(
        "DeepResearch.src.tools.hypothesis_tools.GenerateHypothesesTool.run",
        lambda self, params: ExecutionResult(success=False, error=None),
    )

    with pytest.raises(ValueError, match="Hypothesis generation failed"):
        HypothesisGeneratorAgent().generate(
            "Why does spacing help memory?", _sample_evidence(), 2
        )


def test_hypothesis_evaluator_agent_raises_default_error_on_tool_failure(monkeypatch):
    monkeypatch.setattr(
        "DeepResearch.src.tools.hypothesis_tools.ScoreHypothesesTool.run",
        lambda self, params: ExecutionResult(success=False, error=None),
    )

    with pytest.raises(ValueError, match="Hypothesis scoring failed"):
        HypothesisEvaluatorAgent().rank([_sample_candidate()], 1)


def test_hypothesis_planner_agent_raises_default_error_for_plan_failures(monkeypatch):
    monkeypatch.setattr(
        "DeepResearch.src.tools.hypothesis_tools.CreateHypothesisTestPlansTool.run",
        lambda self, params: ExecutionResult(success=False, error=None),
    )

    with pytest.raises(ValueError, match="Hypothesis test-plan generation failed"):
        HypothesisPlannerAgent().create_test_plans([_sample_candidate()])


def test_hypothesis_planner_agent_raises_default_error_for_report_failures(
    monkeypatch,
):
    monkeypatch.setattr(
        "DeepResearch.src.tools.hypothesis_tools.FormatHypothesisReportTool.run",
        lambda self, params: ExecutionResult(success=False, error=None),
    )

    with pytest.raises(ValueError, match="Hypothesis report formatting failed"):
        HypothesisPlannerAgent().format_report(
            question="Why does spacing help memory?",
            mode="generate",
            evidence=_sample_evidence(),
            hypotheses=[_sample_candidate()],
            test_plans=[],
        )
