"""
Thin agent wrappers for the critical literature review workflow.
"""

from __future__ import annotations

from typing import Any

from DeepResearch.src.datatypes.literature_review import (
    CriticalAppraisal,
    EvidenceTableRow,
    LiteratureSearchPlan,
    LiteratureSource,
    LiteratureSynthesis,
    ScreeningDecision,
)
from DeepResearch.src.tools.literature_review_tools import (
    LiteratureEvidenceAppraisalTool,
    LiteratureRetrievalTool,
    LiteratureSearchPlanningTool,
    LiteratureSourceCurationTool,
    LiteratureSynthesisTool,
)


class LiteratureSearchPlannerAgent:
    """Plan search strategy and retrieve candidate sources."""

    def __init__(self):
        self._planning_tool = LiteratureSearchPlanningTool()
        self._retrieval_tool = LiteratureRetrievalTool()

    def plan(self, **params: Any) -> LiteratureSearchPlan:
        result = self._planning_tool.run(params)
        if not result.success:
            msg = result.error or "Literature search planning failed"
            raise ValueError(msg)
        return LiteratureSearchPlan.model_validate(result.data["search_plan"])

    def retrieve(
        self, *, search_plan: LiteratureSearchPlan, **params: Any
    ) -> tuple[list[LiteratureSource], list[str], bool]:
        result = self._retrieval_tool.run(
            {
                **params,
                "question": search_plan.question,
                "search_plan": search_plan.model_dump(mode="json"),
                "source_mode": search_plan.source_mode,
            }
        )
        if not result.success:
            msg = result.error or "Literature retrieval failed"
            raise ValueError(msg)
        sources = [
            LiteratureSource.model_validate(item)
            for item in result.data.get("candidate_sources", [])
        ]
        warnings = [str(item) for item in result.data.get("warnings", [])]
        return sources, warnings, bool(result.data.get("used_live_retrieval", False))


class LiteratureCurationAgent:
    """Curate sources and extract evidence/appraisal rows."""

    def __init__(self):
        self._curation_tool = LiteratureSourceCurationTool()
        self._appraisal_tool = LiteratureEvidenceAppraisalTool()

    def curate(
        self, *, sources: list[LiteratureSource], **params: Any
    ) -> dict[str, Any]:
        result = self._curation_tool.run(
            {
                **params,
                "sources": [source.model_dump(mode="json") for source in sources],
            }
        )
        if not result.success:
            msg = result.error or "Literature source curation failed"
            raise ValueError(msg)
        return result.data

    def appraise(
        self, *, sources: list[LiteratureSource]
    ) -> tuple[list[EvidenceTableRow], list[CriticalAppraisal]]:
        result = self._appraisal_tool.run(
            {"sources": [source.model_dump(mode="json") for source in sources]}
        )
        if not result.success:
            msg = result.error or "Literature evidence appraisal failed"
            raise ValueError(msg)
        evidence = [
            EvidenceTableRow.model_validate(item)
            for item in result.data.get("evidence_table", [])
        ]
        appraisals = [
            CriticalAppraisal.model_validate(item)
            for item in result.data.get("appraisals", [])
        ]
        return evidence, appraisals


class LiteratureSynthesisAgent:
    """Synthesize a structured literature review report."""

    def __init__(self):
        self._tool = LiteratureSynthesisTool()

    def synthesize(self, **params: Any) -> tuple[LiteratureSynthesis, str]:
        result = self._tool.run(params)
        if not result.success:
            msg = result.error or "Literature synthesis failed"
            raise ValueError(msg)
        return (
            LiteratureSynthesis.model_validate(result.data["synthesis"]),
            str(result.data.get("markdown_report", "")).strip(),
        )


__all__ = [
    "LiteratureCurationAgent",
    "LiteratureSearchPlannerAgent",
    "LiteratureSynthesisAgent",
]
