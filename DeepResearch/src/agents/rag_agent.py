"""
RAG Agent for DeepCritical research workflows.

This module implements a RAG (Retrieval-Augmented Generation) agent
that integrates with the existing DeepCritical agent system and vector stores.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Optional

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
    ):
        super().__init__()
        self.agent_type = "rag"
        self.vector_store: VectorStore | None = None
        self.embeddings: Embeddings | None = embeddings

        if vector_store_config and embeddings:
            self.vector_store = create_vector_store(vector_store_config, embeddings)
        elif vector_store_config and not embeddings:
            raise ValueError(
                "Embeddings must be provided when vector_store_config is specified"
            )
        elif embeddings and not vector_store_config:
            raise ValueError(
                "Vector store config must be provided when embeddings is specified"
            )

    def execute_rag_query(self, query: RAGQuery) -> RAGResponse:
        """Execute a RAG query and return the response."""
        start_time = time.time()

        try:
            # Retrieve relevant documents
            retrieved_documents = self.retrieve_documents(query.text, query.top_k or 5)

            # Generate answer based on retrieved documents
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
        except Exception as e:
            processing_time = time.time() - start_time
            return RAGResponse(
                query=query.text,
                retrieved_documents=[],
                generated_answer=f"Error during RAG processing: {e!s}",
                context="",
                metadata={"status": "error", "error": str(e)},
                processing_time=processing_time,
            )

    def retrieve_documents(self, query: str, limit: int = 5) -> list[Document]:
        """Retrieve relevant documents for a query."""
        if not self.vector_store:
            return []

        try:
            # Perform similarity search
            search_results = self.vector_store.search(
                query=query,
                search_type=SearchType.SIMILARITY,
            )

            # Convert SearchResult to Document
            documents = []
            for result in search_results[:limit]:
                documents.append(result.document)

            return documents
        except Exception as e:
            print(f"Error during document retrieval: {e}")
            return []

    def generate_answer(self, query: str, documents: list[Document]) -> str:
        """Generate an answer based on retrieved documents."""
        if not documents:
            return "No relevant documents found to answer the query."

        # For now, return a simple concatenation
        # In a real implementation, this would use an LLM to generate an answer
        doc_summaries = []
        for i, doc in enumerate(documents, 1):
            content_preview = (
                doc.content[:200] + "..." if len(doc.content) > 200 else doc.content
            )
            doc_summaries.append(f"Document {i}: {content_preview}")

        return f"""Based on the retrieved documents, here's what I found regarding: "{query}"

Context from {len(documents)} documents:
{chr(10).join(doc_summaries)}

Note: This is a basic implementation. A full RAG system would use an LLM to generate a more coherent and contextual answer based on the retrieved documents."""

    def _build_context(self, documents: list[Document]) -> str:
        """Build context string from retrieved documents."""
        if not documents:
            return ""

        context_parts = []
        for i, doc in enumerate(documents, 1):
            context_parts.append(f"[Document {i}]\n{doc.content}\n")

        return "\n".join(context_parts)

    def add_documents(self, documents: list[Document]) -> bool:
        """Add documents to the vector store."""
        if not self.vector_store:
            raise ValueError("Vector store not configured")

        try:
            self.vector_store.add_documents(documents)
            return True
        except Exception as e:
            print(f"Error adding documents: {e}")
            return False

    def add_document_chunks(self, chunks: list[Document]) -> bool:
        """Add document chunks to the vector store."""
        if not self.vector_store:
            raise ValueError("Vector store not configured")

        try:
            # Convert Document chunks to proper format if needed
            # Assuming chunks are Document objects with chunked content
            self.vector_store.add_documents(chunks)
            return True
        except Exception as e:
            print(f"Error adding document chunks: {e}")
            return False

    def search_documents(
        self,
        query: str,
        search_type: SearchType = SearchType.SIMILARITY,
        limit: int = 10,
    ) -> list[SearchResult]:
        """Search documents in the vector store."""
        if not self.vector_store:
            return []

        try:
            return self.vector_store.search(
                query=query,
                search_type=search_type,
            )[:limit]
        except Exception as e:
            print(f"Error searching documents: {e}")
            return []
