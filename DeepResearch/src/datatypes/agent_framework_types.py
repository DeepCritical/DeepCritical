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
