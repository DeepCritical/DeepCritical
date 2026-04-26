"""
Datatypes for the critical literature review workflow.

The models in this module are the structured contract between retrieval,
screening, appraisal, synthesis, and the app-facing report payload.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

SourceMode = Literal["fixture", "openalex", "pubmed", "web", "mixed"]
ScreeningDecisionValue = Literal["include", "exclude", "maybe"]


class LiteratureReviewRequest(BaseModel):
    """Normalized request for a critical literature review."""

    question: str = Field(..., description="Research question or topic")
    mode: str = Field("review", description="Review mode")
    domain: str | None = Field(None, description="Optional domain hint")
    source_mode: SourceMode = Field("fixture", description="Retrieval backend")
    max_sources: int = Field(12, ge=1, description="Maximum candidate sources")
    include_preprints: bool = Field(True, description="Whether to include preprints")
    live_retrieval_enabled: bool = Field(
        False, description="Whether live network retrieval is allowed"
    )
    min_relevance_score: float = Field(
        0.35, ge=0.0, le=1.0, description="Screening threshold"
    )
    inclusion_criteria: list[str] = Field(default_factory=list)
    exclusion_criteria: list[str] = Field(default_factory=list)
    year_min: int | None = Field(None, description="Minimum publication year")
    fixture_path: str | None = Field(None, description="Optional fixture JSON path")

    @field_validator("question")
    @classmethod
    def _strip_question(cls, value: str) -> str:
        normalized = " ".join(value.split()).strip()
        if not normalized:
            msg = "Question cannot be empty"
            raise ValueError(msg)
        return normalized

    model_config = ConfigDict(json_schema_extra={})


class LiteratureSource(BaseModel):
    """Normalized source record used across retrieval backends."""

    source_id: str = Field(..., description="Stable source identifier")
    title: str = Field(..., description="Source title")
    authors: list[str] = Field(default_factory=list)
    year: int | None = Field(None)
    venue: str | None = Field(None)
    doi: str | None = Field(None)
    pmid: str | None = Field(None)
    openalex_id: str | None = Field(None)
    url: str | None = Field(None)
    abstract: str | None = Field(None)
    extracted_text: str | None = Field(None)
    source_backend: str = Field("fixture")
    publication_type: str | None = Field(None)
    is_preprint: bool = Field(False)
    keywords: list[str] = Field(default_factory=list)
    citation: str = Field("", description="Human-readable citation string")
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("title", "source_id")
    @classmethod
    def _strip_required_text(cls, value: str) -> str:
        normalized = " ".join(value.split()).strip()
        if not normalized:
            msg = "Required text fields must not be empty"
            raise ValueError(msg)
        return normalized

    model_config = ConfigDict(json_schema_extra={})


class LiteratureSearchPlan(BaseModel):
    """Search strategy derived from the review request."""

    question: str
    queries: list[str] = Field(default_factory=list)
    focus_terms: list[str] = Field(default_factory=list)
    source_mode: SourceMode = "fixture"
    inclusion_criteria: list[str] = Field(default_factory=list)
    exclusion_criteria: list[str] = Field(default_factory=list)
    max_sources: int = 12
    prompt_bundle: dict[str, str] = Field(default_factory=dict)

    model_config = ConfigDict(json_schema_extra={})


class ScreeningDecision(BaseModel):
    """Decision for a source after relevance screening."""

    source_id: str
    decision: ScreeningDecisionValue
    relevance_score: float = Field(..., ge=0.0, le=1.0)
    reasons: list[str] = Field(default_factory=list)

    model_config = ConfigDict(json_schema_extra={})


class EvidenceTableRow(BaseModel):
    """Evidence table row extracted from an included source."""

    source_id: str
    study_type: str
    population_or_domain: str
    method: str
    key_findings: list[str] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
    evidence_direction: str = Field("contextual")

    model_config = ConfigDict(json_schema_extra={})


class CriticalAppraisal(BaseModel):
    """Transparent critical appraisal for an included source."""

    source_id: str
    quality_score: float = Field(..., ge=0.0, le=1.0)
    confidence: float = Field(..., ge=0.0, le=1.0)
    bias_risks: list[str] = Field(default_factory=list)
    methodological_strengths: list[str] = Field(default_factory=list)
    methodological_limitations: list[str] = Field(default_factory=list)
    applicability_notes: list[str] = Field(default_factory=list)

    model_config = ConfigDict(json_schema_extra={})


class LiteratureGap(BaseModel):
    """Research gap surfaced during synthesis."""

    gap: str
    supporting_source_ids: list[str] = Field(default_factory=list)
    follow_up_question: str | None = None

    model_config = ConfigDict(json_schema_extra={})


class LiteratureSynthesis(BaseModel):
    """Synthesis of the screened and appraised evidence."""

    summary: str
    consensus_findings: list[str] = Field(default_factory=list)
    conflicting_findings: list[str] = Field(default_factory=list)
    themes: list[str] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
    gaps: list[LiteratureGap] = Field(default_factory=list)
    future_work: list[str] = Field(default_factory=list)

    model_config = ConfigDict(json_schema_extra={})


class LiteratureReviewReport(BaseModel):
    """Complete literature review report."""

    request: LiteratureReviewRequest
    search_plan: LiteratureSearchPlan
    included_sources: list[LiteratureSource] = Field(default_factory=list)
    excluded_sources: list[LiteratureSource] = Field(default_factory=list)
    screening_decisions: list[ScreeningDecision] = Field(default_factory=list)
    evidence_table: list[EvidenceTableRow] = Field(default_factory=list)
    appraisals: list[CriticalAppraisal] = Field(default_factory=list)
    synthesis: LiteratureSynthesis
    markdown_report: str
    diagnostics: dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(json_schema_extra={})


class LiteratureReviewWorkflowResult(BaseModel):
    """Top-level workflow result returned to apps and tests."""

    question: str
    mode: str = "review"
    report: LiteratureReviewReport | None = None
    markdown_report: str
    metadata: dict[str, Any] = Field(default_factory=dict)
    status: str = "success"
    warnings: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)

    model_config = ConfigDict(json_schema_extra={})


__all__ = [
    "CriticalAppraisal",
    "EvidenceTableRow",
    "LiteratureGap",
    "LiteratureReviewReport",
    "LiteratureReviewRequest",
    "LiteratureReviewWorkflowResult",
    "LiteratureSearchPlan",
    "LiteratureSource",
    "LiteratureSynthesis",
    "ScreeningDecision",
    "ScreeningDecisionValue",
    "SourceMode",
]
