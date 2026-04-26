"""
Tools for the critical literature review workflow.
"""

from __future__ import annotations

import json
import re
from collections import Counter, OrderedDict
from pathlib import Path
from typing import Any, Protocol

import requests

from DeepResearch.src.datatypes.literature_review import (
    CriticalAppraisal,
    EvidenceTableRow,
    LiteratureGap,
    LiteratureReviewRequest,
    LiteratureSearchPlan,
    LiteratureSource,
    LiteratureSynthesis,
    ScreeningDecision,
)
from DeepResearch.src.prompts.literature_review import build_prompt_bundle

from .base import ExecutionResult, ToolRunner, ToolSpec, registry

STOPWORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "between",
    "by",
    "can",
    "does",
    "during",
    "evidence",
    "for",
    "from",
    "how",
    "in",
    "into",
    "is",
    "it",
    "link",
    "links",
    "literature",
    "of",
    "on",
    "or",
    "quality",
    "review",
    "should",
    "that",
    "the",
    "their",
    "this",
    "to",
    "what",
    "which",
    "with",
}

DEFAULT_INCLUSION = [
    "Directly addresses the review question",
    "Contains interpretable source metadata",
]

DEFAULT_EXCLUSION = [
    "Not relevant to the review question",
    "Insufficient bibliographic metadata",
]


def _clamp(value: float, floor: float = 0.0, ceiling: float = 1.0) -> float:
    return max(floor, min(ceiling, value))


def _compact(text: str | None) -> str:
    return " ".join((text or "").split()).strip()


def _tokens(text: str | None) -> set[str]:
    return {
        token
        for token in re.findall(r"[A-Za-z][A-Za-z0-9_-]*", (text or "").lower())
        if token not in STOPWORDS and len(token) >= 3
    }


def _normalize_identifier(value: str | None) -> str | None:
    normalized = _compact(value).lower()
    return normalized or None


def _normalize_title(title: str) -> str:
    return " ".join(re.findall(r"[a-z0-9]+", title.lower()))


def _trim(text: str | None, limit: int = 220) -> str:
    compact = _compact(text)
    if len(compact) <= limit:
        return compact
    return compact[: limit - 3].rstrip() + "..."


def _year_from_value(value: Any) -> int | None:
    if value is None:
        return None
    if isinstance(value, int):
        return value
    year = getattr(value, "year", None)
    if isinstance(year, int):
        return year
    match = re.search(r"\b(1[5-9]\d{2}|20\d{2}|21\d{2})\b", str(value))
    return int(match.group(1)) if match else None


def _first_sentence(text: str | None, fallback: str) -> str:
    compact = _compact(text)
    if not compact:
        return fallback
    match = re.split(r"(?<=[.!?])\s+", compact, maxsplit=1)
    return _trim(match[0], 240)


def extract_review_terms(question: str, limit: int = 8) -> list[str]:
    """Extract deterministic focus terms from a review question."""

    words = [
        word
        for word in re.findall(r"[A-Za-z][A-Za-z0-9_-]*", question.lower())
        if word not in STOPWORDS and len(word) >= 3
    ]
    ordered: OrderedDict[str, None] = OrderedDict()
    for word in words:
        ordered.setdefault(word, None)
        if len(ordered) >= limit:
            break
    return list(ordered.keys())


def _query_list(value: Any, fallback: str) -> list[str]:
    if value is None:
        return [fallback] if fallback else []
    if isinstance(value, str):
        return [_compact(value)] if _compact(value) else []
    queries: list[str] = []
    for item in value:
        query = _compact(str(item))
        if query:
            queries.append(query)
    return queries or ([fallback] if fallback else [])


def _citation_for(source: LiteratureSource) -> str:
    if source.citation:
        return source.citation
    authors = ", ".join(source.authors[:3]) if source.authors else "Unknown authors"
    year = str(source.year) if source.year else "n.d."
    venue = f" {source.venue}." if source.venue else ""
    doi = f" doi:{source.doi}" if source.doi else ""
    return f"{authors} ({year}). {source.title}.{venue}{doi}".strip()


def _source_key(source: LiteratureSource) -> str:
    for key in (
        _normalize_identifier(source.doi),
        _normalize_identifier(source.pmid),
        _normalize_identifier(source.openalex_id),
        _normalize_identifier(source.url),
    ):
        if key:
            return key
    return _normalize_title(source.title)


