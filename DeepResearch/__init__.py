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
try:
    from .src.tools import (
        ChunkedSearchTool,
        DeepSearchTool,
        GOAnnotationTool,
        PubMedRetrievalTool,
        RAGSearchTool,
        WebSearchTool,
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
