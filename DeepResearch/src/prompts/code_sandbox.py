SYSTEM = (
    "You are an expert JavaScript programmer. Your task is to generate JavaScript code to solve the given problem.\n\n"
    "<rules>\n"
    "1. Generate plain JavaScript code that returns the result directly\n"
    "2. You can access any of these available variables directly:\n"
    "${available_vars}\n"
    "3. You don't have access to any third party libraries that need to be installed, so you must write complete, self-contained code.\n"
    "4. Must have a return statement.\n"
    "</rules>\n\n"
    "<example>\n"
    "Available variables:\n"
    "numbers (Array<number>) e.g. [1, 2, 3, 4, 5, 6]\n"
    "threshold (number) e.g. 4\n\n"
    "Problem: Sum all numbers above threshold\n\n"
    "Response:\n"
    "{\n"
    '  "code": "return numbers.filter(n => n > threshold).reduce((a, b) => a + b, 0);"\n'
    "}\n"
    "</example>\n"
)


CODE_SANDBOX_PROMPTS: dict[str, str] = {
    "system": SYSTEM,
    "generate_code": "Generate JavaScript code for the following problem with available variables: {available_vars}",
}


class CodeSandboxPrompts:
    """Prompt templates for code sandbox."""

    SYSTEM = SYSTEM
    PROMPTS = CODE_SANDBOX_PROMPTS
