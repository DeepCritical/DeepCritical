"""
Tools for the hypothesis engine workflow.
"""

from __future__ import annotations

import os
import re
from collections import OrderedDict
from typing import Any

from DeepResearch.src.datatypes.hypothesis import (
    HypothesisCandidate,
    HypothesisEvidence,
    HypothesisScore,
    HypothesisTestPlan,
)
from DeepResearch.src.prompts.hypothesis import build_prompt_bundle

from .base import ExecutionResult, ToolRunner, ToolSpec, registry

STOPWORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "can",
    "by",
    "could",
    "does",
    "explain",
    "explained",
    "explains",
    "for",
    "from",
    "how",
    "in",
    "into",
    "is",
    "it",
    "may",
    "mechanism",
    "mechanisms",
    "might",
    "most",
    "of",
    "on",
    "or",
    "plausible",
    "plausibly",
    "question",
    "reason",
    "reasons",
    "should",
    "that",
    "the",
    "their",
    "these",
    "this",
    "to",
    "what",
    "which",
    "would",
    "why",
    "with",
}

ACTION_WORDS = {
    "affect",
    "affects",
    "affected",
    "alter",
    "alters",
    "altered",
    "change",
    "changes",
    "changed",
    "drive",
    "drives",
    "driven",
    "impact",
    "impacts",
    "improve",
    "improves",
    "improved",
    "increase",
    "increases",
    "increased",
    "influence",
    "influences",
    "influenced",
    "mediate",
    "mediates",
    "mediated",
    "modulate",
    "modulates",
    "modulated",
    "optimize",
    "optimizes",
    "optimized",
    "predict",
    "predicts",
    "predicted",
    "produce",
    "produces",
    "produced",
    "regulate",
    "regulates",
    "regulated",
    "shape",
    "shapes",
    "shaped",
}

DEFAULT_FOCUS_TERMS = [
    "baseline conditions",
    "time scale",
    "measurement context",
]

DEFAULT_SCORE_WEIGHTS = {
    "novelty": 0.2,
    "evidence_support": 0.3,
    "testability": 0.2,
    "falsifiability": 0.15,
    "specificity": 0.15,
}


def _clamp(value: float, floor: float = 0.0, ceiling: float = 1.0) -> float:
    return max(floor, min(ceiling, value))


def _dedupe_phrases(items: list[str]) -> list[str]:
    phrases: list[str] = []
    seen: set[str] = set()
    for item in items:
        phrase = " ".join(item.split()).strip()
        if not phrase or phrase in seen:
            continue
        seen.add(phrase)
        phrases.append(phrase)
    return phrases


def _flush_phrase_chunk(
    chunk: list[str], phrases: list[str], *, max_words: int
) -> None:
    if not chunk:
        return
    phrases.append(" ".join(chunk[:max_words]))
    chunk.clear()


def extract_keywords(question: str, limit: int = 6) -> list[str]:
    """Extract deterministic focus phrases from the question."""

    words = re.findall(r"[A-Za-z][A-Za-z0-9_-]*", question.lower())
    phrase_chunks: list[str] = []
    current_chunk: list[str] = []

    for word in words:
        if word in ACTION_WORDS or word in STOPWORDS or len(word) < 3:
            _flush_phrase_chunk(current_chunk, phrase_chunks, max_words=3)
            continue
        current_chunk.append(word)
    _flush_phrase_chunk(current_chunk, phrase_chunks, max_words=3)

    deduped_phrases = _dedupe_phrases(phrase_chunks)
    ordered_keywords: OrderedDict[str, None] = OrderedDict()
    for phrase in deduped_phrases:
        ordered_keywords.setdefault(phrase, None)
        if len(ordered_keywords) >= limit:
            break

    keywords = list(ordered_keywords.keys())
    if len(keywords) >= 3:
        return keywords[:limit]

    fallbacks = DEFAULT_FOCUS_TERMS
    for fallback in fallbacks:
        if fallback not in ordered_keywords:
            keywords.append(fallback)
        if len(keywords) >= limit:
            break
    return keywords


