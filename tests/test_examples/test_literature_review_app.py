import pytest
from omegaconf import OmegaConf

from DeepResearch.src.statemachines.literature_review_workflow import (
    run_literature_review_workflow,
)


@pytest.mark.asyncio
async def test_literature_review_app_example_config_smoke():
    cfg = OmegaConf.create(
        {
            "workflow_orchestration": {"enabled": False},
            "flows": {"literature_review": {"enabled": True}},
            "literature_review": {
                "mode": "review",
                "source_mode": "fixture",
                "max_sources": 4,
                "include_preprints": True,
                "live_retrieval_enabled": False,
                "min_relevance_score": 0.35,
                "search": {"max_queries": 2, "year_min": None},
            },
        }
    )

    result = await run_literature_review_workflow(
        "What evidence links sleep quality to memory consolidation?", cfg
    )

    assert result["status"] == "success"
    assert "Critical Literature Review" in result["markdown_report"]
    assert "References" in result["markdown_report"]
