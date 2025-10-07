"""
Main agent framework types module.

This module provides a unified interface to all vendored agent framework types.
"""

# Content types
# Agent types
from .agent_framework_agent import (
    AgentRunResponse,
    AgentRunResponseUpdate,
)

# Chat types
from .agent_framework_chat import (
    ChatMessage,
    ChatResponse,
    ChatResponseUpdate,
)
from .agent_framework_content import (
    BaseContent,
    CitationAnnotation,
    Content,
    DataContent,
    ErrorContent,
    FunctionApprovalRequestContent,
    FunctionApprovalResponseContent,
    FunctionCallContent,
    FunctionResultContent,
    HostedFileContent,
    HostedVectorStoreContent,
    TextContent,
    TextReasoningContent,
    TextSpanRegion,
    UriContent,
    UsageContent,
    prepare_function_call_results,
)

# Enum types
from .agent_framework_enums import (
    FinishReason,
    Role,
    ToolMode,
)

# Options types
from .agent_framework_options import (
    ChatOptions,
)

# Usage types
from .agent_framework_usage import (
    UsageDetails,
)

# Re-export all types for easy importing
__all__ = [
    "AgentRunResponse",
    # Agent types
    "AgentRunResponseUpdate",
    "BaseContent",
    # Chat types
    "ChatMessage",
    # Options types
    "ChatOptions",
    "ChatResponse",
    "ChatResponseUpdate",
    "CitationAnnotation",
    "Content",
    "DataContent",
    "ErrorContent",
    "FinishReason",
    "FunctionApprovalRequestContent",
    "FunctionApprovalResponseContent",
    "FunctionCallContent",
    "FunctionResultContent",
    "HostedFileContent",
    "HostedVectorStoreContent",
    # Enum types
    "Role",
    "TextContent",
    "TextReasoningContent",
    # Content types
    "TextSpanRegion",
    "ToolMode",
    "UriContent",
    "UsageContent",
    # Usage types
    "UsageDetails",
    "prepare_function_call_results",
]
