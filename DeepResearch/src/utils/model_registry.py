"""Role-based model registry resolution helpers."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from DeepResearch.src.datatypes.llm_models import LLMModelConfig, LLMProvider
from DeepResearch.src.datatypes.model_registry import (
    EmbeddingModelSpec,
    LLMModelSpec,
    LLMRuntime,
    ModelRegistryConfig,
    ModelRegistryError,
    PredictorModelSpec,
)
from DeepResearch.src.datatypes.rag import (
    EmbeddingsConfig,
    LLMModelType,
    VLLMConfig,
)

DEFAULT_PYDANTIC_AI_MODEL = "anthropic:claude-sonnet-4-0"

DEFAULT_REGISTRY_DATA: dict[str, Any] = {
    "version": 1,
    "default_models": {
        "llm": "default_chat",
        "embedding": "default_embedding",
        "predictor": "default_predictor",
    },
    "llms": {
        "default_chat": {
            "kind": "llm",
            "runtime": "pydantic_ai",
            "provider": "anthropic",
            "model_name": DEFAULT_PYDANTIC_AI_MODEL,
        },
        "search_chat": {
            "kind": "llm",
            "runtime": "pydantic_ai",
            "provider": "openai",
            "model_name": "gpt-4",
        },
        "local_vllm": {
            "kind": "llm",
            "runtime": "openai_compatible",
            "provider": "vllm",
            "model_name": "TinyLlama/TinyLlama-1.1B-Chat-v1.0",
            "base_url": "http://localhost:8000/v1",
            "host": "localhost",
            "port": 8000,
            "api_key": "EMPTY",
            "generation": {"temperature": 0.7, "max_tokens": 2048, "top_p": 0.9},
        },
    },
    "embeddings": {
        "default_embedding": {
            "kind": "embedding",
            "provider": "sentence_transformers",
            "model_type": "sentence_transformers",
            "model_name": "all-MiniLM-L6-v2",
            "num_dimensions": 384,
            "batch_size": 32,
            "device": "cpu",
        },
        "mixedbread_large": {
            "kind": "embedding",
            "provider": "mixedbread",
            "model_type": "mixedbread",
            "model_name": "mixedbread-ai/mxbai-embed-large-v1",
            "num_dimensions": 1024,
            "batch_size": 32,
            "query_instruction": "Represent this sentence for searching relevant passages:",
        },
        "openai_text_embedding_3_small": {
            "kind": "embedding",
            "provider": "openai",
            "model_type": "openai",
            "model_name": "text-embedding-3-small",
            "num_dimensions": 1536,
            "supported": False,
            "unsupported_reason": "OpenAI embeddings config exists, but the embedding factory does not implement it yet.",
        },
    },
    "predictors": {
        "default_predictor": {
            "kind": "predictor",
            "provider": "none",
            "enabled": False,
        },
        "search_reranker": {
            "kind": "predictor",
            "provider": "custom",
            "task": "reranking",
            "enabled": False,
        },
        "bioinformatics_data_quality": {
            "kind": "predictor",
            "provider": "custom",
            "task": "data_quality",
            "enabled": False,
        },
    },
    "roles": {
        "default": {
            "llm": "default_chat",
            "embedding": "default_embedding",
            "predictor": "default_predictor",
        },
        "parser": {"llm": "default_chat"},
        "planner": {"llm": "default_chat"},
        "executor": {"llm": "default_chat"},
        "search": {
            "llm": "search_chat",
            "embedding": "default_embedding",
            "predictor": "search_reranker",
        },
        "rag": {"llm": "default_chat", "embedding": "default_embedding"},
        "rag_generation": {"llm": "local_vllm"},
        "rag_embedding": {"embedding": "default_embedding"},
        "mgrep_embedding": {"embedding": "default_embedding"},
        "neo4j_embedding": {"embedding": "default_embedding"},
        "judge": {"llm": "default_chat"},
        "evaluator": {"llm": "default_chat"},
        "bioinformatics": {
            "llm": "default_chat",
            "predictor": "bioinformatics_data_quality",
        },
        "bioinformatics_reasoning": {
            "llm": "default_chat",
            "predictor": "bioinformatics_data_quality",
        },
        "code_generation": {"llm": "default_chat"},
        "data_enhancement": {
            "llm": "default_chat",
            "predictor": "bioinformatics_data_quality",
        },
        "tool_use": {"llm": "default_chat"},
        "deep_agent": {"llm": "default_chat"},
        "deepsearch": {"llm": "default_chat"},
        "workflow_pattern": {"llm": "default_chat"},
        "workflow_orchestration": {"llm": "default_chat"},
    },
}


def to_plain_mapping(value: Any) -> dict[str, Any]:
    """Convert plain dicts, BaseModels, and OmegaConf mappings to dicts."""
    if value is None:
        return {}

    try:
        from omegaconf import OmegaConf

        if OmegaConf.is_config(value):
            converted = OmegaConf.to_container(value, resolve=True)
            return dict(converted) if isinstance(converted, Mapping) else {}
    except Exception:
        pass

    if isinstance(value, Mapping):
        return dict(value)
    if hasattr(value, "model_dump"):
        dumped = value.model_dump(mode="python")
        return dict(dumped) if isinstance(dumped, Mapping) else {}

    return {}


def get_model_registry(cfg: Mapping[str, Any] | Any | None) -> ModelRegistryConfig:
    """Return the configured model registry or the built-in compatible default."""
    config_data = to_plain_mapping(cfg)

    if {"llms", "embeddings", "predictors", "roles"} & set(config_data):
        registry_data = config_data
    else:
        registry_data = to_plain_mapping(config_data.get("models"))

    if not registry_data:
        registry_data = DEFAULT_REGISTRY_DATA

    try:
        return ModelRegistryConfig.model_validate(registry_data)
    except Exception as exc:
        msg = f"Invalid model registry configuration: {exc}"
        raise ModelRegistryError(msg) from exc


def _role_ref(
    registry: ModelRegistryConfig,
    role: str,
    kind: str,
) -> str:
    role_spec = registry.roles.get(role) or registry.roles.get("default")
    ref = getattr(role_spec, kind, None) if role_spec is not None else None
    if ref:
        return ref

    default_ref = registry.default_models.get(kind)
    if default_ref:
        return default_ref

    msg = f"No {kind} model configured for role {role!r}"
    raise ModelRegistryError(msg)


def _ensure_supported(spec: Any, role: str, kind: str) -> None:
    if getattr(spec, "supported", True):
        return
    reason = getattr(spec, "unsupported_reason", None) or "profile is unsupported"
    msg = f"{kind} model for role {role!r} is unsupported: {reason}"
    raise ModelRegistryError(msg)


def resolve_llm_spec(
    cfg: Mapping[str, Any] | Any | None,
    role: str = "default",
) -> LLMModelSpec:
    """Resolve an LLM spec for a runtime role."""
    registry = get_model_registry(cfg)
    ref = _role_ref(registry, role, "llm")
    try:
        spec = registry.llms[ref]
    except KeyError as exc:
        msg = f"Unknown llm model reference {ref!r} for role {role!r}"
        raise ModelRegistryError(msg) from exc
    _ensure_supported(spec, role, "llm")
    return spec


def resolve_embedding_spec(
    cfg: Mapping[str, Any] | Any | None,
    role: str = "default",
) -> EmbeddingModelSpec:
    """Resolve an embedding spec for a runtime role."""
    registry = get_model_registry(cfg)
    ref = _role_ref(registry, role, "embedding")
    try:
        spec = registry.embeddings[ref]
    except KeyError as exc:
        msg = f"Unknown embedding model reference {ref!r} for role {role!r}"
        raise ModelRegistryError(msg) from exc
    _ensure_supported(spec, role, "embedding")
    return spec


def resolve_predictor_spec(
    cfg: Mapping[str, Any] | Any | None,
    role: str = "default",
) -> PredictorModelSpec:
    """Resolve a predictor spec for a runtime role."""
    registry = get_model_registry(cfg)
    ref = _role_ref(registry, role, "predictor")
    try:
        spec = registry.predictors[ref]
    except KeyError as exc:
        msg = f"Unknown predictor model reference {ref!r} for role {role!r}"
        raise ModelRegistryError(msg) from exc
    _ensure_supported(spec, role, "predictor")
    return spec


def resolve_pydantic_ai_model(
    cfg: Mapping[str, Any] | Any | None,
    role: str = "default",
) -> str | object:
    """Resolve a role into something Pydantic AI's Agent can accept."""
    spec = resolve_llm_spec(cfg, role)

    if spec.runtime == LLMRuntime.PYDANTIC_AI:
        return spec.model_name

    if spec.runtime == LLMRuntime.OPENAI_COMPATIBLE:
        from DeepResearch.src.models.openai_compatible_model import (
            OpenAICompatibleModel,
        )

        provider = (
            LLMProvider(spec.provider)
            if spec.provider in {provider.value for provider in LLMProvider}
            else LLMProvider.CUSTOM
        )
        model_config = LLMModelConfig(
            provider=provider,
            model_name=spec.model_name,
            base_url=spec.base_url or "",
            api_key=spec.api_key,
        )
        return OpenAICompatibleModel.from_config(
            model_config,
            settings=spec.generation or None,
        )

    msg = f"Unsupported LLM runtime {spec.runtime!r} for role {role!r}"
    raise ModelRegistryError(msg)


