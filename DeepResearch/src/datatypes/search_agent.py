"""
Search Agent Data Types - Pydantic models for search agent operations.

This module defines Pydantic models for search agent configuration, queries,
and results that align with DeepCritical's architecture.
"""

from pydantic import BaseModel, ConfigDict, Field


class SearchAgentConfig(BaseModel):
    """Configuration for the search agent."""

    model: str = Field("gpt-4", description="Model to use for the agent")
    enable_analytics: bool = Field(
        True, description="Whether to enable analytics tracking"
    )
    default_search_type: str = Field("search", description="Default search type")
    default_num_results: int = Field(4, description="Default number of results")
    chunk_size: int = Field(1000, description="Default chunk size")
    chunk_overlap: int = Field(0, description="Default chunk overlap")

    model_config = ConfigDict(json_schema_extra={})


class SearchQuery(BaseModel):
    """Search query model."""

    query: str = Field(..., description="The search query")
    search_type: str | None = Field(
        None, description="Type of search: 'search' or 'news'"
    )
    num_results: int | None = Field(None, description="Number of results to fetch")
    use_rag: bool = Field(False, description="Whether to use RAG-optimized search")

    model_config = ConfigDict(json_schema_extra={})


class SearchResult(BaseModel):
    """Search result model."""

    query: str = Field(..., description="Original query")
    content: str = Field(..., description="Search results content")
    success: bool = Field(..., description="Whether the search was successful")
    processing_time: float | None = Field(
        None, description="Processing time in seconds"
    )
    analytics_recorded: bool = Field(
        False, description="Whether analytics were recorded"
    )
    error: str | None = Field(None, description="Error message if search failed")

    model_config = ConfigDict(json_schema_extra={})


class SearchAgentDependencies(BaseModel):
    """Dependencies for search agent operations."""

    query: str = Field(..., description="The search query")
    search_type: str = Field(..., description="Type of search to perform")
    num_results: int = Field(..., description="Number of results to fetch")
    chunk_size: int = Field(..., description="Chunk size for processing")
    chunk_overlap: int = Field(..., description="Chunk overlap")
    use_rag: bool = Field(False, description="Whether to use RAG format")

    @classmethod
    def from_search_query(
        cls, query: SearchQuery, config: SearchAgentConfig
    ) -> "SearchAgentDependencies":
        """Create dependencies from search query and config."""
        return cls(
            query=query.query,
            search_type=query.search_type or config.default_search_type,
            num_results=query.num_results or config.default_num_results,
            chunk_size=config.chunk_size,
            chunk_overlap=config.chunk_overlap,
            use_rag=query.use_rag,
        )

    model_config = ConfigDict(json_schema_extra={})
