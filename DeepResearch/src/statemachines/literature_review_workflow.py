"""
Critical literature review workflow.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

try:
    from pydantic_graph import BaseNode, End, Graph, GraphRunContext
except ImportError:
    from typing import Generic, TypeVar

    T = TypeVar("T")

    class Graph:
        def __init__(self, *args, **kwargs):
            pass

    class BaseNode(Generic[T]):
        def __init__(self, *args, **kwargs):
            pass

    class End:
        def __init__(self, *args, **kwargs):
            pass

    class GraphRunContext:
        def __init__(self, *args, **kwargs):
            pass


from DeepResearch.src.agents.literature_review_agents import (
    LiteratureCurationAgent,
    LiteratureSearchPlannerAgent,
    LiteratureSynthesisAgent,
)
from DeepResearch.src.datatypes.literature_review import (
    CriticalAppraisal,
    EvidenceTableRow,
    LiteratureReviewReport,
    LiteratureReviewRequest,
    LiteratureReviewWorkflowResult,
    LiteratureSearchPlan,
    LiteratureSource,
    LiteratureSynthesis,
    ScreeningDecision,
)
from DeepResearch.src.utils.execution_status import ExecutionStatus


def _section_get(section: Any, key: str, default: Any = None) -> Any:
    if section is None:
        return default
    if isinstance(section, dict):
        return section.get(key, default)
    getter = getattr(section, "get", None)
    if callable(getter):
        try:
            return getter(key, default)
        except Exception:
            pass
    return getattr(section, key, default)


def _as_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [value]
    return [str(item) for item in value]


class LiteratureReviewWorkflowState(BaseModel):
    """State for the critical literature review workflow."""

    question: str = Field(..., description="Review question")
    mode: str = Field("review", description="Workflow mode")
    source_mode: str = Field("fixture", description="Retrieval source mode")
    max_sources: int = Field(12, description="Maximum candidate sources")
    include_preprints: bool = Field(True)
    live_retrieval_enabled: bool = Field(False)
    min_relevance_score: float = Field(0.35)
    inclusion_criteria: list[str] = Field(default_factory=list)
    exclusion_criteria: list[str] = Field(default_factory=list)
    year_min: int | None = None
    fixture_path: str | None = None
    max_queries: int = 3
    config: Any | None = None
    request: LiteratureReviewRequest | None = None
    search_plan: LiteratureSearchPlan | None = None
    candidate_sources: list[LiteratureSource] = Field(default_factory=list)
    unique_sources: list[LiteratureSource] = Field(default_factory=list)
    included_sources: list[LiteratureSource] = Field(default_factory=list)
    excluded_sources: list[LiteratureSource] = Field(default_factory=list)
    screening_decisions: list[ScreeningDecision] = Field(default_factory=list)
    evidence_table: list[EvidenceTableRow] = Field(default_factory=list)
    appraisals: list[CriticalAppraisal] = Field(default_factory=list)
    synthesis: LiteratureSynthesis | None = None
    report: LiteratureReviewReport | None = None
    markdown_report: str = ""
    duplicate_diagnostics: list[dict[str, Any]] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
    warnings: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
    status: ExecutionStatus = Field(ExecutionStatus.PENDING)

    model_config = ConfigDict(arbitrary_types_allowed=True, json_schema_extra={})


def _mark_failure(
    state: LiteratureReviewWorkflowState,
    message: str,
    *,
    stage: str,
) -> None:
    state.errors.append(message)
    state.metadata["failure_stage"] = stage
    state.metadata["error_summary"] = message
    state.status = ExecutionStatus.FAILED


def _build_failure_payload(state: LiteratureReviewWorkflowState) -> dict[str, Any]:
    error_summary = state.errors[-1] if state.errors else "Unknown error"
    metadata = dict(state.metadata)
    metadata.setdefault("failure_stage", "unknown")
    metadata["error_summary"] = error_summary
    metadata["status"] = state.status.value
    return {
        "question": state.question,
        "mode": state.mode,
        "report": None,
        "markdown_report": f"Literature review workflow failed: {error_summary}",
        "metadata": metadata,
        "status": state.status.value,
        "warnings": state.warnings,
        "errors": state.errors,
    }


class ParseLiteratureReviewRequest(BaseNode[LiteratureReviewWorkflowState]):  # type: ignore[unsupported-base]
    """Validate and normalize workflow inputs."""

    async def run(
        self, ctx: GraphRunContext[LiteratureReviewWorkflowState]
    ) -> PlanSearchStrategy | End[dict[str, Any]]:
        state = ctx.state
        question = " ".join(state.question.split()).strip()
        if not question:
            _mark_failure(state, "Question cannot be empty", stage="request_parsing")
            return End(_build_failure_payload(state))

        state.question = question
        state.max_sources = max(1, min(int(state.max_sources or 12), 50))
        state.max_queries = max(1, min(int(state.max_queries or 3), 5))
        state.min_relevance_score = max(0.0, min(float(state.min_relevance_score), 1.0))
        if state.source_mode != "fixture" and not state.live_retrieval_enabled:
            _mark_failure(
                state,
                f"source_mode '{state.source_mode}' requires live_retrieval_enabled=true",
                stage="request_parsing",
            )
            return End(_build_failure_payload(state))

        try:
            state.request = LiteratureReviewRequest(
                question=state.question,
                mode=state.mode,
                source_mode=state.source_mode,  # type: ignore[arg-type]
                max_sources=state.max_sources,
                include_preprints=state.include_preprints,
                live_retrieval_enabled=state.live_retrieval_enabled,
                min_relevance_score=state.min_relevance_score,
                inclusion_criteria=state.inclusion_criteria,
                exclusion_criteria=state.exclusion_criteria,
                year_min=state.year_min,
                fixture_path=state.fixture_path,
            )
        except Exception as exc:
            _mark_failure(
                state,
                f"Literature review request validation failed: {exc!s}",
                stage="request_parsing",
            )
            return End(_build_failure_payload(state))

        state.status = ExecutionStatus.RUNNING
        return PlanSearchStrategy()


class PlanSearchStrategy(BaseNode[LiteratureReviewWorkflowState]):  # type: ignore[unsupported-base]
    """Plan search queries and criteria."""

    async def run(
        self, ctx: GraphRunContext[LiteratureReviewWorkflowState]
    ) -> RetrieveCandidateSources | LiteratureReviewError:
        state = ctx.state
        try:
            agent = LiteratureSearchPlannerAgent()
            state.search_plan = agent.plan(
                question=state.question,
                mode=state.mode,
                source_mode=state.source_mode,
                max_queries=state.max_queries,
                max_sources=state.max_sources,
                inclusion_criteria=state.inclusion_criteria,
                exclusion_criteria=state.exclusion_criteria,
            )
        except Exception as exc:
            _mark_failure(
                state,
                f"Literature search planning failed: {exc!s}",
                stage="search_planning",
            )
            return LiteratureReviewError()
        return RetrieveCandidateSources()


class RetrieveCandidateSources(BaseNode[LiteratureReviewWorkflowState]):  # type: ignore[unsupported-base]
    """Retrieve candidate sources."""

    async def run(
        self, ctx: GraphRunContext[LiteratureReviewWorkflowState]
    ) -> CurateSources | LiteratureReviewError:
        state = ctx.state
        try:
            if state.search_plan is None:
                msg = "Search plan was not initialized"
                raise ValueError(msg)
            agent = LiteratureSearchPlannerAgent()
            sources, warnings, used_live_retrieval = agent.retrieve(
                search_plan=state.search_plan,
                max_sources=state.max_sources,
                live_retrieval_enabled=state.live_retrieval_enabled,
                fixture_path=state.fixture_path,
                year_min=state.year_min,
            )
            state.candidate_sources = sources
            state.warnings.extend(warnings)
            state.metadata["used_live_retrieval"] = used_live_retrieval
            if not sources:
                state.warnings.append("No candidate literature sources were retrieved")
        except Exception as exc:
            _mark_failure(
                state,
                f"Literature retrieval failed: {exc!s}",
                stage="retrieval",
            )
            return LiteratureReviewError()
        return CurateSources()


class CurateSources(BaseNode[LiteratureReviewWorkflowState]):  # type: ignore[unsupported-base]
    """Deduplicate and screen sources."""

    async def run(
        self, ctx: GraphRunContext[LiteratureReviewWorkflowState]
    ) -> ExtractEvidenceAndAppraise | LiteratureReviewError:
        state = ctx.state
        try:
            agent = LiteratureCurationAgent()
            curated = agent.curate(
                sources=state.candidate_sources,
                question=state.question,
                inclusion_criteria=state.inclusion_criteria,
                exclusion_criteria=state.exclusion_criteria,
                min_relevance_score=state.min_relevance_score,
                include_preprints=state.include_preprints,
            )
            state.unique_sources = [
                LiteratureSource.model_validate(item)
                for item in curated.get("unique_sources", [])
            ]
            state.included_sources = [
                LiteratureSource.model_validate(item)
                for item in curated.get("included_sources", [])
            ]
            state.excluded_sources = [
                LiteratureSource.model_validate(item)
                for item in curated.get("excluded_sources", [])
            ]
            state.screening_decisions = [
                ScreeningDecision.model_validate(item)
                for item in curated.get("screening_decisions", [])
            ]
            state.duplicate_diagnostics = list(curated.get("duplicate_diagnostics", []))
            if not state.included_sources:
                state.warnings.append("No sources passed literature screening")
        except Exception as exc:
            _mark_failure(
                state,
                f"Literature source curation failed: {exc!s}",
                stage="source_curation",
            )
            return LiteratureReviewError()
        return ExtractEvidenceAndAppraise()


class ExtractEvidenceAndAppraise(BaseNode[LiteratureReviewWorkflowState]):  # type: ignore[unsupported-base]
    """Extract evidence rows and critical appraisals."""

    async def run(
        self, ctx: GraphRunContext[LiteratureReviewWorkflowState]
    ) -> SynthesizeLiteratureReview | LiteratureReviewError:
        state = ctx.state
        try:
            agent = LiteratureCurationAgent()
            state.evidence_table, state.appraisals = agent.appraise(
                sources=state.included_sources
            )
        except Exception as exc:
            _mark_failure(
                state,
                f"Literature evidence appraisal failed: {exc!s}",
                stage="evidence_appraisal",
            )
            return LiteratureReviewError()
        return SynthesizeLiteratureReview()


class SynthesizeLiteratureReview(BaseNode[LiteratureReviewWorkflowState]):  # type: ignore[unsupported-base]
    """Synthesize final report and structured payload."""

    async def run(
        self, ctx: GraphRunContext[LiteratureReviewWorkflowState]
    ) -> End[dict[str, Any]] | LiteratureReviewError:
        state = ctx.state
        try:
            if state.request is None or state.search_plan is None:
                msg = "Request or search plan was not initialized"
                raise ValueError(msg)
            agent = LiteratureSynthesisAgent()
            state.synthesis, state.markdown_report = agent.synthesize(
                question=state.question,
                request=state.request.model_dump(mode="json"),
                search_plan=state.search_plan.model_dump(mode="json"),
                included_sources=[
                    source.model_dump(mode="json") for source in state.included_sources
                ],
                excluded_sources=[
                    source.model_dump(mode="json") for source in state.excluded_sources
                ],
                screening_decisions=[
                    decision.model_dump(mode="json")
                    for decision in state.screening_decisions
                ],
                evidence_table=[
                    row.model_dump(mode="json") for row in state.evidence_table
                ],
                appraisals=[
                    appraisal.model_dump(mode="json") for appraisal in state.appraisals
                ],
                duplicate_diagnostics=state.duplicate_diagnostics,
            )
            state.report = LiteratureReviewReport(
                request=state.request,
                search_plan=state.search_plan,
                included_sources=state.included_sources,
                excluded_sources=state.excluded_sources,
                screening_decisions=state.screening_decisions,
                evidence_table=state.evidence_table,
                appraisals=state.appraisals,
                synthesis=state.synthesis,
                markdown_report=state.markdown_report,
                diagnostics={
                    "candidate_sources": len(state.candidate_sources),
                    "unique_sources": len(state.unique_sources),
                    "duplicates_removed": len(state.duplicate_diagnostics),
                },
            )
            state.status = ExecutionStatus.SUCCESS
            result = LiteratureReviewWorkflowResult(
                question=state.question,
                mode=state.mode,
                report=state.report,
                markdown_report=state.markdown_report,
                metadata={
                    **state.metadata,
                    "status": state.status.value,
                    "candidate_sources": len(state.candidate_sources),
                    "included_sources": len(state.included_sources),
                    "excluded_sources": len(state.excluded_sources),
                    "duplicates_removed": len(state.duplicate_diagnostics),
                },
                status=state.status.value,
                warnings=state.warnings,
                errors=state.errors,
            )
            return End(result.model_dump(mode="json"))
        except Exception as exc:
            _mark_failure(
                state,
                f"Literature synthesis failed: {exc!s}",
                stage="synthesis",
            )
            return LiteratureReviewError()


class LiteratureReviewError(BaseNode[LiteratureReviewWorkflowState]):  # type: ignore[unsupported-base]
    """Return a structured failure payload."""

    async def run(
        self, ctx: GraphRunContext[LiteratureReviewWorkflowState]
    ) -> End[dict[str, Any]]:
        return End(_build_failure_payload(ctx.state))


def create_literature_review_workflow() -> Graph:
    """Create the literature review workflow graph."""

    return Graph(
        nodes=[
            ParseLiteratureReviewRequest(),
            PlanSearchStrategy(),
            RetrieveCandidateSources(),
            CurateSources(),
            ExtractEvidenceAndAppraise(),
            SynthesizeLiteratureReview(),
            LiteratureReviewError(),
        ]
    )


async def run_literature_review_workflow(
    question: str,
    cfg: Any | None = None,
    mode: str | None = None,
) -> dict[str, Any]:
    """Run the literature review workflow with config-derived defaults."""

    literature_cfg = _section_get(cfg, "literature_review", {})
    search_cfg = _section_get(literature_cfg, "search", {})
    inferred_mode = mode or _section_get(literature_cfg, "mode", "review")

    state = LiteratureReviewWorkflowState(
        question=question,
        mode=inferred_mode,
        source_mode=_section_get(literature_cfg, "source_mode", "fixture"),
        max_sources=int(_section_get(literature_cfg, "max_sources", 12) or 12),
        include_preprints=bool(_section_get(literature_cfg, "include_preprints", True)),
        live_retrieval_enabled=bool(
            _section_get(literature_cfg, "live_retrieval_enabled", False)
        ),
        min_relevance_score=float(
            _section_get(literature_cfg, "min_relevance_score", 0.35) or 0.35
        ),
        inclusion_criteria=_as_list(
            _section_get(literature_cfg, "inclusion_criteria", [])
        ),
        exclusion_criteria=_as_list(
            _section_get(literature_cfg, "exclusion_criteria", [])
        ),
        year_min=_section_get(search_cfg, "year_min", None),
        fixture_path=_section_get(literature_cfg, "fixture_path", None),
        max_queries=int(_section_get(search_cfg, "max_queries", 3) or 3),
        config=cfg,
    )
    workflow = create_literature_review_workflow()
    result = await workflow.run(ParseLiteratureReviewRequest(), state=state)  # type: ignore[arg-type]
    return result.output if hasattr(result, "output") else {"error": "No output"}  # type: ignore[return-value]


__all__ = [
    "CurateSources",
    "ExtractEvidenceAndAppraise",
    "LiteratureReviewError",
    "LiteratureReviewWorkflowState",
    "ParseLiteratureReviewRequest",
    "PlanSearchStrategy",
    "RetrieveCandidateSources",
    "SynthesizeLiteratureReview",
    "create_literature_review_workflow",
    "run_literature_review_workflow",
]