def resolve_model_name(
    cfg: Mapping[str, Any] | Any | None,
    role: str = "default",
) -> str:
    """Resolve a role to a string model name, for legacy config datatypes."""
    spec = resolve_llm_spec(cfg, role)
    return spec.model_name


def embedding_spec_to_config(spec: EmbeddingModelSpec) -> EmbeddingsConfig:
    """Convert a registry embedding spec to the existing RAG embedding config."""
    return EmbeddingsConfig(
        model_type=spec.model_type,
        model_name=spec.model_name,
        api_key=spec.api_key,
        base_url=spec.base_url,
        num_dimensions=spec.num_dimensions,
        batch_size=spec.batch_size,
        max_retries=spec.max_retries,
        timeout=spec.timeout,
        query_instruction=spec.query_instruction,
        device=spec.device,
    )


def resolve_embeddings_config(
    cfg: Mapping[str, Any] | Any | None,
    role: str = "default",
) -> EmbeddingsConfig:
    """Resolve a role into the existing EmbeddingsConfig datatype."""
    return embedding_spec_to_config(resolve_embedding_spec(cfg, role))


def resolve_vllm_config(
    cfg: Mapping[str, Any] | Any | None,
    role: str = "rag_generation",
) -> VLLMConfig:
    """Resolve a role into the existing RAG VLLMConfig datatype."""
    spec = resolve_llm_spec(cfg, role)
    generation = spec.generation or {}
    model_type_value = "openai" if spec.provider == "openai" else "custom"
    return VLLMConfig(
        model_type=LLMModelType(model_type_value),
        model_name=spec.model_name,
        host=spec.host or "localhost",
        port=spec.port or 8000,
        api_key=spec.api_key,
        max_tokens=int(generation.get("max_tokens", 2048)),
        temperature=float(generation.get("temperature", 0.7)),
        top_p=float(generation.get("top_p", 0.9)),
        frequency_penalty=float(generation.get("frequency_penalty", 0.0)),
        presence_penalty=float(generation.get("presence_penalty", 0.0)),
        stop=generation.get("stop"),
        stream=bool(generation.get("stream", False)),
    )
