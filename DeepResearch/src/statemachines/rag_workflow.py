"""
RAG (Retrieval-Augmented Generation) workflow state machine for DeepCritical.

This module implements a Pydantic Graph-based workflow for RAG operations,
including document ingestion, vector storage, retrieval, and generation.
"""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Annotated, Any

# Optional import for pydantic_graph
try:
    from pydantic_graph import BaseNode, Edge, End, Graph, GraphRunContext
except ImportError:
    # Create placeholder classes for when pydantic_graph is not available
    from typing import Generic, TypeVar

    T = TypeVar("T")

    class BaseNode(Generic[T]):
        def __init__(self, *args, **kwargs):
            pass

    class End:
        def __init__(self, *args, **kwargs):
            pass

    class Graph:
        def __init__(self, *args, **kwargs):
            pass

    class GraphRunContext:
        def __init__(self, *args, **kwargs):
            pass

    class Edge:
        def __init__(self, *args, **kwargs):
            pass


from DeepResearch.src.datatypes.rag import (
    Document,
    RAGConfig,
    RAGQuery,
    RAGResponse,
    SearchType,
)
from DeepResearch.src.datatypes.vllm_integration import VLLMDeployment, VLLMRAGSystem
from DeepResearch.src.utils.execution_status import ExecutionStatus

if TYPE_CHECKING:
    from omegaconf import DictConfig


@dataclass
class RAGState:
    """State for RAG workflow execution."""

    question: str
    rag_config: RAGConfig | None = None
    documents: list[Document] = field(default_factory=list)
    rag_response: RAGResponse | None = None
    rag_result: dict[str, Any] | None = None  # For agent results
    processing_steps: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    config: DictConfig | None = None
    execution_status: ExecutionStatus = ExecutionStatus.PENDING


# --- RAG Workflow Nodes ---


@dataclass
class InitializeRAG(BaseNode[RAGState]):  # type: ignore[unsupported-base]
    """Initialize RAG system with configuration."""

    async def run(self, ctx: GraphRunContext[RAGState]) -> LoadDocuments:
        """Initialize RAG system components."""
        try:
            cfg = ctx.state.config
            rag_cfg = getattr(cfg, "rag", {})

            # Create RAG configuration from Hydra config
            rag_config = self._create_rag_config(rag_cfg)
            ctx.state.rag_config = rag_config

            ctx.state.processing_steps.append("rag_initialized")
            ctx.state.execution_status = ExecutionStatus.RUNNING

            return LoadDocuments()

        except Exception as e:
            error_msg = f"Failed to initialize RAG system: {e!s}"
            ctx.state.errors.append(error_msg)
            ctx.state.execution_status = ExecutionStatus.FAILED
            return RAGError()

    def _create_rag_config(self, rag_cfg: dict[str, Any]) -> RAGConfig:
        """Create RAG configuration from Hydra config."""
        from DeepResearch.src.datatypes.rag import (
            EmbeddingModelType,
            EmbeddingsConfig,
            LLMModelType,
            VectorStoreConfig,
            VectorStoreType,
            VLLMConfig,
        )

        # Create embeddings config
        embeddings_cfg = rag_cfg.get("embeddings", {})
        embeddings_config = EmbeddingsConfig(
            model_type=EmbeddingModelType(embeddings_cfg.get("model_type", "openai")),
            model_name=embeddings_cfg.get("model_name", "text-embedding-3-small"),
            api_key=embeddings_cfg.get("api_key"),
            base_url=embeddings_cfg.get("base_url"),
            num_dimensions=embeddings_cfg.get("num_dimensions", 1536),
            batch_size=embeddings_cfg.get("batch_size", 32),
        )

        # Create LLM config
        llm_cfg = rag_cfg.get("llm", {})
        llm_config = VLLMConfig(
            model_type=LLMModelType(llm_cfg.get("model_type", "huggingface")),
            model_name=llm_cfg.get("model_name", "TinyLlama/TinyLlama-1.1B-Chat-v1.0"),
            host=llm_cfg.get("host", "localhost"),
            port=llm_cfg.get("port", 8000),
            api_key=llm_cfg.get("api_key"),
            max_tokens=llm_cfg.get("max_tokens", 2048),
            temperature=llm_cfg.get("temperature", 0.7),
        )

        # Create vector store config
        vs_cfg = rag_cfg.get("vector_store", {})
        vector_store_config = VectorStoreConfig(
            store_type=VectorStoreType(vs_cfg.get("store_type", "chroma")),
            connection_string=vs_cfg.get("connection_string"),
            host=vs_cfg.get("host", "localhost"),
            port=vs_cfg.get("port", 8000),
            database=vs_cfg.get("database"),
            collection_name=vs_cfg.get("collection_name", "research_docs"),
            embedding_dimension=embeddings_config.num_dimensions,
        )

        return RAGConfig(
            embeddings=embeddings_config,
            llm=llm_config,
            vector_store=vector_store_config,
            chunk_size=rag_cfg.get("chunk_size", 1000),
            chunk_overlap=rag_cfg.get("chunk_overlap", 200),
        )


