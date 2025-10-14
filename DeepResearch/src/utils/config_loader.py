"""
Configuration loader utility for bioinformatics modules.

This module provides utilities for loading and managing bioinformatics
configurations from Hydra config files.
"""

from __future__ import annotations

from typing import Any

from omegaconf import DictConfig, OmegaConf


class BioinformaticsConfigLoader:
    """Loader for bioinformatics configurations."""

    def __init__(self, config: DictConfig | None = None):
        """Initialize config loader."""
        self.config = config or {}
        self.bioinformatics_config = self._extract_bioinformatics_config()

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
        """Get default model name."""
        model_config = self.get_model_config()
        return model_config.get("default", "anthropic:claude-sonnet-4-0")

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
        """Get model for specific agent type."""
        agent_config = self.get_agent_config(agent_type)
        return agent_config.get("model", self.get_default_model())

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
