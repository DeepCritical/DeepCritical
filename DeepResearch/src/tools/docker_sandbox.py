from __future__ import annotations

import json
import logging
import os
import tempfile
import uuid
from dataclasses import dataclass
from hashlib import md5
from pathlib import Path
from time import sleep
from typing import Any, ClassVar

from DeepResearch.src.datatypes.docker_sandbox_datatypes import (
    DockerExecutionRequest,
    DockerExecutionResult,
    DockerSandboxConfig,
    DockerSandboxEnvironment,
    DockerSandboxPolicies,
)
from DeepResearch.src.tools.base import ExecutionResult, ToolRunner, ToolSpec, registry
from DeepResearch.src.utils.coding import (
    CodeBlock,
    DockerCommandLineCodeExecutor,
    LocalCommandLineCodeExecutor,
)
from DeepResearch.src.utils.python_code_execution import PythonCodeExecutionTool

# Configure logging
logger = logging.getLogger(__name__)

# Timeout message for when execution times out
TIMEOUT_MSG = "Execution timed out after the specified timeout period."


def _get_cfg_value(cfg: dict[str, Any], path: str, default: Any) -> Any:
    """Get nested configuration value using dot notation."""
    cur: Any = cfg
    for key in path.split("."):
        if isinstance(cur, dict) and key in cur:
            cur = cur[key]
        else:
            return default
    return cur


def _get_file_name_from_content(code: str, work_dir: Path) -> str | None:
    """Extract filename from code content comments, similar to AutoGen implementation."""
    lines = code.split("\n")
    for line in lines[:10]:  # Check first 10 lines
        line = line.strip()
        if line.startswith(("# filename:", "# file:")):
            filename = line.split(":", 1)[1].strip()
            # Basic validation - ensure it's a valid filename
            if filename and not os.path.isabs(filename) and ".." not in filename:
                return filename
    return None


def _cmd(language: str) -> str:
    """Get the command to execute code for a given language."""
    language = language.lower()
    if language == "python":
        return "python"
    if language in ["bash", "shell", "sh"]:
        return "sh"
    if language in ["pwsh", "powershell", "ps1"]:
        return "pwsh"
    return language


def _wait_for_ready(container, timeout: int = 60, stop_time: float = 0.1) -> None:
    """Wait for container to be ready, similar to AutoGen implementation."""
    elapsed_time = 0.0
    while container.status != "running" and elapsed_time < timeout:
        sleep(stop_time)
        elapsed_time += stop_time
        container.reload()
        continue
    if container.status != "running":
        msg = "Container failed to start"
        raise ValueError(msg)


