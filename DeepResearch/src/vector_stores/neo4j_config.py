from __future__ import annotations

from pydantic import BaseModel, Field

from ..datatypes.neo4j_types import (
    Neo4jConnectionConfig,
    VectorIndexConfig,
    VectorIndexMetric,
)
from ..datatypes.rag import VectorStoreConfig, VectorStoreType


class Neo4jVectorStoreConfig(VectorStoreConfig):
    """Hydra-ready configuration for Neo4j vector store."""

    store_type: VectorStoreType = Field(default=VectorStoreType.NEO4J)
    connection: Neo4jConnectionConfig
    index: VectorIndexConfig
