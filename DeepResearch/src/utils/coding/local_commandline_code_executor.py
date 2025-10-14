"""
Local command line code executor for DeepCritical.

Adapted from AG2 for local code execution without Docker.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from typing import Any

from DeepResearch.src.utils.code_utils import _cmd

from .base import CodeBlock, CodeExecutor, CodeExtractor, CommandLineCodeResult
from .markdown_code_extractor import MarkdownCodeExtractor
from .utils import _get_file_name_from_content


class LocalCommandLineCodeExecutor(CodeExecutor):
    """A code executor class that executes code through local command line.

    The executor saves each code block in a file in the working directory, and then
    executes the code file locally. The executor executes the code blocks in the order
    they are received. Currently, the executor only supports Python and shell scripts.

    For Python code, use the language "python" for the code block.
    For shell scripts, use the language "bash", "shell", or "sh" for the code block.
    """

    DEFAULT_EXECUTION_POLICY: dict[str, bool] = {
        "bash": True,
        "shell": True,
        "sh": True,
        "pwsh": True,
        "powershell": True,
        "ps1": True,
        "python": True,
        "javascript": False,
        "html": False,
        "css": False,
    }
    LANGUAGE_ALIASES: dict[str, str] = {"py": "python", "js": "javascript"}

    def __init__(
        self,
        timeout: int = 60,
        work_dir: Path | str | None = None,
        execution_policies: dict[str, bool] | None = None,
    ):
        """Initialize the local command line code executor.

        Args:
            timeout: The timeout for code execution. Defaults to 60.
            work_dir: The working directory for the code execution. Defaults to Path(".").
            execution_policies: A dictionary mapping language names to boolean values that determine
                whether code in that language should be executed. True means code in that language
                will be executed, False means it will only be saved to a file. This overrides the
                default execution policies. Defaults to None.

        Raises:
            ValueError: On argument error.
        """
        if timeout < 1:
            raise ValueError("Timeout must be greater than or equal to 1.")

        work_dir = work_dir if work_dir is not None else Path()
        if isinstance(work_dir, str):
            work_dir = Path(work_dir)
        work_dir.mkdir(exist_ok=True)

        self._timeout = timeout
        self._work_dir = work_dir
        self._execution_policies = (
            execution_policies or self.DEFAULT_EXECUTION_POLICY.copy()
        )
        self._code_extractor = MarkdownCodeExtractor()

    @property
    def code_extractor(self) -> CodeExtractor:
        """The code extractor used by this code executor."""
        return self._code_extractor

    def execute_code_blocks(
        self, code_blocks: list[CodeBlock]
    ) -> CommandLineCodeResult:
        """Execute code blocks and return the result.

        Args:
            code_blocks: The code blocks to execute.

        Returns:
            CommandLineCodeResult: The result of the code execution.
        """
        # Execute code blocks sequentially
        combined_output = ""
        combined_exit_code = 0

        for code_block in code_blocks:
            result = self._execute_code_block(code_block)
            combined_output += result.output
            if result.exit_code != 0:
                combined_exit_code = result.exit_code

        return CommandLineCodeResult(
            exit_code=combined_exit_code,
            output=combined_output,
            command="",  # Not applicable for multiple blocks
            image=None,
        )

    def _execute_code_block(self, code_block: CodeBlock) -> CommandLineCodeResult:
        """Execute a single code block."""
        lang = self.LANGUAGE_ALIASES.get(
            code_block.language.lower(), code_block.language.lower()
        )

        if lang not in self._execution_policies:
            return CommandLineCodeResult(
                exit_code=1,
                output=f"Unsupported language: {lang}",
                command="",
                image=None,
            )

        if not self._execution_policies[lang]:
            # Save to file only
            filename = _get_file_name_from_content(code_block.code, self._work_dir)
            if not filename:
                filename = f"tmp_code_{hash(code_block.code)}.py"

            code_path = self._work_dir / filename
            with code_path.open("w", encoding="utf-8") as f:
                f.write(code_block.code)

            return CommandLineCodeResult(
                exit_code=0,
                output=f"Code saved to {filename} (execution disabled for {lang})",
                command="",
                image=None,
            )

        # Execute the code
        filename = _get_file_name_from_content(code_block.code, self._work_dir)
        if not filename:
            filename = f"tmp_code_{hash(code_block.code)}.py"

        code_path = self._work_dir / filename
        with code_path.open("w", encoding="utf-8") as f:
            f.write(code_block.code)

        # Build execution command
        if lang == "python":
            cmd = [sys.executable, str(code_path)]
        elif lang in ["bash", "shell", "sh"]:
            cmd = ["sh", str(code_path)]
        elif lang in ["pwsh", "powershell", "ps1"]:
            cmd = ["pwsh", str(code_path)]
        else:
            cmd = [_cmd(lang), str(code_path)]

        try:
            # Execute locally
            result = subprocess.run(
                cmd,
                check=False,
                cwd=self._work_dir,
                capture_output=True,
                text=True,
                timeout=self._timeout,
            )

            output = result.stdout + result.stderr

            return CommandLineCodeResult(
                exit_code=result.returncode,
                output=output,
                command=" ".join(cmd),
                image=None,
            )

        except subprocess.TimeoutExpired:
            return CommandLineCodeResult(
                exit_code=1,
                output=f"Execution timed out after {self._timeout} seconds",
                command=" ".join(cmd),
                image=None,
            )
        except Exception as e:
            return CommandLineCodeResult(
                exit_code=1,
                output=f"Execution failed: {e!s}",
                command=" ".join(cmd),
                image=None,
            )

    def restart(self) -> None:
        """Restart the code executor (no-op for local executor)."""
