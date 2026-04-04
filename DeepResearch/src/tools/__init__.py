"""Tool package exports.

Keep package import lightweight so importing one tool module does not eagerly
initialize unrelated integrations.
"""

from __future__ import annotations

from importlib import import_module
from typing import Any

_DEFAULT_REGISTRY_MODULES = (
    "analytics_tools",
    "bioinformatics_tools",
    "deepsearch_tools",
    "deepsearch_workflow_tool",
    "docker_sandbox",
    "hypothesis_tools",
    "integrated_search_tools",
    "mock_tools",
    "openmm_tools",
    "pyd_ai_tools",
    "websearch_tools",
    "workflow_tools",
)

_SUBMODULE_EXPORTS = {
    "analytics_tools",
    "bioinformatics_tools",
    "code_sandbox",
    "deepsearch_tools",
    "deepsearch_workflow_tool",
    "docker_sandbox",
    "hypothesis_tools",
    "integrated_search_tools",
    "mock_tools",
    "openmm_tools",
    "pyd_ai_tools",
    "websearch_tools",
    "workflow_tools",
}

_CLASS_EXPORTS = {
    "ChunkedSearchTool": ("websearch_tools", "ChunkedSearchTool"),
    "DeepSearchTool": ("deepsearch_tools", "DeepSearchTool"),
    "GOAnnotationTool": ("bioinformatics_tools", "GOAnnotationTool"),
    "PubMedRetrievalTool": ("bioinformatics_tools", "PubMedRetrievalTool"),
    "RAGSearchTool": ("integrated_search_tools", "RAGSearchTool"),
    "WebSearchTool": ("websearch_tools", "WebSearchTool"),
}

_registry_state = {"bootstrapped": False}


def _ensure_default_registrations() -> None:
    """Populate the default tool registry on demand."""

    if _registry_state["bootstrapped"]:
        return

    for module_name in _DEFAULT_REGISTRY_MODULES:
        import_module(f"{__name__}.{module_name}")

    _registry_state["bootstrapped"] = True


def __getattr__(name: str) -> Any:
    if name == "registry":
        _ensure_default_registrations()
        from .base import registry

        return registry

    if name in _SUBMODULE_EXPORTS:
        return import_module(f"{__name__}.{name}")

    if name in _CLASS_EXPORTS:
        module_name, attr_name = _CLASS_EXPORTS[name]
        module = import_module(f"{__name__}.{module_name}")
        return getattr(module, attr_name)

    msg = f"module {__name__!r} has no attribute {name!r}"
    raise AttributeError(msg)


__all__ = [
    "ChunkedSearchTool",
    "DeepSearchTool",
    "GOAnnotationTool",
    "PubMedRetrievalTool",
    "RAGSearchTool",
    "WebSearchTool",
    "analytics_tools",
    "bioinformatics_tools",
    "code_sandbox",
    "deepsearch_tools",
    "deepsearch_workflow_tool",
    "docker_sandbox",
    "hypothesis_tools",
    "integrated_search_tools",
    "mock_tools",
    "openmm_tools",
    "pyd_ai_tools",
    "registry",
    "websearch_tools",
    "workflow_tools",
]
