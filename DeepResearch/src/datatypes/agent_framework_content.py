"""
Vendored content types from agent_framework._types.

This module provides content types for AI agent interactions with minimal external dependencies.
"""

import json
import re
from typing import Any, Literal, Union

from pydantic import BaseModel, field_validator

# Constants
URI_PATTERN = re.compile(
    r"^data:(?P<media_type>[^;]+);base64,(?P<base64_data>[A-Za-z0-9+/=]+)$"
)

KNOWN_MEDIA_TYPES = [
    "application/json",
    "application/octet-stream",
    "application/pdf",
    "application/xml",
    "audio/mpeg",
    "audio/mp3",
    "audio/ogg",
    "audio/wav",
    "image/apng",
    "image/avif",
    "image/bmp",
    "image/gif",
    "image/jpeg",
    "image/png",
    "image/svg+xml",
    "image/tiff",
    "image/webp",
    "text/css",
    "text/csv",
    "text/html",
    "text/javascript",
    "text/plain",
    "text/plain;charset=UTF-8",
    "text/xml",
]


class TextSpanRegion(BaseModel):
    """Represents a region of text that has been annotated."""

    type: Literal["text_span"] = "text_span"
    start_index: int | None = None
    end_index: int | None = None


class CitationAnnotation(BaseModel):
    """Represents a citation annotation."""

    type: Literal["citation"] = "citation"
    title: str | None = None
    url: str | None = None
    file_id: str | None = None
    tool_name: str | None = None
    snippet: str | None = None
    annotated_regions: list[TextSpanRegion] | None = None


class BaseContent(BaseModel):
    """Base class for all content types."""

    annotations: list[CitationAnnotation] | None = None
    additional_properties: dict[str, Any] | None = None
    raw_representation: Any | None = None


class TextContent(BaseContent):
    """Represents text content in a chat."""

    type: Literal["text"] = "text"
    text: str

    def __add__(self, other: "TextContent") -> "TextContent":
        """Concatenate two TextContent instances."""
        if not isinstance(other, TextContent):
            msg = "Incompatible type"
            raise TypeError(msg)

        # Merge annotations
        annotations = []
        if self.annotations:
            annotations.extend(self.annotations)
        if other.annotations:
            annotations.extend(other.annotations)

        # Merge additional properties (self takes precedence)
        additional_properties = {}
        if other.additional_properties:
            additional_properties.update(other.additional_properties)
        if self.additional_properties:
            additional_properties.update(self.additional_properties)

        return TextContent(
            text=self.text + other.text,
            annotations=annotations if annotations else None,
            additional_properties=(
                additional_properties if additional_properties else None
            ),
        )


class TextReasoningContent(BaseContent):
    """Represents text reasoning content in a chat."""

    type: Literal["text_reasoning"] = "text_reasoning"
    text: str

    def __add__(self, other: "TextReasoningContent") -> "TextReasoningContent":
        """Concatenate two TextReasoningContent instances."""
        if not isinstance(other, TextReasoningContent):
            msg = "Incompatible type"
            raise TypeError(msg)

        # Merge annotations
        annotations = []
        if self.annotations:
            annotations.extend(self.annotations)
        if other.annotations:
            annotations.extend(other.annotations)

        # Merge additional properties (self takes precedence)
        additional_properties = {}
        if other.additional_properties:
            additional_properties.update(other.additional_properties)
        if self.additional_properties:
            additional_properties.update(self.additional_properties)

        return TextReasoningContent(
            text=self.text + other.text,
            annotations=annotations if annotations else None,
            additional_properties=(
                additional_properties if additional_properties else None
            ),
        )


class DataContent(BaseContent):
    """Represents binary data content with an associated media type."""

    type: Literal["data"] = "data"
    uri: str
    media_type: str | None = None

    @field_validator("uri", mode="before")
    @classmethod
    def validate_uri(cls, v):
        """Validate URI format and extract media type."""
        match = URI_PATTERN.match(v)
        if not match:
            msg = f"Invalid data URI format: {v}"
            raise ValueError(msg)
        media_type = match.group("media_type")
        if media_type not in KNOWN_MEDIA_TYPES:
            msg = f"Unknown media type: {media_type}"
            raise ValueError(msg)
        return v

    @field_validator("media_type", mode="before")
    @classmethod
    def extract_media_type(cls, v, info):
        """Extract media type from URI if not provided."""
        if v is None and info.data and "uri" in info.data:
            match = URI_PATTERN.match(info.data["uri"])
            if match:
                return match.group("media_type")
        return v

    def has_top_level_media_type(
        self, top_level_media_type: Literal["application", "audio", "image", "text"]
    ) -> bool:
        """Check if content has the specified top-level media type."""
        if self.media_type is None:
            return False

        slash_index = self.media_type.find("/")
        span = self.media_type[:slash_index] if slash_index >= 0 else self.media_type
        span = span.strip()
        return span.lower() == top_level_media_type.lower()


