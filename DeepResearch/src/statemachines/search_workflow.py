"""
Search workflow using Pydantic Graph with integrated websearch and analytics tools.

This workflow demonstrates how to integrate the websearch and analytics tools
into the existing Pydantic Graph state machine architecture.
"""

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

# Optional import for pydantic_graph
try:
    from pydantic_graph import BaseNode, End, Graph
except ImportError:
    # Create placeholder classes for when pydantic_graph is not available
    from typing import Generic, TypeVar

    T = TypeVar("T")

    class Graph:
        def __init__(self, *args, **kwargs):
            pass

    class BaseNode(Generic[T]):
        def __init__(self, *args, **kwargs):
            pass

    class End:
        def __init__(self, *args, **kwargs):
            pass


from DeepResearch.src.datatypes.rag import Chunk, Document
from DeepResearch.src.tools.integrated_search_tools import IntegratedSearchTool
from DeepResearch.src.utils.execution_status import ExecutionStatus


class SearchWorkflowState(BaseModel):
    """State for the search workflow."""

    query: str = Field(..., description="Search query")
    search_type: str = Field("search", description="Type of search")
    num_results: int = Field(4, description="Number of results")
    chunk_size: int = Field(1000, description="Chunk size")
    chunk_overlap: int = Field(0, description="Chunk overlap")

    # Results
    raw_content: str | None = Field(None, description="Raw search content")
    documents: list[Document] = Field(default_factory=list, description="RAG documents")
    chunks: list[Chunk] = Field(default_factory=list, description="RAG chunks")
    search_result: dict[str, Any] | None = Field(
        None, description="Agent search results"
    )

    # Analytics
    analytics_recorded: bool = Field(
        False, description="Whether analytics were recorded"
    )
    processing_time: float = Field(0.0, description="Processing time")

    # Status
    status: ExecutionStatus = Field(
        ExecutionStatus.PENDING, description="Execution status"
    )
    errors: list[str] = Field(
        default_factory=list, description="Any errors encountered"
    )

    model_config = ConfigDict(json_schema_extra={})


class InitializeSearch(BaseNode[SearchWorkflowState]):  # type: ignore[unsupported-base]
    """Initialize the search workflow."""

    def run(self, state: SearchWorkflowState) -> Any:
        """Initialize search parameters and validate inputs."""
        try:
            # Validate query
            if not state.query or not state.query.strip():
                state.errors.append("Query cannot be empty")
                state.status = ExecutionStatus.FAILED
                return End("Search failed: Empty query")

            # Set default values
            if not state.search_type:
                state.search_type = "search"
            if not state.num_results:
                state.num_results = 4
            if not state.chunk_size:
                state.chunk_size = 1000
            if not state.chunk_overlap:
                state.chunk_overlap = 0

            state.status = ExecutionStatus.RUNNING
            return PerformWebSearch()

        except Exception as e:
            state.errors.append(f"Initialization failed: {e!s}")
            state.status = ExecutionStatus.FAILED
            return End(f"Search failed: {e!s}")


class PerformWebSearch(BaseNode[SearchWorkflowState]):  # type: ignore[unsupported-base]
    """Perform web search using the SearchAgent."""

    async def run(self, state: SearchWorkflowState) -> Any:
        """Execute web search operation using SearchAgent."""
        try:
            # Import here to avoid circular import
            from DeepResearch.src.agents import SearchAgent
            from DeepResearch.src.datatypes.search_agent import SearchAgentConfig

            # Create SearchAgent with config
            search_config = SearchAgentConfig(
                model="anthropic:claude-sonnet-4-0",
                default_num_results=state.num_results,
            )
            search_agent = SearchAgent(search_config)

            # Execute search using agent
            from DeepResearch.src.datatypes.search_agent import SearchQuery

            search_query = SearchQuery(
                query=state.query,
                search_type=state.search_type,
                num_results=state.num_results,
                use_rag=True,
            )
            agent_result = await search_agent.search(search_query)

            if agent_result.success:
                # Update state with agent results
                state.search_result = (
                    {"content": agent_result.content}
                    if hasattr(agent_result, "content")
                    else {}
                )
                state.documents = []  # SearchResult doesn't have documents field
                state.chunks = []  # SearchResult doesn't have chunks field
                state.analytics_recorded = agent_result.analytics_recorded
                state.processing_time = agent_result.processing_time or 0.0
            else:
                # Fallback to integrated search tool
                tool = IntegratedSearchTool()
                result = tool.run(
                    {
                        "query": state.query,
                        "search_type": state.search_type,
                        "num_results": state.num_results,
                        "chunk_size": state.chunk_size,
                        "chunk_overlap": state.chunk_overlap,
                        "enable_analytics": True,
                        "convert_to_rag": True,
                    }
                )

                if not result.success:
                    state.errors.append(f"Web search failed: {result.error}")
                    state.status = ExecutionStatus.FAILED
                    return End(f"Search failed: {result.error}")

                # Update state with fallback results
                state.documents = [
                    Document(**doc) for doc in result.data.get("documents", [])
                ]
                state.chunks = [
                    Chunk(**chunk) for chunk in result.data.get("chunks", [])
                ]
                state.analytics_recorded = result.data.get("analytics_recorded", False)
                state.processing_time = result.data.get("processing_time", 0.0)

            return ProcessResults()

        except Exception as e:
            state.errors.append(f"Web search failed: {e!s}")
            state.status = ExecutionStatus.FAILED
            return End(f"Search failed: {e!s}")


