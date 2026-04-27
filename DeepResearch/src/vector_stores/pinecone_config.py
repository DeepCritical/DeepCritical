from __future__ import annotations

from pydantic import Field

from ..datatypes.rag import VectorStoreConfig, VectorStoreType


class PineconeVectorStoreConfig(VectorStoreConfig):
    """Configuration for the Pinecone vector store."""

    store_type: VectorStoreType = Field(default=VectorStoreType.PINECONE)
    index_name: str = Field(default="research-docs", description="Pinecone index name")