@dataclass
class LoadDocuments(BaseNode[RAGState]):  # type: ignore[unsupported-base]
    """Load documents for RAG processing."""

    async def run(self, ctx: GraphRunContext[RAGState]) -> ProcessDocuments:
        """Load documents from various sources."""
        try:
            cfg = ctx.state.config
            rag_cfg = getattr(cfg, "rag", {})

            # Load documents based on configuration
            documents = await self._load_documents(rag_cfg)
            ctx.state.documents = documents

            ctx.state.processing_steps.append(f"loaded_{len(documents)}_documents")

            return ProcessDocuments()

        except Exception as e:
            error_msg = f"Failed to load documents: {e!s}"
            ctx.state.errors.append(error_msg)
            ctx.state.execution_status = ExecutionStatus.FAILED
            return RAGError()

    async def _load_documents(self, rag_cfg: dict[str, Any]) -> list[Document]:
        """Load documents from configured sources."""
        documents = []

        # Load from file sources
        file_sources = rag_cfg.get("file_sources", [])
        for source in file_sources:
            source_docs = await self._load_from_file(source)
            documents.extend(source_docs)

        # Load from database sources
        db_sources = rag_cfg.get("database_sources", [])
        for source in db_sources:
            source_docs = await self._load_from_database(source)
            documents.extend(source_docs)

        # Load from web sources
        web_sources = rag_cfg.get("web_sources", [])
        for source in web_sources:
            source_docs = await self._load_from_web(source)
            documents.extend(source_docs)

        return documents

    async def _load_from_file(self, source: dict[str, Any]) -> list[Document]:
        """Load documents from file sources."""
        # Implementation would depend on file type (PDF, TXT, etc.)
        # For now, return empty list
        return []

    async def _load_from_database(self, source: dict[str, Any]) -> list[Document]:
        """Load documents from database sources."""
        # Implementation would connect to database and extract documents
        # For now, return empty list
        return []

    async def _load_from_web(self, source: dict[str, Any]) -> list[Document]:
        """Load documents from web sources."""
        # Implementation would scrape or fetch from web APIs
        # For now, return empty list
        return []


@dataclass
class ProcessDocuments(BaseNode[RAGState]):  # type: ignore[unsupported-base]
    """Process and chunk documents for vector storage."""

    async def run(self, ctx: GraphRunContext[RAGState]) -> StoreDocuments:
        """Process documents into chunks."""
        try:
            if not ctx.state.documents:
                # Create sample documents if none loaded
                ctx.state.documents = self._create_sample_documents()

            # Chunk documents based on configuration
            rag_config = ctx.state.rag_config
            chunked_documents = await self._chunk_documents(
                ctx.state.documents, rag_config.chunk_size, rag_config.chunk_overlap
            )
            ctx.state.documents = chunked_documents

            ctx.state.processing_steps.append(
                f"processed_{len(chunked_documents)}_chunks"
            )

            return StoreDocuments()

        except Exception as e:
            error_msg = f"Failed to process documents: {e!s}"
            ctx.state.errors.append(error_msg)
            ctx.state.execution_status = ExecutionStatus.FAILED
            return RAGError()

    def _create_sample_documents(self) -> list[Document]:
        """Create sample documents for testing."""
        return [
            Document(
                id="doc_001",
                content="Machine learning is a subset of artificial intelligence that focuses on algorithms that can learn from data.",
                metadata={"source": "research_paper", "topic": "machine_learning"},
            ),
            Document(
                id="doc_002",
                content="Deep learning uses neural networks with multiple layers to model and understand complex patterns in data.",
                metadata={"source": "research_paper", "topic": "deep_learning"},
            ),
            Document(
                id="doc_003",
                content="Natural language processing combines computational linguistics with machine learning to help computers understand human language.",
                metadata={"source": "research_paper", "topic": "nlp"},
            ),
        ]

    async def _chunk_documents(
        self, documents: list[Document], chunk_size: int, chunk_overlap: int
    ) -> list[Document]:
        """Chunk documents into smaller pieces."""
        chunked_docs = []

        for doc in documents:
            content = doc.content
            if len(content) <= chunk_size:
                chunked_docs.append(doc)
                continue

            # Simple chunking by character count
            start = 0
            chunk_id = 0
            while start < len(content):
                end = min(start + chunk_size, len(content))
                chunk_content = content[start:end]

                chunk_doc = Document(
                    id=f"{doc.id}_chunk_{chunk_id}",
                    content=chunk_content,
                    metadata={
                        **doc.metadata,
                        "chunk_id": chunk_id,
                        "original_doc_id": doc.id,
                        "chunk_start": start,
                        "chunk_end": end,
                    },
                )
                chunked_docs.append(chunk_doc)

                start = end - chunk_overlap
                chunk_id += 1

        return chunked_docs


