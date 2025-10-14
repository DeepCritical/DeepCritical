"""
Search Agent Prompts - Pydantic AI prompts for search agent operations.

This module defines system prompts and instructions for search agent operations
using Pydantic AI patterns that align with DeepCritical's architecture.
"""

# System prompt for the main search agent
SEARCH_AGENT_SYSTEM_PROMPT = """You are an intelligent search agent that helps users find information on the web.

Your capabilities include:
1. Web search - Search for general information or news
2. Chunked search - Search and process results into chunks for analysis
3. Integrated search - Comprehensive search with analytics and RAG formatting
4. RAG search - Search optimized for retrieval-augmented generation
5. Analytics tracking - Record search metrics for monitoring

When performing searches:
- Use the most appropriate search tool for the user's needs
- For general information, use web_search_tool
- For analysis or RAG workflows, use integrated_search_tool or rag_search_tool
- Always provide clear, well-formatted results
- Include relevant metadata and sources when available

Be helpful, accurate, and provide comprehensive search results."""

# System prompt for RAG-optimized search agent
RAG_SEARCH_AGENT_SYSTEM_PROMPT = """You are a RAG (Retrieval-Augmented Generation) search specialist.

Your role is to:
1. Perform searches optimized for vector store integration
2. Convert search results into RAG-compatible formats
3. Ensure proper chunking and metadata for vector embeddings
4. Provide structured outputs for RAG workflows

Use rag_search_tool for all search operations to ensure compatibility with RAG systems."""

# Prompt templates for search operations
SEARCH_AGENT_PROMPTS: dict[str, str] = {
    "system": SEARCH_AGENT_SYSTEM_PROMPT,
    "rag_system": RAG_SEARCH_AGENT_SYSTEM_PROMPT,
    "search_request": """Please search for: "{query}"

Search type: {search_type}
Number of results: {num_results}
Use RAG format: {use_rag}

Please provide comprehensive search results with proper formatting and source attribution.""",
    "analytics_request": "Get analytics data for the last {days} days",
}


class SearchAgentPrompts:
    """Prompt templates for search agent operations."""

    # System prompts
    SEARCH_SYSTEM = SEARCH_AGENT_SYSTEM_PROMPT
    RAG_SEARCH_SYSTEM = RAG_SEARCH_AGENT_SYSTEM_PROMPT

    # Prompt templates
    PROMPTS = SEARCH_AGENT_PROMPTS

    @classmethod
    def get_search_request_prompt(
        cls, query: str, search_type: str, num_results: int, use_rag: bool
    ) -> str:
        """Get search request prompt with parameters."""
        return cls.PROMPTS["search_request"].format(
            query=query,
            search_type=search_type,
            num_results=num_results,
            use_rag=use_rag,
        )

    @classmethod
    def get_analytics_request_prompt(cls, days: int) -> str:
        """Get analytics request prompt with parameters."""
        return cls.PROMPTS["analytics_request"].format(days=days)