def _source_from_record(record: dict[str, Any], *, index: int = 0) -> LiteratureSource:
    title = _compact(str(record.get("title") or "Untitled source"))
    doi = _normalize_identifier(record.get("doi"))
    pmid = _normalize_identifier(record.get("pmid"))
    openalex_id = _normalize_identifier(
        record.get("openalex_id") or record.get("openalexId")
    )
    url = _compact(record.get("url")) or None
    source_id = _compact(
        record.get("source_id")
        or record.get("id")
        or doi
        or pmid
        or openalex_id
        or url
        or f"source-{index + 1}"
    )
    authors = record.get("authors") or []
    if isinstance(authors, str):
        authors = [item.strip() for item in authors.split(",") if item.strip()]
    keywords = record.get("keywords") or []
    if isinstance(keywords, str):
        keywords = [item.strip() for item in keywords.split(",") if item.strip()]
    source = LiteratureSource(
        source_id=source_id,
        title=title,
        authors=list(authors),
        year=record.get("year"),
        venue=record.get("venue"),
        doi=doi,
        pmid=pmid,
        openalex_id=openalex_id,
        url=url,
        abstract=record.get("abstract"),
        extracted_text=record.get("extracted_text") or record.get("full_text"),
        source_backend=record.get("source_backend")
        or record.get("backend")
        or "fixture",
        publication_type=record.get("publication_type") or record.get("type"),
        is_preprint=bool(record.get("is_preprint", False)),
        keywords=list(keywords),
        citation=record.get("citation") or "",
        metadata=dict(record.get("metadata") or {}),
    )
    source.citation = _citation_for(source)
    return source


def _default_fixture_records() -> list[dict[str, Any]]:
    return [
        {
            "source_id": "fixture-sleep-memory-1",
            "title": "Sleep quality and memory consolidation in adult learners",
            "authors": ["A. Rivera", "M. Chen"],
            "year": 2021,
            "venue": "Journal of Cognitive Sleep Research",
            "doi": "10.0000/sleep-memory-1",
            "abstract": (
                "Consistent sleep quality was associated with stronger memory "
                "consolidation after learning. The study used repeated recall "
                "testing and controlled for baseline performance."
            ),
            "publication_type": "observational study",
            "keywords": ["sleep", "memory", "consolidation", "learning"],
        },
        {
            "source_id": "fixture-sleep-memory-2",
            "title": "Targeted sleep interventions and delayed recall",
            "authors": ["N. Patel", "S. Gomez"],
            "year": 2023,
            "venue": "Learning and Sleep",
            "doi": "10.0000/sleep-memory-2",
            "abstract": (
                "A randomized sleep hygiene intervention improved delayed recall "
                "in students, although effects were smaller for participants with "
                "irregular schedules."
            ),
            "publication_type": "randomized trial",
            "keywords": ["sleep", "recall", "memory", "intervention"],
        },
        {
            "source_id": "fixture-attention-1",
            "title": "Mobile notification color and purchase intent",
            "authors": ["J. Park"],
            "year": 2019,
            "venue": "Digital Marketing Notes",
            "abstract": (
                "Notification color changed click behavior in a retail app. The "
                "study did not measure sleep, learning, recall, or memory."
            ),
            "publication_type": "field study",
            "keywords": ["notifications", "marketing"],
        },
    ]


class LiteratureSourceAdapter(Protocol):
    """Retrieval adapter interface for normalized literature sources."""

    def retrieve(self, query: str, max_results: int) -> list[LiteratureSource]:
        """Return normalized sources for a query."""


class FixtureLiteratureAdapter:
    """Read deterministic literature records from JSON fixtures or defaults."""

    def __init__(self, fixture_path: str | None = None):
        self.fixture_path = fixture_path

    def retrieve(self, query: str, max_results: int) -> list[LiteratureSource]:
        records = self._load_records()
        sources = [
            _source_from_record(record, index=index)
            for index, record in enumerate(records)
        ]
        terms = _tokens(query)
        if not terms:
            return sources[:max_results]

        scored: list[tuple[float, LiteratureSource]] = []
        for source in sources:
            source_text = " ".join(
                [
                    source.title,
                    source.abstract or "",
                    source.extracted_text or "",
                    " ".join(source.keywords),
                ]
            )
            overlap = len(terms & _tokens(source_text))
            score = overlap / max(1, len(terms))
            scored.append((score, source))

        scored.sort(key=lambda item: item[0], reverse=True)
        return [source for _score, source in scored[:max_results]]

    def _load_records(self) -> list[dict[str, Any]]:
        if not self.fixture_path:
            return _default_fixture_records()
        path = Path(self.fixture_path)
        if not path.exists():
            return _default_fixture_records()
        with path.open(encoding="utf-8") as handle:
            loaded = json.load(handle)
        if isinstance(loaded, dict):
            loaded = loaded.get("sources", [])
        if not isinstance(loaded, list):
            return []
        return [item for item in loaded if isinstance(item, dict)]