@dataclass
class StoreDocuments(BaseNode[RAGState]):  # type: ignore[unsupported-base]
    """Store documents in vector database."""

    async def run(self, ctx: GraphRunContext[RAGState]) -> QueryRAG:
        """Store documents in vector store."""
        try:
            # Initialize VLLM RAG system
            rag_config = ctx.state.rag_config
            deployment = self._create_vllm_deployment(rag_config)
            rag_system = VLLMRAGSystem(deployment=deployment)

            await rag_system.initialize()

            # Store documents
            # TODO: Implement vector store integration
            # if hasattr(rag_system, 'vector_store') and rag_system.vector_store:
            #     document_ids = await rag_system.vector_store.add_documents(
            #         ctx.state.documents
            #     )
            #     ctx.state.processing_steps.append(
            #         f"stored_{len(document_ids)}_documents"
            #     )
            # else:
            ctx.state.processing_steps.append("vector_store_not_available")

            # Store RAG system in context for querying
            ctx.set("rag_system", rag_system)

            return QueryRAG()

        except Exception as e:
            error_msg = f"Failed to store documents: {e!s}"
            ctx.state.errors.append(error_msg)
            ctx.state.execution_status = ExecutionStatus.FAILED
            return RAGError()

    def _create_vllm_deployment(self, rag_config: RAGConfig) -> VLLMDeployment:
        """Create VLLM deployment configuration."""
        from DeepResearch.src.datatypes.vllm_integration import (
            VLLMEmbeddingServerConfig,
            VLLMServerConfig,
        )

        # Create LLM server config
        llm_server_config = VLLMServerConfig(
            model_name=rag_config.llm.model_name,
            host=rag_config.llm.host,
            port=rag_config.llm.port,
        )

        # Create embedding server config
        embedding_server_config = VLLMEmbeddingServerConfig(
            model_name=rag_config.embeddings.model_name,
            host=(
                str(rag_config.embeddings.base_url)
                if rag_config.embeddings.base_url
                else "localhost"
            ),
            port=8001,  # Default embedding port
        )

        return VLLMDeployment(
            llm_config=llm_server_config, embedding_config=embedding_server_config
        )


@dataclass
class QueryRAG(BaseNode[RAGState]):  # type: ignore[unsupported-base]
    """Query the RAG system with the user's question."""

    async def run(self, ctx: GraphRunContext[RAGState]) -> GenerateResponse:
        """Execute RAG query using RAGAgent."""
        try:
            # Import here to avoid circular import
            from DeepResearch.src.agents import RAGAgent

            # Create RAGAgent
            rag_agent = RAGAgent()
            # await rag_agent.initialize()  # Method doesn't exist

            # Create RAG query
            rag_query = RAGQuery(
                text=ctx.state.question, search_type=SearchType.SIMILARITY, top_k=5
            )

            # Execute query using agent
            start_time = time.time()
            rag_response = rag_agent.execute_rag_query(rag_query)
            processing_time = time.time() - start_time

            if rag_response:
                ctx.state.rag_result = (
                    rag_response.model_dump()
                    if hasattr(rag_response, "model_dump")
                    else rag_response.__dict__
                )
                ctx.state.rag_response = rag_response
                ctx.state.processing_steps.append(
                    f"query_completed_in_{processing_time:.2f}s"
                )
            else:
                # Fallback to direct system query
                rag_system = ctx.get("rag_system")
                if rag_system:
                    rag_response = await rag_system.query(rag_query)
                    ctx.state.rag_response = rag_response
                    ctx.state.processing_steps.append(
                        f"fallback_query_completed_in_{processing_time:.2f}s"
                    )
                else:
                    msg = "RAG system not initialized and agent failed"
                    raise RuntimeError(msg)

            return GenerateResponse()

        except Exception as e:
            error_msg = f"Failed to query RAG system: {e!s}"
            ctx.state.errors.append(error_msg)
            ctx.state.execution_status = ExecutionStatus.FAILED
            return RAGError()


