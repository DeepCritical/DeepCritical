"""
System Python environment for DeepCritical.

Adapted from AG2 SystemPythonEnvironment for executing code in the system Python.
"""

import logging
import os
import subprocess
import sys
from typing import Any

from DeepResearch.src.utils.environments.python_environment import PythonEnvironment

logger = logging.getLogger(__name__)

__all__ = ["SystemPythonEnvironment"]


class SystemPythonEnvironment(PythonEnvironment):
    """A Python environment using the system's Python installation."""

    def __init__(
        self,
        executable: str | None = None,
    ):
        """Initialize a system Python environment.

        Args:
            executable: Optional path to a specific Python executable.
                If None, uses the current Python executable.
        """
        self._executable = executable or sys.executable
        super().__init__()

    def _setup_environment(self) -> None:
        """Set up the system Python environment."""
        # Verify the Python executable exists
        if not os.path.exists(self._executable):
            raise RuntimeError(f"Python executable not found at: {self._executable}")

        logger.info(f"Using system Python at: {self._executable}")

    def _cleanup_environment(self) -> None:
        """Clean up the system Python environment."""
        # No cleanup needed for system Python

    def get_executable(self) -> str:
        """Get the path to the Python executable."""
        return self._executable

    def execute_code(
        self, code: str, script_path: str, timeout: int = 30
    ) -> dict[str, Any]:
        """Execute code using the system Python."""
        try:
            # Get the Python executable
            python_executable = self.get_executable()

            # Verify the executable exists
            if not os.path.exists(python_executable):
                return {
                    "success": False,
                    "error": f"Python executable not found at {python_executable}",
                }

            # Ensure the directory for the script exists
            script_dir = os.path.dirname(script_path)
            if script_dir:
                os.makedirs(script_dir, exist_ok=True)

            # Write the code to the script file
            self._write_to_file(script_path, code)

            logger.info(f"Wrote code to {script_path}")

            try:
                # Execute directly with subprocess
                result = self._run_subprocess([python_executable, script_path], timeout)

                # Main execution result
                return {
                    "success": result.returncode == 0,
                    "stdout": result.stdout,
                    "stderr": result.stderr,
                    "returncode": result.returncode,
                }
            except subprocess.TimeoutExpired:
                return {
                    "success": False,
                    "error": f"Execution timed out after {timeout} seconds",
                }

        except Exception as e:
            return {"success": False, "error": f"Execution error: {e!s}"}