class OpenAlexLiteratureAdapter:
    """Retrieve scholarly works from the OpenAlex works search endpoint."""

    def __init__(self, timeout: float = 15.0):
        self.timeout = timeout

    def retrieve(self, query: str, max_results: int) -> list[LiteratureSource]:
        response = requests.get(
            "https://api.openalex.org/works",
            params={"search": query, "per-page": max_results},
            timeout=self.timeout,
        )
        response.raise_for_status()
        works = response.json().get("results", [])
        return [
            self._source_from_work(work, index=index)
            for index, work in enumerate(works[:max_results])
        ]

    def _source_from_work(
        self, work: dict[str, Any], *, index: int
    ) -> LiteratureSource:
        authorships = work.get("authorships") or []
        authors = [
            item.get("author", {}).get("display_name", "")
            for item in authorships
            if item.get("author", {}).get("display_name")
        ]
        primary_location = work.get("primary_location") or {}
        venue = (primary_location.get("source") or {}).get("display_name")
        doi = _normalize_identifier(
            (work.get("doi") or "").removeprefix("https://doi.org/")
        )
        abstract = _openalex_abstract(work.get("abstract_inverted_index") or {})
        return _source_from_record(
            {
                "source_id": work.get("id") or f"openalex-{index + 1}",
                "title": work.get("display_name") or "Untitled OpenAlex work",
                "authors": authors,
                "year": work.get("publication_year"),
                "venue": venue,
                "doi": doi,
                "openalex_id": work.get("id"),
                "url": work.get("id"),
                "abstract": abstract,
                "source_backend": "openalex",
                "publication_type": work.get("type"),
                "is_preprint": work.get("type") == "preprint",
                "metadata": {"cited_by_count": work.get("cited_by_count")},
            },
            index=index,
        )


class PubMedLiteratureAdapter:
    """Adapt the existing PubMed retrieval tool into literature sources."""

    def __init__(self, year_min: int | None = None):
        self.year_min = year_min

    def retrieve(self, query: str, max_results: int) -> list[LiteratureSource]:
        from DeepResearch.src.tools.bioinformatics_tools import PubMedRetrievalTool

        result = PubMedRetrievalTool().run(
            {"query": query, "max_results": max_results, "year_min": self.year_min}
        )
        if not result.success:
            msg = result.error or "PubMed retrieval failed"
            raise RuntimeError(msg)
        papers = result.data.get("papers", [])
        sources: list[LiteratureSource] = []
        for index, paper in enumerate(papers[:max_results]):
            sources.append(
                _source_from_record(
                    {
                        "source_id": paper.get("pmid") or f"pubmed-{index + 1}",
                        "title": paper.get("title") or "Untitled PubMed paper",
                        "authors": paper.get("authors") or [],
                        "year": _year_from_value(
                            paper.get("publication_year")
                            or paper.get("publication_date")
                            or paper.get("year")
                        ),
                        "venue": paper.get("journal"),
                        "doi": paper.get("doi"),
                        "pmid": paper.get("pmid"),
                        "abstract": paper.get("abstract"),
                        "extracted_text": paper.get("full_text"),
                        "url": paper.get("full_text_url"),
                        "source_backend": "pubmed",
                        "is_preprint": False,
                        "keywords": paper.get("keywords")
                        or paper.get("mesh_terms")
                        or [],
                    },
                    index=index,
                )
            )
        return sources


class WebLiteratureAdapter:
    """Adapt chunked web search into literature-like sources."""

    def retrieve(self, query: str, max_results: int) -> list[LiteratureSource]:
        from DeepResearch.src.tools.integrated_search_tools import IntegratedSearchTool

        result = IntegratedSearchTool().run(
            {
                "query": query,
                "search_type": "search",
                "num_results": max_results,
                "chunk_size": 1000,
                "chunk_overlap": 0,
                "enable_analytics": False,
                "convert_to_rag": True,
            }
        )
        if not result.success:
            msg = result.error or "Web retrieval failed"
            raise RuntimeError(msg)
        sources: list[LiteratureSource] = []
        for index, document in enumerate(
            result.data.get("documents", [])[:max_results]
        ):
            metadata = document.get("metadata", {})
            sources.append(
                _source_from_record(
                    {
                        "source_id": metadata.get("url") or f"web-{index + 1}",
                        "title": metadata.get("source_title") or "Untitled web source",
                        "url": metadata.get("url"),
                        "abstract": _trim(document.get("content"), 500),
                        "extracted_text": document.get("content"),
                        "source_backend": "web",
                        "metadata": metadata,
                    },
                    index=index,
                )
            )
        return sources


def _openalex_abstract(inverted_index: dict[str, list[int]]) -> str | None:
    if not inverted_index:
        return None
    positioned: list[tuple[int, str]] = []
    for word, positions in inverted_index.items():
        for position in positions:
            positioned.append((position, word))
    positioned.sort(key=lambda item: item[0])
    return " ".join(word for _position, word in positioned)


