"""
Tool specifications utilities for DeepCritical research workflows.

This module re-exports tool specification types from the datatypes module
for backward compatibility and easier access.
"""

from DeepResearch.src.datatypes.tool_specs import (
    ToolCategory,
    ToolInput,
    ToolOutput,
    ToolSpec,
)

__all__ = [
    "ToolCategory",
    "ToolInput",
    "ToolOutput",
    "ToolSpec",
]
