"""
Code sandbox tool implementation for DeepCritical research workflows.

This module provides the main implementation for code sandbox tools,
importing the necessary data types and prompts from their respective modules.
"""

from __future__ import annotations

# Import the actual tool implementation from datatypes
from DeepResearch.src.datatypes.code_sandbox import CodeSandboxTool

# Re-export for convenience
__all__ = ["CodeSandboxTool"]
