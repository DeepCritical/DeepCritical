"""
WebSearch tools for DeepCritical using Pydantic AI patterns.

This module provides Pydantic AI tool wrappers for the websearch_cleaned.py functionality,
integrating with the existing tool registry and datatypes.
"""

import asyncio
import json
from typing import Any

from pydantic import BaseModel, ConfigDict, Field
from pydantic_ai import RunContext

from .base import ExecutionResult, ToolRunner, ToolSpec
from .websearch_cleaned import search_and_chunk, search_web


class WebSearchRequest(BaseModel):
    """Request model for web search operations."""

    query: str = Field(..., description="Search query")
    search_type: str = Field("search", description="Type of search: 'search' or 'news'")
    num_results: int | None = Field(4, description="Number of results to fetch (1-20)")

    model_config = ConfigDict(json_schema_extra={})


class WebSearchResponse(BaseModel):
    """Response model for web search operations."""

    query: str = Field(..., description="Original search query")
    search_type: str = Field(..., description="Type of search performed")
    num_results: int = Field(..., description="Number of results requested")
    content: str = Field(..., description="Extracted content from search results")
    success: bool = Field(..., description="Whether the search was successful")
    error: str | None = Field(None, description="Error message if search failed")

    model_config = ConfigDict(json_schema_extra={})


class ChunkedSearchRequest(BaseModel):
    """Request model for chunked search operations."""

    query: str = Field(..., description="Search query")
    search_type: str = Field("search", description="Type of search: 'search' or 'news'")
    num_results: int | None = Field(4, description="Number of results to fetch (1-20)")
    tokenizer_or_token_counter: str = Field("character", description="Tokenizer type")
    chunk_size: int = Field(1000, description="Chunk size for processing")
    chunk_overlap: int = Field(0, description="Overlap between chunks")
    heading_level: int = Field(3, description="Heading level for chunking")
    min_characters_per_chunk: int = Field(
        50, description="Minimum characters per chunk"
    )
    max_characters_per_section: int = Field(
        4000, description="Maximum characters per section"
    )
    clean_text: bool = Field(True, description="Whether to clean text")

    model_config = ConfigDict(json_schema_extra={})


class ChunkedSearchResponse(BaseModel):
    """Response model for chunked search operations."""

    query: str = Field(..., description="Original search query")
    chunks: list[dict[str, Any]] = Field(..., description="List of processed chunks")
    success: bool = Field(..., description="Whether the search was successful")
    error: str | None = Field(None, description="Error message if search failed")

    model_config = ConfigDict(json_schema_extra={})


class WebSearchTool(ToolRunner):
    """Tool runner for web search operations."""

    def __init__(self):
        spec = ToolSpec(
            name="web_search",
            description="Search the web for information or fresh news, returning extracted content",
            inputs={"query": "TEXT", "search_type": "TEXT", "num_results": "INTEGER"},
            outputs={"content": "TEXT", "success": "BOOLEAN", "error": "TEXT"},
        )
        super().__init__(spec)

    def run(self, params: dict[str, Any]) -> ExecutionResult:
        """Execute web search operation."""
        try:
            # Validate inputs
            query = params.get("query", "")
            search_type = params.get("search_type", "search")
            num_results = params.get("num_results", 4)

            if not query:
                return ExecutionResult(
                    success=False, error="Query parameter is required"
                )

            # Run async search
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                content = loop.run_until_complete(
                    search_web(query, search_type, num_results)
                )
            finally:
                loop.close()

            # Check if search was successful
            success = not content.startswith("Error:")
            error = None if success else content

            return ExecutionResult(
                success=success,
                data={
                    "content": content,
                    "success": success,
                    "error": error,
                    "query": query,
                    "search_type": search_type,
                    "num_results": num_results,
                },
            )

        except Exception as e:
            return ExecutionResult(success=False, error=f"Web search failed: {e!s}")


