"""
Vendored chat types from agent_framework._types.

This module provides chat message and response types for AI agent interactions.
"""

from collections.abc import Sequence
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field, field_validator

from .agent_framework_content import Content, TextContent
from .agent_framework_enums import FinishReason, Role


class ChatMessage(BaseModel):
    """Represents a chat message."""

    role: Role | str
    contents: list[Content] = Field(default_factory=list)
    author_name: str | None = None
    message_id: str | None = None
    additional_properties: dict[str, Any] | None = None
    raw_representation: Any | None = None

    @field_validator("role", mode="before")
    @classmethod
    def validate_role(cls, v):
        """Convert string role to Role object."""
        if isinstance(v, str):
            return Role(value=v)
        return v

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
        """Returns the text content of the message."""
        return " ".join(
            content.text
            for content in self.contents
            if isinstance(content, TextContent)
        )


class ChatResponseUpdate(BaseModel):
    """Represents a single streaming response chunk from a ChatClient."""

    contents: list[Content] = Field(default_factory=list)
    role: Role | str | None = None
    author_name: str | None = None
    response_id: str | None = None
    message_id: str | None = None
    conversation_id: str | None = None
    model_id: str | None = None
    created_at: str | datetime | None = None
    finish_reason: FinishReason | str | None = None
    additional_properties: dict[str, Any] | None = None
    raw_representation: Any | None = None

    @field_validator("role", mode="before")
    @classmethod
    def validate_role(cls, v):
        """Convert string role to Role object."""
        if isinstance(v, str):
            return Role(value=v)
        return v

    @field_validator("finish_reason", mode="before")
    @classmethod
    def validate_finish_reason(cls, v):
        """Convert string finish reason to FinishReason object."""
        if isinstance(v, str):
            return FinishReason(value=v)
        return v

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
        """Returns the concatenated text of all contents in the update."""
        return "".join(
            content.text
            for content in self.contents
            if isinstance(content, TextContent)
        )

    def with_(
        self, contents: list[Content] | None = None, message_id: str | None = None
    ) -> "ChatResponseUpdate":
        """Returns a new instance with the specified contents and message_id."""
        if contents is None:
            contents = []

        return ChatResponseUpdate(
            contents=self.contents + contents,
            role=self.role,
            author_name=self.author_name,
            response_id=self.response_id,
            message_id=message_id or self.message_id,
            conversation_id=self.conversation_id,
            model_id=self.model_id,
            created_at=self.created_at,
            finish_reason=self.finish_reason,
            additional_properties=self.additional_properties,
            raw_representation=self.raw_representation,
        )


class ChatResponse(BaseModel):
    """Represents the response to a chat request."""

    messages: list[ChatMessage] = Field(default_factory=list)
    response_id: str | None = None
    conversation_id: str | None = None
    model_id: str | None = None
    created_at: str | datetime | None = None
    finish_reason: FinishReason | str | None = None
    usage_details: Any | None = None  # UsageDetails - avoiding circular import
    structured_output: Any | None = None
    additional_properties: dict[str, Any] | None = None
    raw_representation: Any | list[Any] | None = None

    @field_validator("finish_reason", mode="before")
    @classmethod
    def validate_finish_reason(cls, v):
        """Convert string finish reason to FinishReason object."""
        if isinstance(v, str):
            return FinishReason(value=v)
        return v

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
        """Returns the concatenated text of all messages in the response."""
        return (
            "\n".join(
                message.text
                for message in self.messages
                if isinstance(message, ChatMessage)
            )
        ).strip()

    def __str__(self) -> str:
        return self.text

    @classmethod
    def from_chat_response_updates(
        cls,
        updates: Sequence[ChatResponseUpdate],
        *,
        output_format_type: type | None = None,
    ) -> "ChatResponse":
        """Joins multiple updates into a single ChatResponse."""
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
            if update.finish_reason is not None:
                response.finish_reason = update.finish_reason
            if update.conversation_id is not None:
                response.conversation_id = update.conversation_id
            if update.model_id is not None:
                response.model_id = update.model_id
            if update.additional_properties is not None:
                if response.additional_properties is None:
                    response.additional_properties = {}
                response.additional_properties.update(update.additional_properties)

        return response

    @classmethod
    async def from_chat_response_generator(
        cls,
        updates,
        *,
        output_format_type: type | None = None,
    ) -> "ChatResponse":
        """Joins multiple updates from an async generator into a single ChatResponse."""
        response = cls(messages=[])

        async for update in updates:
            # Process each update (same logic as from_chat_response_updates)
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
            if update.finish_reason is not None:
                response.finish_reason = update.finish_reason
            if update.conversation_id is not None:
                response.conversation_id = update.conversation_id
            if update.model_id is not None:
                response.model_id = update.model_id
            if update.additional_properties is not None:
                if response.additional_properties is None:
                    response.additional_properties = {}
                response.additional_properties.update(update.additional_properties)

        return response

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
