from __future__ import annotations

import argparse
import asyncio
import logging

from omegaconf import OmegaConf

from DeepResearch.src.statemachines.hypothesis_workflow import run_hypothesis_workflow

logging.getLogger("MCP").setLevel(logging.ERROR)


def build_config(args: argparse.Namespace):
    mode = args.mode
    return OmegaConf.create(
        {
            "workflow_orchestration": {"enabled": False},
            "flows": {
                "hypothesis_generation": {"enabled": mode == "generate"},
                "hypothesis_testing": {"enabled": mode == "generate_and_plan_tests"},
            },
            "hypothesis": {
                "mode": mode,
                "max_hypotheses": args.max_hypotheses,
                "top_k": args.top_k,
                "evidence_mode": args.evidence_mode,
                "live_evidence_enabled": False,
                "generate_testing_plans": mode == "generate_and_plan_tests",
            },
        }
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run the DeepCritical hypothesis engine"
    )
    parser.add_argument("question", help="Research question to turn into hypotheses")
    parser.add_argument(
        "--mode",
        choices=["generate", "generate_and_plan_tests"],
        default="generate",
        help="Hypothesis workflow mode",
    )
    parser.add_argument(
        "--evidence-mode",
        choices=["search_only", "search_plus_rag"],
        default="search_only",
        help="Evidence gathering mode",
    )
    parser.add_argument("--max-hypotheses", type=int, default=4)
    parser.add_argument("--top-k", type=int, default=3)
    args = parser.parse_args()

    cfg = build_config(args)
    result = asyncio.run(run_hypothesis_workflow(args.question, cfg, mode=args.mode))
    print(result.get("markdown_report", ""))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