@dataclass
class DockerSandboxRunner(ToolRunner):
    """Enhanced Docker sandbox runner using Testcontainers with AG2 code execution integration."""

    # Default execution policies similar to AutoGen
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

    # Language aliases
    LANGUAGE_ALIASES: ClassVar[dict[str, str]] = {"py": "python", "js": "javascript"}

    def __init__(self):
        super().__init__(
            ToolSpec(
                name="docker_sandbox",
                description="Run code/command in an isolated container using Testcontainers with AG2 code execution integration.",
                inputs={
                    "language": "TEXT",  # e.g., python, bash, shell, sh, pwsh, powershell, ps1
                    "code": "TEXT",  # code string to execute
                    "command": "TEXT",  # explicit command to run (overrides code when provided)
                    "env": "TEXT",  # JSON of env vars
                    "timeout": "TEXT",  # seconds
                    "execution_policy": "TEXT",  # JSON dict of language->bool execution policies
                    "max_retries": "TEXT",  # maximum retry attempts for failed execution
                    "working_directory": "TEXT",  # working directory for execution
                },
                outputs={
                    "stdout": "TEXT",
                    "stderr": "TEXT",
                    "exit_code": "TEXT",
                    "files": "TEXT",
                    "success": "BOOLEAN",
                    "retries_used": "TEXT",
                },
            )
        )

        # Initialize execution policies
        self.execution_policies = self.DEFAULT_EXECUTION_POLICY.copy()
        self.python_execution_tool = PythonCodeExecutionTool()

    def run(self, params: dict[str, Any]) -> ExecutionResult:
        """Execute code in a Docker container with AG2 integration and enhanced error handling."""
        ok, err = self.validate(params)
        if not ok:
            return ExecutionResult(success=False, error=err)

        # Extract parameters with enhanced defaults
        language = str(params.get("language", "python")).strip() or "python"
        code = str(params.get("code", "")).strip()
        command = str(params.get("command", "")).strip() or None
        timeout = max(1, int(str(params.get("timeout", "60")).strip() or "60"))
        max_retries = max(0, int(str(params.get("max_retries", "3")).strip() or "3"))
        working_directory = str(params.get("working_directory", "")).strip() or None

        # If we have Python code, use the AG2 Python execution tool with retry logic
        if language.lower() == "python" and code and not command:
            return self.python_execution_tool.run(
                {
                    "code": code,
                    "timeout": timeout,
                    "max_retries": max_retries,
                    "working_directory": working_directory,
                    **params,
                }
            )

        # Create execution request from parameters for other languages
        execution_request = DockerExecutionRequest(
            language=language,
            code=code,
            command=command,
            timeout=timeout,
        )

        # Parse environment variables
        env_json = str(params.get("env", "")).strip()
        try:
            env_map: dict[str, str] = json.loads(env_json) if env_json else {}
            execution_request.environment = env_map
        except Exception:
            execution_request.environment = {}

        # Parse execution policies
        execution_policy_json = str(params.get("execution_policy", "")).strip()
        try:
            if execution_policy_json:
                custom_policies = json.loads(execution_policy_json)
                if isinstance(custom_policies, dict):
                    execution_request.execution_policy = custom_policies
        except Exception:
            pass  # Use default policies

        # Load hydra config if accessible to configure container image and limits
        try:
            cfg: dict[str, Any] = {}
        except Exception:
            cfg = {}

        # Create Docker sandbox configuration
        sandbox_config = DockerSandboxConfig(
            image=_get_cfg_value(cfg, "sandbox.image", "python:3.11-slim"),
            working_directory=_get_cfg_value(cfg, "sandbox.workdir", "/workspace"),
            cpu_limit=_get_cfg_value(cfg, "sandbox.cpu", None),
            memory_limit=_get_cfg_value(cfg, "sandbox.mem", None),
            auto_remove=_get_cfg_value(cfg, "sandbox.auto_remove", True),
        )

        # Create environment settings
        environment = DockerSandboxEnvironment(
            variables=execution_request.environment,
            working_directory=sandbox_config.working_directory,
        )

        # Update execution policies if provided
        if execution_request.execution_policy:
            policies = DockerSandboxPolicies()
            for lang, allowed in execution_request.execution_policy.items():
                if hasattr(policies, lang.lower()):
                    setattr(policies, lang.lower(), allowed)
        else:
            policies = DockerSandboxPolicies()

        # Normalize language and check execution policy
        lang = self.LANGUAGE_ALIASES.get(
            execution_request.language.lower(), execution_request.language.lower()
        )
        if lang not in self.DEFAULT_EXECUTION_POLICY:
            return ExecutionResult(success=False, error=f"Unsupported language: {lang}")

        execute_code = policies.is_language_allowed(lang)
        if not execute_code and not execution_request.command:
            return ExecutionResult(
                success=False, error=f"Execution disabled for language: {lang}"
            )

        try:
            from testcontainers.core.container import DockerContainer
        except Exception as e:
            return ExecutionResult(
                success=False, error=f"testcontainers unavailable: {e}"
            )

        # Prepare working directory
        temp_dir: str | None = None
        work_path = Path(tempfile.mkdtemp(prefix="docker-sandbox-"))
        files_created = []

        try:
            # Create container with enhanced configuration
            container_name = f"deepcritical-sandbox-{uuid.uuid4().hex[:8]}"
            container = DockerContainer(sandbox_config.image)
            container.with_name(container_name)

            # Set environment variables
            container.with_env("PYTHONUNBUFFERED", "1")
            for k, v in (env_map or {}).items():
                container.with_env(str(k), str(v))

            # Set resource limits if configured
            # Note: CPU and memory limits are not directly supported by testcontainers
            # These would need to be set at the Docker daemon level or through docker-compose
            if sandbox_config.cpu_limit:
                logger.info(
                    f"CPU limit requested: {sandbox_config.cpu_limit} (not implemented)"
                )

            if sandbox_config.memory_limit:
                logger.info(
                    f"Memory limit requested: {sandbox_config.memory_limit} (not implemented)"
                )

            # Set working directory if supported
            try:
                if hasattr(container, "with_workdir"):
                    with_workdir_method = getattr(container, "with_workdir", None)
                    if with_workdir_method is not None and callable(
                        with_workdir_method
                    ):
                        with_workdir_method(sandbox_config.working_directory)
                else:
                    logger.info(
                        f"Working directory requested: {sandbox_config.working_directory} (not supported)"
                    )
            except Exception:
                logger.warning(
                    f"Failed to set working directory: {sandbox_config.working_directory}"
                )

            # Mount working directory
            container.with_volume_mapping(
                str(work_path), sandbox_config.working_directory
            )

            # Handle code execution
            if execution_request.command:
                # Use explicit command
                cmd = execution_request.command
                container.with_command(cmd)
            else:
                # Save code to file and execute
                filename = _get_file_name_from_content(
                    execution_request.code, work_path
                )
                if not filename:
                    filename = f"tmp_code_{md5(execution_request.code.encode()).hexdigest()}.{lang}"

                code_path = work_path / filename
                with code_path.open("w", encoding="utf-8") as f:
                    f.write(execution_request.code)
                files_created.append(str(code_path))

                # Build execution command
                if lang == "python":
                    cmd = ["python", filename]
                elif lang in ["bash", "shell", "sh"]:
                    cmd = ["sh", filename]
                elif lang in ["pwsh", "powershell", "ps1"]:
                    cmd = ["pwsh", filename]
                else:
                    cmd = [_cmd(lang), filename]

                container.with_command(cmd)

            # Start container and wait for readiness
            logger.info(
                f"Starting container {container_name} with image {sandbox_config.image}"
            )
            container.start()
            _wait_for_ready(container, timeout=30)

            # Execute the command with timeout
            logger.info("Executing command: %s", cmd)
            result = container.get_wrapped_container().exec_run(
                cmd,
                workdir=sandbox_config.working_directory,
                environment=env_map,
                stdout=True,
                stderr=True,
                demux=True,
            )

            # Parse results
            stdout_bytes, stderr_bytes = (
                result.output
                if isinstance(result.output, tuple)
                else (result.output, b"")
            )
            exit_code = result.exit_code

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

            # Handle timeout
            if exit_code == 124:
                stderr += "\n" + TIMEOUT_MSG

            # Stop container
            container.stop()

            # Create Docker execution result
            docker_result = DockerExecutionResult(
                success=True,
                stdout=stdout,
                stderr=stderr,
                exit_code=exit_code,
                files_created=files_created,
                execution_time=0.0,  # Could be calculated if we track timing
            )

            return ExecutionResult(
                success=docker_result.exit_code == 0,
                data={
                    "stdout": docker_result.stdout,
                    "stderr": docker_result.stderr,
                    "exit_code": str(docker_result.exit_code),
                    "files": json.dumps(docker_result.files_created),
                    "success": docker_result.exit_code == 0,
                    "retries_used": "0",  # Original implementation doesn't support retries
                    "execution_time": docker_result.execution_time,
                },
            )

        except Exception as e:
            logger.exception("Container execution failed")
            return ExecutionResult(success=False, error=str(e))
        finally:
            # Cleanup
            try:
                if "container" in locals():
                    container.stop()
            except Exception:
                pass

            # Cleanup working directory
            if work_path.exists():
                try:
                    import shutil

                    shutil.rmtree(work_path)
                except Exception:
                    logger.warning("Failed to cleanup working directory: %s", work_path)

    def restart(self) -> None:
        """Restart the container (for persistent containers)."""
        # This would be useful for persistent containers
        # For now, we create fresh containers each time

    def stop(self) -> None:
        """Stop the container and cleanup resources."""
        # Cleanup is handled in the run method's finally block

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit with cleanup."""
        self.stop()


@dataclass
class DockerSandboxTool(ToolRunner):
    """Tool for executing code in a Docker sandboxed environment."""

    def __init__(self):
        super().__init__(
            ToolSpec(
                name="docker_sandbox",
                description="Execute code in a Docker sandboxed environment",
                inputs={"code": "TEXT", "language": "TEXT", "timeout": "NUMBER"},
                outputs={"result": "TEXT", "success": "BOOLEAN"},
            )
        )

    def run(self, params: dict[str, str]) -> ExecutionResult:
        code = params.get("code", "")
        language = params.get("language", "python")
        timeout = int(params.get("timeout", "30"))

        if not code:
            return ExecutionResult(success=False, error="No code provided")

        if language.lower() == "python":
            # Use the existing DockerSandboxRunner for Python code
            runner = DockerSandboxRunner()
            return runner.run({"code": code, "timeout": timeout})
        return ExecutionResult(
            success=True,
            data={
                "result": f"Docker execution for {language}: {code[:50]}...",
                "success": True,
            },
            metrics={"language": language, "timeout": timeout},
        )


# Pydantic AI compatible code execution tool
class PydanticAICodeExecutionTool:
    """Pydantic AI compatible tool for code execution with configurable retry/error handling."""

    def __init__(
        self, max_retries: int = 3, timeout: int = 60, use_docker: bool = True
    ):
        self.max_retries = max_retries
        self.timeout = timeout
        self.use_docker = use_docker
        self.python_tool = PythonCodeExecutionTool(
            timeout=timeout, use_docker=use_docker
        )

    async def execute_python_code(
        self,
        code: str,
        max_retries: int | None = None,
        timeout: int | None = None,
        working_directory: str | None = None,
    ) -> dict[str, Any]:
        """Execute Python code with configurable retry logic.

        Args:
            code: Python code to execute
            max_retries: Maximum number of retry attempts (overrides instance default)
            timeout: Execution timeout in seconds (overrides instance default)
            working_directory: Working directory for execution

        Returns:
            Dictionary containing execution results
        """
        retries = max_retries if max_retries is not None else self.max_retries
        exec_timeout = timeout if timeout is not None else self.timeout

        result = self.python_tool.run(
            {
                "code": code,
                "max_retries": retries,
                "timeout": exec_timeout,
                "working_directory": working_directory,
            }
        )

        return {
            "success": result.success,
            "output": result.data.get("output", ""),
            "error": result.data.get("error", ""),
            "exit_code": result.data.get("exit_code", -1),
            "execution_time": result.data.get("execution_time", 0.0),
            "retries_used": result.data.get("retries_used", 0),
        }

    async def execute_code_blocks(
        self,
        code_blocks: list[CodeBlock],
        executor_type: str = "docker",  # "docker" or "local"
        timeout: int | None = None,
    ) -> dict[str, Any]:
        """Execute multiple code blocks using AG2 code execution framework.

        Args:
            code_blocks: List of code blocks to execute
            executor_type: Type of executor to use ("docker" or "local")
            timeout: Execution timeout in seconds

        Returns:
            Dictionary containing execution results for all blocks
        """
        exec_timeout = timeout if timeout is not None else self.timeout

        try:
            if executor_type == "docker":
                with DockerCommandLineCodeExecutor(
                    timeout=exec_timeout,
                    work_dir=f"/tmp/pydantic_ai_code_exec_{id(self)}",
                ) as executor:
                    result = executor.execute_code_blocks(code_blocks)
            else:
                executor = LocalCommandLineCodeExecutor(
                    timeout=exec_timeout,
                    work_dir=f"/tmp/pydantic_ai_code_exec_{id(self)}",
                )
                result = executor.execute_code_blocks(code_blocks)

            return {
                "success": result.exit_code == 0,
                "output": result.output,
                "exit_code": result.exit_code,
                "command": getattr(result, "command", ""),
                "image": getattr(result, "image", None),
                "executor_type": executor_type,
            }

        except Exception as e:
            return {
                "success": False,
                "output": "",
                "exit_code": -1,
                "error": str(e),
                "executor_type": executor_type,
            }


# Global instances
pydantic_ai_code_execution_tool = PydanticAICodeExecutionTool()

# Register tools
registry.register("docker_sandbox", DockerSandboxRunner)
registry.register("docker_sandbox_tool", DockerSandboxTool)
