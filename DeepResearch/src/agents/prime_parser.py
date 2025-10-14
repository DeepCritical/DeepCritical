from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any


class ScientificIntent(Enum):
    """Scientific intent categories for protein engineering tasks."""

    PROTEIN_DESIGN = "protein_design"
    BINDING_ANALYSIS = "binding_analysis"
    STRUCTURE_PREDICTION = "structure_prediction"
    FUNCTION_PREDICTION = "function_prediction"
    SEQUENCE_ANALYSIS = "sequence_analysis"
    MOLECULAR_DOCKING = "molecular_docking"
    DE_NOVO_DESIGN = "de_novo_design"
    CLASSIFICATION = "classification"
    REGRESSION = "regression"
    INTERACTION_PREDICTION = "interaction_prediction"


class DataType(Enum):
    """Data types for input/output validation."""

    SEQUENCE = "sequence"
    STRUCTURE = "structure"
    INTERACTION = "interaction"
    CLASSIFICATION = "classification"
    REGRESSION = "regression"
    FILE = "file"
    URL = "url"
    TEXT = "text"


@dataclass
class StructuredProblem:
    """Structured representation of a research problem."""

    intent: ScientificIntent
    input_data: dict[str, Any]
    output_requirements: dict[str, Any]
    constraints: list[str]
    success_criteria: list[str]
    domain: str
    complexity: str  # "simple", "moderate", "complex"


@dataclass
class QueryParser:
    """PRIME Query Parser agent for semantic and syntactic analysis."""

    def parse(self, query: str) -> StructuredProblem:
        """
        Parse natural language query into structured research problem.

        Performs:
        1. Semantic analysis to determine scientific intent
        2. Syntactic analysis to validate input/output formats
        3. Problem structuring for downstream planning
        """
        # Semantic analysis - determine scientific intent
        intent = self._analyze_semantic_intent(query)

        # Syntactic analysis - extract and validate data formats
        input_data, output_requirements = self._analyze_syntactic_formats(query)

        # Extract constraints and success criteria
        constraints = self._extract_constraints(query)
        success_criteria = self._extract_success_criteria(query)

        # Determine domain and complexity
        domain = self._determine_domain(query)
        complexity = self._assess_complexity(query, intent)

        return StructuredProblem(
            intent=intent,
            input_data=input_data,
            output_requirements=output_requirements,
            constraints=constraints,
            success_criteria=success_criteria,
            domain=domain,
            complexity=complexity,
        )

    def _analyze_semantic_intent(self, query: str) -> ScientificIntent:
        """Analyze query to determine scientific intent."""
        query_lower = query.lower()

        # Intent detection based on keywords and patterns
        if any(
            word in query_lower for word in ["design", "create", "generate", "novel"]
        ):
            if "antibody" in query_lower or "therapeutic" in query_lower:
                return ScientificIntent.DE_NOVO_DESIGN
            return ScientificIntent.PROTEIN_DESIGN

        if any(word in query_lower for word in ["bind", "interaction", "docking"]):
            return ScientificIntent.BINDING_ANALYSIS

        if any(word in query_lower for word in ["structure", "fold", "3d"]):
            return ScientificIntent.STRUCTURE_PREDICTION

        if any(word in query_lower for word in ["function", "activity", "catalytic"]):
            return ScientificIntent.FUNCTION_PREDICTION

        if any(
            word in query_lower for word in ["classify", "classification", "category"]
        ):
            return ScientificIntent.CLASSIFICATION

        if any(word in query_lower for word in ["predict", "regression", "value"]):
            return ScientificIntent.REGRESSION

        # Default to sequence analysis for general queries
        return ScientificIntent.SEQUENCE_ANALYSIS

    def _analyze_syntactic_formats(
        self, query: str
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        """Extract and validate input/output data formats."""
        input_data = {}
        output_requirements = {}

        # Extract input data types and formats
        if "sequence" in query.lower():
            input_data["sequence"] = {"type": DataType.SEQUENCE, "format": "fasta"}

        if "structure" in query.lower():
            input_data["structure"] = {"type": DataType.STRUCTURE, "format": "pdb"}

        if "file" in query.lower():
            input_data["file"] = {"type": DataType.FILE, "format": "auto"}

        # Determine output requirements
        if "classifier" in query.lower() or "classification" in query.lower():
            output_requirements["classification"] = {"type": DataType.CLASSIFICATION}

        if "binding" in query.lower() or "affinity" in query.lower():
            output_requirements["binding"] = {"type": DataType.INTERACTION}

        if "structure" in query.lower():
            output_requirements["structure"] = {"type": DataType.STRUCTURE}

        return input_data, output_requirements

    def _extract_constraints(self, query: str) -> list[str]:
        """Extract constraints from the query."""
        constraints = []
        query_lower = query.lower()

        if "stable" in query_lower:
            constraints.append("stability_requirement")

        if "specific" in query_lower or "selective" in query_lower:
            constraints.append("specificity_requirement")

        if "fast" in query_lower or "efficient" in query_lower:
            constraints.append("efficiency_requirement")

        if "human" in query_lower:
            constraints.append("human_compatibility")

        return constraints

    def _extract_success_criteria(self, query: str) -> list[str]:
        """Extract success criteria from the query."""
        criteria = []
        query_lower = query.lower()

        if "accuracy" in query_lower:
            criteria.append("high_accuracy")

        if "binding" in query_lower:
            criteria.append("strong_binding")

        if "stable" in query_lower:
            criteria.append("structural_stability")

        return criteria

    def _determine_domain(self, query: str) -> str:
        """Determine the biological domain."""
        query_lower = query.lower()

        if any(
            word in query_lower
            for word in ["antibody", "immunoglobulin", "therapeutic"]
        ):
            return "immunology"

        if any(word in query_lower for word in ["enzyme", "catalytic", "substrate"]):
            return "enzymology"

        if any(word in query_lower for word in ["receptor", "ligand", "signaling"]):
            return "cell_biology"

        return "general_protein"

    def _assess_complexity(self, query: str, intent: ScientificIntent) -> str:
        """Assess the complexity of the task."""
        complexity_indicators = {
            "simple": ["analyze", "predict", "classify"],
            "moderate": ["design", "optimize", "compare"],
            "complex": ["de novo", "multi-step", "pipeline", "workflow"],
        }

        query_lower = query.lower()

        for level, indicators in complexity_indicators.items():
            if any(indicator in query_lower for indicator in indicators):
                return level

        # Default based on intent
        if intent in [
            ScientificIntent.DE_NOVO_DESIGN,
            ScientificIntent.MOLECULAR_DOCKING,
        ]:
            return "complex"
        if intent in [
            ScientificIntent.PROTEIN_DESIGN,
            ScientificIntent.BINDING_ANALYSIS,
        ]:
            return "moderate"
        return "simple"


def parse_query(query: str) -> StructuredProblem:
    """Convenience function to parse a query."""
    parser = QueryParser()
    return parser.parse(query)
