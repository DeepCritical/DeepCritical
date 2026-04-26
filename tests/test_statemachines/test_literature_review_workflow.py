from pathlib import Path
from types import SimpleNamespace
from typing import Any, cast

import pytest
from omegaconf import OmegaConf

from DeepResearch.app import LiteratureReviewRun, Plan, ResearchState
from DeepResearch.src.statemachines.literature_review_workflow import (
    run_literature_review_workflow,
)

FIXTURE_PATH = (
    Path(__file__).resolve().parents[1]
    / "fixtures"
    / "literature_review"
    / "sources.json"
)


def _cfg(fixture_path: str | None = None):
    return OmegaConf.create(
        {
            "workflow_orchestration": {"enabled": False},
            "flows": {
                "literature_review": {"enabled": True},
                "hypothesis_generation": {"enabled": False},
                "hypothesis_testing": {"enabled": False},
            },
            "literature_review": {
                "mode": "review",
                "source_mode": "fixture",
                "max_sources": 5,
                "include_preprints": True,
                "live_retrieval_enabled": False,
                "min_relevance_score": 0.35,
                "fixture_path": fixture_path,
                "search": {"max_queries": 3, "year_min": None},
            },
        }
    )


@pytest.mark.asyncio
async def test_literature_review_workflow_fixture_mode():
    result = await run_literature_review_workflow(
        "What evidence links sleep quality to memory consolidation?",
        _cfg(str(FIXTURE_PATH)),
    )

    assert result["status"] == "success"
    assert "Critical Literature Review" in result["markdown_report"]
    report = result["report"]
    assert report is not None
    assert len(report["included_sources"]) >= 2
    assert report["diagnostics"]["duplicates_removed"] == 1


@pytest.mark.asyncio
async def test_literature_review_workflow_empty_fixture_reports_no_sources(tmp_path):
    empty_fixture = tmp_path / "empty_sources.json"
    empty_fixture.write_text('{"sources": []}', encoding="utf-8")

    result = await run_literature_review_workflow(
        "What evidence links sleep quality to memory consolidation?",
        _cfg(str(empty_fixture)),
    )

    assert result["status"] == "success"
    assert "No sources passed screening" in result["markdown_report"]
    assert "No sources passed literature screening" in result["warnings"]
    assert result["report"]["included_sources"] == []


@pytest.mark.asyncio
async def test_literature_review_workflow_empty_question_fails():
    result = await run_literature_review_workflow("   ", _cfg(str(FIXTURE_PATH)))

    assert result["status"] == "failed"
    assert result["metadata"]["failure_stage"] == "request_parsing"
    assert "Question cannot be empty" in result["errors"][-1]


@pytest.mark.asyncio
async def test_literature_review_live_source_mode_requires_enablement():
    cfg = _cfg(str(FIXTURE_PATH))
    cfg.literature_review.source_mode = "openalex"
    cfg.literature_review.live_retrieval_enabled = False

    result = await run_literature_review_workflow(
        "What evidence links sleep quality to memory consolidation?",
        cfg,
    )

    assert result["status"] == "failed"
    assert "requires live_retrieval_enabled=true" in result["errors"][-1]


@pytest.mark.asyncio
async def test_plan_routes_to_literature_review_before_orchestration():
    cfg = OmegaConf.create(
        {
            "workflow_orchestration": {"enabled": True},
            "flows": {
                "literature_review": {"enabled": True},
                "hypothesis_generation": {"enabled": False},
                "hypothesis_testing": {"enabled": False},
            },
        }
    )
    state = ResearchState(question="Test question", config=cfg)
    ctx = cast("Any", SimpleNamespace(state=state))

    next_node = await Plan().run(ctx)

    assert isinstance(next_node, LiteratureReviewRun)


@pytest.mark.asyncio
async def test_literature_review_run_records_structured_result(monkeypatch):
    async def fake_run(question, cfg, mode=None):
        return {
            "status": "success",
            "markdown_report": "# Critical Literature Review\n\nok",
            "warnings": [],
            "errors": [],
        }

    monkeypatch.setattr(
        "DeepResearch.src.statemachines.literature_review_workflow.run_literature_review_workflow",
        fake_run,
    )

    state = ResearchState(question="Test question", config=OmegaConf.create({}))
    ctx = cast("Any", SimpleNamespace(state=state))

    final = await LiteratureReviewRun().run(ctx)

    assert final.data == "# Critical Literature Review\n\nok"
    assert state.execution_results["literature_review"]["status"] == "success"
    assert state.answers[-1] == final.data
