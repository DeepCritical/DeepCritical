SYSTEM = (
    "You're helping fix a corrupted scanned markdown document that has stains (represented by �).\n"
    "Looking at the surrounding context, determine the original text should be in place of the � symbols.\n\n"
    "Rules:\n"
    "1. ONLY output the exact replacement text - no explanations, quotes, or additional text\n"
    "2. Keep your response appropriate to the length of the unknown sequence\n"
    "3. Consider the document appears to be in Chinese if that's what the context suggests\n"
)


BROKEN_CH_FIXER_PROMPTS: dict[str, str] = {
    "system": SYSTEM,
    "fix_broken_characters": "Fix the broken characters in the following text: {text}",
}


class BrokenCHFixerPrompts:
    """Prompt templates for broken character fixing."""

    SYSTEM = SYSTEM
    PROMPTS = BROKEN_CH_FIXER_PROMPTS
