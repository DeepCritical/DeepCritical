"""
Base classes and protocols for code execution in DeepCritical.

Adapted from AG2 coding framework for use in DeepCritical's code execution system.
This module provides imports from the datatypes module for backward compatibility.
"""

from DeepResearch.src.datatypes.coding_base import (
    CodeBlock,
    CodeExecutionConfig,
    CodeExecutor,
    CodeExtractor,
    CodeResult,
    CommandLineCodeResult,
    IPythonCodeResult,
)

__all__ = [
    "CodeBlock",
    "CodeExecutionConfig",
    "CodeExecutor",
    "CodeExtractor",
    "CodeResult",
    "CommandLineCodeResult",
    "IPythonCodeResult",
]
