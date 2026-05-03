"""
Hypothesis generation and test-planning workflow.
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


from DeepResearch.src.agents.hypothesis_agents import (
    HypothesisEvaluatorAgent,
    HypothesisGeneratorAgent,
    HypothesisPlannerAgent,
)
from DeepResearch.src.datatypes.hypothesis import (
    HypothesisCandidate,
    HypothesisEvidence,
    HypothesisTestPlan,
    HypothesisWorkflowResult,
)
from DeepResearch.src.datatypes.workflow_orchestration import (
    HypothesisDataset,
    HypothesisTestingEnvironment,
    WorkflowStatus,
)
from DeepResearch.src.tools.hypothesis_tools import GatherEvidenceTool
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


class HypothesisWorkflowState(BaseModel):
    """State for the hypothesis workflow."""

    question: str = Field(..., description="Research question")
    mode: str = Field("generate", description="Workflow mode")
    evidence_mode: str = Field("search_only", description="Evidence mode")
    live_evidence_enabled: bool = Field(
        False, description="Whether to attempt live external evidence gathering"
    )
    max_hypotheses: int = Field(3, description="Maximum hypotheses to generate")
    top_k: int = Field(3, description="Number of ranked hypotheses to keep")
    generate_testing_plans: bool = Field(
        False, description="Whether to generate validation plans"
    )
    score_weights: dict[str, float] = Field(
        default_factory=dict, description="Optional score weights"
    )
    config: Any | None = Field(default=None, description="Original config object")
    provided_hypotheses: list[HypothesisCandidate] = Field(default_factory=list)
    evidence: list[HypothesisEvidence] = Field(default_factory=list)
    candidates: list[HypothesisCandidate] = Field(default_factory=list)
    ranked_candidates: list[HypothesisCandidate] = Field(default_factory=list)
    test_plans: list[HypothesisTestPlan] = Field(default_factory=list)
    dataset: HypothesisDataset | None = Field(default=None)
    testing_environments: list[HypothesisTestingEnvironment] = Field(
        default_factory=list
    )
    markdown_report: str = Field("", description="Markdown summary")
    metadata: dict[str, Any] = Field(default_factory=dict)
    errors: list[str] = Field(default_factory=list)
    status: ExecutionStatus = Field(
        ExecutionStatus.PENDING, description="Workflow status"
    )

    model_config = ConfigDict(arbitrary_types_allowed=True, json_schema_extra={})


def _mark_failure(
    state: HypothesisWorkflowState,
    message: str,
    *,
    stage: str,
) -> None:
    """Record a structured workflow failure."""

    state.errors.append(message)
    state.metadata["failure_stage"] = stage
    state.metadata["error_summary"] = message
    state.status = ExecutionStatus.FAILED


def _build_failure_payload(state: HypothesisWorkflowState) -> dict[str, Any]:
    """Build a consistent failure payload for hypothesis workflow callers."""

    error_summary = state.errors[-1] if state.errors else "Unknown error"
    metadata = dict(state.metadata)
    metadata.setdefault("failure_stage", "unknown")
    metadata["error_summary"] = error_summary
    metadata["status"] = state.status.value

    return {
        "question": state.question,
        "mode": state.mode,
        "evidence": [],
        "ranked_hypotheses": [],
        "test_plans": [],
        "markdown_report": f"Hypothesis workflow failed: {error_summary}",
        "metadata": metadata,
        "status": state.status.value,
        "errors": state.errors,
        "dataset": None,
        "testing_environments": [],
    }


def _normalize_mode(mode: str | None) -> str:
    normalized = (mode or "generate").strip().lower()
    aliases = {
        "generate": "generate",
        "generation": "generate",
        "testing": "testing",
        "generate_and_plan_tests": "testing",
        "full": "full",
    }
    return aliases.get(normalized, "generate")


def _normalize_hypothesis_candidates(items: list[Any]) -> list[HypothesisCandidate]:
    return [
        item
        if isinstance(item, HypothesisCandidate)
        else HypothesisCandidate.model_validate(item)
        for item in items
    ]


class ParseHypothesisRequest(BaseNode[HypothesisWorkflowState]):  # type: ignore[unsupported-base]
    """Validate and normalize workflow inputs."""

    async def run(
        self, ctx: GraphRunContext[HypothesisWorkflowState]
    ) -> GatherEvidence | End[dict[str, Any]]:
        state = ctx.state
        question = state.question.strip()
        if not question and not state.provided_hypotheses:
            _mark_failure(
                state,
                "Question cannot be empty unless hypotheses are provided",
                stage="request_parsing",
            )
            return End(_build_failure_payload(state))

        state.question = question or "Provided hypotheses"
        state.mode = _normalize_mode(state.mode)
        state.max_hypotheses = max(
            1, int(state.max_hypotheses), len(state.provided_hypotheses)
        )
        state.top_k = max(1, min(int(state.top_k), state.max_hypotheses))
        state.generate_testing_plans = state.generate_testing_plans or state.mode in {
            "testing",
            "full",
        }
        if state.provided_hypotheses:
            state.candidates = list(state.provided_hypotheses)
            state.metadata["used_provided_hypotheses"] = True
        state.status = ExecutionStatus.RUNNING
        return GatherEvidence()


class GatherEvidence(BaseNode[HypothesisWorkflowState]):  # type: ignore[unsupported-base]
    """Collect grounding evidence for the workflow."""

    async def run(
        self, ctx: GraphRunContext[HypothesisWorkflowState]
    ) -> GenerateHypotheses | HypothesisError:
        state = ctx.state
        result = GatherEvidenceTool().run(
            {
                "question": state.question,
                "evidence_mode": state.evidence_mode,
                "max_evidence_items": max(3, state.top_k + 2),
                "live_evidence_enabled": state.live_evidence_enabled,
            }
        )
        if not result.success:
            _mark_failure(
                state,
                result.error or "Evidence gathering failed",
                stage="evidence_gathering",
            )
            return HypothesisError()

        state.evidence = [
            HypothesisEvidence.model_validate(item)
            for item in result.data.get("evidence", [])
        ]
        state.metadata["used_external_evidence"] = bool(
            result.data.get("used_external_evidence", False)
        )
        return GenerateHypotheses()


class GenerateHypotheses(BaseNode[HypothesisWorkflowState]):  # type: ignore[unsupported-base]
    """Generate candidate hypotheses."""

    async def run(
        self, ctx: GraphRunContext[HypothesisWorkflowState]
    ) -> ScoreAndRankHypotheses | HypothesisError:
        state = ctx.state
        if state.candidates:
            return ScoreAndRankHypotheses()
        try:
            generator = HypothesisGeneratorAgent()
            state.candidates = generator.generate(
                question=state.question,
                evidence=state.evidence,
                max_hypotheses=state.max_hypotheses,
            )
        except Exception as exc:
            _mark_failure(
                state,
                f"Hypothesis generation failed: {exc!s}",
                stage="hypothesis_generation",
            )
            return HypothesisError()
        return ScoreAndRankHypotheses()


class ScoreAndRankHypotheses(BaseNode[HypothesisWorkflowState]):  # type: ignore[unsupported-base]
    """Score and rank generated hypotheses."""

    async def run(
        self, ctx: GraphRunContext[HypothesisWorkflowState]
    ) -> CreateTestingPlans | SynthesizeHypothesisReport | HypothesisError:
        state = ctx.state
        try:
            evaluator = HypothesisEvaluatorAgent()
            state.ranked_candidates = evaluator.rank(
                candidates=state.candidates,
                top_k=state.top_k,
                score_weights=state.score_weights,
            )
        except Exception as exc:
            _mark_failure(
                state,
                f"Hypothesis ranking failed: {exc!s}",
                stage="hypothesis_ranking",
            )
            return HypothesisError()

        if state.generate_testing_plans:
            return CreateTestingPlans()
        return SynthesizeHypothesisReport()


class CreateTestingPlans(BaseNode[HypothesisWorkflowState]):  # type: ignore[unsupported-base]
    """Generate validation plans for ranked hypotheses."""

    async def run(
        self, ctx: GraphRunContext[HypothesisWorkflowState]
    ) -> SynthesizeHypothesisReport | HypothesisError:
        state = ctx.state
        try:
            planner = HypothesisPlannerAgent()
            state.test_plans = planner.create_test_plans(state.ranked_candidates)
        except Exception as exc:
            _mark_failure(
                state,
                f"Hypothesis test planning failed: {exc!s}",
                stage="test_plan_creation",
            )
            return HypothesisError()
        return SynthesizeHypothesisReport()


class SynthesizeHypothesisReport(BaseNode[HypothesisWorkflowState]):  # type: ignore[unsupported-base]
    """Convert structured results into compatibility outputs and markdown."""

    async def run(
        self, ctx: GraphRunContext[HypothesisWorkflowState]
    ) -> End[dict[str, Any]] | HypothesisError:
        state = ctx.state
        try:
            planner = HypothesisPlannerAgent()
            state.markdown_report = planner.format_report(
                question=state.question,
                mode=state.mode,
                evidence=state.evidence,
                hypotheses=state.ranked_candidates,
                test_plans=state.test_plans,
            )
            state.dataset = _build_dataset(state)
            state.testing_environments = _build_testing_environments(state)
            state.status = ExecutionStatus.SUCCESS

            workflow_result = HypothesisWorkflowResult(
                question=state.question,
                mode=state.mode,
                evidence=state.evidence,
                ranked_hypotheses=state.ranked_candidates,
                test_plans=state.test_plans,
                markdown_report=state.markdown_report,
                metadata={
                    **state.metadata,
                    "status": state.status.value,
                    "generated_hypotheses": len(state.candidates),
                    "ranked_hypotheses": len(state.ranked_candidates),
                },
            )
            payload = workflow_result.model_dump(mode="json")
            payload["dataset"] = state.dataset.model_dump(mode="json")
            payload["testing_environments"] = [
                environment.model_dump(mode="json")
                for environment in state.testing_environments
            ]
            payload["status"] = state.status.value
            payload["errors"] = state.errors
            return End(payload)
        except Exception as exc:
            _mark_failure(
                state,
                f"Hypothesis report synthesis failed: {exc!s}",
                stage="report_synthesis",
            )
            return HypothesisError()


class HypothesisError(BaseNode[HypothesisWorkflowState]):  # type: ignore[unsupported-base]
    """Return a structured failure payload."""

    async def run(
        self, ctx: GraphRunContext[HypothesisWorkflowState]
    ) -> End[dict[str, Any]]:
        return End(_build_failure_payload(ctx.state))


def _build_dataset(state: HypothesisWorkflowState) -> HypothesisDataset:
    return HypothesisDataset(
        name=f"Hypotheses for {state.question[:50]}",
        description="Ranked hypotheses generated by the hypothesis engine",
        hypotheses=[
            candidate.model_dump(mode="json") for candidate in state.ranked_candidates
        ],
        metadata={
            "mode": state.mode,
            "evidence_mode": state.evidence_mode,
            "generated_hypotheses": len(state.candidates),
            "used_external_evidence": state.metadata.get(
                "used_external_evidence", False
            ),
        },
        source_workflows=["hypothesis_workflow"],
    )


def _build_testing_environments(
    state: HypothesisWorkflowState,
) -> list[HypothesisTestingEnvironment]:
    environments: list[HypothesisTestingEnvironment] = []
    for plan in state.test_plans:
        candidate = next(
            (
                hypothesis
                for hypothesis in state.ranked_candidates
                if hypothesis.id == plan.hypothesis_id
            ),
            None,
        )
        if candidate is None:
            continue
        environments.append(
            HypothesisTestingEnvironment(
                name=f"Validation plan for {candidate.id}",
                hypothesis=candidate.model_dump(mode="json"),
                test_configuration={
                    "test_type": plan.test_type,
                    "method": plan.method,
                    "required_inputs": plan.required_inputs,
                },
                expected_outcomes=plan.success_criteria,
                success_criteria={
                    "criteria": plan.success_criteria,
                    "minimum_overall_score": (
                        candidate.score.overall_score if candidate.score else None
                    ),
                },
                status=WorkflowStatus.PENDING,
            )
        )
    return environments


def create_hypothesis_workflow() -> Graph:
    """Create the hypothesis workflow graph."""

    return Graph(
        nodes=[
            ParseHypothesisRequest(),
            GatherEvidence(),
            GenerateHypotheses(),
            ScoreAndRankHypotheses(),
            CreateTestingPlans(),
            SynthesizeHypothesisReport(),
            HypothesisError(),
        ]
    )


async def run_hypothesis_workflow(
    question: str,
    cfg: Any | None = None,
    mode: str | None = None,
    existing_hypotheses: list[dict[str, Any]] | list[HypothesisCandidate] | None = None,
) -> dict[str, Any]:
    """Run the hypothesis workflow with config-derived defaults."""

    hypothesis_cfg = _section_get(cfg, "hypothesis", {})
    flows_cfg = _section_get(cfg, "flows", {})
    testing_cfg = _section_get(flows_cfg, "hypothesis_testing", {})

    inferred_mode = mode
    if inferred_mode is None:
        if _section_get(testing_cfg, "enabled", False):
            inferred_mode = "testing"
        else:
            inferred_mode = _section_get(hypothesis_cfg, "mode", "generate")
    inferred_mode = _normalize_mode(inferred_mode)

    provided_hypotheses = existing_hypotheses
    if provided_hypotheses is None:
        provided_hypotheses = _section_get(hypothesis_cfg, "existing_hypotheses", [])

    state = HypothesisWorkflowState(
        question=question,
        mode=inferred_mode,
        evidence_mode=_section_get(hypothesis_cfg, "evidence_mode", "search_only"),
        live_evidence_enabled=bool(
            _section_get(hypothesis_cfg, "live_evidence_enabled", False)
        ),
        max_hypotheses=int(_section_get(hypothesis_cfg, "max_hypotheses", 3) or 3),
        top_k=int(_section_get(hypothesis_cfg, "top_k", 3) or 3),
        generate_testing_plans=bool(
            _section_get(hypothesis_cfg, "generate_testing_plans", False)
            or inferred_mode in {"testing", "full"}
        ),
        score_weights=dict(_section_get(hypothesis_cfg, "score_weights", {}) or {}),
        config=cfg,
        provided_hypotheses=_normalize_hypothesis_candidates(
            list(provided_hypotheses or [])
        ),
    )
    workflow = create_hypothesis_workflow()
    result = await workflow.run(ParseHypothesisRequest(), state=state)  # type: ignore[arg-type]
    if not hasattr(result, "output") or not isinstance(result.output, dict):
        raise RuntimeError("Hypothesis workflow did not return a structured output")
    return result.output  # type: ignore[return-value]


__all__ = [
    "CreateTestingPlans",
    "GatherEvidence",
    "GenerateHypotheses",
    "HypothesisError",
    "HypothesisWorkflowState",
    "ParseHypothesisRequest",
    "ScoreAndRankHypotheses",
    "SynthesizeHypothesisReport",
    "create_hypothesis_workflow",
    "run_hypothesis_workflow",
]
