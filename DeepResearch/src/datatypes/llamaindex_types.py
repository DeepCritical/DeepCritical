"""
Minimal LlamaIndex-compatible types for vector storage integration.

This module provides minimal type definitions that are compatible with LlamaIndex
interfaces, mapped to our existing DeepCritical datatypes. This allows for
seamless integration with LlamaIndex-based tools without requiring the full
LlamaIndex dependency.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, Field

from .chunk_dataclass import Chunk
from .document_dataclass import Document


class BaseNode(BaseModel):
    """Base node type compatible with LlamaIndex Node interface."""

    id_: str = Field(..., description="Unique node identifier")
    embedding: list[float] | None = Field(None, description="Node embedding vector")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Node metadata")
    excluded_embed_metadata_keys: list[str] = Field(
        default_factory=list, description="Keys to exclude from embedding"
    )
    excluded_llm_metadata_keys: list[str] = Field(
        default_factory=list, description="Keys to exclude from LLM context"
    )
    relationships: dict[str, Any] = Field(
        default_factory=dict, description="Node relationships"
    )
    hash: str = Field("", description="Content hash for caching")

    class Config:
        arbitrary_types_allowed = True

    @property
    def node_id(self) -> str:
        """Alias for id_ to match LlamaIndex interface."""
        return self.id_

    @node_id.setter
    def node_id(self, value: str) -> None:
        """Set node_id (alias for id_)."""
        self.id_ = value

    def get_metadata_str(self) -> str:
        """Get metadata as formatted string."""
        return str(self.metadata)


class TextNode(BaseNode):
    """Text node type compatible with LlamaIndex TextNode interface."""

    text: str = Field("", description="Node text content")
    start_char_idx: int | None = Field(None, description="Start character index")
    end_char_idx: int | None = Field(None, description="End character index")
    text_template: str = Field(
        "{metadata_str}\n\n{content}", description="Template for text formatting"
    )

    @classmethod
    def from_chunk(cls, chunk: Chunk) -> TextNode:
        """Create TextNode from DeepCritical Chunk."""
        return cls(
            id_=chunk.id,
            text=chunk.text,
            embedding=chunk.embedding,
            metadata={
                "start_index": chunk.start_index,
                "end_index": chunk.end_index,
                "token_count": chunk.token_count,
                "context": chunk.context,
            },
        )

    def get_content(self, metadata_mode: str = "all") -> str:
        """Get node content with optional metadata."""
        if metadata_mode == "none":
            return self.text
        if metadata_mode == "all":
            metadata_str = self.get_metadata_str()
            return self.text_template.format(
                metadata_str=metadata_str, content=self.text
            )
        # Minimal metadata mode
        return f"{self.text}"

    def get_text(self) -> str:
        """Get raw text content."""
        return self.text


class DocumentNode(BaseNode):
    """Document node type for full documents."""

    content: str = Field("", description="Document content")
    title: str | None = Field(None, description="Document title")
    doc_id: str | None = Field(None, description="Document identifier")
    source_file: str | None = Field(None, description="Source file path")

    @classmethod
    def from_document(cls, doc: Document) -> DocumentNode:
        """Create DocumentNode from DeepCritical Document."""
        return cls(
            id_=doc.id,
            content=doc.content,
            embedding=None,  # Document doesn't have embedding
            metadata=doc.metadata,
            title=doc.metadata.get("title"),
            doc_id=doc.id,
        )


class VectorRecord(BaseModel):
    """Vector record compatible with LlamaIndex vector store records."""

    id: str = Field(..., description="Record identifier")
    embedding: list[float] | None = Field(None, description="Embedding vector")
    metadata: dict[str, Any] = Field(
        default_factory=dict, description="Record metadata"
    )
    node: Union[TextNode, DocumentNode] | None = Field(
        None, description="Associated node"
    )

    @classmethod
    def from_text_node(cls, node: TextNode) -> VectorRecord:
        """Create VectorRecord from TextNode."""
        return cls(
            id=node.id_,
            embedding=node.embedding,
            metadata=node.metadata,
            node=node,
        )

    @classmethod
    def from_document_node(cls, node: DocumentNode) -> VectorRecord:
        """Create VectorRecord from DocumentNode."""
        return cls(
            id=node.id_,
            embedding=node.embedding,
            metadata=node.metadata,
            node=node,
        )


class VectorStoreQuery(BaseModel):
    """Query structure compatible with LlamaIndex vector store queries."""

    query_embedding: list[float] | None = Field(None, description="Query embedding")
    similarity_top_k: int = Field(10, description="Number of similar results to return")
    doc_ids: list[str] | None = Field(
        None, description="Specific document IDs to search"
    )
    query_str: str | None = Field(None, description="Query string")
    mode: str = Field("default", description="Query mode")
    filters: dict[str, Any] | None = Field(None, description="Query filters")

    class Config:
        arbitrary_types_allowed = True


class VectorStoreQueryResult(BaseModel):
    """Query result structure compatible with LlamaIndex vector store results."""

    nodes: list[Union[TextNode, DocumentNode]] = Field(
        default_factory=list, description="Retrieved nodes"
    )
    similarities: list[float] = Field(
        default_factory=list, description="Similarity scores"
    )
    ids: list[str] = Field(default_factory=list, description="Node IDs")

    def __len__(self) -> int:
        """Get number of results."""
        return len(self.nodes)


class MetadataFilter(BaseModel):
    """Metadata filter for vector store queries."""

    key: str = Field(..., description="Metadata key to filter on")
    value: Any = Field(..., description="Value to match")
    operator: str = Field("==", description="Comparison operator")


class MetadataFilters(BaseModel):
    """Collection of metadata filters."""

    filters: list[MetadataFilter] = Field(
        default_factory=list, description="List of filters"
    )
    condition: str = Field("and", description="How to combine filters ('and' or 'or')")


# Utility functions for conversion between DeepCritical and LlamaIndex types


def chunk_to_llamaindex_node(chunk: Chunk) -> TextNode:
    """Convert DeepCritical Chunk to LlamaIndex TextNode."""
    return TextNode.from_chunk(chunk)


def document_to_llamaindex_node(doc: Document) -> DocumentNode:
    """Convert DeepCritical Document to LlamaIndex DocumentNode."""
    return DocumentNode.from_document(doc)


def llamaindex_node_to_chunk(node: TextNode) -> Chunk:
    """Convert LlamaIndex TextNode to DeepCritical Chunk."""
    return Chunk(
        id=node.id_,
        text=node.text,
        start_index=node.start_char_idx or 0,
        end_index=node.end_char_idx or len(node.text),
        token_count=len(node.text.split()),  # Rough estimate
        context=node.metadata.get("context"),
        embedding=node.embedding,
    )


def llamaindex_node_to_document(node: DocumentNode) -> Document:
    """Convert LlamaIndex DocumentNode to DeepCritical Document."""
    return Document(
        id=node.id_,
        content=node.content,
        metadata=node.metadata,
        # Document doesn't have embedding attribute
    )


def create_vector_records_from_chunks(chunks: list[Chunk]) -> list[VectorRecord]:
    """Create VectorRecord objects from Chunk objects."""
    records = []
    for chunk in chunks:
        node = chunk_to_llamaindex_node(chunk)
        record = VectorRecord.from_text_node(node)
        records.append(record)
    return records


def create_vector_records_from_documents(docs: list[Document]) -> list[VectorRecord]:
    """Create VectorRecord objects from Document objects."""
    records = []
    for doc in docs:
        node = document_to_llamaindex_node(doc)
        record = VectorRecord.from_document_node(node)
        records.append(record)
    return records
