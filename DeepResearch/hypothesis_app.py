from __future__ import annotations

import asyncio
import logging

import hydra
from omegaconf import DictConfig

from .src.statemachines.hypothesis_workflow import run_hypothesis_workflow

logging.getLogger("MCP").setLevel(logging.ERROR)


@hydra.main(
    version_base=None, config_path="../configs", config_name="hypothesis_example"
)
def main(cfg: DictConfig) -> None:
    question = cfg.get("question", "What hypotheses best explain this outcome?")
    result = asyncio.run(run_hypothesis_workflow(question, cfg))
    print(result.get("markdown_report", ""))


if __name__ == "__main__":
    main()
