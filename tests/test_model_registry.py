from pathlib import Path

import pytest
from hydra import compose, initialize_config_dir
from omegaconf import OmegaConf

from DeepResearch.src.datatypes.model_registry import (
    ModelRegistryConfig,
    ModelRegistryError,
)
from DeepResearch.src.statemachines.rag_workflow import InitializeRAG
from DeepResearch.src.tools.bioinformatics_tools import BioinformaticsToolDeps
from DeepResearch.src.tools.mgrep.runtime import load_mgrep_config
from DeepResearch.src.utils.model_registry import (
    DEFAULT_PYDANTIC_AI_MODEL,
    get_model_registry,
    resolve_embeddings_config,
    resolve_model_name,
    resolve_pydantic_ai_model,
)


def _registry_with_role_model(role: str, model_name: str) -> dict:
    registry_data = get_model_registry(None).model_dump(mode="python")
    registry_data["llms"][f"{role}_model"] = {
        "kind": "llm",
        "runtime": "pydantic_ai",
        "provider": "anthropic",
        "model_name": model_name,
    }
    registry_data["roles"][role] = {"llm": f"{role}_model"}
    return {"models": registry_data}


def test_default_registry_resolves_backward_compatible_roles():
    registry = get_model_registry(None)

    assert registry.default_models["llm"] == "default_chat"
    assert resolve_model_name(None, "planner") == DEFAULT_PYDANTIC_AI_MODEL
    assert resolve_pydantic_ai_model(None, "search") == "gpt-4"

    embedding = resolve_embeddings_config(None, "rag_embedding")
    assert embedding.model_name == "all-MiniLM-L6-v2"
    assert embedding.num_dimensions == 384


def test_registry_validates_missing_role_reference():
    with pytest.raises(ValueError, match="Unknown llm model reference"):
        ModelRegistryConfig.model_validate(
            {
                "default_models": {"llm": "default_chat"},
                "llms": {
                    "default_chat": {
                        "kind": "llm",
                        "runtime": "pydantic_ai",
                        "provider": "anthropic",
                        "model_name": DEFAULT_PYDANTIC_AI_MODEL,
                    }
                },
                "embeddings": {},
                "predictors": {},
                "roles": {"planner": {"llm": "missing_model"}},
            }
        )


def test_unsupported_embedding_profile_fails_early():
    registry_data = get_model_registry(None).model_dump(mode="python")
    registry_data["roles"]["rag_embedding"]["embedding"] = (
        "openai_text_embedding_3_small"
    )
    with pytest.raises(ModelRegistryError, match="OpenAI embeddings"):
        resolve_embeddings_config({"models": registry_data}, "rag_embedding")


def test_hydra_default_config_composes_models_group():
    config_dir = str((Path(__file__).parent.parent / "configs").resolve())
    with initialize_config_dir(config_dir=config_dir, version_base=None):
        cfg = compose(config_name="config")

    assert "models" in cfg
    assert cfg.models.roles.search.llm == "search_chat"
    assert cfg.models.roles.workflow_pattern.llm == "default_chat"
    assert cfg.models.roles.workflow_orchestration.llm == "default_chat"
    assert resolve_model_name(cfg, "planner") == DEFAULT_PYDANTIC_AI_MODEL


def test_public_agents_resolve_role_defaults_from_registry():
    from DeepResearch.agents import ParserAgent, SearchAgent

    parser_config = _registry_with_role_model("parser", "parser-specialist")
    search_config = _registry_with_role_model("search", "search-specialist")

    assert ParserAgent(config=parser_config).model_name == "parser-specialist"
    assert SearchAgent(config=search_config).model_name == "search-specialist"


def test_workflow_and_code_agents_resolve_role_defaults_from_registry():
    from DeepResearch.src.agents.code_improvement_agent import CodeImprovementAgent
    from DeepResearch.src.agents.workflow_pattern_agents import PatternOrchestratorAgent
    from DeepResearch.src.workflow_patterns import WorkflowPatternFactory

    code_config = _registry_with_role_model("code_generation", "test")
    workflow_config = _registry_with_role_model(
        "workflow_pattern", "workflow-specialist"
    )

    assert CodeImprovementAgent(config=code_config).model_name == "test"
    assert (
        PatternOrchestratorAgent(config=workflow_config).model_name
        == "workflow-specialist"
    )
    assert (
        WorkflowPatternFactory.create_pattern_orchestrator(
            config=workflow_config
        ).model_name
        == "workflow-specialist"
    )


