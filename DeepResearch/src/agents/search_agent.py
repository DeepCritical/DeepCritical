"""
Search Agent using Pydantic AI with integrated websearch and analytics tools.

This agent demonstrates how to use the websearch and analytics tools with Pydantic AI
for intelligent search and retrieval operations.
"""

from typing import Any

from pydantic_ai import Agent

from DeepResearch.src.datatypes.search_agent import (
    SearchAgentConfig,
    SearchAgentDependencies,
    SearchQuery,
    SearchResult,
)
from DeepResearch.src.prompts.search_agent import SearchAgentPrompts
from DeepResearch.src.tools.analytics_tools import (
    get_analytics_data_tool,
    record_request_tool,
)
from DeepResearch.src.tools.integrated_search_tools import (
    integrated_search_tool,
    rag_search_tool,
)
from DeepResearch.src.tools.websearch_tools import chunked_search_tool, web_search_tool


class SearchAgent:
    """Search agent using Pydantic AI with integrated tools."""

    def __init__(self, config: SearchAgentConfig):
        self.config = config
        self.agent = Agent(
            model=config.model,
            system_prompt=self._get_system_prompt(),
            tools=[
                web_search_tool,
                chunked_search_tool,
                integrated_search_tool,
                rag_search_tool,
                record_request_tool,
                get_analytics_data_tool,
            ],
        )

    def _get_system_prompt(self) -> str:
        """Get the system prompt for the search agent."""
        return SearchAgentPrompts.SEARCH_SYSTEM

    async def search(self, query: SearchQuery) -> SearchResult:
        """Perform a search using the agent."""
        try:
            # Prepare dependencies for the agent
            deps = SearchAgentDependencies.from_search_query(query, self.config)

            # Create the user message
            user_message = SearchAgentPrompts.get_search_request_prompt(
                query=query.query,
                search_type=deps.search_type,
                num_results=deps.num_results,
                use_rag=query.use_rag,
            )

            # Run the agent
            result = await self.agent.run(user_message, deps=deps)

            # Extract processing time if available
            processing_time = None
            analytics_recorded = False

            # Check if the result contains processing information
            if hasattr(result, "data") and isinstance(result.data, dict):
                processing_time = result.data.get("processing_time")
                analytics_recorded = result.data.get("analytics_recorded", False)

            return SearchResult(
                query=query.query,
                content=result.data if hasattr(result, "data") else str(result),
                success=True,
                processing_time=processing_time,
                analytics_recorded=analytics_recorded,
            )

        except Exception as e:
            return SearchResult(
                query=query.query, content="", success=False, error=str(e)
            )

    async def get_analytics(self, days: int = 30) -> dict[str, Any]:
        """Get analytics data for the specified number of days."""
        try:
            deps = {"days": days}
            user_message = SearchAgentPrompts.get_analytics_request_prompt(days)
            result = await self.agent.run(user_message, deps=deps)
            return result.data if hasattr(result, "data") else {}
        except Exception as e:
            return {"error": str(e)}

    def create_rag_agent(self) -> Agent:
        """Create a specialized RAG agent for vector store integration."""
        return Agent(
            model=self.config.model,
            system_prompt=SearchAgentPrompts.RAG_SEARCH_SYSTEM,
            tools=[rag_search_tool, integrated_search_tool],
        )


# Example usage functions
async def example_basic_search():
    """Example of basic search functionality."""
    config = SearchAgentConfig(
        model="gpt-4",
        enable_analytics=True,
        default_search_type="search",
        default_num_results=3,
    )

    agent = SearchAgent(config)

    query = SearchQuery(
        query="artificial intelligence developments 2024",
        search_type="news",
        num_results=5,
    )

    await agent.search(query)


async def example_rag_search():
    """Example of RAG-optimized search."""
    config = SearchAgentConfig(
        model="gpt-4", enable_analytics=True, chunk_size=1000, chunk_overlap=100
    )

    agent = SearchAgent(config)

    query = SearchQuery(
        query="machine learning algorithms", use_rag=True, num_results=3
    )

    await agent.search(query)


async def example_analytics():
    """Example of analytics retrieval."""
    config = SearchAgentConfig(enable_analytics=True)
    agent = SearchAgent(config)

    await agent.get_analytics(days=7)


if __name__ == "__main__":
    import asyncio

    # Run examples
    asyncio.run(example_basic_search())
    asyncio.run(example_rag_search())
    asyncio.run(example_analytics())