class ChunkedSearchTool(ToolRunner):
    """Tool runner for chunked search operations."""

    def __init__(self):
        spec = ToolSpec(
            name="chunked_search",
            description="Search the web and return chunked content for RAG processing",
            inputs={
                "query": "TEXT",
                "search_type": "TEXT",
                "num_results": "INTEGER",
                "chunk_size": "INTEGER",
                "chunk_overlap": "INTEGER",
                "heading_level": "INTEGER",
                "min_characters_per_chunk": "INTEGER",
                "max_characters_per_section": "INTEGER",
                "clean_text": "BOOLEAN",
            },
            outputs={"chunks": "JSON", "success": "BOOLEAN", "error": "TEXT"},
        )
        super().__init__(spec)

    def run(self, params: dict[str, Any]) -> ExecutionResult:
        """Execute chunked search operation."""
        try:
            # Validate inputs
            query = params.get("query", "")
            search_type = params.get("search_type", "search")
            num_results = params.get("num_results", 4)
            chunk_size = params.get("chunk_size", 1000)
            chunk_overlap = params.get("chunk_overlap", 0)
            heading_level = params.get("heading_level", 3)
            min_characters_per_chunk = params.get("min_characters_per_chunk", 50)
            max_characters_per_section = params.get("max_characters_per_section", 4000)
            clean_text = params.get("clean_text", True)

            if not query:
                return ExecutionResult(
                    success=False, error="Query parameter is required"
                )

            # Run async chunked search
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                chunks_json = loop.run_until_complete(
                    search_and_chunk(
                        query=query,
                        search_type=search_type,
                        num_results=num_results,
                        tokenizer_or_token_counter="character",
                        chunk_size=chunk_size,
                        chunk_overlap=chunk_overlap,
                        heading_level=heading_level,
                        min_characters_per_chunk=min_characters_per_chunk,
                        max_characters_per_section=max_characters_per_section,
                        clean_text=clean_text,
                    )
                )
            finally:
                loop.close()

            # Parse chunks
            try:
                chunks = json.loads(chunks_json)
                success = not (
                    isinstance(chunks, list)
                    and len(chunks) > 0
                    and "error" in chunks[0]
                )
                error = None if success else chunks[0].get("error", "Unknown error")
            except json.JSONDecodeError:
                chunks = []
                success = False
                error = "Failed to parse chunks JSON"

            return ExecutionResult(
                success=success,
                data={
                    "chunks": chunks,
                    "success": success,
                    "error": error,
                    "query": query,
                },
            )

        except Exception as e:
            return ExecutionResult(success=False, error=f"Chunked search failed: {e!s}")


# Pydantic AI Tool Functions
def web_search_tool(ctx: RunContext[Any]) -> str:
    """
    Search the web for information or fresh news, returning extracted content.

    This tool can perform two types of searches:
    - "search" (default): General web search for diverse, relevant content from various sources
    - "news": Specifically searches for fresh news articles and breaking stories

    Args:
        query: The search query (required)
        search_type: Type of search - "search" or "news" (optional, default: "search")
        num_results: Number of results to fetch, 1-20 (optional, default: 4)

    Returns:
        Formatted text containing extracted content with metadata for each result
    """
    # Extract parameters from context
    params = ctx.deps if isinstance(ctx.deps, dict) else {}

    # Create and run tool
    tool = WebSearchTool()
    result = tool.run(params)

    if result.success:
        return result.data.get("content", "No content returned")
    return f"Search failed: {result.error}"


def chunked_search_tool(ctx: RunContext[Any]) -> str:
    """
    Search the web and return chunked content optimized for RAG processing.

    This tool performs web search and processes the results into chunks suitable
    for vector storage and retrieval-augmented generation.

    Args:
        query: The search query (required)
        search_type: Type of search - "search" or "news" (optional, default: "search")
        num_results: Number of results to fetch, 1-20 (optional, default: 4)
        chunk_size: Size of each chunk in characters (optional, default: 1000)
        chunk_overlap: Overlap between chunks (optional, default: 0)
        heading_level: Heading level for chunking (optional, default: 3)
        min_characters_per_chunk: Minimum characters per chunk (optional, default: 50)
        max_characters_per_section: Maximum characters per section (optional, default: 4000)
        clean_text: Whether to clean text (optional, default: true)

    Returns:
        JSON string containing processed chunks with metadata
    """
    # Extract parameters from context
    params = ctx.deps if isinstance(ctx.deps, dict) else {}

    # Create and run tool
    tool = ChunkedSearchTool()
    result = tool.run(params)

    if result.success:
        return json.dumps(result.data.get("chunks", []))
    return f"Chunked search failed: {result.error}"


# Register tools with the global registry
def register_websearch_tools():
    """Register websearch tools with the global registry."""
    from .base import registry

    registry.register("web_search", WebSearchTool)
    registry.register("chunked_search", ChunkedSearchTool)


# Auto-register when module is imported
register_websearch_tools()
