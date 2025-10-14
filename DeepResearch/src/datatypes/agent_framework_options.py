"""
Vendored chat options types from agent_framework._types.

This module provides chat options and tool configuration types.
"""

from typing import Any

from pydantic import BaseModel, Field, field_validator

from .agent_framework_enums import ToolMode


class ChatOptions(BaseModel):
    """Common request settings for AI services."""

    model_id: str | None = None
    allow_multiple_tool_calls: bool | None = None
    conversation_id: str | None = None
    frequency_penalty: float | None = Field(None, ge=-2.0, le=2.0)
    instructions: str | None = None
    logit_bias: dict[str | int, float] | None = None
    max_tokens: int | None = Field(None, gt=0)
    metadata: dict[str, str] | None = None
    presence_penalty: float | None = Field(None, ge=-2.0, le=2.0)
    response_format: type | None = None
    seed: int | None = None
    stop: str | list[str] | None = None
    store: bool | None = None
    temperature: float | None = Field(None, ge=0.0, le=2.0)
    tool_choice: ToolMode | str | dict[str, Any] | None = None
    tools: list[Any] | None = None  # ToolProtocol | Callable | Dict
    top_p: float | None = Field(None, ge=0.0, le=1.0)
    user: str | None = None
    additional_properties: dict[str, Any] | None = None

    @field_validator("tool_choice", mode="before")
    @classmethod
    def validate_tool_choice(cls, v):
        """Validate tool_choice field."""
        if not v:
            return None
        if isinstance(v, str):
            if v == "auto":
                return ToolMode(mode="auto")
            if v == "required":
                return ToolMode(mode="required")
            if v == "none":
                return ToolMode(mode="none")
            msg = f"Invalid tool choice: {v}"
            raise ValueError(msg)
        if isinstance(v, dict):
            return ToolMode(mode=v.get("mode", "auto"))
        return v

    @field_validator("tools", mode="before")
    @classmethod
    def validate_tools(cls, v):
        """Validate tools field."""
        if not v:
            return None
        if not isinstance(v, list):
            return [v]
        return v

    def to_provider_settings(
        self, by_alias: bool = True, exclude: set | None = None
    ) -> dict[str, Any]:
        """Convert the ChatOptions to a dictionary suitable for provider requests."""
        default_exclude = {"additional_properties", "type"}

        # No tool choice if no tools are defined
        if self.tools is None or len(self.tools) == 0:
            default_exclude.add("tool_choice")

        # No metadata and logit bias if they are empty
        if not self.logit_bias:
            default_exclude.add("logit_bias")
        if not self.metadata:
            default_exclude.add("metadata")

        merged_exclude = (
            default_exclude if exclude is None else default_exclude | set(exclude)
        )

        settings = self.model_dump(exclude_none=True, exclude=merged_exclude)

        if by_alias and self.model_id is not None:
            settings["model"] = settings.pop("model_id", None)

        # Serialize tool_choice to its string representation for provider settings
        if "tool_choice" in settings and isinstance(self.tool_choice, ToolMode):
            settings["tool_choice"] = self.tool_choice.serialize_model()

        settings = {k: v for k, v in settings.items() if v is not None}
        if self.additional_properties:
            settings.update(self.additional_properties)

        for key in merged_exclude:
            settings.pop(key, None)

        return settings

    def __and__(self, other: object) -> "ChatOptions":
        """Combines two ChatOptions instances."""
        if not isinstance(other, ChatOptions):
            return self

        # Start with a copy of self
        combined = self.copy()

        # Apply updates from other
        for field_name, field_value in other.model_dump(
            exclude_none=True, exclude={"tools"}
        ).items():
            if field_value is not None:
                setattr(combined, field_name, field_value)

        # Handle tools combination
        if other.tools:
            if combined.tools is None:
                combined.tools = list(other.tools)
            else:
                for tool in other.tools:
                    if tool not in combined.tools:
                        combined.tools.append(tool)

        # Handle tool_choice
        combined.tool_choice = other.tool_choice or self.tool_choice

        # Handle response_format
        if other.response_format is not None:
            combined.response_format = other.response_format

        # Combine instructions
        if other.instructions:
            combined.instructions = "\n".join(
                [combined.instructions or "", other.instructions or ""]
            ).strip()

        # Combine logit_bias
        if other.logit_bias:
            if combined.logit_bias is None:
                combined.logit_bias = {}
            combined.logit_bias.update(other.logit_bias)

        # Combine metadata
        if other.metadata:
            if combined.metadata is None:
                combined.metadata = {}
            combined.metadata.update(other.metadata)

        # Combine additional_properties
        if other.additional_properties:
            if combined.additional_properties is None:
                combined.additional_properties = {}
            combined.additional_properties.update(other.additional_properties)

        return combined
