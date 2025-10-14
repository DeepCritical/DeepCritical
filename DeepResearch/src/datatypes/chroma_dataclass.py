"""
Comprehensive ChromaDB API dataclass implementation covering all functionality.

This module provides complete dataclass representations of all ChromaDB API components
as documented in the Chroma Cookbook: https://cookbook.chromadb.dev/core/api/

Based on the official Chroma API documentation and OpenAPI specification.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Protocol

# ============================================================================
# Core Enums and Types
# ============================================================================


class DistanceFunction(str, Enum):
    """Distance functions supported by ChromaDB."""

    EUCLIDEAN = "l2"
    COSINE = "cosine"
    INNER_PRODUCT = "ip"


class IncludeType(str, Enum):
    """Types of data to include in responses."""

    METADATA = "metadatas"
    DOCUMENTS = "documents"
    DISTANCES = "distances"
    EMBEDDINGS = "embeddings"
    URIS = "uris"
    DATA = "data"


class AuthType(str, Enum):
    """Authentication types supported by ChromaDB."""

    NONE = "none"
    BASIC = "basic"
    TOKEN = "token"


class EmbeddingFunctionType(str, Enum):
    """Types of embedding functions."""

    DEFAULT = "default"
    OPENAI = "openai"
    HUGGINGFACE = "huggingface"
    SENTENCE_TRANSFORMERS = "sentence_transformers"
    CUSTOM = "custom"


# ============================================================================
# Core Data Structures
# ============================================================================


@dataclass
class ID:
    """Document ID structure."""

    value: str

    def __post_init__(self):
        if not self.value:
            self.value = str(uuid.uuid4())

    def __str__(self) -> str:
        return self.value


@dataclass
class Metadata:
    """Document metadata structure."""

    data: dict[str, Any] = field(default_factory=dict)

    def get(self, key: str, default: Any = None) -> Any:
        """Get metadata value by key."""
        return self.data.get(key, default)

    def set(self, key: str, value: Any) -> None:
        """Set metadata value."""
        self.data[key] = value

    def update(self, metadata: dict[str, Any]) -> None:
        """Update metadata with new values."""
        self.data.update(metadata)

    def __getitem__(self, key: str) -> Any:
        return self.data[key]

    def __setitem__(self, key: str, value: Any) -> None:
        self.data[key] = value


@dataclass
class Embedding:
    """Embedding vector structure."""

    vector: list[float]
    dimension: int | None = None

    def __post_init__(self):
        if self.dimension is None:
            self.dimension = len(self.vector)
        elif self.dimension != len(self.vector):
            msg = (
                f"Dimension mismatch: expected {self.dimension}, got {len(self.vector)}"
            )
            raise ValueError(msg)


@dataclass
class Document:
    """Document structure containing content, metadata, and embeddings."""

    id: ID
    content: str
    metadata: Metadata | None = None
    embedding: Embedding | None = None
    uri: str | None = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = Metadata()


# ============================================================================
# Filter Structures
# ============================================================================


@dataclass
class WhereFilter:
    """Metadata filter structure (similar to MongoDB queries)."""

    field: str
    operator: str
    value: Any

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary format."""
        return {self.field: {self.operator: self.value}}


@dataclass
class WhereDocumentFilter:
    """Document content filter structure."""

    operator: str
    value: str

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary format."""
        return {self.operator: self.value}


@dataclass
class CompositeFilter:
    """Composite filter combining multiple conditions."""

    and_conditions: list[WhereFilter | WhereDocumentFilter] | None = None
    or_conditions: list[WhereFilter | WhereDocumentFilter] | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary format."""
        result = {}
        if self.and_conditions:
            result["$and"] = [condition.to_dict() for condition in self.and_conditions]
        if self.or_conditions:
            result["$or"] = [condition.to_dict() for condition in self.or_conditions]
        return result


# ============================================================================
# Include Structure
# ============================================================================


