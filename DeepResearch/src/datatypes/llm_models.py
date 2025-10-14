"""
Data types for LLM model configurations.

This module defines Pydantic models for configuring various LLM providers
(vLLM, llama.cpp, TGI, etc.) with proper validation and type safety.
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, ConfigDict, Field, field_validator


class LLMProvider(str, Enum):
    """Supported LLM providers."""

    VLLM = "vllm"
    LLAMACPP = "llamacpp"
    TGI = "tgi"
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    CUSTOM = "custom"


class LLMModelConfig(BaseModel):
    """Configuration for LLM models.

    Validates all configuration parameters for LLM models,
    ensuring type safety and proper constraints on values.
    """

    provider: LLMProvider = Field(..., description="Model provider type")
    model_name: str = Field(..., min_length=1, description="Model identifier")
    base_url: str = Field(..., description="Server base URL")
    api_key: str | None = Field(None, description="API key for authentication")
    timeout: float = Field(60.0, gt=0, le=600, description="Request timeout in seconds")
    max_retries: int = Field(3, ge=0, le=10, description="Maximum retry attempts")
    retry_delay: float = Field(
        1.0, gt=0, le=60, description="Delay between retries in seconds"
    )

    @field_validator("model_name")
    @classmethod
    def validate_model_name(cls, v: str) -> str:
        """Validate that model_name is not empty or whitespace."""
        if not v or not v.strip():
            msg = "model_name cannot be empty or whitespace"
            raise ValueError(msg)
        return v.strip()

    @field_validator("base_url")
    @classmethod
    def validate_base_url(cls, v: str) -> str:
        """Validate that base_url is not empty."""
        if not v or not v.strip():
            msg = "base_url cannot be empty"
            raise ValueError(msg)
        return v.strip()

    model_config = ConfigDict(use_enum_values=True)


class GenerationConfig(BaseModel):
    """Generation parameters for LLM models.

    Defines and validates parameters used during text generation,
    ensuring all values are within acceptable ranges.
    """

    temperature: float = Field(
        0.7,
        ge=0.0,
        le=2.0,
        description="Sampling temperature (0.0 = deterministic, 2.0 = very random)",
    )
    max_tokens: int = Field(
        512, gt=0, le=32000, description="Maximum number of tokens to generate"
    )
    top_p: float = Field(
        0.9, ge=0.0, le=1.0, description="Top-p (nucleus) sampling parameter"
    )
    frequency_penalty: float = Field(
        0.0, ge=-2.0, le=2.0, description="Frequency penalty for reducing repetition"
    )
    presence_penalty: float = Field(
        0.0, ge=-2.0, le=2.0, description="Presence penalty for encouraging diversity"
    )


class LLMConnectionConfig(BaseModel):
    """Advanced connection configuration for LLM servers."""

    timeout: float = Field(60.0, gt=0, le=600, description="Request timeout in seconds")
    max_retries: int = Field(3, ge=0, le=10, description="Maximum retry attempts")
    retry_delay: float = Field(1.0, gt=0, le=60, description="Delay between retries")
    verify_ssl: bool = Field(True, description="Verify SSL certificates")
    custom_headers: dict[str, str] = Field(
        default_factory=dict, description="Custom HTTP headers"
    )
