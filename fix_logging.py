#!/usr/bin/env python3
"""
Script to automatically fix f-string logging issues in Python files.
Converts f-string logging calls to lazy % formatting.
"""

import re
import sys
from pathlib import Path


def fix_fstring_logging(content: str) -> str:
    """
    Fix f-string logging calls by converting them to lazy % formatting.

    This handles patterns like:
    - logger.info(f"message: {var}")
    - logger.exception(f"message: {e}")

    Becomes:
    - logger.info("message: %s", var)
    - logger.exception("message: %s", e)
    """

    # Pattern to match f-string logging calls
    pattern = r'(\s+)(\w+)\.(\w+)\(f"([^"]*\{\w+\}[^"]*)"\)'

    def replace_match(match):
        indent = match.group(1)
        logger_name = match.group(2)
        method_name = match.group(3)
        fstring_content = match.group(4)

        # Parse the f-string content to extract variables
        # Simple regex to find {variable} patterns
        var_pattern = r"\{(\w+)\}"
        variables = re.findall(var_pattern, fstring_content)

        if not variables:
            return match.group(0)  # No variables found, return unchanged

        # Replace {var} with %s in the string
        format_string = re.sub(var_pattern, "%s", fstring_content)

        # Create the new logging call
        if method_name == "exception":
            # For logging.exception, we typically only pass one argument (the exception)
            # The format string should not include the exception variable
            if len(variables) == 1:
                # Remove the last variable from format string if it's the exception
                parts = format_string.rsplit(" %s", 1)
                if len(parts) == 2:
                    format_string = parts[0]
                    args = f"{variables[0]}"
                else:
                    args = ", ".join(variables)
            else:
                args = ", ".join(variables)
        else:
            args = ", ".join(variables)

        return f'{indent}{logger_name}.{method_name}("{format_string}", {args})'

    return re.sub(pattern, replace_match, content)


def main():
    if len(sys.argv) != 2:
        print("Usage: python fix_logging.py <file_path>")
        sys.exit(1)

    file_path = Path(sys.argv[1])
    if not file_path.exists():
        print(f"File {file_path} does not exist")
        sys.exit(1)

    # Read the file
    with open(file_path, encoding="utf-8") as f:
        content = f.read()

    # Fix the logging calls
    fixed_content = fix_fstring_logging(content)

    # Write back if changed
    if fixed_content != content:
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(fixed_content)
        print(f"Fixed logging in {file_path}")
    else:
        print(f"No changes needed in {file_path}")


if __name__ == "__main__":
    main()
