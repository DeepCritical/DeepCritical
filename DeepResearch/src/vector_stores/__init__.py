from __future__ import annotations

from ..datatypes.rag import Embeddings, VectorStore, VectorStoreConfig, VectorStoreType
from .faiss_config import FaissVectorStoreConfig
from .faiss_vector_store import FaissVectorStore

try:  # pragma: no cover - optional dependency guard
    from ..datatypes.neo4j_types import (
        Neo4jVectorStoreConfig,
        VectorIndexMetric,
        VectorSearchDefaults,
    )
    from .neo4j_vector_store import Neo4jVectorStore
except Exception:  # pragma: no cover - neo4j not installed in minimal envs
    Neo4jVectorStore = None  # type: ignore[assignment]
    Neo4jVectorStoreConfig = None  # type: ignore[assignment]

__all__ = [
    "Neo4jVectorStore",
    "Neo4jVectorStoreConfig",
    "FaissVectorStore",
    "FaissVectorStoreConfig",
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
        if Neo4jVectorStore is None or Neo4jVectorStoreConfig is None:
            msg = "Neo4j support requires the neo4j Python driver"
            raise ValueError(msg)
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

    if config.store_type == VectorStoreType.FAISS:
        if isinstance(config, FaissVectorStoreConfig):
            faiss_config = config
        else:
            faiss_config = FaissVectorStoreConfig.model_validate(config.model_dump())
        return FaissVectorStore(faiss_config, embeddings)

    raise ValueError(f"Unsupported vector store type: {config.store_type}")
