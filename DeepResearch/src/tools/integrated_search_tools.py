"""
Integrated search tools combining websearch and analytics with RAG datatypes.

This module provides comprehensive search capabilities that integrate websearch,
analytics tracking, and RAG datatypes for a complete search and retrieval system.
"""

import json
from datetime import datetime
from typing import Any

from pydantic_ai import RunContext

from DeepResearch.src.datatypes.rag import Chunk, Document, RAGQuery, SearchType

from .analytics_tools import RecordRequestTool
from .base import ExecutionResult, ToolRunner, ToolSpec
from .websearch_tools import ChunkedSearchTool


class IntegratedSearchTool(ToolRunner):
    """Tool runner for integrated search operations with RAG datatypes."""

    def __init__(self):
        spec = ToolSpec(
            name="integrated_search",
            description="Perform web search with analytics tracking and RAG datatype conversion",
            inputs={
                "query": "TEXT",
                "search_type": "TEXT",
                "num_results": "INTEGER",
                "chunk_size": "INTEGER",
                "chunk_overlap": "INTEGER",
                "enable_analytics": "BOOLEAN",
                "convert_to_rag": "BOOLEAN",
            },
            outputs={
                "documents": "JSON",
                "chunks": "JSON",
                "analytics_recorded": "BOOLEAN",
                "processing_time": "FLOAT",
                "success": "BOOLEAN",
                "error": "TEXT",
            },
        )
        super().__init__(spec)

    def run(self, params: dict[str, Any]) -> ExecutionResult:
        """Execute integrated search operation."""
        start_time = datetime.now()

        try:
            # Extract parameters
            query = params.get("query", "")
            search_type = params.get("search_type", "search")
            num_results = params.get("num_results", 4)
            chunk_size = params.get("chunk_size", 1000)
            chunk_overlap = params.get("chunk_overlap", 0)
            enable_analytics = params.get("enable_analytics", True)
            convert_to_rag = params.get("convert_to_rag", True)

            if not query:
                return ExecutionResult(
                    success=False, error="Query parameter is required"
                )

            # Step 1: Perform chunked search
            chunked_tool = ChunkedSearchTool()
            chunked_result = chunked_tool.run(
                {
                    "query": query,
                    "search_type": search_type,
                    "num_results": num_results,
                    "chunk_size": chunk_size,
                    "chunk_overlap": chunk_overlap,
                    "heading_level": 3,
                    "min_characters_per_chunk": 50,
                    "max_characters_per_section": 4000,
                    "clean_text": True,
                }
            )

            if not chunked_result.success:
                return ExecutionResult(
                    success=False,
                    error=f"Chunked search failed: {chunked_result.error}",
                )

            # Step 2: Convert to RAG datatypes if requested
            documents = []
            chunks = []

            if convert_to_rag:
                raw_chunks = chunked_result.data.get("chunks", [])

                # Group chunks by source
                source_groups = {}
                for chunk_data in raw_chunks:
                    source_title = chunk_data.get("source_title", "Unknown")
                    if source_title not in source_groups:
                        source_groups[source_title] = []
                    source_groups[source_title].append(chunk_data)

                # Create documents and chunks
                for source_title, chunk_list in source_groups.items():
                    # Create document content
                    doc_content = "\n\n".join(
                        [chunk.get("text", "") for chunk in chunk_list]
                    )

                    # Create RAG Document
                    document = Document(
                        content=doc_content,
                        metadata={
                            "source_title": source_title,
                            "url": chunk_list[0].get("url", ""),
                            "source": chunk_list[0].get("source", ""),
                            "date": chunk_list[0].get("date", ""),
                            "domain": chunk_list[0].get("domain", ""),
                            "search_query": query,
                            "search_type": search_type,
                            "num_chunks": len(chunk_list),
                        },
                    )
                    documents.append(document)

                    # Create RAG Chunks (using Chunk dataclass fields)
                    for _i, chunk_data in enumerate(chunk_list):
                        chunk = Chunk(
                            text=chunk_data.get("text", ""),
                            # Place URL in context since Chunk has no source field
                            context=chunk_data.get("url", ""),
                        )
                        chunks.append(chunk)

            # Step 3: Record analytics if enabled
            analytics_recorded = False
            if enable_analytics:
                processing_time = (datetime.now() - start_time).total_seconds()
                analytics_tool = RecordRequestTool()
                analytics_result = analytics_tool.run(
                    {"duration": processing_time, "num_results": num_results}
                )
                analytics_recorded = analytics_result.success

            processing_time = (datetime.now() - start_time).total_seconds()

            return ExecutionResult(
                success=True,
                data={
                    "documents": [doc.model_dump() for doc in documents],
                    "chunks": [chunk.to_dict() for chunk in chunks],
                    "analytics_recorded": analytics_recorded,
                    "processing_time": processing_time,
                    "success": True,
                    "error": None,
                    "query": query,
                },
            )

        except Exception as e:
            processing_time = (datetime.now() - start_time).total_seconds()
            return ExecutionResult(
                success=False,
                error=f"Integrated search failed: {e!s}",
                data={"processing_time": processing_time, "success": False},
            )


