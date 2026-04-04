from __future__ import annotations

from DeepResearch.src.tools.mgrep import runtime


def test_get_mgrep_service_reuses_cached_service_and_loaded_config(
    monkeypatch, tmp_path
):
    class FakeService:
        instances: list[FakeService] = []

        def __init__(self, repo_root, config):
            self.repo_root = repo_root
            self.config = config
            self.__class__.instances.append(self)

    first_config_path = tmp_path / "mgrep-a.yaml"
    first_config_path.write_text(
        """store_dir: ".cache-a"
supported_extensions: [".py", ".md"]
max_file_size_bytes: 123
search_fetch_multiplier: 2
distance_metric: "cosine"
chunking_strategy_version: "mgrep-v1"
embeddings:
  model_type: "sentence_transformers"
  model_name: "test-model"
  num_dimensions: 8
  batch_size: 4
  device: "cpu"
""",
        encoding="utf-8",
    )
    second_config_path = tmp_path / "mgrep-b.yaml"
    second_config_path.write_text(
        first_config_path.read_text(encoding="utf-8").replace(".cache-a", ".cache-b"),
        encoding="utf-8",
    )

    runtime.clear_mgrep_service_cache()
    monkeypatch.setattr(runtime, "MgrepService", FakeService)

    first = runtime.get_mgrep_service(tmp_path, config_path=first_config_path)
    second = runtime.get_mgrep_service(tmp_path, config_path=first_config_path)
    third = runtime.get_mgrep_service(tmp_path, config_path=second_config_path)

    assert first is second
    assert third is not first
    assert len(FakeService.instances) == 2
    assert first.config.store_dir == ".cache-a"
    assert third.config.store_dir == ".cache-b"

    runtime.clear_mgrep_service_cache()


def test_load_mgrep_config_falls_back_to_model_defaults_when_default_yaml_missing(
    monkeypatch, tmp_path
):
    monkeypatch.setattr(runtime, "DEFAULT_MGREP_CONFIG_PATH", tmp_path / "missing.yaml")

    config = runtime.load_mgrep_config()

    assert config == runtime.MgrepConfig()
