"""
Configuration loader utility for bioinformatics modules.

This module provides utilities for loading and managing bioinformatics
configurations from Hydra config files.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any

from omegaconf import DictConfig, OmegaConf

# Configure module logger
logger = logging.getLogger(__name__)

# Constants (Uncle Bob: No magic numbers!)
DEFAULT_EMBEDDING_DIMENSION = 384  # MiniLM-L6-v2 embedding dimension
CONFIG_FILE_NAME = "default.yaml"
CONFIGS_DIR_NAME = "configs"
MODELS_SUBDIR = "models"


def _find_project_root(start_path: Path) -> Path:
    """
    Find project root by looking for configs/ directory.

    This is more robust than hardcoded .parent.parent chains.
    Uncle Bob: "Make code resilient to change"

    Args:
        start_path: Starting path (usually __file__)

    Returns:
        Project root path

    Raises:
        FileNotFoundError: If configs/ directory not found in any parent
    """
    current = start_path
    max_levels = 10  # Safety limit

    for _ in range(max_levels):
        if (current / CONFIGS_DIR_NAME).is_dir():
            return current
        if current.parent == current:  # Reached filesystem root
            break
        current = current.parent

    raise FileNotFoundError(
        f"Could not find '{CONFIGS_DIR_NAME}' directory in any parent of {start_path}. "
        "Ensure config_loader.py is within project structure."
    )


class ModelConfigLoader:
    """
    Centralized loader for LLM and embedding model configurations.

    Supports environment variable overrides with the following priority:
    1. Environment variables (DEFAULT_LLM_MODEL, DEFAULT_EMBEDDING_MODEL)
    2. Agent-specific config (models.llm.agents.<agent_type>)
    3. Default config (models.llm.default, models.embeddings.default)

    When instantiated without a config argument, automatically loads from
    configs/models/default.yaml using OmegaConf.
    """

    def __init__(self, config: DictConfig | None = None):
        """
        Initialize model config loader.

        Args:
            config: Optional Hydra DictConfig. If None, loads from configs/models/default.yaml
        """
        if config is None:
            # Load from file when no config passed (SSOT approach)
            self.config = self._load_default_config()
        else:
            self.config = config
        self.models_config = self._extract_models_config()

    def _load_default_config(self) -> DictConfig:
        """
        Load default models config from YAML file.

        Uncle Bob: "Fail fast and fail explicitly" - No silent exceptions!

        Returns:
            DictConfig with models config loaded from configs/models/default.yaml

        Raises:
            FileNotFoundError: If config file cannot be found
            ValueError: If config file is malformed
        """
        try:
            # Find project root using robust search (not brittle .parent chains)
            current_file = Path(__file__)
            project_root = _find_project_root(current_file.parent)
            config_path = project_root / CONFIGS_DIR_NAME / MODELS_SUBDIR / CONFIG_FILE_NAME

            logger.debug(f"Loading model config from: {config_path}")

            if not config_path.exists():
                logger.warning(
                    f"Model config file not found: {config_path}. "
                    f"Using hardcoded defaults. Create this file to customize models."
                )
                return OmegaConf.create({})

            # Load and validate config
            models_cfg = OmegaConf.load(config_path)
            logger.info(f"Successfully loaded model config from {config_path}")

            # Wrap in parent structure to match Hydra format
            return OmegaConf.create({"models": models_cfg})

        except FileNotFoundError as e:
            # Project structure issue - log and re-raise
            logger.error(f"Project structure error: {e}")
            logger.warning("Falling back to hardcoded model defaults")
            return OmegaConf.create({})

        except Exception as e:
            # Config file parse error or other issue - FAIL EXPLICITLY
            logger.error(
                f"Failed to load model config from {config_path}: {e}",
                exc_info=True
            )
            # Uncle Bob: Make failures visible!
            raise ValueError(
                f"Model configuration file is malformed or unreadable: {config_path}"
            ) from e

    def _extract_models_config(self) -> dict[str, Any]:
        """Extract models configuration from main config."""
        result = OmegaConf.to_container(self.config.get("models", {}), resolve=True)
        from typing import cast

        return cast("dict[str, Any]", result) if isinstance(result, dict) else {}

    def get_llm_config(self) -> dict[str, Any]:
        """Get LLM configuration."""
        return self.models_config.get("llm", {})

    def get_embeddings_config(self) -> dict[str, Any]:
        """Get embeddings configuration."""
        return self.models_config.get("embeddings", {})

    def _get_llm_model(
        self,
        config_key: str,
        hardcoded_fallback: str,
        env_var_name: str | None = None
    ) -> str:
        """
        DRY helper to get LLM model configuration.

        Uncle Bob: "Don't Repeat Yourself" - consolidate duplicate logic!

        Args:
            config_key: Key in llm config (e.g., "default", "fast", "advanced")
            hardcoded_fallback: Ultimate fallback value
            env_var_name: Optional environment variable name for override

        Returns:
            Model name from env var > config > fallback
        """
        # Check environment variable first (if provided)
        if env_var_name:
            env_model = os.getenv(env_var_name)
            if env_model:
                logger.debug(f"Using model from {env_var_name}: {env_model}")
                return env_model

        # Check config
        llm_config = self.get_llm_config()
        model = llm_config.get(config_key, hardcoded_fallback)

        if model == hardcoded_fallback:
            logger.debug(
                f"No config for llm.{config_key}, using hardcoded fallback: {hardcoded_fallback}"
            )

        return model

    def get_default_llm_model(self) -> str:
        """
        Get default LLM model name.

        Priority: ENV_VAR > Config > Hardcoded Fallback
        """
        return self._get_llm_model(
            config_key="default",
            hardcoded_fallback="anthropic:claude-sonnet-4-0",
            env_var_name="DEFAULT_LLM_MODEL"
        )

    def get_fast_llm_model(self) -> str:
        """Get fast LLM model for simple tasks."""
        return self._get_llm_model(
            config_key="fast",
            hardcoded_fallback="anthropic:claude-haiku-3-5"
        )

    def get_advanced_llm_model(self) -> str:
        """Get advanced LLM model for complex reasoning."""
        return self._get_llm_model(
            config_key="advanced",
            hardcoded_fallback="anthropic:claude-opus-4"
        )

    def get_fallback_llm_model(self) -> str:
        """Get fallback LLM model for rate limits or errors."""
        return self._get_llm_model(
            config_key="fallback",
            hardcoded_fallback="anthropic:claude-sonnet-3-5"
        )

    def get_agent_llm_model(self, agent_type: str) -> str:
        """
        Get LLM model for specific agent type.

        Falls back to default model if agent-specific config not found.
        """
        llm_config = self.get_llm_config()
        agents_config = llm_config.get("agents", {})
        return agents_config.get(agent_type, self.get_default_llm_model())

    def get_default_embedding_model(self) -> str:
        """
        Get default embedding model name.

        Priority: ENV_VAR > Config > Hardcoded Fallback
        """
        # Check environment variable first
        env_model = os.getenv("DEFAULT_EMBEDDING_MODEL")
        if env_model:
            logger.debug(f"Using embedding model from DEFAULT_EMBEDDING_MODEL: {env_model}")
            return env_model

        # Check config
        embeddings_config = self.get_embeddings_config()
        model = embeddings_config.get("default", "sentence-transformers/all-MiniLM-L6-v2")

        if model == "sentence-transformers/all-MiniLM-L6-v2":
            logger.debug("No embedding config found, using hardcoded default")

        return model

    def get_embedding_params(self) -> dict[str, Any]:
        """Get default embedding model parameters."""
        embeddings_config = self.get_embeddings_config()
        return embeddings_config.get("default_params", {})

    def get_embedding_dimension(self) -> int:
        """
        Get default embedding dimension.

        Uncle Bob: "No magic numbers!" - Use named constants.
        """
        params = self.get_embedding_params()
        return params.get("num_dimensions", DEFAULT_EMBEDDING_DIMENSION)


class BioinformaticsConfigLoader:
    """Loader for bioinformatics configurations."""

    def __init__(self, config: DictConfig | None = None):
        """Initialize config loader."""
        self.config = config or {}
        self.bioinformatics_config = self._extract_bioinformatics_config()
        self.model_loader = ModelConfigLoader(config)

    def _extract_bioinformatics_config(self) -> dict[str, Any]:
        """Extract bioinformatics configuration from main config."""
        result = OmegaConf.to_container(
            self.config.get("bioinformatics", {}), resolve=True
        )
        return result if isinstance(result, dict) else {}

    def get_model_config(self) -> dict[str, Any]:
        """Get model configuration."""
        return self.bioinformatics_config.get("model", {})

    def get_quality_config(self) -> dict[str, Any]:
        """Get quality configuration."""
        return self.bioinformatics_config.get("quality", {})

    def get_evidence_codes_config(self) -> dict[str, Any]:
        """Get evidence codes configuration."""
        return self.bioinformatics_config.get("evidence_codes", {})

    def get_temporal_config(self) -> dict[str, Any]:
        """Get temporal configuration."""
        return self.bioinformatics_config.get("temporal", {})

    def get_limits_config(self) -> dict[str, Any]:
        """Get limits configuration."""
        return self.bioinformatics_config.get("limits", {})

    def get_data_sources_config(self) -> dict[str, Any]:
        """Get data sources configuration."""
        return self.bioinformatics_config.get("data_sources", {})

    def get_fusion_config(self) -> dict[str, Any]:
        """Get fusion configuration."""
        return self.bioinformatics_config.get("fusion", {})

    def get_reasoning_config(self) -> dict[str, Any]:
        """Get reasoning configuration."""
        return self.bioinformatics_config.get("reasoning", {})

    def get_agents_config(self) -> dict[str, Any]:
        """Get agents configuration."""
        return self.bioinformatics_config.get("agents", {})

    def get_tools_config(self) -> dict[str, Any]:
        """Get tools configuration."""
        return self.bioinformatics_config.get("tools", {})

    def get_workflow_config(self) -> dict[str, Any]:
        """Get workflow configuration."""
        return self.bioinformatics_config.get("workflow", {})

    def get_performance_config(self) -> dict[str, Any]:
        """Get performance configuration."""
        return self.bioinformatics_config.get("performance", {})

    def get_validation_config(self) -> dict[str, Any]:
        """Get validation configuration."""
        return self.bioinformatics_config.get("validation", {})

    def get_output_config(self) -> dict[str, Any]:
        """Get output configuration."""
        return self.bioinformatics_config.get("output", {})

    def get_error_handling_config(self) -> dict[str, Any]:
        """Get error handling configuration."""
        return self.bioinformatics_config.get("error_handling", {})

    def get_default_model(self) -> str:
        """
        Get default model name.

        Uses centralized ModelConfigLoader to eliminate hardcoded strings.
        """
        return self.model_loader.get_default_llm_model()

    def get_default_quality_threshold(self) -> float:
        """Get default quality threshold."""
        quality_config = self.get_quality_config()
        return quality_config.get("default_threshold", 0.8)

    def get_default_max_entities(self) -> int:
        """Get default max entities."""
        limits_config = self.get_limits_config()
        return limits_config.get("default_max_entities", 1000)

    def get_evidence_codes(self, level: str = "high_quality") -> list:
        """Get evidence codes for specified level."""
        evidence_config = self.get_evidence_codes_config()
        return evidence_config.get(level, ["IDA", "EXP"])

    def get_temporal_filter(self, filter_type: str = "recent_year") -> int:
        """Get temporal filter value."""
        temporal_config = self.get_temporal_config()
        return temporal_config.get(filter_type, 2022)

    def get_data_source_config(self, source: str) -> dict[str, Any]:
        """Get configuration for specific data source."""
        data_sources_config = self.get_data_sources_config()
        return data_sources_config.get(source, {})

    def is_data_source_enabled(self, source: str) -> bool:
        """Check if data source is enabled."""
        source_config = self.get_data_source_config(source)
        return source_config.get("enabled", False)

    def get_agent_config(self, agent_type: str) -> dict[str, Any]:
        """Get configuration for specific agent type."""
        agents_config = self.get_agents_config()
        return agents_config.get(agent_type, {})

    def get_agent_model(self, agent_type: str) -> str:
        """
        Get model for specific agent type.

        Uses centralized ModelConfigLoader with agent-specific overrides.
        """
        return self.model_loader.get_agent_llm_model(agent_type)

    def get_agent_system_prompt(self, agent_type: str) -> str:
        """Get system prompt for specific agent type."""
        agent_config = self.get_agent_config(agent_type)
        return agent_config.get("system_prompt", "")

    def get_tool_config(self, tool_name: str) -> dict[str, Any]:
        """Get configuration for specific tool."""
        tools_config = self.get_tools_config()
        return tools_config.get(tool_name, {})

    def get_tool_defaults(self, tool_name: str) -> dict[str, Any]:
        """Get defaults for specific tool."""
        tool_config = self.get_tool_config(tool_name)
        return tool_config.get("defaults", {})

    def get_workflow_config_section(self, section: str) -> dict[str, Any]:
        """Get specific workflow configuration section."""
        workflow_config = self.get_workflow_config()
        return workflow_config.get(section, {})

    def get_performance_setting(self, setting: str) -> Any:
        """Get specific performance setting."""
        performance_config = self.get_performance_config()
        return performance_config.get(setting)

    def get_validation_setting(self, setting: str) -> Any:
        """Get specific validation setting."""
        validation_config = self.get_validation_config()
        return validation_config.get(setting)

    def get_output_setting(self, setting: str) -> Any:
        """Get specific output setting."""
        output_config = self.get_output_config()
        return output_config.get(setting)

    def get_error_handling_setting(self, setting: str) -> Any:
        """Get specific error handling setting."""
        error_config = self.get_error_handling_config()
        return error_config.get(setting)

    def to_dict(self) -> dict[str, Any]:
        """Convert configuration to dictionary."""
        return self.bioinformatics_config

    def update_config(self, updates: dict[str, Any]) -> None:
        """Update configuration with new values."""
        self.bioinformatics_config.update(updates)

    def merge_config(self, other_config: dict[str, Any]) -> None:
        """Merge with another configuration."""

        def deep_merge(base: dict[str, Any], update: dict[str, Any]) -> dict[str, Any]:
            """Deep merge two dictionaries."""
            for key, value in update.items():
                if (
                    key in base
                    and isinstance(base[key], dict)
                    and isinstance(value, dict)
                ):
                    base[key] = deep_merge(base[key], value)
                else:
                    base[key] = value
            return base

        self.bioinformatics_config = deep_merge(
            self.bioinformatics_config, other_config
        )


def load_bioinformatics_config(
    config: DictConfig | None = None,
) -> BioinformaticsConfigLoader:
    """Load bioinformatics configuration from Hydra config."""
    return BioinformaticsConfigLoader(config)


def load_model_config(config: DictConfig | None = None) -> ModelConfigLoader:
    """Load model configuration from Hydra config."""
    return ModelConfigLoader(config)
