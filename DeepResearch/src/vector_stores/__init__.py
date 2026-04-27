from __future__ import annotations

from ..datatypes.rag import Embeddings, VectorStore, VectorStoreConfig, VectorStoreType
from .chroma_config import ChromaVectorStoreConfig
from .chroma_vector_store import ChromaVectorStore
from .postgres_config import PostgresVectorStoreConfig
from .postgres_vector_store import PostgresVectorStore
from .milvus_config import MilvusVectorStoreConfig
from .milvus_vector_store import MilvusVectorStore
from .pinecone_config import PineconeVectorStoreConfig
from .pinecone_vector_store import PineconeVectorStore

__all__ = [
    "ChromaVectorStore",
    "ChromaVectorStoreConfig",
    "Neo4jVectorStore",
    "Neo4jVectorStoreConfig",
    "PostgresVectorStore",
    "PostgresVectorStoreConfig",
    "MilvusVectorStore",
    "MilvusVectorStoreConfig",
    "PineconeVectorStore",
    "PineconeVectorStoreConfig",
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
    if config.store_type == VectorStoreType.CHROMA:
        if isinstance(config, ChromaVectorStoreConfig):
            return ChromaVectorStore(config, embeddings)

        chroma_config = ChromaVectorStoreConfig(
            store_type=VectorStoreType.CHROMA,
            connection_string=getattr(config, "connection_string", None),
            host=getattr(config, "host", "localhost"),
            port=getattr(config, "port", 8000),
            database=getattr(config, "database", None),
            collection_name=getattr(config, "collection_name", "research_docs"),
            api_key=getattr(config, "api_key", None),
            embedding_dimension=getattr(config, "embedding_dimension", 1536),
            distance_metric=getattr(config, "distance_metric", "cosine"),
            index_type=getattr(config, "index_type", "hnsw"),
            persist_directory=getattr(config, "persist_directory", None),
            tenant=getattr(config, "tenant", None),
            database_name=getattr(config, "database_name", None),
        )
        return ChromaVectorStore(chroma_config, embeddings)

    if config.store_type == VectorStoreType.NEO4J:
        from ..datatypes.neo4j_types import (
            Neo4jVectorStoreConfig,
            VectorIndexConfig,
            VectorIndexMetric,
            Neo4jConnectionConfig,
        )
        from .neo4j_vector_store import Neo4jVectorStore

        if isinstance(config, Neo4jVectorStoreConfig):
            return Neo4jVectorStore(config, embeddings)
        # Try to create Neo4jVectorStoreConfig from base config
        # This assumes the config has neo4j-specific attributes

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

    if config.store_type == VectorStoreType.POSTGRES:
        if isinstance(config, PostgresVectorStoreConfig):
            return PostgresVectorStore(config, embeddings)
            
        postgres_config = PostgresVectorStoreConfig(
            store_type=VectorStoreType.POSTGRES,
            table_name=getattr(config, "collection_name", "documents"),
            connection_string=getattr(config, "connection_string", None),
            embedding_dimension=getattr(config, "embedding_dimension", 1536),
            distance_metric=getattr(config, "distance_metric", "cosine"),
        )
        return PostgresVectorStore(postgres_config, embeddings)

    if config.store_type == VectorStoreType.MILVUS:
        if isinstance(config, MilvusVectorStoreConfig):
            return MilvusVectorStore(config, embeddings)
            
        milvus_config = MilvusVectorStoreConfig(
            store_type=VectorStoreType.MILVUS,
            collection_name=getattr(config, "collection_name", "research_docs"),
            uri=getattr(config, "connection_string", "http://localhost:19530"),
            token=getattr(config, "api_key", None),
            embedding_dimension=getattr(config, "embedding_dimension", 1536),
            distance_metric=getattr(config, "distance_metric", "cosine"),
        )
        return MilvusVectorStore(milvus_config, embeddings)

    if config.store_type == VectorStoreType.PINECONE:
        if isinstance(config, PineconeVectorStoreConfig):
            return PineconeVectorStore(config, embeddings)
            
        pinecone_config = PineconeVectorStoreConfig(
            store_type=VectorStoreType.PINECONE,
            index_name=getattr(config, "collection_name", "research-docs"),
            api_key=getattr(config, "api_key", None),
            embedding_dimension=getattr(config, "embedding_dimension", 1536),
            distance_metric=getattr(config, "distance_metric", "cosine"),
        )
        return PineconeVectorStore(pinecone_config, embeddings)

    if config.store_type == VectorStoreType.FAISS:
        from .faiss_config import FAISSVectorStoreConfig
        from .faiss_vector_store import FAISSVectorStore

        if isinstance(config, FAISSVectorStoreConfig):
            return FAISSVectorStore(config, embeddings)

        # Create FAISS config from generic config
        # Default paths relative to execution dir
        index_path = getattr(config, "index_path", "./data/faiss.index")
        data_path = getattr(config, "data_path", "./data/faiss_docs.pkl")

        faiss_config = FAISSVectorStoreConfig(
            store_type=VectorStoreType.FAISS,
            embedding_dimension=config.embedding_dimension,
            index_path=index_path,
            data_path=data_path,
            connection_string=None,
            host=None,
            port=None,
            database=None,
            collection_name=None,
            api_key=None,
            distance_metric=config.distance_metric,
            index_type=config.index_type,
        )
        return FAISSVectorStore(faiss_config, embeddings)

    raise ValueError(f"Unsupported vector store type: {config.store_type}")
