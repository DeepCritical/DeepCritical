"""
DeepCritical utilities module.

This package keeps top-level imports lazy so utility submodules can be imported
without eagerly initializing deployment backends.
"""

from __future__ import annotations

from importlib import import_module
from typing import Any

_SUBMODULE_EXPORTS = {
    "analytics",
    "config_loader",
    "deepsearch_schemas",
    "deepsearch_utils",
    "execution_history",
    "execution_status",
    "pydantic_ai_utils",
    "tool_registry",
    "tool_specs",
}

_ATTR_EXPORTS = {
    "CodeBlock": ("coding", "CodeBlock"),
    "CodeExecutor": ("coding", "CodeExecutor"),
    "CodeExtractor": ("coding", "CodeExtractor"),
    "CodeResult": ("coding", "CodeResult"),
    "CommandLineCodeResult": ("coding", "CommandLineCodeResult"),
    "DockerCommandLineCodeExecutor": (
        "coding",
        "DockerCommandLineCodeExecutor",
    ),
    "DockerComposeDeployer": (
        "docker_compose_deployer",
        "DockerComposeDeployer",
    ),
    "IPythonCodeResult": ("coding", "IPythonCodeResult"),
    "JupyterClient": ("jupyter", "JupyterClient"),
    "JupyterCodeExecutor": ("jupyter", "JupyterCodeExecutor"),
    "JupyterConnectable": ("jupyter", "JupyterConnectable"),
    "JupyterConnectionInfo": ("jupyter", "JupyterConnectionInfo"),
    "JupyterKernelClient": ("jupyter", "JupyterKernelClient"),
    "LocalCommandLineCodeExecutor": (
        "coding",
        "LocalCommandLineCodeExecutor",
    ),
    "MarkdownCodeExtractor": ("coding", "MarkdownCodeExtractor"),
    "PythonCodeExecutionTool": (
        "python_code_execution",
        "PythonCodeExecutionTool",
    ),
    "PythonEnvironment": ("environments", "PythonEnvironment"),
    "SystemPythonEnvironment": ("environments", "SystemPythonEnvironment"),
    "TestcontainersDeployer": (
        "testcontainers_deployer",
        "TestcontainersDeployer",
    ),
    "WorkingDirectory": ("environments", "WorkingDirectory"),
}


def __getattr__(name: str) -> Any:
    if name in _SUBMODULE_EXPORTS:
        return import_module(f"{__name__}.{name}")

    if name in _ATTR_EXPORTS:
        module_name, attr_name = _ATTR_EXPORTS[name]
        module = import_module(f"{__name__}.{module_name}")
        return getattr(module, attr_name)

    msg = f"module {__name__!r} has no attribute {name!r}"
    raise AttributeError(msg)


__all__ = [
    "CodeBlock",
    "CodeExecutor",
    "CodeExtractor",
    "CodeResult",
    "CommandLineCodeResult",
    "DockerCommandLineCodeExecutor",
    "DockerComposeDeployer",
    "IPythonCodeResult",
    "JupyterClient",
    "JupyterCodeExecutor",
    "JupyterConnectable",
    "JupyterConnectionInfo",
    "JupyterKernelClient",
    "LocalCommandLineCodeExecutor",
    "MarkdownCodeExtractor",
    "PythonCodeExecutionTool",
    "PythonEnvironment",
    "SystemPythonEnvironment",
    "TestcontainersDeployer",
    "WorkingDirectory",
    "analytics",
    "config_loader",
    "deepsearch_schemas",
    "deepsearch_utils",
    "execution_history",
    "execution_status",
    "pydantic_ai_utils",
    "tool_registry",
    "tool_specs",
]
