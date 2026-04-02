from DeepResearch.src.datatypes.hypothesis import HypothesisCandidate
from DeepResearch.src.tools.hypothesis_tools import (
    CreateHypothesisTestPlansTool,
    GatherEvidenceTool,
    ScoreHypothesesTool,
    extract_keywords,
)


class TestHypothesisTools:
    def test_extract_keywords_returns_ordered_focus_terms(self):
        keywords = extract_keywords(
            "Why does targeted feedback improve long-term learning outcomes?"
        )

        assert keywords[:3] == ["targeted", "feedback", "improve"]

    def test_gather_evidence_returns_question_driven_fallbacks(self, monkeypatch):
        monkeypatch.setattr(
            "DeepResearch.src.tools.hypothesis_tools.GatherEvidenceTool._collect_external_evidence",
            lambda self, question, evidence_mode: [],
        )

        result = GatherEvidenceTool().run(
            {
                "question": "Why does sleep quality affect memory performance?",
                "evidence_mode": "search_only",
            }
        )

        assert result.success is True
        evidence = result.data["evidence"]
        assert len(evidence) >= 3
        assert evidence[0]["source_type"] == "question"
        assert result.data["used_external_evidence"] is False

    def test_score_hypotheses_ranks_candidates_deterministically(self):
        stronger = HypothesisCandidate(
            id="hyp-1",
            statement="A focused intervention changes a measurable outcome under a known context.",
            rationale="Grounded in multiple evidence sources.",
            assumptions=[
                "The intervention can be measured.",
                "The context can be stratified.",
            ],
            predictions=[
                "The outcome moves in the expected direction.",
                "The effect persists after stratification.",
            ],
            supporting_evidence=["ev-1", "ev-2", "ev-3"],
            counter_evidence=["No change in outcome would weaken the hypothesis."],
            keywords=["intervention", "outcome", "context"],
        )
        weaker = HypothesisCandidate(
            id="hyp-2",
            statement="A broad factor may matter.",
            rationale="Less grounded and less specific.",
            assumptions=["The factor exists."],
            predictions=["Something changes."],
            supporting_evidence=["ev-1"],
            counter_evidence=[],
            keywords=["factor"],
        )

        result = ScoreHypothesesTool().run(
            {"hypotheses": [weaker.model_dump(), stronger.model_dump()], "top_k": 2}
        )

        assert result.success is True
        ranked = result.data["ranked_hypotheses"]
        assert ranked[0]["id"] == "hyp-1"
        assert (
            ranked[0]["score"]["overall_score"] >= ranked[1]["score"]["overall_score"]
        )

    def test_create_test_plans_returns_required_fields(self):
        candidate = HypothesisCandidate(
            id="hyp-1",
            statement="Variation in feedback intensity improves retention.",
            rationale="Grounded in feedback and retention evidence.",
            assumptions=["Feedback intensity can be measured."],
            predictions=["Higher intensity predicts better retention."],
            supporting_evidence=["ev-1", "ev-2"],
            counter_evidence=["No retention change would weaken the hypothesis."],
            keywords=["feedback", "retention", "intensity"],
        )

        result = CreateHypothesisTestPlansTool().run(
            {"hypotheses": [candidate.model_dump()]}
        )

        assert result.success is True
        plan = result.data["test_plans"][0]
        assert plan["hypothesis_id"] == "hyp-1"
        assert len(plan["required_inputs"]) >= 3
        assert len(plan["success_criteria"]) >= 2
