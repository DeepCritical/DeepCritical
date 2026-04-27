from __future__ import annotations

from pydantic import Field

from ..datatypes.rag import VectorStoreConfig, VectorStoreType


class PostgresVectorStoreConfig(VectorStoreConfig):
    """Configuration for the Postgres (pgvector) vector store."""

    store_type: VectorStoreType = Field(default=VectorStoreType.POSTGRES)
    table_name: str = Field(
        default="documents",
        description="Name of the PostgreSQL table to store vectors in.",
    )
