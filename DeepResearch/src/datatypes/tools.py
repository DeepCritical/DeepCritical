"""
Core tool data types for DeepCritical research workflows.

This module defines the fundamental types and base classes for tool execution
in the PRIME ecosystem, including tool specifications, execution results,
and tool runners.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

from .tool_specs import ToolCategory, ToolSpec


@dataclass
class ToolMetadata:
    """Metadata for registered tools."""

    name: str
    category: ToolCategory
    description: str
    version: str = "1.0.0"
    tags: list[str] = field(default_factory=list)


@dataclass
class ExecutionResult:
    """Result of tool execution."""

    success: bool
    data: dict[str, Any] = field(default_factory=dict)
    error: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


class ToolRunner(ABC):
    """Abstract base class for tool runners."""

    def __init__(self, tool_spec: ToolSpec):
        self.tool_spec = tool_spec

    @abstractmethod
    def run(self, parameters: dict[str, Any]) -> ExecutionResult:
        """Execute the tool with given parameters."""

    def validate_inputs(self, parameters: dict[str, Any]) -> ExecutionResult:
        """Validate input parameters against tool specification."""
        for param_name, expected_type in self.tool_spec.input_schema.items():
            if param_name not in parameters:
                return ExecutionResult(
                    success=False, error=f"Missing required parameter: {param_name}"
                )

            if not self._validate_type(parameters[param_name], expected_type):
                return ExecutionResult(
                    success=False,
                    error=f"Invalid type for parameter '{param_name}': expected {expected_type}",
                )

        return ExecutionResult(success=True)

    def _validate_type(self, value: Any, expected_type: str) -> bool:
        """Validate that value matches expected type."""
        type_mapping = {
            "string": str,
            "int": int,
            "float": float,
            "list": list,
            "dict": dict,
            "bool": bool,
        }

        expected_python_type = type_mapping.get(expected_type, Any)
        return isinstance(value, expected_python_type)


class MockToolRunner(ToolRunner):
    """Mock implementation of tool runner for testing."""

    def run(self, parameters: dict[str, Any]) -> ExecutionResult:
        """Mock execution that returns simulated results."""
        # Validate inputs first
        validation = self.validate_inputs(parameters)
        if not validation.success:
            return validation

        # Generate mock results based on tool type
        if self.tool_spec.category == ToolCategory.KNOWLEDGE_QUERY:
            return self._mock_knowledge_query(parameters)
        if self.tool_spec.category == ToolCategory.SEQUENCE_ANALYSIS:
            return self._mock_sequence_analysis(parameters)
        if self.tool_spec.category == ToolCategory.STRUCTURE_PREDICTION:
            return self._mock_structure_prediction(parameters)
        if self.tool_spec.category == ToolCategory.MOLECULAR_DOCKING:
            return self._mock_molecular_docking(parameters)
        if self.tool_spec.category == ToolCategory.DE_NOVO_DESIGN:
            return self._mock_de_novo_design(parameters)
        if self.tool_spec.category == ToolCategory.FUNCTION_PREDICTION:
            return self._mock_function_prediction(parameters)
        return ExecutionResult(
            success=True,
            data={"result": "mock_execution_completed"},
            metadata={"tool": self.tool_spec.name, "mock": True},
        )

    def _mock_knowledge_query(self, parameters: dict[str, Any]) -> ExecutionResult:
        """Mock knowledge query results."""
        query = parameters.get("query", "")
        return ExecutionResult(
            success=True,
            data={
                "sequences": [
                    "MKTVRQERLKSIVRILERSKEPVSGAQLAEELSVSRQVIVQDIAYLRSLGYNIVATPRGYVLAGG"
                ],
                "annotations": {
                    "organism": "Homo sapiens",
                    "function": "Protein function annotation",
                    "confidence": 0.95,
                },
            },
            metadata={"query": query, "mock": True},
        )

    def _mock_sequence_analysis(self, parameters: dict[str, Any]) -> ExecutionResult:
        """Mock sequence analysis results."""
        sequence = parameters.get("sequence", "")
        return ExecutionResult(
            success=True,
            data={
                "hits": [
                    {
                        "id": "P12345",
                        "description": "Similar protein",
                        "e_value": 1e-10,
                    },
                    {
                        "id": "Q67890",
                        "description": "Another similar protein",
                        "e_value": 1e-8,
                    },
                ],
                "e_values": [1e-10, 1e-8],
                "domains": [{"name": "PF00001", "start": 10, "end": 50, "score": 25.5}],
            },
            metadata={"sequence_length": len(sequence), "mock": True},
        )

    def _mock_structure_prediction(self, parameters: dict[str, Any]) -> ExecutionResult:
        """Mock structure prediction results."""
        sequence = parameters.get("sequence", "")
        return ExecutionResult(
            success=True,
            data={
                "structure": "ATOM      1  N   ALA A   1      20.154  16.967  23.862  1.00 11.18           N",
                "confidence": {
                    "plddt": 85.5,
                    "global_confidence": 0.89,
                    "per_residue_confidence": [0.9, 0.85, 0.88, 0.92],
                },
            },
            metadata={"sequence_length": len(sequence), "mock": True},
        )

    def _mock_molecular_docking(self, parameters: dict[str, Any]) -> ExecutionResult:
        """Mock molecular docking results."""
        return ExecutionResult(
            success=True,
            data={
                "poses": [
                    {"id": 1, "binding_affinity": -7.2, "rmsd": 1.5},
                    {"id": 2, "binding_affinity": -6.8, "rmsd": 2.1},
                ],
                "binding_affinity": -7.2,
                "confidence": 0.75,
            },
            metadata={"num_poses": 2, "mock": True},
        )

    def _mock_de_novo_design(self, parameters: dict[str, Any]) -> ExecutionResult:
        """Mock de novo design results."""
        num_designs = parameters.get("num_designs", 1)
        return ExecutionResult(
            success=True,
            data={
                "structures": [
                    f"DESIGNED_STRUCTURE_{i + 1}.pdb" for i in range(num_designs)
                ],
                "sequences": [
                    f"MKTVRQERLKSIVRILERSKEPVSGAQLAEELSVSRQVIVQDIAYLRSLGYNIVATPRGYVLAGG_{i + 1}"
                    for i in range(num_designs)
                ],
                "confidence": 0.82,
            },
            metadata={"num_designs": num_designs, "mock": True},
        )

    def _mock_function_prediction(self, parameters: dict[str, Any]) -> ExecutionResult:
        """Mock function prediction results."""
        return ExecutionResult(
            success=True,
            data={
                "function": "Enzyme activity",
                "confidence": 0.88,
                "predictions": {
                    "catalytic_activity": 0.92,
                    "binding_activity": 0.75,
                    "structural_stability": 0.85,
                },
            },
            metadata={"mock": True},
        )