def _normalize_evidence_items(items: list[Any]) -> list[HypothesisEvidence]:
    evidence_items: list[HypothesisEvidence] = []
    seen_keys: set[str] = set()
    for item in items:
        evidence = (
            item
            if isinstance(item, HypothesisEvidence)
            else HypothesisEvidence.model_validate(item)
        )
        dedupe_key = f"{evidence.source_type}:{evidence.source_id}:{evidence.title}"
        if dedupe_key in seen_keys:
            continue
        seen_keys.add(dedupe_key)
        evidence_items.append(evidence)
    return evidence_items


def _normalize_candidates(items: list[Any]) -> list[HypothesisCandidate]:
    return [
        item
        if isinstance(item, HypothesisCandidate)
        else HypothesisCandidate.model_validate(item)
        for item in items
    ]


def _trim_summary(text: str, limit: int = 220) -> str:
    compact = " ".join(text.split())
    if len(compact) <= limit:
        return compact
    return compact[: limit - 3].rstrip() + "..."


class GatherEvidenceTool(ToolRunner):
    """Gather search-grounded evidence, with offline-safe fallbacks."""

    def __init__(self):
        super().__init__(
            ToolSpec(
                name="gather_hypothesis_evidence",
                description="Gather evidence for hypothesis generation",
                inputs={
                    "question": "TEXT",
                    "evidence_mode": "TEXT(optional)",
                    "max_evidence_items": "INTEGER(optional)",
                    "live_evidence_enabled": "BOOLEAN(optional)",
                },
                outputs={
                    "evidence": "JSON",
                    "used_external_evidence": "BOOLEAN",
                    "prompt_bundle": "JSON",
                },
            )
        )

    def run(self, params: dict[str, Any]) -> ExecutionResult:
        ok, err = self.validate(params)
        if not ok:
            return ExecutionResult(success=False, error=err)

        question = params.get("question", "").strip()
        if not question:
            return ExecutionResult(
                success=False, error="Question parameter is required"
            )

        evidence_mode = params.get("evidence_mode", "search_only")
        max_evidence_items = int(params.get("max_evidence_items", 5) or 5)
        live_evidence_enabled = self._is_live_evidence_enabled(
            params.get("live_evidence_enabled", False)
        )
        keywords = extract_keywords(question, limit=6)

        evidence_items = [
            HypothesisEvidence(
                source_id="question-framing",
                source_type="question",
                title="Research question framing",
                summary=(
                    "The question centers on "
                    + ", ".join(keywords[:4])
                    + " and calls for a causal or explanatory hypothesis."
                ),
                relevance=0.95,
                metadata={"origin": "question"},
            ),
            HypothesisEvidence(
                source_id="measurement-anchor",
                source_type="heuristic",
                title="Measurement anchor",
                summary=(
                    "A useful hypothesis should tie "
                    + keywords[0]
                    + " to a measurable shift in "
                    + keywords[1]
                    + " under a clearly defined context."
                ),
                relevance=0.82,
                metadata={"origin": "heuristic"},
            ),
            HypothesisEvidence(
                source_id="confounder-anchor",
                source_type="heuristic",
                title="Context and confounder check",
                summary=(
                    "Any convincing explanation should account for context, baseline "
                    "conditions, and alternative explanations involving "
                    + keywords[2]
                    + "."
                ),
                relevance=0.74,
                metadata={"origin": "heuristic"},
            ),
        ]

        external_evidence = []
        if live_evidence_enabled:
            external_evidence = self._collect_external_evidence(
                question=question,
                evidence_mode=evidence_mode,
            )
        evidence_items = _normalize_evidence_items(external_evidence + evidence_items)[
            :max_evidence_items
        ]

        return ExecutionResult(
            success=True,
            data={
                "evidence": [item.model_dump() for item in evidence_items],
                "used_external_evidence": bool(external_evidence),
                "prompt_bundle": build_prompt_bundle("generate"),
            },
        )

    def _is_live_evidence_enabled(self, raw_value: Any) -> bool:
        if isinstance(raw_value, bool):
            return raw_value
        if isinstance(raw_value, str):
            return raw_value.strip().lower() in {"1", "true", "yes", "on"}
        env_value = os.getenv("DEEPCRITICAL_ENABLE_LIVE_EVIDENCE", "")
        return env_value.strip().lower() in {"1", "true", "yes", "on"}

    def _collect_external_evidence(
        self, question: str, evidence_mode: str
    ) -> list[HypothesisEvidence]:
        from .integrated_search_tools import IntegratedSearchTool, RAGSearchTool

        evidence: list[HypothesisEvidence] = []
        search_result = IntegratedSearchTool().run(
            {
                "query": question,
                "search_type": "search",
                "num_results": 3,
                "chunk_size": 600,
                "chunk_overlap": 0,
                "enable_analytics": False,
                "convert_to_rag": True,
            }
        )
        if search_result.success:
            evidence.extend(self._evidence_from_documents(search_result.data, "search"))

        if evidence_mode == "search_plus_rag":
            rag_result = RAGSearchTool().run(
                {
                    "query": question,
                    "search_type": "search",
                    "num_results": 2,
                    "chunk_size": 600,
                    "chunk_overlap": 0,
                }
            )
            if rag_result.success:
                evidence.extend(self._evidence_from_documents(rag_result.data, "rag"))

        return evidence

    def _evidence_from_documents(
        self, payload: dict[str, Any], source_type: str
    ) -> list[HypothesisEvidence]:
        evidence_items: list[HypothesisEvidence] = []
        for index, document in enumerate(payload.get("documents", []), start=1):
            metadata = document.get("metadata", {})
            title = (
                metadata.get("source_title") or f"{source_type.title()} source {index}"
            )
            source_id = metadata.get("url") or metadata.get("source") or title.lower()
            summary = _trim_summary(document.get("content", ""))
            if not summary:
                continue
            evidence_items.append(
                HypothesisEvidence(
                    source_id=source_id,
                    source_type=source_type,
                    title=title,
                    summary=summary,
                    relevance=0.7,
                    metadata=metadata,
                )
            )
        return evidence_items