class LiteratureSearchPlanningTool(ToolRunner):
    """Plan a deterministic literature search strategy."""

    def __init__(self):
        super().__init__(
            ToolSpec(
                name="plan_literature_search",
                description="Plan a critical literature review search",
                inputs={
                    "question": "TEXT",
                    "source_mode": "TEXT(optional)",
                    "max_queries": "INTEGER(optional)",
                },
                outputs={"search_plan": "JSON"},
            )
        )

    def run(self, params: dict[str, Any]) -> ExecutionResult:
        ok, err = self.validate(params)
        if not ok:
            return ExecutionResult(success=False, error=err)

        question = _compact(params.get("question"))
        if not question:
            return ExecutionResult(
                success=False, error="Question parameter is required"
            )

        max_queries = max(1, min(int(params.get("max_queries", 3) or 3), 5))
        source_mode = params.get("source_mode", "fixture")
        focus_terms = extract_review_terms(question)
        inclusion_criteria = list(params.get("inclusion_criteria") or DEFAULT_INCLUSION)
        exclusion_criteria = list(params.get("exclusion_criteria") or DEFAULT_EXCLUSION)
        expanded_terms = " ".join(focus_terms[:4])
        candidate_queries = [
            question,
            f"{expanded_terms} critical literature review".strip(),
            f"{expanded_terms} evidence limitations".strip(),
        ]
        queries = list(
            OrderedDict.fromkeys(query for query in candidate_queries if query)
        )
        plan = LiteratureSearchPlan(
            question=question,
            queries=queries[:max_queries],
            focus_terms=focus_terms,
            source_mode=source_mode,
            inclusion_criteria=inclusion_criteria,
            exclusion_criteria=exclusion_criteria,
            max_sources=int(params.get("max_sources", 12) or 12),
            prompt_bundle=build_prompt_bundle(params.get("mode", "review")),
        )
        return ExecutionResult(
            success=True, data={"search_plan": plan.model_dump(mode="json")}
        )


