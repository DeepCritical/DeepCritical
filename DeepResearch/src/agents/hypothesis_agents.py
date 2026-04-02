"""
Agent wrappers for the hypothesis engine.
"""

from __future__ import annotations

from typing import Any

from DeepResearch.src.datatypes.hypothesis import (
    HypothesisCandidate,
    HypothesisEvidence,
    HypothesisTestPlan,
)
from DeepResearch.src.tools.hypothesis_tools import (
    CreateHypothesisTestPlansTool,
    FormatHypothesisReportTool,
    GenerateHypothesesTool,
    ScoreHypothesesTool,
)


class HypothesisGeneratorAgent:
    """Generate structured hypothesis candidates."""

    def __init__(self):
        self._tool = GenerateHypothesesTool()

    def generate(
        self,
        question: str,
        evidence: list[HypothesisEvidence],
        max_hypotheses: int,
    ) -> list[HypothesisCandidate]:
        result = self._tool.run(
            {
                "question": question,
                "evidence": [item.model_dump() for item in evidence],
                "max_hypotheses": max_hypotheses,
            }
        )
        if not result.success:
            msg = result.error or "Hypothesis generation failed"
            raise ValueError(msg)
        return [
            HypothesisCandidate.model_validate(item)
            for item in result.data.get("hypotheses", [])
        ]


class HypothesisEvaluatorAgent:
    """Rank hypothesis candidates deterministically."""

    def __init__(self):
        self._tool = ScoreHypothesesTool()

    def rank(
        self,
        candidates: list[HypothesisCandidate],
        top_k: int,
        score_weights: dict[str, Any] | None = None,
    ) -> list[HypothesisCandidate]:
        result = self._tool.run(
            {
                "hypotheses": [item.model_dump() for item in candidates],
                "score_weights": score_weights or {},
                "top_k": top_k,
            }
        )
        if not result.success:
            msg = result.error or "Hypothesis scoring failed"
            raise ValueError(msg)
        return [
            HypothesisCandidate.model_validate(item)
            for item in result.data.get("ranked_hypotheses", [])
        ]


class HypothesisPlannerAgent:
    """Create test plans and format the final report."""

    def __init__(self):
        self._plan_tool = CreateHypothesisTestPlansTool()
        self._report_tool = FormatHypothesisReportTool()

    def create_test_plans(
        self, candidates: list[HypothesisCandidate]
    ) -> list[HypothesisTestPlan]:
        result = self._plan_tool.run(
            {"hypotheses": [item.model_dump() for item in candidates]}
        )
        if not result.success:
            msg = result.error or "Hypothesis test-plan generation failed"
            raise ValueError(msg)
        return [
            HypothesisTestPlan.model_validate(item)
            for item in result.data.get("test_plans", [])
        ]

    def format_report(
        self,
        question: str,
        mode: str,
        evidence: list[HypothesisEvidence],
        hypotheses: list[HypothesisCandidate],
        test_plans: list[HypothesisTestPlan],
    ) -> str:
        result = self._report_tool.run(
            {
                "question": question,
                "mode": mode,
                "evidence": [item.model_dump() for item in evidence],
                "hypotheses": [item.model_dump() for item in hypotheses],
                "test_plans": [item.model_dump() for item in test_plans],
            }
        )
        if not result.success:
            msg = result.error or "Hypothesis report formatting failed"
            raise ValueError(msg)
        return str(result.data.get("markdown_report", "")).strip()


__all__ = [
    "HypothesisEvaluatorAgent",
    "HypothesisGeneratorAgent",
    "HypothesisPlannerAgent",
]