class RAGSearchTool(ToolRunner):
    """Tool runner for RAG-compatible search operations."""

    def __init__(self):
        spec = ToolSpec(
            name="rag_search",
            description="Perform search optimized for RAG workflows with vector store integration",
            inputs={
                "query": "TEXT",
                "search_type": "TEXT",
                "num_results": "INTEGER",
                "chunk_size": "INTEGER",
                "chunk_overlap": "INTEGER",
            },
            outputs={
                "rag_query": "JSON",
                "documents": "JSON",
                "chunks": "JSON",
                "success": "BOOLEAN",
                "error": "TEXT",
            },
        )
        super().__init__(spec)

    def run(self, params: dict[str, Any]) -> ExecutionResult:
        """Execute RAG search operation."""
        try:
            # Extract parameters
            query = params.get("query", "")
            search_type = params.get("search_type", "search")
            num_results = params.get("num_results", 4)
            chunk_size = params.get("chunk_size", 1000)
            chunk_overlap = params.get("chunk_overlap", 0)

            if not query:
                return ExecutionResult(
                    success=False, error="Query parameter is required"
                )

            # Create RAG query
            rag_query = RAGQuery(
                text=query,
                search_type=SearchType.SIMILARITY,
                top_k=num_results,
                filters={"search_type": search_type, "chunk_size": chunk_size},
            )

            # Use integrated search to get documents and chunks
            integrated_tool = IntegratedSearchTool()
            search_result = integrated_tool.run(
                {
                    "query": query,
                    "search_type": search_type,
                    "num_results": num_results,
                    "chunk_size": chunk_size,
                    "chunk_overlap": chunk_overlap,
                    "enable_analytics": True,
                    "convert_to_rag": True,
                }
            )

            if not search_result.success:
                return ExecutionResult(
                    success=False, error=f"RAG search failed: {search_result.error}"
                )

            return ExecutionResult(
                success=True,
                data={
                    "rag_query": rag_query.model_dump(),
                    "documents": search_result.data.get("documents", []),
                    "chunks": search_result.data.get("chunks", []),
                    "success": True,
                    "error": None,
                },
            )

        except Exception as e:
            return ExecutionResult(success=False, error=f"RAG search failed: {e!s}")


# Pydantic AI Tool Functions
def integrated_search_tool(ctx: RunContext[Any]) -> str:
    """
    Perform integrated web search with analytics tracking and RAG datatype conversion.

    This tool combines web search, analytics recording, and RAG datatype conversion
    for a comprehensive search and retrieval system.

    Args:
        query: The search query (required)
        search_type: Type of search - "search" or "news" (optional, default: "search")
        num_results: Number of results to fetch, 1-20 (optional, default: 4)
        chunk_size: Size of each chunk in characters (optional, default: 1000)
        chunk_overlap: Overlap between chunks (optional, default: 0)
        enable_analytics: Whether to record analytics (optional, default: true)
        convert_to_rag: Whether to convert results to RAG format (optional, default: true)

    Returns:
        JSON string containing RAG documents, chunks, and metadata
    """
    # Extract parameters from context
    params = ctx.deps if isinstance(ctx.deps, dict) else {}

    # Create and run tool
    tool = IntegratedSearchTool()
    result = tool.run(params)

    if result.success:
        return json.dumps(
            {
                "documents": result.data.get("documents", []),
                "chunks": result.data.get("chunks", []),
                "analytics_recorded": result.data.get("analytics_recorded", False),
                "processing_time": result.data.get("processing_time", 0.0),
                "query": result.data.get("query", ""),
            }
        )
    return f"Integrated search failed: {result.error}"


def rag_search_tool(ctx: RunContext[Any]) -> str:
    """
    Perform search optimized for RAG workflows with vector store integration.

    This tool creates RAG-compatible search results that can be directly
    integrated with vector stores and RAG systems.

    Args:
        query: The search query (required)
        search_type: Type of search - "search" or "news" (optional, default: "search")
        num_results: Number of results to fetch, 1-20 (optional, default: 4)
        chunk_size: Size of each chunk in characters (optional, default: 1000)
        chunk_overlap: Overlap between chunks (optional, default: 0)

    Returns:
        JSON string containing RAG query, documents, and chunks
    """
    # Extract parameters from context
    params = ctx.deps if isinstance(ctx.deps, dict) else {}

    # Create and run tool
    tool = RAGSearchTool()
    result = tool.run(params)

    if result.success:
        return json.dumps(
            {
                "rag_query": result.data.get("rag_query", {}),
                "documents": result.data.get("documents", []),
                "chunks": result.data.get("chunks", []),
            }
        )
    return f"RAG search failed: {result.error}"


# Register tools with the global registry
def register_integrated_search_tools():
    """Register integrated search tools with the global registry."""
    from .base import registry

    registry.register("integrated_search", IntegratedSearchTool)
    registry.register("rag_search", RAGSearchTool)


# Auto-register when module is imported
register_integrated_search_tools()
