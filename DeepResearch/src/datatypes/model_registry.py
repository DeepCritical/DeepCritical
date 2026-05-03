"""Typed configuration for role-based specialized model selection."""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from .rag import EmbeddingModelType


class ModelRegistryError(ValueError):
    """Raised when a model registry or role reference is invalid."""


class ModelKind(str, Enum):
    """Supported model spec kinds."""

    LLM = "llm"
    EMBEDDING = "embedding"
    PREDICTOR = "predictor"


class LLMRuntime(str, Enum):
    """How an LLM spec should be converted into a runtime model."""

    PYDANTIC_AI = "pydantic_ai"
    OPENAI_COMPATIBLE = "openai_compatible"


class LLMModelSpec(BaseModel):
    """LLM profile referenced by model roles."""

    kind: ModelKind = Field(ModelKind.LLM, description="Model kind")
    runtime: LLMRuntime = Field(
        LLMRuntime.PYDANTIC_AI, description="Runtime adapter to use"
    )
    provider: str = Field("custom", description="Provider name")
    model_name: str = Field(..., min_length=1, description="Model identifier")
    base_url: str | None = Field(None, description="OpenAI-compatible base URL")
    api_key: str | None = Field(None, description="Provider API key or token")
    host: str | None = Field(None, description="Optional host for RAG/VLLM configs")
    port: int | None = Field(None, ge=1, le=65535, description="Optional service port")
    generation: dict[str, Any] = Field(
        default_factory=dict, description="Generation settings"
    )
    supported: bool = Field(True, description="Whether this profile is selectable")
    unsupported_reason: str | None = Field(None, description="Why selection is blocked")
    notes: str | None = Field(None, description="Human-facing implementation notes")
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("model_name")
    @classmethod
    def validate_model_name(cls, value: str) -> str:
        """Reject empty or whitespace-only model identifiers."""
        stripped = value.strip()
        if not stripped:
            msg = "model_name cannot be empty"
            raise ValueError(msg)
        return stripped

    @model_validator(mode="after")
    def validate_supported_runtime(self) -> LLMModelSpec:
        """Ensure OpenAI-compatible profiles have connection data."""
        if (
            self.supported
            and self.runtime == LLMRuntime.OPENAI_COMPATIBLE
            and not self.base_url
        ):
            msg = "openai_compatible LLM specs require base_url"
            raise ValueError(msg)
        return self

    model_config = ConfigDict(use_enum_values=True)


class EmbeddingModelSpec(BaseModel):
    """Embedding profile referenced by model roles."""

    kind: ModelKind = Field(ModelKind.EMBEDDING, description="Model kind")
    provider: str = Field("sentence_transformers", description="Provider name")
    model_type: EmbeddingModelType = Field(..., description="Embedding factory type")
    model_name: str = Field(..., min_length=1, description="Model identifier")
    api_key: str | None = Field(None, description="Provider API key")
    base_url: str | None = Field(None, description="Provider endpoint")
    num_dimensions: int = Field(..., gt=0, description="Embedding vector dimensions")
    batch_size: int = Field(32, gt=0, description="Embedding batch size")
    max_retries: int = Field(3, ge=0, description="Maximum retry attempts")
    timeout: float = Field(30.0, gt=0, description="Request timeout")
    query_instruction: str | None = Field(None, description="Optional query prefix")
    device: str | None = Field(None, description="Local inference device")
    supported: bool = Field(True, description="Whether this profile is selectable")
    unsupported_reason: str | None = Field(None, description="Why selection is blocked")
    notes: str | None = Field(None, description="Human-facing implementation notes")
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("model_name")
    @classmethod
    def validate_model_name(cls, value: str) -> str:
        """Reject empty or whitespace-only model identifiers."""
        stripped = value.strip()
        if not stripped:
            msg = "model_name cannot be empty"
            raise ValueError(msg)
        return stripped

    model_config = ConfigDict(use_enum_values=True)


class PredictorModelSpec(BaseModel):
    """Predictor profile referenced by model roles."""

    kind: ModelKind = Field(ModelKind.PREDICTOR, description="Model kind")
    provider: str = Field("none", description="Provider name")
    task: str | None = Field(None, description="Predictor task type")
    model_name: str | None = Field(None, description="Model identifier")
    base_url: str | None = Field(None, description="Provider endpoint")
    api_key: str | None = Field(None, description="Provider API key")
    device: str | None = Field(None, description="Local inference device")
    batch_size: int = Field(1, gt=0, description="Prediction batch size")
    timeout: float = Field(30.0, gt=0, description="Request timeout")
    enabled: bool = Field(False, description="Whether runtime use is enabled")
    supported: bool = Field(True, description="Whether this profile is selectable")
    unsupported_reason: str | None = Field(None, description="Why selection is blocked")
    notes: str | None = Field(None, description="Human-facing implementation notes")
    metadata: dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(use_enum_values=True)


class ModelRoleSpec(BaseModel):
    """Role-level references into model catalogs."""

    llm: str | None = Field(None, description="LLM catalog key")
    embedding: str | None = Field(None, description="Embedding catalog key")
    predictor: str | None = Field(None, description="Predictor catalog key")


class ModelRegistryConfig(BaseModel):
    """Central registry for specialized model profiles and role routing."""

    version: int = 1
    default_models: dict[str, str] = Field(default_factory=dict)
    llms: dict[str, LLMModelSpec] = Field(default_factory=dict)
    embeddings: dict[str, EmbeddingModelSpec] = Field(default_factory=dict)
    predictors: dict[str, PredictorModelSpec] = Field(default_factory=dict)
    roles: dict[str, ModelRoleSpec] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_references(self) -> ModelRegistryConfig:
        """Validate default and role catalog references."""
        for kind, key in self.default_models.items():
            self._validate_catalog_ref(kind, key, f"default_models.{kind}")

        for role_name, role in self.roles.items():
            if role.llm is not None:
                self._validate_catalog_ref("llm", role.llm, f"roles.{role_name}.llm")
            if role.embedding is not None:
                self._validate_catalog_ref(
                    "embedding", role.embedding, f"roles.{role_name}.embedding"
                )
            if role.predictor is not None:
                self._validate_catalog_ref(
                    "predictor", role.predictor, f"roles.{role_name}.predictor"
                )
        return self

    def _validate_catalog_ref(self, kind: str, key: str, path: str) -> None:
        catalog: dict[str, Any]
        if kind == "llm":
            catalog = self.llms
        elif kind == "embedding":
            catalog = self.embeddings
        elif kind == "predictor":
            catalog = self.predictors
        else:
            msg = f"Unknown model kind {kind!r} at {path}"
            raise ValueError(msg)

        if key not in catalog:
            msg = f"Unknown {kind} model reference {key!r} at {path}"
            raise ValueError(msg)
