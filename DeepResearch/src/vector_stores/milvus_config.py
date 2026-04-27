from __future__ import annotations

from pydantic import Field

from ..datatypes.rag import VectorStoreConfig, VectorStoreType


class MilvusVectorStoreConfig(VectorStoreConfig):
    """Configuration for the Milvus vector store."""

    store_type: VectorStoreType = Field(default=VectorStoreType.MILVUS)
    uri: str = Field(
        default="http://localhost:19530", description="Milvus connection URI"
    )
    token: str | None = Field(
        default=None, description="Milvus authentication token or API key"
    )
