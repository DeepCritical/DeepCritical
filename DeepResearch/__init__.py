from __future__ import annotations

from importlib import import_module
from typing import Any

_TOOL_EXPORTS = {
    "ChunkedSearchTool",
    "DeepSearchTool",
    "GOAnnotationTool",
    "PubMedRetrievalTool",
    "RAGSearchTool",
    "WebSearchTool",
    "registry",
}

__all__ = [
    "ChunkedSearchTool",
    "DeepSearchTool",
    "GOAnnotationTool",
    "PubMedRetrievalTool",
    "RAGSearchTool",
    "WebSearchTool",
    "app",
    "registry",
    "tools",
]


def __getattr__(name: str) -> Any:
    if name == "tools":
        return import_module(f"{__name__}.src.tools")

    if name == "app":
        return import_module(f"{__name__}.app")

    if name in _TOOL_EXPORTS:
        tools_module = import_module(f"{__name__}.src.tools")
        return getattr(tools_module, name)

    msg = f"module {__name__!r} has no attribute {name!r}"
    raise AttributeError(msg)
