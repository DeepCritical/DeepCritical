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

# Direct import for tools to make them available for documentation
from contextlib import suppress

with suppress(ImportError):
    from .src.tools import (
        ChunkedSearchTool,
        DeepSearchTool,
        GOAnnotationTool,
        PubMedRetrievalTool,
        RAGSearchTool,
        WebSearchTool,
        registry,
    )


# Lazy import for tools to avoid circular imports
def __getattr__(name):
    if name == "tools":
        from .src import tools

        return tools

    msg = f"module '{__name__}' has no attribute '{name}'"
    raise AttributeError(msg)
