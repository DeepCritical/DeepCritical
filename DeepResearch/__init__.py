__all__ = [
    "app",
    "tools",
    "WebSearchTool",
    "ChunkedSearchTool",
    "GOAnnotationTool",
    "PubMedRetrievalTool",
    "DeepSearchTool",
    "RAGSearchTool",
    "registry",
]

# Direct import for tools to make them available for documentation
try:
    from .src.tools import (
        WebSearchTool,
        ChunkedSearchTool,
        GOAnnotationTool,
        PubMedRetrievalTool,
        DeepSearchTool,
        RAGSearchTool,
        registry,
    )
except ImportError:
    # Fallback for when tools can't be imported
    pass


# Lazy import for tools to avoid circular imports
def __getattr__(name):
    if name == "tools":
        from .src import tools

        return tools
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")
