from pathlib import Path

from DeepResearch.src.tools.literature_review_tools import (
    LiteratureEvidenceAppraisalTool,
    LiteratureRetrievalTool,
    LiteratureSearchPlanningTool,
    LiteratureSourceCurationTool,
    LiteratureSynthesisTool,
    extract_review_terms,
)

FIXTURE_PATH = (
    Path(__file__).resolve().parents[1]
    / "fixtures"
    / "literature_review"
    / "sources.json"
)


def test_extract_review_terms_returns_focus_terms():
    terms = extract_review_terms(
        "What evidence links sleep quality to memory consolidation?"
    )

    assert terms[:3] == ["sleep", "memory", "consolidation"]


def test_search_planning_returns_queries_and_criteria():
    result = LiteratureSearchPlanningTool().run(
        {
            "question": "What evidence links sleep quality to memory consolidation?",
            "source_mode": "fixture",
            "max_queries": 2,
        }
    )

    assert result.success is True
    plan = result.data["search_plan"]
    assert plan["source_mode"] == "fixture"
    assert len(plan["queries"]) == 2
    assert "sleep" in plan["focus_terms"]


def test_fixture_retrieval_loads_sources_without_live_access():
    result = LiteratureRetrievalTool().run(
        {
            "question": "What evidence links sleep quality to memory consolidation?",
            "source_mode": "fixture",
            "fixture_path": str(FIXTURE_PATH),
            "max_sources": 5,
        }
    )

    assert result.success is True
    assert result.data["used_live_retrieval"] is False
    assert len(result.data["candidate_sources"]) == 5


def test_fixture_retrieval_does_not_repeat_sources_across_planned_queries():
    result = LiteratureRetrievalTool().run(
        {
            "question": "What evidence links sleep quality to memory consolidation?",
            "source_mode": "fixture",
            "fixture_path": str(FIXTURE_PATH),
            "search_plan": {
                "source_mode": "fixture",
                "queries": [
                    "sleep memory",
                    "sleep memory evidence limitations",
                    "memory consolidation critical literature review",
                ],
            },
            "max_sources": 12,
        }
    )

    source_ids = [item["source_id"] for item in result.data["candidate_sources"]]

    assert result.success is True
    assert len(source_ids) == 5
    assert len(source_ids) == len(set(source_ids))


def test_live_retrieval_requires_explicit_enablement():
    result = LiteratureRetrievalTool().run(
        {
            "question": "sleep and memory",
            "source_mode": "openalex",
            "live_retrieval_enabled": False,
        }
    )

    assert result.success is False
    assert result.error is not None
    assert "requires live_retrieval_enabled=true" in result.error


def test_curation_dedupes_and_screens_sources():
    retrieved = LiteratureRetrievalTool().run(
        {
            "question": "What evidence links sleep quality to memory consolidation?",
            "source_mode": "fixture",
            "fixture_path": str(FIXTURE_PATH),
            "max_sources": 5,
        }
    )

    result = LiteratureSourceCurationTool().run(
        {
            "question": "What evidence links sleep quality to memory consolidation?",
            "sources": retrieved.data["candidate_sources"],
            "min_relevance_score": 0.35,
        }
    )

    assert result.success is True
    assert len(result.data["duplicate_diagnostics"]) == 1
    included_ids = {item["source_id"] for item in result.data["included_sources"]}
    excluded_ids = {item["source_id"] for item in result.data["excluded_sources"]}
    assert "sleep-memory-2021" in included_ids
    assert "sleep-recall-trial-2023" in included_ids
    assert "marketing-notifications-2019" in excluded_ids


def test_appraisal_and_synthesis_emit_markdown_report():
    retrieved = LiteratureRetrievalTool().run(
        {
            "question": "What evidence links sleep quality to memory consolidation?",
            "source_mode": "fixture",
            "fixture_path": str(FIXTURE_PATH),
            "max_sources": 5,
        }
    )
    curated = LiteratureSourceCurationTool().run(
        {
            "question": "What evidence links sleep quality to memory consolidation?",
            "sources": retrieved.data["candidate_sources"],
            "min_relevance_score": 0.35,
        }
    )
    appraised = LiteratureEvidenceAppraisalTool().run(
        {"sources": curated.data["included_sources"]}
    )
    plan = (
        LiteratureSearchPlanningTool()
        .run(
            {
                "question": "What evidence links sleep quality to memory consolidation?",
                "source_mode": "fixture",
            }
        )
        .data["search_plan"]
    )

    synthesized = LiteratureSynthesisTool().run(
        {
            "question": "What evidence links sleep quality to memory consolidation?",
            "request": {
                "question": "What evidence links sleep quality to memory consolidation?",
                "source_mode": "fixture",
            },
            "search_plan": plan,
            "included_sources": curated.data["included_sources"],
            "excluded_sources": curated.data["excluded_sources"],
            "screening_decisions": curated.data["screening_decisions"],
            "evidence_table": appraised.data["evidence_table"],
            "appraisals": appraised.data["appraisals"],
            "duplicate_diagnostics": curated.data["duplicate_diagnostics"],
        }
    )

    assert synthesized.success is True
    report = synthesized.data["markdown_report"]
    assert "Critical Literature Review" in report
    assert "Evidence Table" in report
    assert "Critical Appraisal" in report
    assert "References" in report
