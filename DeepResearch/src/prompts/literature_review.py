"""
Prompt scaffolding for the critical literature review app.

The MVP workflow is deterministic, but these prompts make the intended model
responsibilities explicit for later LLM-backed screening or synthesis.
"""

QUESTION_DECOMPOSITION_PROMPT = """
Decompose the user question into review scope, core concepts, likely synonyms,
and inclusion or exclusion criteria.
""".strip()

SEARCH_STRATEGY_PROMPT = """
Create a concise search strategy for scholarly retrieval. Favor precise queries
that preserve the original question and include the most important concepts.
""".strip()

SCREENING_CRITERIA_PROMPT = """
Screen sources for relevance to the question. Preserve explicit reasons for
inclusion, exclusion, or uncertainty.
""".strip()

EVIDENCE_EXTRACTION_PROMPT = """
Extract study type, method, population or domain, key findings, limitations,
and evidence direction from each retained source.
""".strip()

CRITICAL_APPRAISAL_PROMPT = """
Critically appraise each source using transparent criteria. Separate strengths,
limitations, bias risks, and applicability notes.
""".strip()

SYNTHESIS_PROMPT = """
Synthesize retained sources into consensus findings, conflicting findings,
limitations, and research gaps. Tie claims to source identifiers.
""".strip()

GAP_ANALYSIS_PROMPT = """
Identify unanswered questions and evidence gaps that follow from the retained
sources rather than from unsupported speculation.
""".strip()

REPORT_FORMATTING_PROMPT = """
Format the final report as a source-grounded critical literature review with
screening summary, evidence table, appraisal, synthesis, gaps, and references.
""".strip()


def build_prompt_bundle(mode: str) -> dict[str, str]:
    """Return literature review prompt scaffolding for the requested mode."""

    return {
        "mode": mode,
        "question_decomposition": QUESTION_DECOMPOSITION_PROMPT,
        "search_strategy": SEARCH_STRATEGY_PROMPT,
        "screening_criteria": SCREENING_CRITERIA_PROMPT,
        "evidence_extraction": EVIDENCE_EXTRACTION_PROMPT,
        "critical_appraisal": CRITICAL_APPRAISAL_PROMPT,
        "synthesis": SYNTHESIS_PROMPT,
        "gap_analysis": GAP_ANALYSIS_PROMPT,
        "report_formatting": REPORT_FORMATTING_PROMPT,
    }


__all__ = [
    "CRITICAL_APPRAISAL_PROMPT",
    "EVIDENCE_EXTRACTION_PROMPT",
    "GAP_ANALYSIS_PROMPT",
    "QUESTION_DECOMPOSITION_PROMPT",
    "REPORT_FORMATTING_PROMPT",
    "SCREENING_CRITERIA_PROMPT",
    "SEARCH_STRATEGY_PROMPT",
    "SYNTHESIS_PROMPT",
    "build_prompt_bundle",
]
