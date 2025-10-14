"""
Vendored enum types from agent_framework._types.

This module provides enum-like types for AI agent interactions.
"""

from typing import ClassVar, Literal

from pydantic import BaseModel


class Role(BaseModel):
    """Describes the intended purpose of a message within a chat interaction."""

    value: str

    # Predefined role constants
    SYSTEM: ClassVar[str] = "system"
    USER: ClassVar[str] = "user"
    ASSISTANT: ClassVar[str] = "assistant"
    TOOL: ClassVar[str] = "tool"

    def __str__(self) -> str:
        """Returns the string representation of the role."""
        return self.value

    def __repr__(self) -> str:
        """Returns the string representation of the role."""
        return f"Role(value={self.value!r})"

    def __eq__(self, other: object) -> bool:
        """Check if two Role instances are equal."""
        if isinstance(other, str):
            return self.value == other
        if isinstance(other, Role):
            return self.value == other.value
        return False

    def __hash__(self) -> int:
        """Return hash of the Role for use in sets and dicts."""
        return hash(self.value)


class FinishReason(BaseModel):
    """Represents the reason a chat response completed."""

    value: str

    # Predefined finish reason constants
    CONTENT_FILTER: ClassVar[str] = "content_filter"
    LENGTH: ClassVar[str] = "length"
    STOP: ClassVar[str] = "stop"
    TOOL_CALLS: ClassVar[str] = "tool_calls"

    def __eq__(self, other: object) -> bool:
        """Check if two FinishReason instances are equal."""
        if isinstance(other, str):
            return self.value == other
        if isinstance(other, FinishReason):
            return self.value == other.value
        return False

    def __hash__(self) -> int:
        """Return hash of the FinishReason for use in sets and dicts."""
        return hash(self.value)

    def __str__(self) -> str:
        """Returns the string representation of the finish reason."""
        return self.value

    def __repr__(self) -> str:
        """Returns the string representation of the finish reason."""
        return f"FinishReason(value={self.value!r})"


class ToolMode(BaseModel):
    """Defines if and how tools are used in a chat request."""

    mode: Literal["auto", "required", "none"]
    required_function_name: str | None = None

    # Predefined tool mode constants
    AUTO: ClassVar[str] = "auto"
    REQUIRED_ANY: ClassVar[str] = "required"
    NONE: ClassVar[str] = "none"

    @classmethod
    def REQUIRED(cls, function_name: str | None = None) -> "ToolMode":
        """Returns a ToolMode that requires the specified function to be called."""
        return cls(mode="required", required_function_name=function_name)

    def __eq__(self, other: object) -> bool:
        """Checks equality with another ToolMode or string."""
        if isinstance(other, str):
            return self.mode == other
        if isinstance(other, ToolMode):
            return (
                self.mode == other.mode
                and self.required_function_name == other.required_function_name
            )
        return False

    def __hash__(self) -> int:
        """Return hash of the ToolMode for use in sets and dicts."""
        return hash((self.mode, self.required_function_name))

    def serialize_model(self) -> str:
        """Serializes the ToolMode to just the mode string."""
        return self.mode

    def __str__(self) -> str:
        """Returns the string representation of the mode."""
        return self.mode

    def __repr__(self) -> str:
        """Returns the string representation of the ToolMode."""
        if self.required_function_name:
            return f"ToolMode(mode={self.mode!r}, required_function_name={self.required_function_name!r})"
        return f"ToolMode(mode={self.mode!r})"