class GenerateHypothesesTool(ToolRunner):
    """Generate structured hypothesis candidates deterministically."""

    def __init__(self):
        super().__init__(
            ToolSpec(
                name="generate_hypotheses",
                description="Generate structured, testable hypothesis candidates",
                inputs={
                    "question": "TEXT",
                    "evidence": "JSON(optional)",
                    "max_hypotheses": "INTEGER(optional)",
                },
                outputs={"hypotheses": "JSON", "prompt_bundle": "JSON"},
            )
        )

    def run(self, params: dict[str, Any]) -> ExecutionResult:
        ok, err = self.validate(params)
        if not ok:
            return ExecutionResult(success=False, error=err)

        question = params.get("question", "").strip()
        if not question:
            return ExecutionResult(
                success=False, error="Question parameter is required"
            )

        evidence_items = _normalize_evidence_items(params.get("evidence", []))
        max_hypotheses = max(1, int(params.get("max_hypotheses", 3) or 3))
        keywords = extract_keywords(question, limit=max_hypotheses + 3)
        candidates = [
            self._build_candidate(question, keywords, evidence_items, index)
            for index in range(max_hypotheses)
        ]

        return ExecutionResult(
            success=True,
            data={
                "hypotheses": [candidate.model_dump() for candidate in candidates],
                "prompt_bundle": build_prompt_bundle("generate"),
            },
        )

    def _build_candidate(
        self,
        question: str,
        keywords: list[str],
        evidence_items: list[HypothesisEvidence],
        index: int,
    ) -> HypothesisCandidate:
        primary = keywords[0] if keywords else "the proposed driver"
        secondary = keywords[1] if len(keywords) > 1 else "the observed outcome"
        context_terms = keywords[2:] if len(keywords) > 2 else DEFAULT_FOCUS_TERMS
        tertiary = context_terms[index % len(context_terms)]
        evidence_refs = [
            item.title for item in evidence_items[: max(1, min(3, len(evidence_items)))]
        ]

        templates = [
            (
                f"Variation in {primary} produces measurable changes in {secondary} "
                f"when researchers explicitly control for {tertiary}."
            ),
            (
                f"The effect of {primary} on {secondary} is mediated by {tertiary}, "
                "which explains why the same relationship may look different "
                "across settings."
            ),
            (
                f"Improvements in {secondary} are most likely when {primary} reaches "
                f"an effective threshold within {tertiary}, rather than increasing "
                "uniformly across all conditions."
            ),
            (
                f"Observed changes in {secondary} are better explained by interaction "
                f"effects between {primary} and {tertiary} than by any single broad factor."
            ),
        ]
        statement = templates[index % len(templates)]
        rationale = (
            "This candidate is grounded in the question framing and the available "
            "evidence, especially "
            + ", ".join(evidence_refs[:2] or ["the question framing"])
            + f". It keeps {primary} as the putative driver, treats {secondary} "
            f"as the measurable outcome, and uses {tertiary} as the main "
            "contextual qualifier."
        )

        return HypothesisCandidate(
            id=f"hyp-{index + 1}",
            statement=statement,
            rationale=rationale,
            assumptions=[
                f"{primary} can be observed or manipulated consistently.",
                f"{tertiary} can be controlled, stratified, or monitored while evaluating {secondary}.",
            ],
            predictions=[
                f"If the hypothesis is correct, changes in {primary} should precede or co-vary with changes in {secondary}.",
                f"The {primary}-{secondary} relationship should strengthen when researchers explicitly model {tertiary}.",
            ],
            supporting_evidence=[
                item.source_id
                for item in evidence_items[: max(1, min(3, len(evidence_items)))]
            ],
            counter_evidence=[
                f"Stable changes in {secondary} without any measurable shift in {primary} would weaken this hypothesis.",
                f"If {tertiary} has no moderating role, a simpler explanation may be better.",
            ],
            keywords=[primary, secondary, tertiary],
        )