@dataclass
class Include:
    """Specifies what data to include in responses."""

    metadatas: bool = False
    documents: bool = False
    distances: bool = False
    embeddings: bool = False
    uris: bool = False
    data: bool = False

    def to_list(self) -> list[str]:
        """Convert to list of include types."""
        includes = []
        if self.metadatas:
            includes.append(IncludeType.METADATA.value)
        if self.documents:
            includes.append(IncludeType.DOCUMENTS.value)
        if self.distances:
            includes.append(IncludeType.DISTANCES.value)
        if self.embeddings:
            includes.append(IncludeType.EMBEDDINGS.value)
        if self.uris:
            includes.append(IncludeType.URIS.value)
        if self.data:
            includes.append(IncludeType.DATA.value)
        return includes


# ============================================================================
# Query Request/Response Structures
# ============================================================================


@dataclass
class QueryRequest:
    """Query request structure."""

    query_texts: list[str] | None = None
    query_embeddings: list[list[float]] | None = None
    n_results: int = 10
    where: dict[str, Any] | None = None
    where_document: dict[str, Any] | None = None
    include: Include | None = None
    collection_name: str | None = None
    collection_id: str | None = None

    def __post_init__(self):
        if self.include is None:
            self.include = Include(metadatas=True, documents=True, distances=True)


@dataclass
class QueryResult:
    """Single query result structure."""

    id: str
    distance: float | None = None
    metadata: dict[str, Any] | None = None
    document: str | None = None
    embedding: list[float] | None = None
    uri: str | None = None
    data: Any | None = None


@dataclass
class QueryResponse:
    """Query response structure."""

    ids: list[list[str]]
    distances: list[list[float]] | None = None
    metadatas: list[list[dict[str, Any]]] | None = None
    documents: list[list[str]] | None = None
    embeddings: list[list[list[float]]] | None = None
    uris: list[list[str]] | None = None
    data: list[list[Any]] | None = None

    def get_results(self, query_index: int = 0) -> list[QueryResult]:
        """Get results for a specific query."""
        results = []
        for i in range(len(self.ids[query_index])):
            result = QueryResult(
                id=self.ids[query_index][i],
                distance=self.distances[query_index][i] if self.distances else None,
                metadata=self.metadatas[query_index][i] if self.metadatas else None,
                document=self.documents[query_index][i] if self.documents else None,
                embedding=self.embeddings[query_index][i] if self.embeddings else None,
                uri=self.uris[query_index][i] if self.uris else None,
                data=self.data[query_index][i] if self.data else None,
            )
            results.append(result)
        return results


# ============================================================================
# Collection Management Structures
# ============================================================================


@dataclass
class CollectionMetadata:
    """Collection metadata structure."""

    name: str
    id: str
    metadata: dict[str, Any] | None = None
    dimension: int | None = None
    distance_function: DistanceFunction = DistanceFunction.EUCLIDEAN
    created_at: datetime | None = None
    updated_at: datetime | None = None


@dataclass
class CreateCollectionRequest:
    """Request to create a new collection."""

    name: str
    metadata: dict[str, Any] | None = None
    embedding_function: str | None = None
    distance_function: DistanceFunction = DistanceFunction.EUCLIDEAN


