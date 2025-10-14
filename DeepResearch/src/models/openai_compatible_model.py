"""
Pydantic AI model wrapper for OpenAI-compatible servers.

This module provides a generic OpenAICompatibleModel that can work with:
- vLLM (OpenAI-compatible API)
- llama.cpp server (OpenAI-compatible mode)
- Text Generation Inference (TGI)
- Any other server implementing the OpenAI Chat Completions API

All configuration is managed through Hydra config files.
"""

from __future__ import annotations

import os
from typing import Any

from omegaconf import DictConfig, OmegaConf
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.ollama import OllamaProvider

from DeepResearch.src.datatypes.llm_models import (
    GenerationConfig,
    LLMModelConfig,
    LLMProvider,
)


class OpenAICompatibleModel(OpenAIChatModel):
    """Pydantic AI model for OpenAI-compatible servers.

    This is a thin wrapper around Pydantic AI's OpenAIChatModel that makes it
    easy to connect to local or custom OpenAI-compatible servers.

    Supports:
    - vLLM with OpenAI-compatible API
    - llama.cpp server in OpenAI mode
    - Text Generation Inference (TGI)
    - Any custom OpenAI-compatible endpoint
    """

    @classmethod
    def from_config(
        cls,
        config: DictConfig | dict | LLMModelConfig,
        model_name: str | None = None,
        base_url: str | None = None,
        api_key: str | None = None,
        **kwargs: Any,
    ) -> OpenAICompatibleModel:
        """Create a model from Hydra configuration.

        Args:
            config: Hydra configuration (DictConfig), dict, or LLMModelConfig with model settings.
            model_name: Override model name from config.
            base_url: Override base URL from config.
            api_key: Override API key from config.
            **kwargs: Additional arguments passed to the model.

        Returns:
            Configured OpenAICompatibleModel instance.
        """
        # If already a validated LLMModelConfig, use it
        if isinstance(config, LLMModelConfig):
            validated_config = config
        else:
            # Convert DictConfig to dict if needed
            if isinstance(config, DictConfig):
                config_dict = OmegaConf.to_container(config, resolve=True)
                if not isinstance(config_dict, dict):
                    msg = f"Expected dict after OmegaConf.to_container, got {type(config_dict)}"
                    raise ValueError(msg)
                config = config_dict
            elif not isinstance(config, dict):
                msg = f"Expected dict or DictConfig, got {type(config)}"
                raise ValueError(msg)

            # Build config dict with fallbacks for validation
            provider_value = config.get("provider", "custom")
            model_name_value = (
                model_name
                or config.get("model_name")
                or config.get("model", {}).get("name", "gpt-3.5-turbo")
            )
            base_url_value = (
                base_url or config.get("base_url") or os.getenv("LLM_BASE_URL", "")
            )
            timeout_value = config.get("timeout", 60.0) or 60.0
            max_retries_value = config.get("max_retries", 3) or 3
            retry_delay_value = config.get("retry_delay", 1.0) or 1.0

            config_dict = {
                "provider": (
                    LLMProvider(provider_value)
                    if provider_value
                    else LLMProvider.CUSTOM
                ),
                "model_name": (
                    str(model_name_value) if model_name_value else "gpt-3.5-turbo"
                ),
                "base_url": str(base_url_value) if base_url_value else "",
                "api_key": api_key or config.get("api_key") or os.getenv("LLM_API_KEY"),
                "timeout": float(timeout_value),
                "max_retries": int(max_retries_value),
                "retry_delay": float(retry_delay_value),
            }

            # Validate using Pydantic model
            try:
                validated_config = LLMModelConfig(**config_dict)  # type: ignore
            except Exception as e:
                msg = f"Invalid LLM model configuration: {e}"
                raise ValueError(msg)

        # Apply direct parameter overrides
        final_model_name = model_name or validated_config.model_name
        final_base_url = base_url or validated_config.base_url
        final_api_key = api_key or validated_config.api_key or "EMPTY"

        # Extract and validate generation settings from config
        settings = kwargs.pop("settings", {})

        if isinstance(config, (dict, DictConfig)) and not isinstance(
            config, LLMModelConfig
        ):
            if isinstance(config, DictConfig):
                config_dict = OmegaConf.to_container(config, resolve=True)
                if not isinstance(config_dict, dict):
                    msg = f"Expected dict after OmegaConf.to_container, got {type(config_dict)}"
                    raise ValueError(msg)
                config = config_dict
            elif not isinstance(config, dict):
                msg = f"Expected dict or DictConfig, got {type(config)}"
                raise ValueError(msg)

            generation_config_dict = config.get("generation", {})

            # Validate generation parameters that are present in config
            if generation_config_dict:
                try:
                    # Validate only the parameters present in the config
                    validated_gen_config = GenerationConfig(**generation_config_dict)
                    # Only include parameters that were in the original config
                    for key in generation_config_dict:
                        if hasattr(validated_gen_config, key):
                            settings[key] = getattr(validated_gen_config, key)
                except Exception as e:
                    msg = f"Invalid generation configuration: {e}"
                    raise ValueError(msg)

        provider = OllamaProvider(
            base_url=final_base_url,
            api_key=final_api_key,
        )

        return cls(
            final_model_name, provider=provider, settings=settings or None, **kwargs
        )

    @classmethod
    def from_vllm(
        cls,
        config: DictConfig | dict | None = None,
        model_name: str | None = None,
        base_url: str | None = None,
        api_key: str | None = None,
        **kwargs: Any,
    ) -> OpenAICompatibleModel:
        """Create a model for a vLLM server.

        Args:
            config: Optional Hydra configuration with vLLM settings.
            model_name: Model name (overrides config if provided).
            base_url: vLLM server URL (overrides config if provided).
            api_key: API key (overrides config if provided).
            **kwargs: Additional arguments passed to the model.

        Returns:
            Configured OpenAICompatibleModel instance.
        """
        if config is not None:
            return cls.from_config(config, model_name, base_url, api_key, **kwargs)

        # Fallback for direct parameter usage
        if not base_url:
            msg = "base_url is required when not using config"
            raise ValueError(msg)
        if not model_name:
            msg = "model_name is required when not using config"
            raise ValueError(msg)

        provider = OllamaProvider(
            base_url=base_url,
            api_key=api_key or "EMPTY",
        )
        return cls(model_name, provider=provider, **kwargs)

    @classmethod
    def from_llamacpp(
        cls,
        config: DictConfig | dict | None = None,
        model_name: str | None = None,
        base_url: str | None = None,
        api_key: str | None = None,
        **kwargs: Any,
    ) -> OpenAICompatibleModel:
        """Create a model for a llama.cpp server.

        Args:
            config: Optional Hydra configuration with llama.cpp settings.
            model_name: Model name (overrides config if provided).
            base_url: llama.cpp server URL (overrides config if provided).
            api_key: API key (overrides config if provided).
            **kwargs: Additional arguments passed to the model.

        Returns:
            Configured OpenAICompatibleModel instance.
        """
        if config is not None:
            # Use default llama model name if not specified
            if model_name is None and "model_name" not in config:
                model_name = "llama"
            return cls.from_config(config, model_name, base_url, api_key, **kwargs)

        # Fallback for direct parameter usage
        if not base_url:
            msg = "base_url is required when not using config"
            raise ValueError(msg)

        provider = OllamaProvider(
            base_url=base_url,
            api_key=api_key or "sk-no-key-required",
        )
        return cls(model_name or "llama", provider=provider, **kwargs)

    @classmethod
    def from_tgi(
        cls,
        config: DictConfig | dict | None = None,
        model_name: str | None = None,
        base_url: str | None = None,
        api_key: str | None = None,
        **kwargs: Any,
    ) -> OpenAICompatibleModel:
        """Create a model for a Text Generation Inference (TGI) server.

        Args:
            config: Optional Hydra configuration with TGI settings.
            model_name: Model name (overrides config if provided).
            base_url: TGI server URL (overrides config if provided).
            api_key: API key (overrides config if provided).
            **kwargs: Additional arguments passed to the model.

        Returns:
            Configured OpenAICompatibleModel instance.
        """
        if config is not None:
            return cls.from_config(config, model_name, base_url, api_key, **kwargs)

        # Fallback for direct parameter usage
        if not base_url:
            msg = "base_url is required when not using config"
            raise ValueError(msg)
        if not model_name:
            msg = "model_name is required when not using config"
            raise ValueError(msg)

        provider = OllamaProvider(
            base_url=base_url,
            api_key=api_key or "EMPTY",
        )
        return cls(model_name, provider=provider, **kwargs)

    @classmethod
    def from_custom(
        cls,
        config: DictConfig | dict | None = None,
        model_name: str | None = None,
        base_url: str | None = None,
        api_key: str | None = None,
        **kwargs: Any,
    ) -> OpenAICompatibleModel:
        """Create a model for any custom OpenAI-compatible server.

        Args:
            config: Optional Hydra configuration with custom server settings.
            model_name: Model name (overrides config if provided).
            base_url: Server URL (overrides config if provided).
            api_key: API key (overrides config if provided).
            **kwargs: Additional arguments passed to the model.

        Returns:
            Configured OpenAICompatibleModel instance.
        """
        if config is not None:
            return cls.from_config(config, model_name, base_url, api_key, **kwargs)

        # Fallback for direct parameter usage
        if not base_url:
            msg = "base_url is required when not using config"
            raise ValueError(msg)
        if not model_name:
            msg = "model_name is required when not using config"
            raise ValueError(msg)

        provider = OllamaProvider(
            base_url=base_url,
            api_key=api_key or "EMPTY",
        )
        return cls(model_name, provider=provider, **kwargs)


# Convenience aliases
VLLMModel = OpenAICompatibleModel
"""Alias for OpenAICompatibleModel when using vLLM.
"""

LlamaCppModel = OpenAICompatibleModel
"""Alias for OpenAICompatibleModel when using llama.cpp.
"""