class ProcessResults(BaseNode[SearchWorkflowState]):  # type: ignore[unsupported-base]
    """Process and validate search results."""

    def run(self, state: SearchWorkflowState) -> Any:
        """Process search results and prepare for output."""
        try:
            # Validate results
            if not state.documents and not state.chunks:
                state.errors.append("No search results found")
                state.status = ExecutionStatus.FAILED
                return End("Search failed: No results found")

            # Create summary content
            state.raw_content = self._create_summary(state.documents, state.chunks)

            state.status = ExecutionStatus.SUCCESS
            return GenerateFinalResponse()

        except Exception as e:
            state.errors.append(f"Result processing failed: {e!s}")
            state.status = ExecutionStatus.FAILED
            return End(f"Search failed: {e!s}")

    def _create_summary(self, documents: list[Document], chunks: list[Chunk]) -> str:
        """Create a summary of search results."""
        summary_parts = []

        # Add document summaries
        for i, doc in enumerate(documents, 1):
            summary_parts.append(
                f"## Document {i}: {doc.metadata.get('source_title', 'Unknown')}"
            )
            summary_parts.append(f"**URL:** {doc.metadata.get('url', 'N/A')}")
            summary_parts.append(f"**Source:** {doc.metadata.get('source', 'N/A')}")
            summary_parts.append(f"**Date:** {doc.metadata.get('date', 'N/A')}")
            summary_parts.append(f"**Content:** {doc.content[:500]}...")
            summary_parts.append("")

        # Add chunk count
        summary_parts.append(f"**Total Chunks:** {len(chunks)}")
        summary_parts.append(f"**Total Documents:** {len(documents)}")

        return "\n".join(summary_parts)


class GenerateFinalResponse(BaseNode[SearchWorkflowState]):  # type: ignore[unsupported-base]
    """Generate the final response."""

    def run(self, state: SearchWorkflowState) -> Any:
        """Generate final response with all results."""
        try:
            # Create comprehensive response
            response = {
                "query": state.query,
                "search_type": state.search_type,
                "num_results": state.num_results,
                "documents": [doc.model_dump() for doc in state.documents],
                "chunks": [],  # No chunks available from SearchResult
                "summary": state.raw_content,
                "analytics_recorded": state.analytics_recorded,
                "processing_time": state.processing_time,
                "status": state.status.value,
                "errors": state.errors,
            }

            # Add agent results if available
            if state.search_result:
                response["agent_results"] = state.search_result
                response["agent_used"] = True
            else:
                response["agent_used"] = False

            return End(response)

        except Exception as e:
            state.errors.append(f"Response generation failed: {e!s}")
            state.status = ExecutionStatus.FAILED
            return End(f"Search failed: {e!s}")


class SearchWorkflowError(BaseNode[SearchWorkflowState]):  # type: ignore[unsupported-base]
    """Handle search workflow errors."""

    def run(self, state: SearchWorkflowState) -> Any:
        """Handle errors and provide fallback response."""
        error_summary = "; ".join(state.errors) if state.errors else "Unknown error"

        response = {
            "query": state.query,
            "search_type": state.search_type,
            "num_results": state.num_results,
            "documents": [],
            "chunks": [],
            "summary": f"Search failed: {error_summary}",
            "analytics_recorded": state.analytics_recorded,
            "processing_time": state.processing_time,
            "status": state.status.value,
            "errors": state.errors,
        }

        return End(response)


# Create the search workflow graph
def create_search_workflow() -> Graph:
    """Create the search workflow graph."""
    return Graph(
        nodes=[
            InitializeSearch(),
            PerformWebSearch(),
            ProcessResults(),
            GenerateFinalResponse(),
            SearchWorkflowError(),
        ]
    )


# Workflow execution function
async def run_search_workflow(
    query: str,
    search_type: str = "search",
    num_results: int = 4,
    chunk_size: int = 1000,
    chunk_overlap: int = 0,
) -> dict[str, Any]:
    """Run the search workflow with the given parameters."""

    # Create initial state
    state = SearchWorkflowState(
        query=query,
        search_type=search_type,
        num_results=num_results,
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
    )

    # Create and run workflow
    workflow = create_search_workflow()
    result = await workflow.run(InitializeSearch(), state=state)  # type: ignore

    return result.output if hasattr(result, "output") else {"error": "No output"}  # type: ignore


# Example usage
async def example_search_workflow():
    """Example of using the search workflow."""

    # Basic search
    await run_search_workflow(
        query="artificial intelligence developments 2024",
        search_type="news",
        num_results=3,
    )

    # RAG-optimized search
    await run_search_workflow(
        query="machine learning algorithms",
        search_type="search",
        num_results=5,
        chunk_size=1000,
        chunk_overlap=100,
    )


if __name__ == "__main__":
    import asyncio

    asyncio.run(example_search_workflow())