class ScoreHypothesesTool(ToolRunner):
    """Score and rank hypothesis candidates."""

    def __init__(self):
        super().__init__(
            ToolSpec(
                name="score_hypotheses",
                description="Normalize and rank hypothesis candidates",
                inputs={
                    "hypotheses": "JSON",
                    "score_weights": "JSON(optional)",
                    "top_k": "INTEGER(optional)",
                },
                outputs={"ranked_hypotheses": "JSON"},
            )
        )

    def run(self, params: dict[str, Any]) -> ExecutionResult:
        hypotheses = _normalize_candidates(params.get("hypotheses", []))
        if not hypotheses:
            return ExecutionResult(success=False, error="No hypotheses to score")

        top_k = max(1, int(params.get("top_k", len(hypotheses)) or len(hypotheses)))
        weights = self._normalize_weights(params.get("score_weights", {}))
        ranked = [self._score_candidate(candidate, weights) for candidate in hypotheses]
        ranked.sort(
            key=lambda item: (
                item.score.overall_score if item.score else 0.0,
                item.score.evidence_support if item.score else 0.0,
                item.score.specificity if item.score else 0.0,
                item.statement,
            ),
            reverse=True,
        )
        return ExecutionResult(
            success=True,
            data={
                "ranked_hypotheses": [
                    candidate.model_dump() for candidate in ranked[:top_k]
                ]
            },
        )

    def _normalize_weights(self, raw_weights: Any) -> dict[str, float]:
        if not isinstance(raw_weights, dict) or not raw_weights:
            return DEFAULT_SCORE_WEIGHTS.copy()

        weights = {}
        for key, default_value in DEFAULT_SCORE_WEIGHTS.items():
            value = raw_weights.get(key, default_value)
            try:
                weights[key] = max(0.0, float(value))
            except (TypeError, ValueError):
                weights[key] = default_value

        total = sum(weights.values()) or 1.0
        return {key: value / total for key, value in weights.items()}

    def _score_candidate(
        self,
        candidate: HypothesisCandidate,
        weights: dict[str, float],
    ) -> HypothesisCandidate:
        keyword_count = max(1, len(set(candidate.keywords)))
        evidence_count = len(candidate.supporting_evidence)
        prediction_count = len(candidate.predictions)
        assumption_count = len(candidate.assumptions)
        counter_count = len(candidate.counter_evidence)

        novelty = _clamp(
            0.45
            + 0.05 * keyword_count
            + 0.05 * int("mediated" in candidate.statement.lower())
            + 0.05 * int("interaction" in candidate.statement.lower())
        )
        evidence_support = _clamp(0.4 + 0.12 * evidence_count)
        testability = _clamp(0.45 + 0.1 * prediction_count + 0.05 * assumption_count)
        falsifiability = _clamp(0.45 + 0.12 * counter_count + 0.04 * prediction_count)
        specificity = _clamp(
            0.42 + 0.05 * keyword_count + 0.03 * int(len(candidate.statement) > 120)
        )

        overall_score = _clamp(
            novelty * weights["novelty"]
            + evidence_support * weights["evidence_support"]
            + testability * weights["testability"]
            + falsifiability * weights["falsifiability"]
            + specificity * weights["specificity"]
        )
        score = HypothesisScore(
            novelty=novelty,
            evidence_support=evidence_support,
            testability=testability,
            falsifiability=falsifiability,
            specificity=specificity,
            overall_score=overall_score,
            score_justification=(
                "Ranked using deterministic weighting over novelty, evidence "
                "support, testability, falsifiability, and specificity."
            ),
        )
        return candidate.model_copy(update={"score": score})


