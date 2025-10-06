"""
Search workflow using Pydantic Graph with integrated websearch and analytics tools.

This workflow demonstrates how to integrate the websearch and analytics tools
into the existing Pydantic Graph state machine architecture.
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

# Optional import for pydantic_graph
try:
    from pydantic_graph import Graph, BaseNode, End
except ImportError:
    # Create placeholder classes for when pydantic_graph is not available
    from typing import TypeVar, Generic

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


from ..tools.integrated_search_tools import IntegratedSearchTool
from ..datatypes.rag import Document, Chunk
from ..utils.execution_status import ExecutionStatus


class SearchWorkflowState(BaseModel):
    """State for the search workflow."""

    query: str = Field(..., description="Search query")
    search_type: str = Field("search", description="Type of search")
    num_results: int = Field(4, description="Number of results")
    chunk_size: int = Field(1000, description="Chunk size")
    chunk_overlap: int = Field(0, description="Chunk overlap")

    # Results
    raw_content: Optional[str] = Field(None, description="Raw search content")
    documents: List[Document] = Field(default_factory=list, description="RAG documents")
    chunks: List[Chunk] = Field(default_factory=list, description="RAG chunks")
    search_result: Optional[Dict[str, Any]] = Field(
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
    errors: List[str] = Field(
        default_factory=list, description="Any errors encountered"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "query": "artificial intelligence developments 2024",
                "search_type": "news",
                "num_results": 5,
                "chunk_size": 1000,
                "chunk_overlap": 100,
                "raw_content": None,
                "documents": [],
                "chunks": [],
                "analytics_recorded": False,
                "processing_time": 0.0,
                "status": "PENDING",
                "errors": [],
            }
        }


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
            state.errors.append(f"Initialization failed: {str(e)}")
            state.status = ExecutionStatus.FAILED
            return End(f"Search failed: {str(e)}")


class PerformWebSearch(BaseNode[SearchWorkflowState]):  # type: ignore[unsupported-base]
    """Perform web search using the SearchAgent."""

    async def run(self, state: SearchWorkflowState) -> Any:
        """Execute web search operation using SearchAgent."""
        try:
            # Import here to avoid circular import
            from ..agents import SearchAgent
            from ..datatypes.search_agent import SearchAgentConfig

            # Create SearchAgent with config
            search_config = SearchAgentConfig(
                model="anthropic:claude-sonnet-4-0",
                default_num_results=state.num_results,
            )
            search_agent = SearchAgent(search_config)

            # Execute search using agent
            from ..datatypes.search_agent import SearchQuery

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
            state.errors.append(f"Web search failed: {str(e)}")
            state.status = ExecutionStatus.FAILED
            return End(f"Search failed: {str(e)}")


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
            state.errors.append(f"Result processing failed: {str(e)}")
            state.status = ExecutionStatus.FAILED
            return End(f"Search failed: {str(e)}")

    def _create_summary(self, documents: List[Document], chunks: List[Chunk]) -> str:
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
            state.errors.append(f"Response generation failed: {str(e)}")
            state.status = ExecutionStatus.FAILED
            return End(f"Search failed: {str(e)}")


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
) -> Dict[str, Any]:
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
    result = await run_search_workflow(
        query="artificial intelligence developments 2024",
        search_type="news",
        num_results=3,
    )

    print(f"Search successful: {result.get('status') == 'SUCCESS'}")
    print(f"Documents found: {len(result.get('documents', []))}")
    print(f"Chunks created: {len(result.get('chunks', []))}")
    print(f"Analytics recorded: {result.get('analytics_recorded', False)}")
    print(f"Processing time: {result.get('processing_time', 0):.2f}s")

    # RAG-optimized search
    rag_result = await run_search_workflow(
        query="machine learning algorithms",
        search_type="search",
        num_results=5,
        chunk_size=1000,
        chunk_overlap=100,
    )

    print(f"\nRAG search successful: {rag_result.get('status') == 'SUCCESS'}")
    print(f"RAG documents: {len(rag_result.get('documents', []))}")
    print(f"RAG chunks: {len(rag_result.get('chunks', []))}")


if __name__ == "__main__":
    import asyncio

    asyncio.run(example_search_workflow())
