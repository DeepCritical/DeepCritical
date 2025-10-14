"""Shared tool specifications and types for the PRIME ecosystem."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class ToolCategory(Enum):
    """Tool categories in the PRIME ecosystem."""

    KNOWLEDGE_QUERY = "knowledge_query"
    SEARCH = "search"
    ANALYSIS = "analysis"
    SEQUENCE_ANALYSIS = "sequence_analysis"
    STRUCTURE_PREDICTION = "structure_prediction"
    MOLECULAR_DOCKING = "molecular_docking"
    DE_NOVO_DESIGN = "de_novo_design"
    FUNCTION_PREDICTION = "function_prediction"


@dataclass
class ToolInput:
    """Input specification for a tool."""

    name: str
    type: str
    required: bool = True
    description: str = ""
    default_value: Any = None


@dataclass
class ToolOutput:
    """Output specification for a tool."""

    name: str
    type: str
    description: str = ""


@dataclass
class ToolSpec:
    """Specification for a tool in the PRIME ecosystem."""

    name: str
    category: ToolCategory
    input_schema: dict[str, Any]
    output_schema: dict[str, Any]
    dependencies: list[str] = field(default_factory=list)
    parameters: dict[str, Any] = field(default_factory=dict)
    success_criteria: dict[str, Any] = field(default_factory=dict)