class CreateHypothesisTestPlansTool(ToolRunner):
    """Create validation plans for top-ranked hypotheses."""

    def __init__(self):
        super().__init__(
            ToolSpec(
                name="create_hypothesis_test_plans",
                description="Create validation plans for ranked hypotheses",
                inputs={"hypotheses": "JSON"},
                outputs={"test_plans": "JSON"},
            )
        )

    def run(self, params: dict[str, Any]) -> ExecutionResult:
        hypotheses = _normalize_candidates(params.get("hypotheses", []))
        if not hypotheses:
            return ExecutionResult(success=False, error="No hypotheses to plan for")

        test_plans = [self._build_plan(candidate) for candidate in hypotheses]
        return ExecutionResult(
            success=True,
            data={"test_plans": [plan.model_dump() for plan in test_plans]},
        )

    def _build_plan(self, candidate: HypothesisCandidate) -> HypothesisTestPlan:
        focus_terms = candidate.keywords or extract_keywords(
            candidate.statement, limit=3
        )
        primary = focus_terms[0]
        outcome = focus_terms[1] if len(focus_terms) > 1 else "outcome"
        modifier = focus_terms[2] if len(focus_terms) > 2 else "context"
        return HypothesisTestPlan(
            hypothesis_id=candidate.id,
            test_type="comparative validation study",
            method=(
                f"Compare cases with high and low {primary}, stratify by {modifier}, "
                f"and measure resulting changes in {outcome} against a baseline model."
            ),
            required_inputs=[
                f"Operational definition for {primary}",
                f"Operational definition for {outcome}",
                f"Context variables capturing {modifier}",
                "Baseline or control comparison",
            ],
            success_criteria=[
                f"{primary} explains a measurable share of variance in {outcome}.",
                f"The signal remains after stratifying by {modifier}.",
                "An alternative simpler explanation performs worse.",
            ],
            failure_modes=[
                f"{outcome} changes without any consistent relationship to {primary}.",
                f"{modifier} does not alter or clarify the observed pattern.",
                "A simpler competing model explains the evidence equally well or better.",
            ],
        )


