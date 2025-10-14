"""
VLLM Agent data types for DeepCritical research workflows.

This module defines Pydantic models for VLLM agent configuration,
dependencies, and related data structures.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from pydantic import BaseModel, ConfigDict, Field

if TYPE_CHECKING:
    from DeepResearch.src.utils.vllm_client import VLLMClient


class VLLMAgentDependencies(BaseModel):
    """Dependencies for VLLM agent."""

    vllm_client: VLLMClient = Field(..., description="VLLM client instance")
    default_model: str = Field(
        "TinyLlama/TinyLlama-1.1B-Chat-v1.0", description="Default model name"
    )
    embedding_model: str | None = Field(None, description="Embedding model name")

    model_config = ConfigDict(arbitrary_types_allowed=True)


class VLLMAgentConfig(BaseModel):
    """Configuration for VLLM agent."""

    client_config: dict[str, Any] = Field(
        default_factory=dict, description="VLLM client configuration"
    )
    default_model: str = Field(
        "TinyLlama/TinyLlama-1.1B-Chat-v1.0", description="Default model"
    )
    embedding_model: str | None = Field(None, description="Embedding model")
    system_prompt: str = Field(
        "You are a helpful AI assistant powered by VLLM. You can perform various tasks including text generation, conversation, and analysis.",
        description="System prompt for the agent",
    )
    max_tokens: int = Field(512, description="Maximum tokens for generation")
    temperature: float = Field(0.7, description="Sampling temperature")
    top_p: float = Field(0.9, description="Top-p sampling parameter")
