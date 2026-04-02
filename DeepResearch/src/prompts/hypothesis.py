"""
Prompt scaffolding for the hypothesis engine.

The first implementation uses deterministic workflow logic, but these prompt
definitions make the intended model responsibilities explicit and give the
engine a stable place to evolve if LLM-backed generation is added later.
"""

GENERATOR_SYSTEM = """
You generate multiple plausible, testable research hypotheses grounded in the
available evidence. Favor concrete mechanisms, measurable outcomes, and
clear assumptions over broad speculation.
""".strip()

EVALUATOR_SYSTEM = """
You evaluate research hypotheses across novelty, evidence support, testability,
falsifiability, and specificity. Favor concise, evidence-grounded judgments.
""".strip()

TESTING_PLAN_SYSTEM = """
You convert a ranked hypothesis into a practical validation plan with required
inputs, success criteria, and failure modes.
""".strip()

OUTPUT_INSTRUCTIONS = """
Return structured outputs that preserve:
- a short statement
- reasoning
- assumptions
- predictions
- supporting evidence references
- counter-evidence considerations
""".strip()


def build_prompt_bundle(mode: str) -> dict[str, str]:
    """Return the prompt bundle relevant to the requested hypothesis mode."""

    return {
        "mode": mode,
        "generator": GENERATOR_SYSTEM,
        "evaluator": EVALUATOR_SYSTEM,
        "testing_plan": TESTING_PLAN_SYSTEM,
        "output_instructions": OUTPUT_INSTRUCTIONS,
    }


__all__ = [
    "EVALUATOR_SYSTEM",
    "GENERATOR_SYSTEM",
    "OUTPUT_INSTRUCTIONS",
    "TESTING_PLAN_SYSTEM",
    "build_prompt_bundle",
]
