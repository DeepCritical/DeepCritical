"""
Python code execution tool for DeepCritical.

Adapted from AG2's PythonCodeExecutionTool for use in DeepCritical's agent system
with enhanced error handling and pydantic-ai integration.
"""

import os
import tempfile
from typing import Annotated, Any

from pydantic import BaseModel, Field

from DeepResearch.src.tools.base import ExecutionResult, ToolRunner, ToolSpec
from DeepResearch.src.utils.code_utils import execute_code


class PythonCodeExecutionTool(ToolRunner):
    """Executes Python code in a given environment and returns the result."""

    def __init__(
        self,
        *,
        timeout: int = 30,
        work_dir: str | None = None,
        use_docker: bool = True,
    ):
        """Initialize the PythonCodeExecutionTool.

        **CAUTION**: If provided a local environment, this tool will execute code in your local environment, which can be dangerous if the code is untrusted.

        Args:
            timeout: Maximum execution time allowed in seconds, will raise a TimeoutError exception if exceeded.
            work_dir: Working directory for code execution.
            use_docker: Whether to use Docker for code execution.
        """
        # Store configuration parameters
        self.timeout = timeout
        self.work_dir = work_dir or tempfile.mkdtemp(prefix="deepcritical_code_exec_")
        self.use_docker = use_docker

        # Create tool spec
        self._spec = ToolSpec(
            name="python_code_execution",
            description="Executes Python code and returns the result with configurable retry/error handling.",
            inputs={
                "code": "TEXT",  # Python code to execute
                "timeout": "NUMBER",  # Execution timeout in seconds
                "use_docker": "BOOLEAN",  # Whether to use Docker
                "max_retries": "NUMBER",  # Maximum number of retry attempts
                "working_directory": "TEXT",  # Working directory path
            },
            outputs={
                "exit_code": "NUMBER",
                "output": "TEXT",
                "error": "TEXT",
                "success": "BOOLEAN",
                "execution_time": "NUMBER",
                "retries_used": "NUMBER",
            },
        )

    def run(self, params: dict[str, Any]) -> ExecutionResult:
        """Execute Python code with retry logic and error handling."""
        code = params.get("code", "").strip()
        timeout = max(1, int(params.get("timeout", self.timeout)))
        use_docker = params.get("use_docker", self.use_docker)
        max_retries = max(0, int(params.get("max_retries", 3)))
        working_directory = params.get(
            "working_directory", self.work_dir
        ) or tempfile.mkdtemp(prefix="deepcritical_code_exec_")

        if not code:
            return ExecutionResult(
                success=False,
                error="No code provided for execution",
                data={"error": "No code provided"},
            )

        # Ensure working directory exists
        os.makedirs(working_directory, exist_ok=True)

        last_error = None
        retries_used = 0

        # Retry loop
        for attempt in range(max_retries + 1):
            try:
                exit_code, output, image = execute_code(
                    code=code,
                    timeout=timeout,
                    work_dir=working_directory,
                    use_docker=use_docker,
                    lang="python",
                )

                success = exit_code == 0

                return ExecutionResult(
                    success=success,
                    data={
                        "exit_code": exit_code,
                        "output": output,
                        "error": "" if success else output,
                        "success": success,
                        "execution_time": 0.0,  # Could be enhanced to track timing
                        "retries_used": attempt,
                        "image": image,
                    },
                    metrics={
                        "exit_code": exit_code,
                        "retries_used": attempt,
                        "execution_time": 0.0,
                    },
                )

            except Exception as e:
                last_error = str(e)
                retries_used = attempt

                # If this is the last attempt, don't retry
                if attempt >= max_retries:
                    break

                # Log retry attempt
                print(
                    f"Code execution failed (attempt {attempt + 1}/{max_retries + 1}): {last_error}"
                )
                continue

        # All attempts failed
        return ExecutionResult(
            success=False,
            error=f"Code execution failed after {retries_used + 1} attempts: {last_error}",
            data={
                "exit_code": -1,
                "output": "",
                "error": last_error or "Unknown error",
                "success": False,
                "execution_time": 0.0,
                "retries_used": retries_used,
            },
        )
