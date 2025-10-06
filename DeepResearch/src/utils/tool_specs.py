"""
Tool specifications utilities for DeepCritical research workflows.

This module re-exports tool specification types from the datatypes module
for backward compatibility and easier access.
"""

from ..datatypes.tool_specs import (
    ToolSpec,
    ToolCategory,
    ToolInput,
    ToolOutput,
)

__all__ = [
    "ToolSpec",
    "ToolCategory",
    "ToolInput",
    "ToolOutput",
]