@dataclass
class Collection:
    """Collection structure."""

    name: str
    id: str
    metadata: dict[str, Any] | None = None
    dimension: int | None = None
    distance_function: DistanceFunction = DistanceFunction.EUCLIDEAN
    created_at: datetime | None = None
    updated_at: datetime | None = None
    count: int = 0

    def add(
        self,
        documents: list[str],
        metadatas: list[dict[str, Any]] | None = None,
        ids: list[str] | None = None,
        embeddings: list[list[float]] | None = None,
        uris: list[str] | None = None,
    ) -> list[str]:
        """Add documents to collection."""
        # This would be implemented by the actual Chroma client
        return []

    def query(
        self,
        query_texts: list[str] | None = None,
        query_embeddings: list[list[float]] | None = None,
        n_results: int = 10,
        where: dict[str, Any] | None = None,
        where_document: dict[str, Any] | None = None,
        include: Include | None = None,
    ) -> QueryResponse:
        """Query documents in collection."""
        # This would be implemented by the actual Chroma client
        return QueryResponse(
            ids=[],
            distances=[],
            metadatas=[],
            documents=[],
            embeddings=[],
            uris=[],
            data=[],
        )

    def get(
        self,
        ids: list[str] | None = None,
        where: dict[str, Any] | None = None,
        where_document: dict[str, Any] | None = None,
        include: Include | None = None,
        limit: int | None = None,
        offset: int | None = None,
    ) -> QueryResponse:
        """Get documents from collection."""
        # This would be implemented by the actual Chroma client
        return QueryResponse(
            ids=[],
            distances=[],
            metadatas=[],
            documents=[],
            embeddings=[],
            uris=[],
            data=[],
        )

    def update(
        self,
        ids: list[str],
        documents: list[str] | None = None,
        metadatas: list[dict[str, Any]] | None = None,
        embeddings: list[list[float]] | None = None,
        uris: list[str] | None = None,
    ) -> None:
        """Update documents in collection."""
        # This would be implemented by the actual Chroma client

    def delete(
        self,
        ids: list[str] | None = None,
        where: dict[str, Any] | None = None,
        where_document: dict[str, Any] | None = None,
    ) -> list[str]:
        """Delete documents from collection."""
        # This would be implemented by the actual Chroma client
        return []

    def peek(self, limit: int = 10) -> QueryResponse:
        """Peek at documents in collection."""
        return self.get(limit=limit)

    def get_count(self) -> int:
        """Get document count in collection."""
        # This would be implemented by the actual Chroma client
        return self.count


# ============================================================================
# Embedding Function Structures
# ============================================================================


class EmbeddingFunction(Protocol):
    """Protocol for embedding functions."""

    def __call__(self, input_texts: list[str]) -> list[list[float]]:
        """Generate embeddings for input texts."""
        ...


@dataclass
class EmbeddingFunctionConfig:
    """Configuration for embedding functions."""

    function_type: EmbeddingFunctionType
    model_name: str | None = None
    api_key: str | None = None
    base_url: str | None = None
    custom_function: EmbeddingFunction | None = None
    dimension: int | None = None

    def create_function(self) -> EmbeddingFunction:
        """Create embedding function from config."""

        # This would be implemented based on the function type
        # Return a mock embedding function for now
        class MockEmbeddingFunction(EmbeddingFunction):
            def __call__(self, texts):
                return [[0.0] * 384 for _ in texts]  # Mock 384-dimensional embeddings

        return MockEmbeddingFunction()


# ============================================================================
# Authentication Structures
# ============================================================================


@dataclass
class AuthConfig:
    """Authentication configuration."""

    auth_type: AuthType = AuthType.NONE
    username: str | None = None
    password: str | None = None
    token: str | None = None
    ssl_enabled: bool = False
    ssl_cert_path: str | None = None
    ssl_key_path: str | None = None


# ============================================================================
# Client Configuration
# ============================================================================


@dataclass
class ClientConfig:
    """ChromaDB client configuration."""

    host: str = "localhost"
    port: int = 8000
    ssl: bool = False
    headers: dict[str, str] | None = None
    settings: dict[str, Any] | None = None
    auth_config: AuthConfig | None = None
    embedding_function: EmbeddingFunctionConfig | None = None


# ============================================================================
# Main Client Structure
# ============================================================================


