from pathlib import Path

import pytest
from hydra import compose, initialize_config_dir

from DeepResearch.app import run_graph


@pytest.fixture
def config_dir() -> str:
    return str(Path(__file__).resolve().parents[2] / "configs")


def test_hypothesis_example_config_composes(config_dir):
    with initialize_config_dir(version_base=None, config_dir=config_dir):
        cfg = compose(config_name="hypothesis_example")

    assert cfg.flows.hypothesis_generation.enabled is True
    assert cfg.workflow_orchestration.enabled is False
    assert cfg.hypothesis.mode == "generate"
    assert "enabled" not in cfg.hypothesis
    assert "require_reasoning" not in cfg.hypothesis
    assert "output_format" not in cfg.hypothesis


def test_run_graph_with_hypothesis_example_config(config_dir, monkeypatch):
    monkeypatch.setattr(
        "DeepResearch.src.tools.hypothesis_tools.GatherEvidenceTool._collect_external_evidence",
        lambda self, question, evidence_mode: [],
    )

    with initialize_config_dir(version_base=None, config_dir=config_dir):
        cfg = compose(config_name="hypothesis_example")

    output = run_graph(cfg.question, cfg)

    assert "Hypothesis Engine Report" in output
    assert "Ranked Hypotheses" in output