@dataclass
class GenerateResponse(BaseNode[RAGState]):  # type: ignore[unsupported-base]
    """Generate final response from RAG results."""

    async def run(
        self, ctx: GraphRunContext[RAGState]
    ) -> Annotated[End[str], Edge(label="done")]:
        """Generate and return final response."""
        try:
            rag_response = ctx.state.rag_response
            if not rag_response:
                msg = "No RAG response available"
                raise RuntimeError(msg)

            # Format final response
            final_response = self._format_response(rag_response, ctx.state)

            ctx.state.processing_steps.append("response_generated")
            ctx.state.execution_status = ExecutionStatus.SUCCESS

            return End(final_response)

        except Exception as e:
            error_msg = f"Failed to generate response: {e!s}"
            ctx.state.errors.append(error_msg)
            ctx.state.execution_status = ExecutionStatus.FAILED
            return RAGError()

    def _format_response(
        self, rag_response: RAGResponse | None, state: RAGState
    ) -> str:
        """Format the final response."""
        response_parts = [
            "RAG Analysis Complete",
            "",
            f"Question: {state.question}",
            "",
        ]

        # Handle agent results
        if state.rag_result:
            answer = state.rag_result.get("answer", "No answer generated")
            confidence = state.rag_result.get("confidence", 0.0)
            retrieved_docs = state.rag_result.get("retrieved_documents", [])

            response_parts.extend(
                [
                    f"Answer: {answer}",
                    f"Confidence: {confidence:.3f}",
                    "",
                    f"Retrieved Documents ({len(retrieved_docs)}):",
                ]
            )

            for i, doc in enumerate(retrieved_docs, 1):
                if isinstance(doc, dict):
                    score = doc.get("score", 0.0)
                    content = doc.get("content", "")[:200]
                    response_parts.append(f"{i}. Score: {score:.3f}")
                    response_parts.append(f"   Content: {content}...")
                else:
                    response_parts.append(f"{i}. {str(doc)[:200]}...")
                response_parts.append("")

        # Handle traditional RAG response
        elif rag_response:
            response_parts.extend(
                [
                    f"Answer: {rag_response.generated_answer}",
                    "",
                    f"Retrieved Documents ({len(rag_response.retrieved_documents)}):",
                ]
            )

            for i, result in enumerate(rag_response.retrieved_documents, 1):
                response_parts.append(f"{i}. Score: {result.score:.3f}")
                response_parts.append(f"   Content: {result.document.content[:200]}...")
                response_parts.append("")

        else:
            response_parts.append("Answer: No response generated")
            response_parts.append("")

        response_parts.extend([f"Steps Completed: {', '.join(state.processing_steps)}"])

        if state.errors:
            response_parts.extend(["", f"Errors: {', '.join(state.errors)}"])

        return "\n".join(response_parts)


@dataclass
class RAGError(BaseNode[RAGState]):  # type: ignore[unsupported-base]
    """Handle RAG workflow errors."""

    async def run(
        self, ctx: GraphRunContext[RAGState]
    ) -> Annotated[End[str], Edge(label="error")]:
        """Handle errors and return error response."""
        error_response = [
            "RAG Workflow Failed",
            "",
            f"Question: {ctx.state.question}",
            "",
            "Errors:",
        ]

        for error in ctx.state.errors:
            error_response.append(f"- {error}")

        error_response.extend(
            [
                "",
                f"Steps Completed: {', '.join(ctx.state.processing_steps)}",
                f"Status: {ctx.state.execution_status.value}",
            ]
        )

        return End("\n".join(error_response))


# --- RAG Workflow Graph ---

rag_workflow_graph = Graph(
    nodes=(
        InitializeRAG(),
        LoadDocuments(),
        ProcessDocuments(),
        StoreDocuments(),
        QueryRAG(),
        GenerateResponse(),
        RAGError(),
    ),
)


def run_rag_workflow(question: str, config: DictConfig) -> str:
    """Run the complete RAG workflow."""
    state = RAGState(question=question, config=config)
    result = asyncio.run(rag_workflow_graph.run(InitializeRAG(), state=state))  # type: ignore
    return result.output or ""