class LiteratureRetrievalTool(ToolRunner):
    """Retrieve candidate literature sources from fixture or live adapters."""

    def __init__(self):
        super().__init__(
            ToolSpec(
                name="retrieve_literature_sources",
                description="Retrieve candidate sources for literature review",
                inputs={
                    "question": "TEXT",
                    "source_mode": "TEXT(optional)",
                    "live_retrieval_enabled": "BOOLEAN(optional)",
                },
                outputs={"candidate_sources": "JSON", "warnings": "JSON"},
            )
        )

    def run(self, params: dict[str, Any]) -> ExecutionResult:
        ok, err = self.validate(params)
        if not ok:
            return ExecutionResult(success=False, error=err)

        question = _compact(params.get("question"))
        source_mode = params.get("source_mode") or params.get("search_plan", {}).get(
            "source_mode", "fixture"
        )
        live_retrieval_enabled = bool(params.get("live_retrieval_enabled", False))
        if source_mode != "fixture" and not live_retrieval_enabled:
            return ExecutionResult(
                success=False,
                error=(
                    f"source_mode '{source_mode}' requires live_retrieval_enabled=true"
                ),
            )

        search_plan = params.get("search_plan") or {}
        queries = _query_list(search_plan.get("queries"), question)
        if source_mode == "fixture":
            queries = queries[:1]
        max_sources = max(1, min(int(params.get("max_sources", 12) or 12), 50))
        per_query_limit = (
            max_sources
            if source_mode == "fixture"
            else max(1, max_sources // max(1, len(queries)))
        )
        adapters = self._adapters_for_mode(source_mode, params)
        warnings: list[str] = []
        candidates: list[LiteratureSource] = []

        for adapter in adapters:
            for query in queries:
                try:
                    candidates.extend(adapter.retrieve(query, per_query_limit))
                except Exception as exc:
                    warnings.append(f"{adapter.__class__.__name__}: {exc!s}")

        if not candidates and warnings:
            return ExecutionResult(
                success=False,
                error="; ".join(warnings),
                data={"warnings": warnings, "candidate_sources": []},
            )

        return ExecutionResult(
            success=True,
            data={
                "candidate_sources": [
                    source.model_dump(mode="json")
                    for source in candidates[:max_sources]
                ],
                "warnings": warnings,
                "used_live_retrieval": source_mode != "fixture",
            },
        )

    def _adapters_for_mode(
        self, source_mode: str, params: dict[str, Any]
    ) -> list[LiteratureSourceAdapter]:
        fixture_path = params.get("fixture_path")
        year_min = params.get("year_min")
        if source_mode == "fixture":
            return [FixtureLiteratureAdapter(fixture_path)]
        if source_mode == "openalex":
            return [OpenAlexLiteratureAdapter()]
        if source_mode == "pubmed":
            return [PubMedLiteratureAdapter(year_min=year_min)]
        if source_mode == "web":
            return [WebLiteratureAdapter()]
        if source_mode == "mixed":
            return [
                FixtureLiteratureAdapter(fixture_path),
                OpenAlexLiteratureAdapter(),
            ]
        msg = f"Unsupported source_mode: {source_mode}"
        raise ValueError(msg)


class LiteratureSourceCurationTool(ToolRunner):
    """Normalize, deduplicate, and screen retrieved literature sources."""

    def __init__(self):
        super().__init__(
            ToolSpec(
                name="curate_literature_sources",
                description="Deduplicate and screen literature sources",
                inputs={"question": "TEXT", "sources": "JSON(optional)"},
                outputs={
                    "unique_sources": "JSON",
                    "included_sources": "JSON",
                    "excluded_sources": "JSON",
                    "screening_decisions": "JSON",
                },
            )
        )

    def run(self, params: dict[str, Any]) -> ExecutionResult:
        ok, err = self.validate(params)
        if not ok:
            return ExecutionResult(success=False, error=err)

        sources = [
            item
            if isinstance(item, LiteratureSource)
            else LiteratureSource.model_validate(item)
            for item in params.get("sources", [])
        ]
        unique_sources, duplicate_diagnostics = self._dedupe(sources)
        min_score = float(params.get("min_relevance_score", 0.35) or 0.35)
        inclusion_criteria = list(params.get("inclusion_criteria") or [])
        exclusion_criteria = list(params.get("exclusion_criteria") or [])
        decisions = [
            self._screen_source(
                source,
                question=params.get("question", ""),
                inclusion_criteria=inclusion_criteria,
                exclusion_criteria=exclusion_criteria,
                include_preprints=bool(params.get("include_preprints", True)),
                min_score=min_score,
            )
            for source in unique_sources
        ]
        included_ids = {
            decision.source_id
            for decision in decisions
            if decision.decision == "include"
        }
        included_sources = [
            source for source in unique_sources if source.source_id in included_ids
        ]
        excluded_sources = [
            source for source in unique_sources if source.source_id not in included_ids
        ]
        return ExecutionResult(
            success=True,
            data={
                "unique_sources": [
                    source.model_dump(mode="json") for source in unique_sources
                ],
                "included_sources": [
                    source.model_dump(mode="json") for source in included_sources
                ],
                "excluded_sources": [
                    source.model_dump(mode="json") for source in excluded_sources
                ],
                "screening_decisions": [
                    decision.model_dump(mode="json") for decision in decisions
                ],
                "duplicate_diagnostics": duplicate_diagnostics,
            },
        )

    def _dedupe(
        self, sources: list[LiteratureSource]
    ) -> tuple[list[LiteratureSource], list[dict[str, Any]]]:
        unique: list[LiteratureSource] = []
        seen: dict[str, str] = {}
        duplicates: list[dict[str, Any]] = []
        for source in sources:
            key = _source_key(source)
            if key in seen:
                duplicates.append(
                    {
                        "duplicate_source_id": source.source_id,
                        "kept_source_id": seen[key],
                        "dedupe_key": key,
                    }
                )
                continue
            seen[key] = source.source_id
            unique.append(source)
        return unique, duplicates

    def _screen_source(
        self,
        source: LiteratureSource,
        *,
        question: str,
        inclusion_criteria: list[str],
        exclusion_criteria: list[str],
        include_preprints: bool,
        min_score: float,
    ) -> ScreeningDecision:
        source_text = " ".join(
            [
                source.title,
                source.abstract or "",
                source.extracted_text or "",
                " ".join(source.keywords),
            ]
        )
        source_text_lower = source_text.lower()
        question_terms = _tokens(question)
        criteria_terms = _tokens(" ".join(inclusion_criteria))
        terms = question_terms | criteria_terms
        source_terms = _tokens(source_text)
        overlap = len(terms & source_terms)
        relevance = 0.2 + (0.7 * overlap / max(1, len(terms)))
        if question_terms & _tokens(source.title):
            relevance += 0.1
        if not source.abstract and not source.extracted_text:
            relevance -= 0.1
        relevance = _clamp(relevance)

        reasons: list[str] = []
        if source.is_preprint and not include_preprints:
            return ScreeningDecision(
                source_id=source.source_id,
                decision="exclude",
                relevance_score=relevance,
                reasons=["Preprints are disabled by configuration"],
            )

        if (
            "did not measure" in source_text_lower
            or "not relevant" in source_text_lower
        ):
            return ScreeningDecision(
                source_id=source.source_id,
                decision="exclude",
                relevance_score=relevance,
                reasons=["Source text explicitly signals non-relevance"],
            )

        exclusion_hits = _tokens(" ".join(exclusion_criteria)) & source_terms
        if exclusion_hits:
            reasons.append(
                f"Matched exclusion terms: {', '.join(sorted(exclusion_hits))}"
            )
            return ScreeningDecision(
                source_id=source.source_id,
                decision="exclude",
                relevance_score=relevance,
                reasons=reasons,
            )

        if relevance >= min_score:
            reasons.append("Relevant terms overlap with the review question")
            if source.abstract or source.extracted_text:
                reasons.append("Contains usable abstract or extracted text")
            return ScreeningDecision(
                source_id=source.source_id,
                decision="include",
                relevance_score=relevance,
                reasons=reasons,
            )

        reasons.append("Insufficient relevance to the review question")
        return ScreeningDecision(
            source_id=source.source_id,
            decision="exclude",
            relevance_score=relevance,
            reasons=reasons,
        )


class LiteratureEvidenceAppraisalTool(ToolRunner):
    """Extract evidence rows and critical appraisals from included sources."""

    def __init__(self):
        super().__init__(
            ToolSpec(
                name="appraise_literature_evidence",
                description="Extract evidence and appraise included literature",
                inputs={"sources": "JSON(optional)"},
                outputs={"evidence_table": "JSON", "appraisals": "JSON"},
            )
        )

    def run(self, params: dict[str, Any]) -> ExecutionResult:
        sources = [
            item
            if isinstance(item, LiteratureSource)
            else LiteratureSource.model_validate(item)
            for item in params.get("sources", [])
        ]
        evidence_rows = [self._evidence_row(source) for source in sources]
        appraisals = [self._appraisal(source) for source in sources]
        return ExecutionResult(
            success=True,
            data={
                "evidence_table": [
                    row.model_dump(mode="json") for row in evidence_rows
                ],
                "appraisals": [
                    appraisal.model_dump(mode="json") for appraisal in appraisals
                ],
            },
        )

    def _evidence_row(self, source: LiteratureSource) -> EvidenceTableRow:
        abstract = source.abstract or source.extracted_text or ""
        return EvidenceTableRow(
            source_id=source.source_id,
            study_type=_infer_study_type(source),
            population_or_domain=_infer_domain(source),
            method=_infer_method(source),
            key_findings=[
                _first_sentence(
                    abstract,
                    f"{source.title} is relevant to the review question.",
                )
            ],
            limitations=_source_limitations(source),
            evidence_direction=_infer_evidence_direction(source),
        )

    def _appraisal(self, source: LiteratureSource) -> CriticalAppraisal:
        score = 0.45
        strengths: list[str] = []
        limitations: list[str] = []
        bias_risks: list[str] = []

        if source.abstract or source.extracted_text:
            score += 0.15
            strengths.append("Contains inspectable abstract or extracted text")
        else:
            limitations.append("No abstract or extracted text available")
            bias_risks.append("Limited appraisal detail")

        if source.doi or source.pmid or source.openalex_id:
            score += 0.1
            strengths.append("Contains a stable scholarly identifier")
        else:
            limitations.append("Missing stable scholarly identifier")

        if source.year and source.year >= 2020:
            score += 0.1
            strengths.append("Recent source")
        elif source.year:
            limitations.append("Older source; interpret in context")

        study_type = _infer_study_type(source)
        if study_type in {"meta-analysis", "systematic review", "randomized trial"}:
            score += 0.1
            strengths.append(f"Stronger study design signal: {study_type}")

        if source.is_preprint:
            score -= 0.1
            bias_risks.append("Preprint status; may not be peer reviewed")

        quality = _clamp(score)
        return CriticalAppraisal(
            source_id=source.source_id,
            quality_score=quality,
            confidence=_clamp(quality - 0.05, 0.1, 1.0),
            bias_risks=bias_risks or ["No obvious bias risk detected heuristically"],
            methodological_strengths=strengths or ["Relevant source metadata present"],
            methodological_limitations=limitations
            or ["Heuristic appraisal cannot replace expert risk-of-bias review"],
            applicability_notes=[
                "Use as source-grounded evidence, not as exhaustive systematic review evidence"
            ],
        )


class LiteratureSynthesisTool(ToolRunner):
    """Synthesize appraised sources into a markdown critical review."""

    def __init__(self):
        super().__init__(
            ToolSpec(
                name="synthesize_literature_review",
                description="Synthesize a critical literature review report",
                inputs={"question": "TEXT"},
                outputs={"synthesis": "JSON", "markdown_report": "TEXT"},
            )
        )

    def run(self, params: dict[str, Any]) -> ExecutionResult:
        ok, err = self.validate(params)
        if not ok:
            return ExecutionResult(success=False, error=err)

        request = LiteratureReviewRequest.model_validate(params.get("request"))
        search_plan = LiteratureSearchPlan.model_validate(params.get("search_plan"))
        included_sources = [
            LiteratureSource.model_validate(item)
            for item in params.get("included_sources", [])
        ]
        excluded_sources = [
            LiteratureSource.model_validate(item)
            for item in params.get("excluded_sources", [])
        ]
        screening_decisions = [
            ScreeningDecision.model_validate(item)
            for item in params.get("screening_decisions", [])
        ]
        evidence_table = [
            EvidenceTableRow.model_validate(item)
            for item in params.get("evidence_table", [])
        ]
        appraisals = [
            CriticalAppraisal.model_validate(item)
            for item in params.get("appraisals", [])
        ]
        duplicate_diagnostics = list(params.get("duplicate_diagnostics") or [])
        synthesis = self._synthesis(
            request=request,
            sources=included_sources,
            evidence_table=evidence_table,
            appraisals=appraisals,
        )
        markdown = self._markdown(
            request=request,
            search_plan=search_plan,
            included_sources=included_sources,
            excluded_sources=excluded_sources,
            screening_decisions=screening_decisions,
            evidence_table=evidence_table,
            appraisals=appraisals,
            synthesis=synthesis,
            duplicate_diagnostics=duplicate_diagnostics,
        )
        return ExecutionResult(
            success=True,
            data={
                "synthesis": synthesis.model_dump(mode="json"),
                "markdown_report": markdown,
            },
        )

    def _synthesis(
        self,
        *,
        request: LiteratureReviewRequest,
        sources: list[LiteratureSource],
        evidence_table: list[EvidenceTableRow],
        appraisals: list[CriticalAppraisal],
    ) -> LiteratureSynthesis:
        if not sources:
            gap = LiteratureGap(
                gap="No retained source was available to support a critical synthesis.",
                follow_up_question=(
                    "What sources directly address this review question?"
                ),
            )
            return LiteratureSynthesis(
                summary=(
                    "No sources passed screening, so the workflow did not generate "
                    "source-grounded conclusions."
                ),
                limitations=[
                    "The result is limited by retrieval and screening, not by evidence synthesis."
                ],
                gaps=[gap],
                future_work=[
                    "Broaden the search strategy or lower the screening threshold."
                ],
            )

        themes = _common_themes(sources)
        consensus = [
            f"[{row.source_id}] {row.key_findings[0]}"
            for row in evidence_table
            if row.key_findings
        ]
        conflicts = [
            f"[{row.source_id}] Reports mixed or context-dependent evidence."
            for row in evidence_table
            if row.evidence_direction == "mixed"
        ]
        limitations = sorted(
            {
                limitation
                for appraisal in appraisals
                for limitation in appraisal.methodological_limitations
            }
        )
        gaps = [
            LiteratureGap(
                gap="The retained sources do not establish exhaustive coverage of the topic.",
                supporting_source_ids=[source.source_id for source in sources],
                follow_up_question=(
                    "What additional databases should be searched for this review "
                    "question?"
                ),
            )
        ]
        return LiteratureSynthesis(
            summary=(
                f"{len(sources)} retained source(s) support a bounded critical "
                f"review of: {request.question}"
            ),
            consensus_findings=consensus,
            conflicting_findings=conflicts,
            themes=themes,
            limitations=limitations
            or ["Heuristic appraisal is not a substitute for expert review."],
            gaps=gaps,
            future_work=[
                "Validate the search strategy against additional scholarly databases.",
                "Have a domain expert review screening and appraisal decisions.",
            ],
        )

    def _markdown(
        self,
        *,
        request: LiteratureReviewRequest,
        search_plan: LiteratureSearchPlan,
        included_sources: list[LiteratureSource],
        excluded_sources: list[LiteratureSource],
        screening_decisions: list[ScreeningDecision],
        evidence_table: list[EvidenceTableRow],
        appraisals: list[CriticalAppraisal],
        synthesis: LiteratureSynthesis,
        duplicate_diagnostics: list[dict[str, Any]],
    ) -> str:
        lines = [
            "# Critical Literature Review",
            "",
            f"**Question:** {request.question}",
            "",
            "## Search Strategy",
            "",
            f"- Source mode: `{request.source_mode}`",
            f"- Queries: {', '.join(search_plan.queries) if search_plan.queries else 'None'}",
            f"- Focus terms: {', '.join(search_plan.focus_terms) if search_plan.focus_terms else 'None'}",
            "",
            "## Screening Summary",
            "",
            f"- Candidate sources after dedupe: {len(included_sources) + len(excluded_sources)}",
            f"- Included sources: {len(included_sources)}",
            f"- Excluded sources: {len(excluded_sources)}",
            f"- Duplicates removed: {len(duplicate_diagnostics)}",
            "",
        ]
        if not included_sources:
            lines.extend(
                [
                    "No sources passed screening. The workflow therefore does not "
                    "make evidence claims.",
                    "",
                ]
            )

        lines.extend(["## Evidence Table", ""])
        if evidence_table:
            lines.append(
                "| Source | Study Type | Key Finding | Limitations | Direction |"
            )
            lines.append("| --- | --- | --- | --- | --- |")
            for row in evidence_table:
                lines.append(
                    "| "
                    + " | ".join(
                        [
                            row.source_id,
                            row.study_type,
                            _trim("; ".join(row.key_findings), 180),
                            _trim("; ".join(row.limitations), 160),
                            row.evidence_direction,
                        ]
                    )
                    + " |"
                )
        else:
            lines.append("No evidence rows were extracted.")

        lines.extend(["", "## Critical Appraisal", ""])
        if appraisals:
            for appraisal in appraisals:
                lines.extend(
                    [
                        f"### {appraisal.source_id}",
                        "",
                        f"- Quality score: {appraisal.quality_score:.2f}",
                        f"- Confidence: {appraisal.confidence:.2f}",
                        f"- Strengths: {'; '.join(appraisal.methodological_strengths)}",
                        f"- Limitations: {'; '.join(appraisal.methodological_limitations)}",
                        f"- Bias risks: {'; '.join(appraisal.bias_risks)}",
                        "",
                    ]
                )
        else:
            lines.append("No appraisals were generated.")

        lines.extend(
            [
                "",
                "## Synthesis",
                "",
                synthesis.summary,
                "",
                "### Consensus Findings",
                "",
            ]
        )
        lines.extend(
            [f"- {finding}" for finding in synthesis.consensus_findings]
            or ["- No source-grounded consensus finding was generated."]
        )
        lines.extend(["", "### Conflicts and Limitations", ""])
        lines.extend(
            [f"- {finding}" for finding in synthesis.conflicting_findings]
            or ["- No direct conflicts were detected heuristically."]
        )
        lines.extend([f"- {limitation}" for limitation in synthesis.limitations])
        lines.extend(["", "### Research Gaps", ""])
        for gap in synthesis.gaps:
            support = (
                f" Sources: {', '.join(gap.supporting_source_ids)}."
                if gap.supporting_source_ids
                else ""
            )
            follow_up = (
                f" Follow-up: {gap.follow_up_question}"
                if gap.follow_up_question
                else ""
            )
            lines.append(f"- {gap.gap}{support}{follow_up}")

        lines.extend(["", "## References", ""])
        for source in included_sources:
            lines.append(f"- [{source.source_id}] {source.citation}")

        lines.extend(["", "## Screening Decisions", ""])
        for decision in screening_decisions:
            lines.append(
                f"- [{decision.source_id}] {decision.decision} "
                f"({decision.relevance_score:.2f}): {'; '.join(decision.reasons)}"
            )
        return "\n".join(lines).strip() + "\n"


def _infer_study_type(source: LiteratureSource) -> str:
    text = f"{source.publication_type or ''} {source.title} {source.abstract or ''}".lower()
    if "meta-analysis" in text or "meta analysis" in text:
        return "meta-analysis"
    if "systematic review" in text:
        return "systematic review"
    if "randomized" in text or "randomised" in text:
        return "randomized trial"
    if "review" in text:
        return "review"
    if "observational" in text or "associated" in text:
        return "observational study"
    if source.is_preprint:
        return "preprint"
    return source.publication_type or "unspecified study"


def _infer_domain(source: LiteratureSource) -> str:
    text = f"{source.venue or ''} {' '.join(source.keywords)}".lower()
    if any(term in text for term in ["bio", "medical", "pubmed", "clinical"]):
        return "biomedical"
    if any(term in text for term in ["learning", "memory", "cognitive", "sleep"]):
        return "cognitive science"
    return "general research"


def _infer_method(source: LiteratureSource) -> str:
    study_type = _infer_study_type(source)
    if study_type == "randomized trial":
        return "Randomized comparison inferred from source text"
    if study_type in {"systematic review", "meta-analysis", "review"}:
        return "Secondary synthesis inferred from source type"
    return "Method details summarized from title and abstract heuristics"


def _source_limitations(source: LiteratureSource) -> list[str]:
    limitations: list[str] = []
    if not source.abstract and not source.extracted_text:
        limitations.append("No abstract or full text available")
    if source.year and source.year < 2015:
        limitations.append("Older source")
    if source.is_preprint:
        limitations.append("Preprint status")
    return limitations or ["Limitations require domain-expert review"]


def _infer_evidence_direction(source: LiteratureSource) -> str:
    text = f"{source.title} {source.abstract or ''}".lower()
    if any(term in text for term in ["mixed", "inconsistent", "unclear", "smaller"]):
        return "mixed"
    if any(
        term in text
        for term in ["associated", "improved", "stronger", "support", "linked"]
    ):
        return "supportive"
    return "contextual"


def _common_themes(sources: list[LiteratureSource], limit: int = 5) -> list[str]:
    counter: Counter[str] = Counter()
    for source in sources:
        counter.update(_tokens(" ".join([source.title, source.abstract or ""])))
        counter.update(token.lower() for token in source.keywords)
    return [term for term, _count in counter.most_common(limit)]


def _register() -> None:
    registry.register("plan_literature_search", lambda: LiteratureSearchPlanningTool())
    registry.register("retrieve_literature_sources", lambda: LiteratureRetrievalTool())
    registry.register(
        "curate_literature_sources", lambda: LiteratureSourceCurationTool()
    )
    registry.register(
        "appraise_literature_evidence", lambda: LiteratureEvidenceAppraisalTool()
    )
    registry.register("synthesize_literature_review", lambda: LiteratureSynthesisTool())


_register()


__all__ = [
    "FixtureLiteratureAdapter",
    "LiteratureEvidenceAppraisalTool",
    "LiteratureRetrievalTool",
    "LiteratureSearchPlanningTool",
    "LiteratureSourceAdapter",
    "LiteratureSourceCurationTool",
    "LiteratureSynthesisTool",
    "OpenAlexLiteratureAdapter",
    "PubMedLiteratureAdapter",
    "WebLiteratureAdapter",
    "extract_review_terms",
]
