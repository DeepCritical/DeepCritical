from __future__ import annotations

from pydantic import Field

from ..datatypes.rag import VectorStoreConfig, VectorStoreType


class ChromaVectorStoreConfig(VectorStoreConfig):
    """Configuration for the Chroma vector store."""

    store_type: VectorStoreType = Field(default=VectorStoreType.CHROMA)
    persist_directory: str | None = Field(
        default=None,
        description="Directory for Chroma persistent storage (local mode).",
    )
    tenant: str | None = Field(
        default=None,
        description="Optional Chroma tenant for multi-tenant deployments.",
    )
    database_name: str | None = Field(
        default=None,
        description="Optional Chroma database name for multi-database deployments.",
    )
