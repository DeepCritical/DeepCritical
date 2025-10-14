"""
Vendored agent types from agent_framework._types.

This module provides agent run response types for AI agent interactions.
"""

from collections.abc import Sequence
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field, field_validator

from .agent_framework_chat import ChatMessage
from .agent_framework_content import (
    Content,
    FunctionApprovalRequestContent,
    TextContent,
)


class AgentRunResponseUpdate(BaseModel):
    """Represents a single streaming response chunk from an Agent."""

    contents: list[Content] = Field(default_factory=list)
    role: str | Any | None = None
    author_name: str | None = None
    response_id: str | None = None
    message_id: str | None = None
    created_at: str | datetime | None = None
    additional_properties: dict[str, Any] | None = None
    raw_representation: Any | list[Any] | None = None

    @field_validator("contents", mode="before")
    @classmethod
    def validate_contents(cls, v):
        """Ensure contents is a list."""
        if v is None:
            return []
        if not isinstance(v, list):
            return [v]
        return v

    @property
    def text(self) -> str:
        """Get the concatenated text of all TextContent objects in contents."""
        return (
            "".join(
                content.text
                for content in self.contents
                if isinstance(content, TextContent)
            )
            if self.contents
            else ""
        )

    @property
    def user_input_requests(self) -> list[FunctionApprovalRequestContent]:
        """Get all BaseUserInputRequest messages from the response."""
        return [
            content
            for content in self.contents
            if isinstance(content, FunctionApprovalRequestContent)
        ]

    def __str__(self) -> str:
        return self.text


class AgentRunResponse(BaseModel):
    """Represents the response to an Agent run request."""

    messages: list[ChatMessage] = Field(default_factory=list)
    response_id: str | None = None
    created_at: str | datetime | None = None
    usage_details: Any | None = None  # UsageDetails - avoiding circular import
    structured_output: Any | None = None
    additional_properties: dict[str, Any] | None = None
    raw_representation: Any | list[Any] | None = None

    @field_validator("messages", mode="before")
    @classmethod
    def validate_messages(cls, v):
        """Ensure messages is a list."""
        if v is None:
            return []
        if not isinstance(v, list):
            return [v]
        return v

    @property
    def text(self) -> str:
        """Get the concatenated text of all messages."""
        return "".join(msg.text for msg in self.messages) if self.messages else ""

    @property
    def user_input_requests(self) -> list[FunctionApprovalRequestContent]:
        """Get all BaseUserInputRequest messages from the response."""
        return [
            content
            for msg in self.messages
            for content in msg.contents
            if isinstance(content, FunctionApprovalRequestContent)
        ]

    @classmethod
    def from_agent_run_response_updates(
        cls,
        updates: Sequence[AgentRunResponseUpdate],
        *,
        output_format_type: type | None = None,
    ) -> "AgentRunResponse":
        """Joins multiple updates into a single AgentRunResponse."""
        response = cls(messages=[])

        for update in updates:
            # Process each update
            if update.contents:
                # Create or update message
                if (
                    not response.messages
                    or (
                        update.message_id
                        and response.messages[-1].message_id
                        and response.messages[-1].message_id != update.message_id
                    )
                    or (update.role and response.messages[-1].role != update.role)
                ):
                    # Create new message
                    from .agent_framework_enums import Role

                    message = ChatMessage(
                        role=update.role or Role.ASSISTANT,
                        contents=update.contents,
                        author_name=update.author_name,
                        message_id=update.message_id,
                    )
                    response.messages.append(message)
                else:
                    # Update last message
                    response.messages[-1].contents.extend(update.contents)
                    if update.author_name:
                        response.messages[-1].author_name = update.author_name
                    if update.message_id:
                        response.messages[-1].message_id = update.message_id

            # Update response metadata
            if update.response_id:
                response.response_id = update.response_id
            if update.created_at is not None:
                response.created_at = update.created_at
            if update.additional_properties is not None:
                if response.additional_properties is None:
                    response.additional_properties = {}
                response.additional_properties.update(update.additional_properties)

        return response

    @classmethod
    async def from_agent_response_generator(
        cls,
        updates,
        *,
        output_format_type: type | None = None,
    ) -> "AgentRunResponse":
        """Joins multiple updates from an async generator into a single AgentRunResponse."""
        response = cls(messages=[])

        async for update in updates:
            # Process each update (same logic as from_agent_run_response_updates)
            if update.contents:
                if (
                    not response.messages
                    or (
                        update.message_id
                        and response.messages[-1].message_id
                        and response.messages[-1].message_id != update.message_id
                    )
                    or (update.role and response.messages[-1].role != update.role)
                ):
                    from .agent_framework_enums import Role

                    message = ChatMessage(
                        role=update.role or Role.ASSISTANT,
                        contents=update.contents,
                        author_name=update.author_name,
                        message_id=update.message_id,
                    )
                    response.messages.append(message)
                else:
                    response.messages[-1].contents.extend(update.contents)
                    if update.author_name:
                        response.messages[-1].author_name = update.author_name
                    if update.message_id:
                        response.messages[-1].message_id = update.message_id

            if update.response_id:
                response.response_id = update.response_id
            if update.created_at is not None:
                response.created_at = update.created_at
            if update.additional_properties is not None:
                if response.additional_properties is None:
                    response.additional_properties = {}
                response.additional_properties.update(update.additional_properties)

        return response

    def __str__(self) -> str:
        return self.text

    def try_parse_value(self, output_format_type: type) -> None:
        """If there is a value, does nothing, otherwise tries to parse the text into the value."""
        if self.structured_output is None:
            try:
                import json

                # Parse JSON first, then validate with the model
                json_data = json.loads(self.text)
                if hasattr(output_format_type, "model_validate"):
                    model_validate_method = getattr(
                        output_format_type, "model_validate", None
                    )
                    if model_validate_method is not None and callable(
                        model_validate_method
                    ):
                        self.structured_output = model_validate_method(json_data)
                    else:
                        self.structured_output = output_format_type(**json_data)
                else:
                    self.structured_output = output_format_type(**json_data)
            except Exception:
                # If parsing fails, leave structured_output as None
                pass
