"""
Datatypes for the hypothesis engine workflow.

These models provide the internal structured contracts used by the
hypothesis generation and test-planning workflow.
"""

from __future__ import annotations

import uuid
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


class HypothesisEvidence(BaseModel):
    """Evidence item used to ground hypothesis generation."""

    evidence_id: str = Field(
        default_factory=lambda: str(uuid.uuid4()), description="Evidence identifier"
    )
    source_id: str = Field(..., description="Stable source identifier")
    source_type: str = Field(..., description="Source type")
    title: str = Field(..., description="Evidence title")
    summary: str = Field(..., description="Evidence summary")
    relevance: float = Field(
        0.5, ge=0.0, le=1.0, description="Relative relevance of the evidence"
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict, description="Additional evidence metadata"
    )

    model_config = ConfigDict(json_schema_extra={})


class HypothesisScore(BaseModel):
    """Scoring dimensions for a hypothesis candidate."""

    novelty: float = Field(..., ge=0.0, le=1.0)
    evidence_support: float = Field(..., ge=0.0, le=1.0)
    testability: float = Field(..., ge=0.0, le=1.0)
    falsifiability: float = Field(..., ge=0.0, le=1.0)
    specificity: float = Field(..., ge=0.0, le=1.0)
    overall_score: float = Field(..., ge=0.0, le=1.0)
    score_justification: str = Field(..., description="Human-readable score summary")

    model_config = ConfigDict(json_schema_extra={})


class HypothesisCandidate(BaseModel):
    """Structured hypothesis candidate."""

    id: str = Field(..., description="Candidate identifier")
    statement: str = Field(..., description="Hypothesis statement")
    rationale: str = Field(..., description="Reasoning behind the hypothesis")
    assumptions: list[str] = Field(default_factory=list, description="Assumptions")
    predictions: list[str] = Field(default_factory=list, description="Predictions")
    supporting_evidence: list[str] = Field(
        default_factory=list, description="Supporting evidence identifiers"
    )
    counter_evidence: list[str] = Field(
        default_factory=list, description="Counter-evidence considerations"
    )
    keywords: list[str] = Field(default_factory=list, description="Key focus terms")
    score: HypothesisScore | None = Field(
        None, description="Ranking score attached after evaluation"
    )

    @field_validator("statement", "rationale")
    @classmethod
    def _strip_required_text(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            msg = "Text fields must not be empty"
            raise ValueError(msg)
        return normalized

    model_config = ConfigDict(json_schema_extra={})


class HypothesisTestPlan(BaseModel):
    """Validation plan for a hypothesis candidate."""

    hypothesis_id: str = Field(..., description="Linked hypothesis identifier")
    test_type: str = Field(..., description="Test class")
    method: str = Field(..., description="Validation method")
    required_inputs: list[str] = Field(
        default_factory=list, description="Required inputs"
    )
    success_criteria: list[str] = Field(
        default_factory=list, description="Signals of support"
    )
    failure_modes: list[str] = Field(
        default_factory=list, description="Signals of rejection or weak support"
    )

    model_config = ConfigDict(json_schema_extra={})


class HypothesisWorkflowResult(BaseModel):
    """Top-level internal workflow result."""

    question: str = Field(..., description="Original research question")
    mode: str = Field(..., description="Workflow mode")
    evidence: list[HypothesisEvidence] = Field(
        default_factory=list, description="Evidence bundle"
    )
    ranked_hypotheses: list[HypothesisCandidate] = Field(
        default_factory=list, description="Ranked hypotheses"
    )
    test_plans: list[HypothesisTestPlan] = Field(
        default_factory=list, description="Generated validation plans"
    )
    markdown_report: str = Field(..., description="User-facing markdown report")
    metadata: dict[str, Any] = Field(
        default_factory=dict, description="Execution metadata"
    )

    model_config = ConfigDict(json_schema_extra={})


__all__ = [
    "HypothesisCandidate",
    "HypothesisEvidence",
    "HypothesisScore",
    "HypothesisTestPlan",
    "HypothesisWorkflowResult",
]
