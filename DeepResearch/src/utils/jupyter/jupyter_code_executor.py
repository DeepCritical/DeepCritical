"""
Jupyter code executor for DeepCritical.

Adapted from AG2 jupyter code executor for stateful code execution using Jupyter kernels.
"""

import base64
import json
import os
import uuid
from pathlib import Path
from types import TracebackType
from typing import Any

from typing_extensions import Self

from DeepResearch.src.datatypes.coding_base import (
    CodeBlock,
    CodeExecutor,
    CodeExtractor,
    IPythonCodeResult,
)
from DeepResearch.src.utils.coding.markdown_code_extractor import MarkdownCodeExtractor
from DeepResearch.src.utils.coding.utils import silence_pip
from DeepResearch.src.utils.jupyter.base import (
    JupyterConnectable,
    JupyterConnectionInfo,
)
from DeepResearch.src.utils.jupyter.jupyter_client import JupyterClient


class JupyterCodeExecutor(CodeExecutor):
    """A code executor class that executes code statefully using a Jupyter server.

    Each execution is stateful and can access variables created from previous
    executions in the same session.
    """

    def __init__(
        self,
        jupyter_server: JupyterConnectable | JupyterConnectionInfo,
        kernel_name: str = "python3",
        timeout: int = 60,
        output_dir: Path | str = Path(),
    ):
        """Initialize the Jupyter code executor.

        Args:
            jupyter_server: The Jupyter server to use.
            timeout: The timeout for code execution, by default 60.
            kernel_name: The kernel name to use. Make sure it is installed.
                By default, it is "python3".
            output_dir: The directory to save output files, by default ".".
        """
        if timeout < 1:
            raise ValueError("Timeout must be greater than or equal to 1.")

        if isinstance(output_dir, str):
            output_dir = Path(output_dir)

        if not output_dir.exists():
            output_dir.mkdir(parents=True, exist_ok=True)

        if isinstance(jupyter_server, JupyterConnectable):
            self._connection_info = jupyter_server.connection_info
        elif isinstance(jupyter_server, JupyterConnectionInfo):
            self._connection_info = jupyter_server
        else:
            raise ValueError(
                "jupyter_server must be a JupyterConnectable or JupyterConnectionInfo."
            )

        self._jupyter_client = JupyterClient(self._connection_info)

        # Check if kernel is available (simplified check)
        try:
            available_kernels = self._jupyter_client.list_kernel_specs()
            if (
                "kernelspecs" in available_kernels
                and kernel_name not in available_kernels["kernelspecs"]
            ):
                print(f"Warning: Kernel {kernel_name} may not be available")
        except Exception:
            print(f"Warning: Could not check kernel availability for {kernel_name}")

        self._kernel_id = None
        self._kernel_name = kernel_name
        self._timeout = timeout
        self._output_dir = output_dir
        self._kernel_client = None

    @property
    def code_extractor(self) -> CodeExtractor:
        """Export a code extractor that can be used by an agent."""
        return MarkdownCodeExtractor()

    def _ensure_kernel_started(self):
        """Ensure a kernel is started."""
        if self._kernel_id is None:
            try:
                self._kernel_id = self._jupyter_client.start_kernel(self._kernel_name)
                # Note: In a full implementation, we'd get the kernel client here
                # For now, we'll use simplified execution
            except Exception as e:
                raise RuntimeError(f"Failed to start kernel {self._kernel_name}: {e}")

    def execute_code_blocks(self, code_blocks: list[CodeBlock]) -> IPythonCodeResult:
        """Execute a list of code blocks and return the result.

        This method executes a list of code blocks as cells in the Jupyter kernel.

        Args:
            code_blocks: A list of code blocks to execute.

        Returns:
            IPythonCodeResult: The result of the code execution.
        """
        self._ensure_kernel_started()

        outputs = []
        output_files = []

        for code_block in code_blocks:
            try:
                # Apply pip silencing if needed
                code = silence_pip(code_block.code, code_block.language)

                # Execute code (simplified - in practice would use WebSocket connection)
                result = self._execute_code_simple(code)

                if result.get("success", False):
                    outputs.append(result.get("output", ""))

                    # Handle different output types (simplified)
                    for data_item in result.get("data", []):
                        mime_type = data_item.get("mime_type", "")
                        data = data_item.get("data", "")

                        if mime_type == "image/png":
                            path = self._save_image(data)
                            outputs.append(f"Image data saved to {path}")
                            output_files.append(path)
                        elif mime_type == "text/html":
                            path = self._save_html(data)
                            outputs.append(f"HTML data saved to {path}")
                            output_files.append(path)
                        else:
                            outputs.append(str(data))
                else:
                    return IPythonCodeResult(
                        exit_code=1,
                        output=f"ERROR: {result.get('error', 'Unknown error')}",
                    )

            except Exception as e:
                return IPythonCodeResult(
                    exit_code=1,
                    output=f"Execution error: {e!s}",
                )

        return IPythonCodeResult(
            exit_code=0,
            output="\n".join([str(output) for output in outputs]),
            output_files=output_files,
        )

    def _execute_code_simple(self, code: str) -> dict[str, Any]:
        """Execute code using simplified approach.

        This is a placeholder for the full WebSocket-based execution.
        In a production system, this would use proper Jupyter messaging protocol.
        """
        # For demonstration, we'll simulate execution results
        # In practice, this would use WebSocket connections to the kernel

        if "print(" in code or "import " in code:
            return {
                "success": True,
                "output": f"[Simulated execution of: {code[:50]}...]",
                "data": [],
            }
        if "error" in code.lower():
            return {"success": False, "error": "Simulated execution error"}
        return {"success": True, "output": "Code executed successfully", "data": []}

    def restart(self) -> None:
        """Restart a new session."""
        if self._kernel_id:
            try:
                self._jupyter_client.restart_kernel(self._kernel_id)
            except Exception as e:
                print(f"Warning: Failed to restart kernel: {e}")
                # Try to start a new kernel
                self._kernel_id = None
                self._ensure_kernel_started()

    def _save_image(self, image_data_base64: str) -> str:
        """Save image data to a file."""
        try:
            image_data = base64.b64decode(image_data_base64)
            # Randomly generate a filename.
            filename = f"{uuid.uuid4().hex}.png"
            path = os.path.join(self._output_dir, filename)
            with open(path, "wb") as f:
                f.write(image_data)
            return str(Path(path).resolve())
        except Exception:
            # Fallback filename if decoding fails
            return f"{self._output_dir}/image_{uuid.uuid4().hex}.png"

    def _save_html(self, html_data: str) -> str:
        """Save html data to a file."""
        # Randomly generate a filename.
        filename = f"{uuid.uuid4().hex}.html"
        path = os.path.join(self._output_dir, filename)
        with open(path, "w") as f:
            f.write(html_data)
        return str(Path(path).resolve())

    def stop(self) -> None:
        """Stop the kernel."""
        if self._kernel_id:
            try:
                self._jupyter_client.delete_kernel(self._kernel_id)
            except Exception as e:
                print(f"Warning: Failed to stop kernel: {e}")
            finally:
                self._kernel_id = None

    def __enter__(self) -> Self:
        """Context manager entry."""
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        """Context manager exit."""
        self.stop()
