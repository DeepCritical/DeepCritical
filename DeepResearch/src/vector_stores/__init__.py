from __future__ import annotations

from ..datatypes.neo4j_types import (
    Neo4jVectorStoreConfig,
    VectorIndexMetric,
    VectorSearchDefaults,
)
from ..datatypes.rag import Embeddings, VectorStore, VectorStoreConfig, VectorStoreType
from .neo4j_vector_store import Neo4jVectorStore

__all__ = [
    "Neo4jVectorStore",
    "Neo4jVectorStoreConfig",
    "create_vector_store",
]


def create_vector_store(
    config: VectorStoreConfig, embeddings: Embeddings
) -> VectorStore:
    """Factory function to create vector store instances based on configuration.

    Args:
        config: Vector store configuration
        embeddings: Embeddings instance

    Returns:
        Vector store instance

    Raises:
        ValueError: If store type is not supported
    """
    if config.store_type == VectorStoreType.NEO4J:
        if isinstance(config, Neo4jVectorStoreConfig):
            return Neo4jVectorStore(config, embeddings)
        # Try to create Neo4jVectorStoreConfig from base config
        # This assumes the config has neo4j-specific attributes
        from ..datatypes.neo4j_types import (
            Neo4jConnectionConfig,
            VectorIndexConfig,
            VectorSearchDefaults,
        )

        # Extract or create connection config
        connection = getattr(config, "connection", None)
        if connection is None:
            connection = Neo4jConnectionConfig(
                uri=getattr(config, "connection_string", "neo4j://localhost:7687"),
                username="neo4j",
                password="password",
                database=getattr(config, "database", "neo4j"),
            )

        # Extract or create index config
        index = getattr(config, "index", None)
        if index is None:
            index = VectorIndexConfig(
                index_name=getattr(config, "collection_name", "documents"),
                node_label="Document",
                vector_property="embedding",
                dimensions=getattr(config, "embedding_dimension", 384),
                metric=VectorIndexMetric.COSINE,
            )

        # Create a basic VectorStoreConfig for the constructor
        vector_store_config = VectorStoreConfig(
            store_type=VectorStoreType.NEO4J,
            connection_string=getattr(
                config, "connection_string", "neo4j://localhost:7687"
            ),
            database=getattr(config, "database", "neo4j"),
            collection_name=getattr(config, "collection_name", "documents"),
            embedding_dimension=getattr(config, "embedding_dimension", 384),
            distance_metric="cosine",
        )

        return Neo4jVectorStore(
            vector_store_config, embeddings, neo4j_config=connection
        )

    raise ValueError(f"Unsupported vector store type: {config.store_type}")