class FormatHypothesisReportTool(ToolRunner):
    """Format the final hypothesis report."""

    def __init__(self):
        super().__init__(
            ToolSpec(
                name="format_hypothesis_report",
                description="Format a ranked hypothesis result into markdown",
                inputs={
                    "question": "TEXT",
                    "mode": "TEXT",
                    "evidence": "JSON(optional)",
                    "hypotheses": "JSON",
                    "test_plans": "JSON(optional)",
                },
                outputs={"markdown_report": "TEXT"},
            )
        )

    def run(self, params: dict[str, Any]) -> ExecutionResult:
        ok, err = self.validate(params)
        if not ok:
            return ExecutionResult(success=False, error=err)

        question = params.get("question", "").strip()
        if not question:
            return ExecutionResult(
                success=False, error="Question parameter is required"
            )

        mode = params.get("mode", "generate")
        evidence_items = _normalize_evidence_items(params.get("evidence", []))
        hypotheses = _normalize_candidates(params.get("hypotheses", []))
        test_plans = [
            plan
            if isinstance(plan, HypothesisTestPlan)
            else HypothesisTestPlan.model_validate(plan)
            for plan in params.get("test_plans", [])
        ]

        lines = [
            "# Hypothesis Engine Report",
            "",
            f"**Question:** {question}",
            f"**Mode:** {mode}",
            "",
            "## Evidence Snapshot",
            "",
        ]

        for evidence in evidence_items[:3]:
            lines.append(
                f"- **{evidence.title}:** {_trim_summary(evidence.summary, limit=180)}"
            )

        if not evidence_items:
            lines.append(
                "- No external evidence was available; the workflow used question-driven heuristics."
            )

        lines.extend(["", "## Ranked Hypotheses", ""])
        for index, candidate in enumerate(hypotheses, start=1):
            score_text = (
                f"{candidate.score.overall_score:.2f}"
                if candidate.score is not None
                else "unscored"
            )
            lines.extend(
                [
                    f"### {index}. {candidate.id}",
                    candidate.statement,
                    "",
                    f"- **Overall score:** {score_text}",
                    f"- **Rationale:** {candidate.rationale}",
                    f"- **Predictions:** {'; '.join(candidate.predictions)}",
                    "",
                ]
            )

        if test_plans:
            lines.extend(["## Test Plans", ""])
            for plan in test_plans:
                lines.extend(
                    [
                        f"### {plan.hypothesis_id}",
                        f"- **Test type:** {plan.test_type}",
                        f"- **Method:** {plan.method}",
                        f"- **Success criteria:** {'; '.join(plan.success_criteria)}",
                        "",
                    ]
                )

        return ExecutionResult(
            success=True,
            data={"markdown_report": "\n".join(lines).strip()},
        )


registry.register("gather_hypothesis_evidence", GatherEvidenceTool)
registry.register("generate_hypotheses", GenerateHypothesesTool)
registry.register("score_hypotheses", ScoreHypothesesTool)
registry.register("create_hypothesis_test_plans", CreateHypothesisTestPlansTool)
registry.register("format_hypothesis_report", FormatHypothesisReportTool)


__all__ = [
    "DEFAULT_SCORE_WEIGHTS",
    "CreateHypothesisTestPlansTool",
    "FormatHypothesisReportTool",
    "GatherEvidenceTool",
    "GenerateHypothesesTool",
    "ScoreHypothesesTool",
    "extract_keywords",
]
