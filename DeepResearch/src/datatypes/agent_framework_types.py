"""
Main agent framework types module.

This module provides a unified interface to all vendored agent framework types.
"""

# Content types
from .agent_framework_content import (
    TextSpanRegion,
    CitationAnnotation,
    BaseContent,
    TextContent,
    TextReasoningContent,
    DataContent,
    UriContent,
    ErrorContent,
    FunctionCallContent,
    FunctionResultContent,
    UsageContent,
    HostedFileContent,
    HostedVectorStoreContent,
    FunctionApprovalRequestContent,
    FunctionApprovalResponseContent,
    Content,
    prepare_function_call_results,
)

# Usage types
from .agent_framework_usage import (
    UsageDetails,
)

# Enum types
from .agent_framework_enums import (
    Role,
    FinishReason,
    ToolMode,
)

# Chat types
from .agent_framework_chat import (
    ChatMessage,
    ChatResponseUpdate,
    ChatResponse,
)

# Agent types
from .agent_framework_agent import (
    AgentRunResponseUpdate,
    AgentRunResponse,
)

# Options types
from .agent_framework_options import (
    ChatOptions,
)

# Re-export all types for easy importing
__all__ = [
    # Content types
    "TextSpanRegion",
    "CitationAnnotation",
    "BaseContent",
    "TextContent",
    "TextReasoningContent",
    "DataContent",
    "UriContent",
    "ErrorContent",
    "FunctionCallContent",
    "FunctionResultContent",
    "UsageContent",
    "HostedFileContent",
    "HostedVectorStoreContent",
    "FunctionApprovalRequestContent",
    "FunctionApprovalResponseContent",
    "Content",
    "prepare_function_call_results",
    # Usage types
    "UsageDetails",
    # Enum types
    "Role",
    "FinishReason",
    "ToolMode",
    # Chat types
    "ChatMessage",
    "ChatResponseUpdate",
    "ChatResponse",
    # Agent types
    "AgentRunResponseUpdate",
    "AgentRunResponse",
    # Options types
    "ChatOptions",
]