def test_bioinformatics_tool_deps_prefer_configured_role_over_legacy_default():
    config = _registry_with_role_model(
        "bioinformatics_reasoning", "bioinformatics-specialist"
    )
    config["bioinformatics"] = {
        "model": {
            "default": "legacy-hardcoded-model",
            "role": "bioinformatics_reasoning",
        }
    }

    deps = BioinformaticsToolDeps.from_config(config)

    assert deps.model_name == "bioinformatics-specialist"
    assert deps.model_role == "bioinformatics_reasoning"
    assert (
        BioinformaticsToolDeps.from_config(
            config, model_name="explicit-model"
        ).model_name
        == "explicit-model"
    )


def test_mgrep_config_can_resolve_embedding_role(tmp_path):
    config_path = tmp_path / "mgrep.yaml"
    config_path.write_text(
        """
store_dir: ".deepcritical/mgrep"
embedding_model_role: "mgrep_embedding"
models:
  default_models:
    llm: default_chat
    embedding: custom_embedding
    predictor: default_predictor
  llms:
    default_chat:
      kind: llm
      runtime: pydantic_ai
      provider: anthropic
      model_name: anthropic:claude-sonnet-4-0
  embeddings:
    custom_embedding:
      kind: embedding
      provider: sentence_transformers
      model_type: sentence_transformers
      model_name: custom-mgrep-model
      num_dimensions: 12
      batch_size: 4
  predictors:
    default_predictor:
      kind: predictor
      provider: none
      enabled: false
  roles:
    default:
      llm: default_chat
      embedding: custom_embedding
      predictor: default_predictor
    mgrep_embedding:
      embedding: custom_embedding
""",
        encoding="utf-8",
    )

    config = load_mgrep_config(config_path)

    assert config.embedding_model_role == "mgrep_embedding"
    assert config.embeddings.model_name == "custom-mgrep-model"
    assert config.embeddings.num_dimensions == 12


def test_rag_workflow_can_resolve_registry_roles():
    cfg = OmegaConf.create(
        {
            "models": {
                "default_models": {
                    "llm": "default_chat",
                    "embedding": "custom_embedding",
                    "predictor": "default_predictor",
                },
                "llms": {
                    "default_chat": {
                        "kind": "llm",
                        "runtime": "pydantic_ai",
                        "provider": "anthropic",
                        "model_name": DEFAULT_PYDANTIC_AI_MODEL,
                    },
                    "rag_llm": {
                        "kind": "llm",
                        "runtime": "openai_compatible",
                        "provider": "vllm",
                        "model_name": "rag-test-model",
                        "base_url": "http://localhost:8000/v1",
                        "host": "127.0.0.1",
                        "port": 9000,
                        "generation": {"max_tokens": 99, "temperature": 0.2},
                    },
                },
                "embeddings": {
                    "custom_embedding": {
                        "kind": "embedding",
                        "provider": "sentence_transformers",
                        "model_type": "sentence_transformers",
                        "model_name": "rag-embedding-model",
                        "num_dimensions": 24,
                        "batch_size": 6,
                    }
                },
                "predictors": {
                    "default_predictor": {
                        "kind": "predictor",
                        "provider": "none",
                        "enabled": False,
                    }
                },
                "roles": {
                    "default": {
                        "llm": "default_chat",
                        "embedding": "custom_embedding",
                        "predictor": "default_predictor",
                    },
                    "rag_embedding": {"embedding": "custom_embedding"},
                    "rag_generation": {"llm": "rag_llm"},
                },
            },
            "rag": {
                "embedding_model_role": "rag_embedding",
                "llm_model_role": "rag_generation",
                "vector_store": {"store_type": "faiss", "collection_name": "test"},
            },
        }
    )

    rag_config = InitializeRAG()._create_rag_config(cfg.rag, cfg)

    assert rag_config.embeddings.model_name == "rag-embedding-model"
    assert rag_config.embeddings.num_dimensions == 24
    assert rag_config.llm.model_name == "rag-test-model"
    assert rag_config.llm.host == "127.0.0.1"
    assert rag_config.llm.port == 9000
    assert rag_config.llm.max_tokens == 99
