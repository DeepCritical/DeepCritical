"""
AG2-compatible types for code execution and content handling.

This module provides type definitions adapted from AG2 for use in DeepCritical's
code execution and content processing capabilities.
"""

from typing import Any, Literal, TypedDict

# Message content types for compatibility with AG2
MessageContentType = str | list[dict[str, Any] | str] | None


class UserMessageTextContentPart(TypedDict):
    """Represents a text content part of a user message."""

    type: Literal["text"]
    """The type of the content part. Always "text" for text content parts."""
    text: str
    """The text content of the part."""


class UserMessageImageContentPart(TypedDict):
    """Represents an image content part of a user message."""

    type: Literal["image_url"]
    """The type of the content part. Always "image_url" for image content parts."""
    # Ignoring the other "detail param for now
    image_url: dict[Literal["url"], str]
    """The URL of the image."""


def content_str(
    content: str
    | list[UserMessageTextContentPart | UserMessageImageContentPart]
    | None,
) -> str:
    """Converts the `content` field of an OpenAI message into a string format.

    This function processes content that may be a string, a list of mixed text and image URLs, or None,
    and converts it into a string. Text is directly appended to the result string, while image URLs are
    represented by a placeholder image token. If the content is None, an empty string is returned.

    Args:
        content: The content to be processed. Can be a string, a list of dictionaries representing text and image URLs, or None.

    Returns:
        str: A string representation of the input content. Image URLs are replaced with an image token.

    Note:
    - The function expects each dictionary in the list to have a "type" key that is either "text" or "image_url".
      For "text" type, the "text" key's value is appended to the result. For "image_url", an image token is appended.
    - This function is useful for handling content that may include both text and image references, especially
      in contexts where images need to be represented as placeholders.
    """
    if content is None:
        return ""
    if isinstance(content, str):
        return content
    if not isinstance(content, list):
        raise TypeError(f"content must be None, str, or list, but got {type(content)}")

    rst = []
    for item in content:
        if not isinstance(item, dict):
            raise TypeError(
                "Wrong content format: every element should be dict if the content is a list."
            )
        assert "type" in item, (
            "Wrong content format. Missing 'type' key in content's dict."
        )
        if item["type"] in ["text", "input_text"]:
            rst.append(item["text"])
        elif item["type"] in ["image_url", "input_image"]:
            rst.append("<image>")
        elif item["type"] in ["function", "tool_call", "tool_calls"]:
            rst.append(
                "<function>" if "name" not in item else f"<function: {item['name']}>"
            )
        else:
            raise ValueError(
                f"Wrong content format: unknown type {item['type']} within the content"
            )
    return "\n".join(rst)
