from __future__ import annotations

import asyncio
import logging

from omegaconf import OmegaConf

from DeepResearch.src.statemachines.hypothesis_workflow import run_hypothesis_workflow

logging.getLogger("MCP").setLevel(logging.ERROR)


def main() -> int:
    cfg = OmegaConf.create(
        {
            "workflow_orchestration": {"enabled": False},
            "flows": {
                "hypothesis_generation": {"enabled": False},
                "hypothesis_testing": {"enabled": True},
            },
            "hypothesis": {
                "mode": "generate_and_plan_tests",
                "max_hypotheses": 3,
                "top_k": 2,
                "evidence_mode": "search_only",
                "live_evidence_enabled": False,
                "generate_testing_plans": True,
            },
        }
    )
    result = asyncio.run(
        run_hypothesis_workflow(
            "What mechanisms could explain why sleep quality affects memory performance?",
            cfg,
            mode="generate_and_plan_tests",
        )
    )
    hypotheses = result.get("ranked_hypotheses", [])
    test_plans = result.get("test_plans", [])
    if not hypotheses or not test_plans:
        print("Hypothesis smoke test failed.")
        return 1

    print("Hypothesis smoke test passed.")
    print(result.get("markdown_report", ""))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
