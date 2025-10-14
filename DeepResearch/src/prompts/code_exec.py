SYSTEM = (
    "Execute the following code and return ONLY the final output as plain text.\n\n"
    "<code>\n"
    "${code}\n"
    "</code>\n"
)


CODE_EXEC_PROMPTS: dict[str, str] = {
    "system": SYSTEM,
    "execute_code": "Execute the following code: {code}",
}


class CodeExecPrompts:
    """Prompt templates for code execution."""

    SYSTEM = SYSTEM
    PROMPTS = CODE_EXEC_PROMPTS
