"""
Docker-based command line code executor for DeepCritical.

Adapted from AG2's DockerCommandLineCodeExecutor for use in DeepCritical's
code execution system with enhanced error handling and pydantic-ai integration.
"""

from __future__ import annotations

import atexit
import logging
import uuid
from hashlib import md5
from pathlib import Path
from time import sleep
from types import TracebackType
from typing import Any, ClassVar

from docker.errors import ImageNotFound
from typing_extensions import Self

import docker
from DeepResearch.src.utils.code_utils import TIMEOUT_MSG, _cmd

from .base import CodeBlock, CodeExecutor, CodeExtractor, CommandLineCodeResult
from .markdown_code_extractor import MarkdownCodeExtractor
from .utils import _get_file_name_from_content, silence_pip

logger = logging.getLogger(__name__)


def _wait_for_ready(container: Any, timeout: int = 60, stop_time: float = 0.1) -> None:
    """Wait for container to be ready."""
    elapsed_time = 0.0
    while container.status != "running" and elapsed_time < timeout:
        sleep(stop_time)
        elapsed_time += stop_time
        container.reload()
        continue
    if container.status != "running":
        msg = "Container failed to start"
        raise ValueError(msg)


class DockerCommandLineCodeExecutor(CodeExecutor):
    """A code executor class that executes code through a command line environment in a Docker container.

    The executor first saves each code block in a file in the working directory, and then executes the
    code file in the container. The executor executes the code blocks in the order they are received.
    Currently, the executor only supports Python and shell scripts.

    For Python code, use the language "python" for the code block.
    For shell scripts, use the language "bash", "shell", or "sh" for the code block.
    """

    DEFAULT_EXECUTION_POLICY: ClassVar[dict[str, bool]] = {
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
    LANGUAGE_ALIASES: ClassVar[dict[str, str]] = {"py": "python", "js": "javascript"}

    def __init__(
        self,
        image: str = "python:3-slim",
        container_name: str | None = None,
        timeout: int = 60,
        work_dir: Path | str | None = None,
        bind_dir: Path | str | None = None,
        auto_remove: bool = True,
        stop_container: bool = True,
        execution_policies: dict[str, bool] | None = None,
        *,
        container_create_kwargs: dict[str, Any] | None = None,
    ):
        """Initialize the Docker command line code executor.

        Args:
            image: Docker image to use for code execution. Defaults to "python:3-slim".
            container_name: Name of the Docker container which is created. If None, will autogenerate a name. Defaults to None.
            timeout: The timeout for code execution. Defaults to 60.
            work_dir: The working directory for the code execution. Defaults to Path(".").
            bind_dir: The directory that will be bound to the code executor container. Useful for cases where you want to spawn
                the container from within a container. Defaults to work_dir.
            auto_remove: If true, will automatically remove the Docker container when it is stopped. Defaults to True.
            stop_container: If true, will automatically stop the
                container when stop is called, when the context manager exits or when
                the Python process exits with atext. Defaults to True.
            execution_policies: A dictionary mapping language names to boolean values that determine
                whether code in that language should be executed. True means code in that language
                will be executed, False means it will only be saved to a file. This overrides the
                default execution policies. Defaults to None.
            container_create_kwargs: Optional dict forwarded verbatim to
                "docker.client.containers.create". Use it to set advanced Docker
                options (environment variables, GPU device_requests, port mappings, etc.).
                Values here override the class defaults when keys collide. Defaults to None.

        Raises:
            ValueError: On argument error, or if the container fails to start.
        """
        work_dir = work_dir if work_dir is not None else Path()

        if timeout < 1:
            raise ValueError("Timeout must be greater than or equal to 1.")

        if isinstance(work_dir, str):
            work_dir = Path(work_dir)
        work_dir.mkdir(exist_ok=True)

        if bind_dir is None:
            bind_dir = work_dir
        elif isinstance(bind_dir, str):
            bind_dir = Path(bind_dir)

        client = docker.from_env()
        # Check if the image exists
        try:
            client.images.get(image)
        except ImageNotFound:
            logger.info(f"Pulling image {image}...")
            # Let the docker exception escape if this fails.
            client.images.pull(image)

        if container_name is None:
            container_name = f"deepcritical-code-exec-{uuid.uuid4()}"

        # build kwargs for docker.create
        base_kwargs: dict[str, Any] = {
            "image": image,
            "name": container_name,
            "entrypoint": "/bin/sh",
            "tty": True,
            "auto_remove": auto_remove,
            "volumes": {str(bind_dir.resolve()): {"bind": "/workspace", "mode": "rw"}},
            "working_dir": "/workspace",
        }

        if container_create_kwargs:
            for k in ("entrypoint", "volumes", "working_dir", "tty"):
                if k in container_create_kwargs:
                    logger.warning(
                        "DockerCommandLineCodeExecutor: overriding default %s=%s",
                        k,
                        container_create_kwargs[k],
                    )
            base_kwargs.update(container_create_kwargs)

        # Create the container
        self._container = client.containers.create(**base_kwargs)
        self._client = client
        self._container_name = container_name
        self._timeout = timeout
        self._work_dir = work_dir
        self._bind_dir = bind_dir
        self._auto_remove = auto_remove
        self._stop_container = stop_container
        self._execution_policies = (
            execution_policies or self.DEFAULT_EXECUTION_POLICY.copy()
        )
        self._code_extractor = MarkdownCodeExtractor()

        # Start the container
        self._container.start()
        _wait_for_ready(self._container, timeout=30)

        if stop_container:
            atexit.register(self.stop)

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
        image = self._container.image.tags[0] if self._container.image.tags else None

        for code_block in code_blocks:
            result = self._execute_code_block(code_block)
            combined_output += result.output
            if result.exit_code != 0:
                combined_exit_code = result.exit_code

        return CommandLineCodeResult(
            exit_code=combined_exit_code,
            output=combined_output,
            command="",  # Not applicable for multiple blocks
            image=image,
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
                filename = (
                    f"tmp_code_{md5(code_block.code.encode()).hexdigest()}.{lang}"
                )

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
            filename = f"tmp_code_{md5(code_block.code.encode()).hexdigest()}.{lang}"

        code_path = self._work_dir / filename
        with code_path.open("w", encoding="utf-8") as f:
            f.write(code_block.code)

        # Build execution command
        if lang == "python":
            cmd = ["python", filename]
        elif lang in ["bash", "shell", "sh"]:
            cmd = ["sh", filename]
        elif lang in ["pwsh", "powershell", "ps1"]:
            cmd = ["pwsh", filename]
        else:
            cmd = [_cmd(lang), filename]

        # Execute in container
        try:
            exec_result = self._container.exec_run(
                cmd,
                workdir="/workspace",
                stdout=True,
                stderr=True,
                demux=True,
            )

            stdout_bytes, stderr_bytes = (
                exec_result.output
                if isinstance(exec_result.output, tuple)
                else (exec_result.output, b"")
            )

            # Decode output
            stdout = (
                stdout_bytes.decode("utf-8", errors="replace")
                if isinstance(stdout_bytes, (bytes, bytearray))
                else str(stdout_bytes)
            )
            stderr = (
                stderr_bytes.decode("utf-8", errors="replace")
                if isinstance(stderr_bytes, (bytes, bytearray))
                else ""
            )

            exit_code = exec_result.exit_code

            # Handle timeout
            if exit_code == 124:
                stderr += "\n" + TIMEOUT_MSG

            output = stdout + stderr

            return CommandLineCodeResult(
                exit_code=exit_code,
                output=output,
                command=" ".join(cmd),
                image=self._container.image.tags[0]
                if self._container.image.tags
                else None,
            )

        except Exception as e:
            return CommandLineCodeResult(
                exit_code=1,
                output=f"Execution failed: {e!s}",
                command=" ".join(cmd),
                image=None,
            )

    def restart(self) -> None:
        """Restart the code executor."""
        self.stop()
        self._container.start()
        _wait_for_ready(self._container, timeout=30)

    def stop(self) -> None:
        """Stop the container."""
        try:
            if self._container:
                self._container.stop()
                if self._auto_remove:
                    self._container.remove()
        except Exception:
            # Container might already be stopped/removed
            pass

    def __enter__(self) -> Self:
        """Enter context manager."""
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        """Exit context manager."""
        if self._stop_container:
            self.stop()