class UriContent(BaseContent):
    """Represents a URI content."""

    type: Literal["uri"] = "uri"
    uri: str
    media_type: str

    def has_top_level_media_type(
        self, top_level_media_type: Literal["application", "audio", "image", "text"]
    ) -> bool:
        """Check if content has the specified top-level media type."""
        if self.media_type is None:
            return False

        slash_index = self.media_type.find("/")
        span = self.media_type[:slash_index] if slash_index >= 0 else self.media_type
        span = span.strip()
        return span.lower() == top_level_media_type.lower()


class ErrorContent(BaseContent):
    """Represents an error."""

    type: Literal["error"] = "error"
    message: str | None = None
    error_code: str | None = None
    details: str | None = None

    def __str__(self) -> str:
        """Returns a string representation of the error."""
        return (
            f"Error {self.error_code}: {self.message}"
            if self.error_code
            else self.message or "Unknown error"
        )


class FunctionCallContent(BaseContent):
    """Represents a function call request."""

    type: Literal["function_call"] = "function_call"
    call_id: str
    name: str
    arguments: str | dict[str, Any] | None = None
    exception: Any | None = None  # Exception - avoiding Pydantic schema issues

    def parse_arguments(self) -> dict[str, Any] | None:
        """Parse arguments from string or return dict."""
        if isinstance(self.arguments, str):
            try:
                loaded = json.loads(self.arguments)
                if isinstance(loaded, dict):
                    return loaded
                return {"raw": loaded}
            except (json.JSONDecodeError, TypeError):
                return {"raw": self.arguments}
        return self.arguments


class FunctionResultContent(BaseContent):
    """Represents the result of a function call."""

    type: Literal["function_result"] = "function_result"
    call_id: str
    result: Any | None = None
    exception: Any | None = None  # Exception - avoiding Pydantic schema issues


class UsageContent(BaseContent):
    """Represents usage information associated with a chat request and response."""

    type: Literal["usage"] = "usage"
    details: Any  # UsageDetails - avoiding circular import


class HostedFileContent(BaseContent):
    """Represents a hosted file content."""

    type: Literal["hosted_file"] = "hosted_file"
    file_id: str


class HostedVectorStoreContent(BaseContent):
    """Represents a hosted vector store content."""

    type: Literal["hosted_vector_store"] = "hosted_vector_store"
    vector_store_id: str


class FunctionApprovalRequestContent(BaseContent):
    """Represents a request for user approval of a function call."""

    type: Literal["function_approval_request"] = "function_approval_request"
    id: str
    function_call: FunctionCallContent

    def create_response(self, approved: bool) -> "FunctionApprovalResponseContent":
        """Create a response for the function approval request."""
        return FunctionApprovalResponseContent(
            approved=approved,
            id=self.id,
            function_call=self.function_call,
            additional_properties=self.additional_properties,
        )


class FunctionApprovalResponseContent(BaseContent):
    """Represents a response for user approval of a function call."""

    type: Literal["function_approval_response"] = "function_approval_response"
    id: str
    approved: bool
    function_call: FunctionCallContent


# Union type for all content types
Content = Union[
    TextContent,
    DataContent,
    TextReasoningContent,
    UriContent,
    FunctionCallContent,
    FunctionResultContent,
    ErrorContent,
    UsageContent,
    HostedFileContent,
    HostedVectorStoreContent,
    FunctionApprovalRequestContent,
    FunctionApprovalResponseContent,
]


def prepare_function_call_results(
    content: Content | Any | list[Content | Any],
) -> str:
    """Prepare the values of the function call results."""
    if isinstance(content, BaseContent):
        # For BaseContent objects, serialize to JSON
        return json.dumps(
            content.dict(exclude={"raw_representation", "additional_properties"})
        )

    if isinstance(content, list):
        return json.dumps([prepare_function_call_results(item) for item in content])

    if isinstance(content, dict):
        return json.dumps(
            {k: prepare_function_call_results(v) for k, v in content.items()}
        )

    if isinstance(content, str):
        return content

    # fallback
    return json.dumps(content)
