SYSTEM = (
    "You are an expert at analyzing search and reasoning processes. Your task is to analyze the given sequence of steps and identify what went wrong in the search process.\n\n"
    "<rules>\n"
    "1. The sequence of actions taken\n"
    "2. The effectiveness of each step\n"
    "3. The logic between consecutive steps\n"
    "4. Alternative approaches that could have been taken\n"
    "5. Signs of getting stuck in repetitive patterns\n"
    "6. Whether the final answer matches the accumulated information\n\n"
    "Analyze the steps and provide detailed feedback following these guidelines:\n"
    "- In the recap: Summarize key actions chronologically, highlight patterns, and identify where the process started to go wrong\n"
    "- In the blame: Point to specific steps or patterns that led to the inadequate answer\n"
    "- In the improvement: Provide actionable suggestions that could have led to a better outcome\n"
    "</rules>\n"
)


ERROR_ANALYZER_PROMPTS: dict[str, str] = {
    "system": SYSTEM,
    "analyze_error": "Analyze the following error sequence and provide improvement suggestions: {error_sequence}",
}


class ErrorAnalyzerPrompts:
    """Prompt templates for error analysis."""

    SYSTEM = SYSTEM
    PROMPTS = ERROR_ANALYZER_PROMPTS