@dataclass
class ChromaClient:
    """Main ChromaDB client structure."""

    config: ClientConfig
    collections: dict[str, Collection] = field(default_factory=dict)

    def __post_init__(self):
        if self.config.auth_config is None:
            self.config.auth_config = AuthConfig()

    def create_collection(
        self,
        name: str,
        metadata: dict[str, Any] | None = None,
        embedding_function: EmbeddingFunctionConfig | None = None,
        distance_function: DistanceFunction = DistanceFunction.EUCLIDEAN,
    ) -> Collection:
        """Create a new collection."""
        collection_id = str(uuid.uuid4())
        collection = Collection(
            name=name,
            id=collection_id,
            metadata=metadata,
            distance_function=distance_function,
            created_at=datetime.now(),
        )
        self.collections[name] = collection
        return collection

    def get_collection(self, name: str) -> Collection | None:
        """Get collection by name."""
        return self.collections.get(name)

    def list_collections(self) -> list[CollectionMetadata]:
        """List all collections."""
        return [
            CollectionMetadata(
                name=col.name,
                id=col.id,
                metadata=col.metadata,
                dimension=col.dimension,
                distance_function=col.distance_function,
                created_at=col.created_at,
                updated_at=col.updated_at,
            )
            for col in self.collections.values()
        ]

    def delete_collection(self, name: str) -> bool:
        """Delete a collection."""
        if name in self.collections:
            del self.collections[name]
            return True
        return False

    def get_or_create_collection(
        self,
        name: str,
        metadata: dict[str, Any] | None = None,
        embedding_function: EmbeddingFunctionConfig | None = None,
        distance_function: DistanceFunction = DistanceFunction.EUCLIDEAN,
    ) -> Collection:
        """Get existing collection or create new one."""
        collection = self.get_collection(name)
        if collection is None:
            collection = self.create_collection(
                name=name,
                metadata=metadata,
                embedding_function=embedding_function,
                distance_function=distance_function,
            )
        return collection

    def reset(self) -> None:
        """Reset the client (delete all collections)."""
        self.collections.clear()

    def heartbeat(self) -> int:
        """Get server heartbeat."""
        # This would be implemented by the actual Chroma client
        return 0

    def version(self) -> str:
        """Get server version."""
        # This would be implemented by the actual Chroma client
        return "0.4.0"


# ============================================================================
# Utility Functions
# ============================================================================


def create_client(
    host: str = "localhost",
    port: int = 8000,
    ssl: bool = False,
    auth_config: AuthConfig | None = None,
    embedding_function: EmbeddingFunctionConfig | None = None,
) -> ChromaClient:
    """Create a new ChromaDB client."""
    config = ClientConfig(
        host=host,
        port=port,
        ssl=ssl,
        auth_config=auth_config,
        embedding_function=embedding_function,
    )
    return ChromaClient(config=config)


def create_embedding_function(
    function_type: EmbeddingFunctionType,
    model_name: str | None = None,
    api_key: str | None = None,
    base_url: str | None = None,
    custom_function: EmbeddingFunction | None = None,
) -> EmbeddingFunctionConfig:
    """Create embedding function configuration."""
    return EmbeddingFunctionConfig(
        function_type=function_type,
        model_name=model_name,
        api_key=api_key,
        base_url=base_url,
        custom_function=custom_function,
    )


# ============================================================================
# Export all classes and functions
# ============================================================================

__all__ = [
    # Core structures
    "ID",
    # Authentication structures
    "AuthConfig",
    "AuthType",
    "ChromaClient",
    # Aliases
    "ChromaDocument",
    # Client structures
    "ClientConfig",
    "Collection",
    # Collection structures
    "CollectionMetadata",
    "CompositeFilter",
    "CreateCollectionRequest",
    # Enums
    "DistanceFunction",
    "Document",
    "Embedding",
    # Embedding function structures
    "EmbeddingFunction",
    "EmbeddingFunctionConfig",
    "EmbeddingFunctionType",
    # Include structure
    "Include",
    "IncludeType",
    "Metadata",
    # Query structures
    "QueryRequest",
    "QueryResponse",
    "QueryResult",
    "WhereDocumentFilter",
    # Filter structures
    "WhereFilter",
    # Utility functions
    "create_client",
    "create_embedding_function",
]


# Aliases for backward compatibility
ChromaDocument = Document
