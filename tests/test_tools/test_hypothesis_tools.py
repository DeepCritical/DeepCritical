from DeepResearch.src.datatypes.hypothesis import HypothesisCandidate
from DeepResearch.src.tools.base import ExecutionResult
from DeepResearch.src.tools.hypothesis_tools import (
    FormatHypothesisReportTool,
    CreateHypothesisTestPlansTool,
    GatherEvidenceTool,
    GenerateHypothesesTool,
    ScoreHypothesesTool,
    extract_keywords,
)


class TestHypothesisTools:
    def test_extract_keywords_returns_ordered_focus_terms(self):
        keywords = extract_keywords(
            "Why does targeted feedback improve long-term learning outcomes?"
        )

        assert keywords[:2] == ["targeted feedback", "long-term learning outcomes"]

    def test_extract_keywords_preserves_driver_and_outcome_phrases(self):
        keywords = extract_keywords(
            "What mechanisms could explain how sleep quality affects memory performance?"
        )

        assert keywords[:2] == ["sleep quality", "memory performance"]
        assert "affects" not in keywords[:2]

    def test_extract_keywords_uses_default_focus_terms_for_sparse_questions(self):
        keywords = extract_keywords("Why?", limit=3)

        assert keywords == [
            "baseline conditions",
            "time scale",
            "measurement context",
        ]

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

    def test_gather_evidence_rejects_missing_or_blank_questions(self):
        missing = GatherEvidenceTool().run({})
        blank = GatherEvidenceTool().run({"question": "   "})

        assert missing.success is False
        assert blank.success is False

    def test_gather_evidence_collects_search_and_rag_results(self, monkeypatch):
        monkeypatch.setenv("DEEPCRITICAL_ENABLE_LIVE_EVIDENCE", "true")

        def fake_search_run(self, params):
            return ExecutionResult(
                success=True,
                data={
                    "documents": [
                        {
                            "content": (
                                "Evidence from the search result about memory retention."
                            ),
                            "metadata": {
                                "source_title": "Search study",
                                "url": "https://example.com/search",
                            },
                        },
                        {
                            "content": "   ",
                            "metadata": {"source_title": "Ignored empty result"},
                        },
                    ]
                },
            )

        def fake_rag_run(self, params):
            return ExecutionResult(
                success=True,
                data={
                    "documents": [
                        {
                            "content": (
                                "RAG retrieved supporting material about spaced repetition."
                            ),
                            "metadata": {
                                "source_title": "RAG source",
                                "source": "rag://memory",
                            },
                        }
                    ]
                },
            )

        monkeypatch.setattr(
            "DeepResearch.src.tools.integrated_search_tools.IntegratedSearchTool.run",
            fake_search_run,
        )
        monkeypatch.setattr(
            "DeepResearch.src.tools.integrated_search_tools.RAGSearchTool.run",
            fake_rag_run,
        )

        tool = GatherEvidenceTool()
        assert tool._is_live_evidence_enabled(None) is True

        result = tool.run(
            {
                "question": "Why does spaced repetition improve recall?",
                "evidence_mode": "search_plus_rag",
                "live_evidence_enabled": "yes",
                "max_evidence_items": 5,
            }
        )

        assert result.success is True
        evidence = result.data["evidence"]
        assert result.data["used_external_evidence"] is True
        assert any(item["source_type"] == "search" for item in evidence)
        assert any(item["source_type"] == "rag" for item in evidence)
        assert not any(item["title"] == "Ignored empty result" for item in evidence)

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

    def test_score_hypotheses_handles_empty_input_and_invalid_weights(self):
        empty_result = ScoreHypothesesTool().run({"hypotheses": []})
        assert empty_result.success is False

        candidate = HypothesisCandidate(
            id="hyp-weights",
            statement="A measured intervention shifts a measurable outcome.",
            rationale="Grounded in a structured comparison.",
            assumptions=["The intervention is measurable."],
            predictions=["The outcome changes in the expected direction."],
            supporting_evidence=["ev-1"],
            counter_evidence=["No observed change would weaken the claim."],
            keywords=["intervention", "outcome", "comparison"],
        )

        weighted_result = ScoreHypothesesTool().run(
            {
                "hypotheses": [candidate.model_dump()],
                "score_weights": {"novelty": "bad-value"},
            }
        )

        assert weighted_result.success is True
        assert (
            weighted_result.data["ranked_hypotheses"][0]["score"]["overall_score"] > 0
        )

    def test_generate_hypotheses_anchors_driver_and_outcome_terms(self):
        result = GenerateHypothesesTool().run(
            {
                "question": "Why does spaced repetition improve recall?",
                "max_hypotheses": 3,
            }
        )

        assert result.success is True
        hypotheses = result.data["hypotheses"]
        assert hypotheses[0]["keywords"][:2] == ["spaced repetition", "recall"]
        assert "spaced repetition" in hypotheses[0]["statement"].lower()
        assert "recall" in hypotheses[0]["statement"].lower()
        assert "improve" not in hypotheses[0]["keywords"][:2]

    def test_generate_hypotheses_rejects_missing_or_blank_questions(self):
        missing = GenerateHypothesesTool().run({})
        blank = GenerateHypothesesTool().run({"question": "   "})

        assert missing.success is False
        assert blank.success is False

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

    def test_create_test_plans_supports_keyword_fallback_and_empty_input(self):
        empty = CreateHypothesisTestPlansTool().run({"hypotheses": []})
        assert empty.success is False

        candidate = HypothesisCandidate(
            id="hyp-fallback",
            statement="Improved tutoring cadence changes learner confidence.",
            rationale="Cadence and confidence are observable.",
            assumptions=["Cadence is measurable."],
            predictions=["Confidence rises when cadence improves."],
            supporting_evidence=["ev-1"],
            counter_evidence=["Confidence stays flat."],
            keywords=[],
        )

        result = CreateHypothesisTestPlansTool().run(
            {"hypotheses": [candidate.model_dump()]}
        )

        assert result.success is True
        method = result.data["test_plans"][0]["method"]
        assert "tutoring cadence" in method
        assert "learner confidence" in method

    def test_format_report_handles_empty_evidence_and_missing_question(self):
        missing = FormatHypothesisReportTool().run({})
        blank = FormatHypothesisReportTool().run({"question": "   ", "hypotheses": []})

        assert missing.success is False
        assert blank.success is False

        candidate = HypothesisCandidate(
            id="hyp-report",
            statement="Spaced repetition improves long-term recall.",
            rationale="Supported by question framing.",
            assumptions=["Spacing intervals can be controlled."],
            predictions=["Recall improves after spaced review."],
            supporting_evidence=["ev-1"],
            counter_evidence=["No recall gain after spacing."],
            keywords=["spaced repetition", "long-term recall", "review interval"],
        )

        report = FormatHypothesisReportTool().run(
            {
                "question": "Why does spaced repetition improve recall?",
                "mode": "testing",
                "hypotheses": [candidate.model_dump()],
                "test_plans": CreateHypothesisTestPlansTool()
                .run({"hypotheses": [candidate.model_dump()]})
                .data["test_plans"],
            }
        )

        assert report.success is True
        assert "No external evidence was available" in report.data["markdown_report"]
        assert "## Test Plans" in report.data["markdown_report"]
