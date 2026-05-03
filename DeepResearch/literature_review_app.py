from __future__ import annotations

import asyncio
import json
import logging
from pathlib import Path

import hydra
from omegaconf import DictConfig

from .src.statemachines.literature_review_workflow import (
    run_literature_review_workflow,
)

logging.getLogger("MCP").setLevel(logging.ERROR)


@hydra.main(
    version_base=None, config_path="../configs", config_name="literature_review_example"
)
def main(cfg: DictConfig) -> None:
    question = cfg.get(
        "question",
        "What evidence links sleep quality to memory consolidation?",
    )
    result = asyncio.run(run_literature_review_workflow(question, cfg))
    markdown_report = result.get("markdown_report", "")
    print(markdown_report)

    literature_cfg = cfg.get("literature_review", {})
    outputs_cfg = literature_cfg.get("outputs", {}) if literature_cfg else {}
    markdown_path = outputs_cfg.get("markdown_path")
    json_path = outputs_cfg.get("json_path")
    if markdown_path:
        output_path = Path(markdown_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(markdown_report, encoding="utf-8")
    if json_path:
        output_path = Path(json_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(
            json.dumps(result, indent=2, sort_keys=True), encoding="utf-8"
        )


if __name__ == "__main__":
    main()
