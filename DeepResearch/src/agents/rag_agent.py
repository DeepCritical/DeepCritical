"""
RAG Agent for DeepCritical research workflows.

This module implements a RAG (Retrieval-Augmented Generation) agent
that integrates with the existing DeepCritical agent system and vector stores.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any, Optional

from ..datatypes.rag import (
    Document,
    Embeddings,
    RAGQuery,
    RAGResponse,
    SearchResult,
    SearchType,
    VectorStore,
    VectorStoreConfig,
)
from ..vector_stores import create_vector_store
from .research_agent import ResearchAgent


@dataclass
class RAGAgent(ResearchAgent):
    """RAG Agent for retrieval-augmented generation tasks."""

    def __init__(
        self,
        vector_store_config: VectorStoreConfig | None = None,
        embeddings: Embeddings | None = None,
        *,
        vector_store: VectorStore | None = None,
    ):
        super().__init__()
        self.agent_type = "rag"
        self.vector_store: VectorStore | None = vector_store
        self.embeddings: Embeddings | None = embeddings

        if vector_store is not None and vector_store_config is not None:
            msg = "Provide either an existing vector store or a configuration, not both"
            raise ValueError(msg)

        if vector_store_config and embeddings:
            self.vector_store = create_vector_store(vector_store_config, embeddings)
        elif vector_store_config and not embeddings:
            msg = "Embeddings must be provided when vector_store_config is specified"
            raise ValueError(msg)
        elif embeddings and not vector_store_config and vector_store is None:
            msg = "Vector store config must be provided when embeddings is specified"
            raise ValueError(msg)

    async def execute_rag_query(self, query: RAGQuery) -> RAGResponse:
        """Execute a RAG query and return the response."""
        start_time = time.time()

        try:
            retrieved_documents = await self.retrieve_documents(
                query.text,
                limit=query.top_k or 5,
                search_type=query.search_type,
                filters=query.filters,
            )

            context = self._build_context(retrieved_documents)
            generated_answer = self.generate_answer(query.text, retrieved_documents)

            processing_time = time.time() - start_time

            return RAGResponse(
                query=query.text,
                retrieved_documents=retrieved_documents,
                generated_answer=generated_answer,
                context=context,
                metadata={
                    "status": "success",
                    "num_documents": len(retrieved_documents),
                    "vector_store_type": self.vector_store.__class__.__name__
                    if self.vector_store
                    else "None",
                },
                processing_time=processing_time,
            )
        except Exception as exc:
            processing_time = time.time() - start_time
            return RAGResponse(
                query=query.text,
                retrieved_documents=[],
                generated_answer=f"Error during RAG processing: {exc!s}",
                context="",
                metadata={"status": "error", "error": str(exc)},
                processing_time=processing_time,
            )

    async def retrieve_documents(
        self,
        query: str,
        *,
        limit: int = 5,
        search_type: SearchType = SearchType.SIMILARITY,
        filters: dict[str, Any] | None = None,
    ) -> list[SearchResult]:
        """Retrieve relevant documents for a query."""

        if not self.vector_store:
            return []

        try:
            search_results = await self.vector_store.search(
                query=query,
                search_type=search_type,
                top_k=limit,
                filters=filters,
            )
            return search_results[:limit]
        except Exception as exc:  # pragma: no cover - logged for debugging
            print(f"Error during document retrieval: {exc}")
            return []

    def generate_answer(self, query: str, results: list[SearchResult]) -> str:
        """Generate an answer based on retrieved documents."""

        if not results:
            return "No relevant documents found to answer the query."

        doc_summaries = []
        for index, result in enumerate(results, 1):
            doc = result.document
            content_preview = (
                doc.content[:200] + "..." if len(doc.content) > 200 else doc.content
            )
            doc_summaries.append(f"Document {index}: {content_preview}")

        return (
            f"Based on the retrieved documents, here's what I found regarding: "
            f'"{query}"\n\nContext from {len(results)} documents:\n'
            f"{chr(10).join(doc_summaries)}\n\nNote: This is a basic implementation. "
            "A full RAG system would use an LLM to generate a more coherent and "
            "contextual answer based on the retrieved documents."
        )

    def _build_context(self, results: list[SearchResult]) -> str:
        """Build context string from retrieved documents."""

        if not results:
            return ""

        context_parts = []
        for index, result in enumerate(results, 1):
            context_parts.append(f"[Document {index}]\n{result.document.content}\n")

        return "\n".join(context_parts)

    async def add_documents(self, documents: list[Document]) -> bool:
        """Add documents to the vector store."""

        if not self.vector_store:
            raise ValueError("Vector store not configured")

        try:
            await self.vector_store.add_documents(documents)
            return True
        except Exception as exc:  # pragma: no cover - logged for debugging
            print(f"Error adding documents: {exc}")
            return False

    async def add_document_chunks(self, chunks: list[Document]) -> bool:
        """Add document chunks to the vector store."""

        if not self.vector_store:
            raise ValueError("Vector store not configured")

        try:
            await self.vector_store.add_documents(chunks)
            return True
        except Exception as exc:  # pragma: no cover - logged for debugging
            print(f"Error adding document chunks: {exc}")
            return False

    async def search_documents(
        self,
        query: str,
        search_type: SearchType = SearchType.SIMILARITY,
        limit: int = 10,
        filters: dict[str, Any] | None = None,
    ) -> list[SearchResult]:
        """Search documents in the vector store."""

        if not self.vector_store:
            return []

        try:
            results = await self.vector_store.search(
                query=query,
                search_type=search_type,
                top_k=limit,
                filters=filters,
            )
            return results[:limit]
        except Exception as exc:  # pragma: no cover - logged for debugging
            print(f"Error searching documents: {exc}")
            return []
