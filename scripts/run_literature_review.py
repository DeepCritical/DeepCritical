from __future__ import annotations

import argparse
import asyncio
import logging

from omegaconf import OmegaConf

from DeepResearch.src.statemachines.literature_review_workflow import (
    run_literature_review_workflow,
)

logging.getLogger("MCP").setLevel(logging.ERROR)


def build_config(args: argparse.Namespace):
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
                "source_mode": args.source_mode,
                "max_sources": args.max_sources,
                "include_preprints": args.include_preprints,
                "live_retrieval_enabled": args.live_retrieval_enabled,
                "min_relevance_score": args.min_relevance_score,
                "fixture_path": args.fixture_path,
                "search": {
                    "max_queries": args.max_queries,
                    "year_min": args.year_min,
                },
            },
        }
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run the DeepCritical critical literature review app"
    )
    parser.add_argument("question", help="Research question to review")
    parser.add_argument(
        "--source-mode",
        choices=["fixture", "openalex", "pubmed", "web", "mixed"],
        default="fixture",
    )
    parser.add_argument("--max-sources", type=int, default=12)
    parser.add_argument("--max-queries", type=int, default=3)
    parser.add_argument("--min-relevance-score", type=float, default=0.35)
    parser.add_argument("--year-min", type=int, default=None)
    parser.add_argument("--fixture-path", default=None)
    parser.add_argument("--include-preprints", action="store_true", default=True)
    parser.add_argument(
        "--exclude-preprints", dest="include_preprints", action="store_false"
    )
    parser.add_argument("--live-retrieval-enabled", action="store_true")
    args = parser.parse_args()

    cfg = build_config(args)
    result = asyncio.run(run_literature_review_workflow(args.question, cfg))
    print(result.get("markdown_report", ""))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
