"""
Comprehensive ChromaDB API dataclass implementation covering all functionality.

This module provides complete dataclass representations of all ChromaDB API components
as documented in the Chroma Cookbook: https://cookbook.chromadb.dev/core/api/

Based on the official Chroma API documentation and OpenAPI specification.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Union, Protocol
from datetime import datetime


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

    data: Dict[str, Any] = field(default_factory=dict)

    def get(self, key: str, default: Any = None) -> Any:
        """Get metadata value by key."""
        return self.data.get(key, default)

    def set(self, key: str, value: Any) -> None:
        """Set metadata value."""
        self.data[key] = value

    def update(self, metadata: Dict[str, Any]) -> None:
        """Update metadata with new values."""
        self.data.update(metadata)

    def __getitem__(self, key: str) -> Any:
        return self.data[key]

    def __setitem__(self, key: str, value: Any) -> None:
        self.data[key] = value


@dataclass
class Embedding:
    """Embedding vector structure."""

    vector: List[float]
    dimension: Optional[int] = None

    def __post_init__(self):
        if self.dimension is None:
            self.dimension = len(self.vector)
        elif self.dimension != len(self.vector):
            raise ValueError(
                f"Dimension mismatch: expected {self.dimension}, got {len(self.vector)}"
            )


@dataclass
class Document:
    """Document structure containing content, metadata, and embeddings."""

    id: ID
    content: str
    metadata: Optional[Metadata] = None
    embedding: Optional[Embedding] = None
    uri: Optional[str] = None

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

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format."""
        return {self.field: {self.operator: self.value}}


@dataclass
class WhereDocumentFilter:
    """Document content filter structure."""

    operator: str
    value: str

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format."""
        return {self.operator: self.value}


@dataclass
class CompositeFilter:
    """Composite filter combining multiple conditions."""

    and_conditions: Optional[List[Union[WhereFilter, WhereDocumentFilter]]] = None
    or_conditions: Optional[List[Union[WhereFilter, WhereDocumentFilter]]] = None

    def to_dict(self) -> Dict[str, Any]:
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

    def to_list(self) -> List[str]:
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

    query_texts: Optional[List[str]] = None
    query_embeddings: Optional[List[List[float]]] = None
    n_results: int = 10
    where: Optional[Dict[str, Any]] = None
    where_document: Optional[Dict[str, Any]] = None
    include: Optional[Include] = None
    collection_name: Optional[str] = None
    collection_id: Optional[str] = None

    def __post_init__(self):
        if self.include is None:
            self.include = Include(metadatas=True, documents=True, distances=True)


@dataclass
class QueryResult:
    """Single query result structure."""

    id: str
    distance: Optional[float] = None
    metadata: Optional[Dict[str, Any]] = None
    document: Optional[str] = None
    embedding: Optional[List[float]] = None
    uri: Optional[str] = None
    data: Optional[Any] = None


@dataclass
class QueryResponse:
    """Query response structure."""

    ids: List[List[str]]
    distances: Optional[List[List[float]]] = None
    metadatas: Optional[List[List[Dict[str, Any]]]] = None
    documents: Optional[List[List[str]]] = None
    embeddings: Optional[List[List[List[float]]]] = None
    uris: Optional[List[List[str]]] = None
    data: Optional[List[List[Any]]] = None

    def get_results(self, query_index: int = 0) -> List[QueryResult]:
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
    metadata: Optional[Dict[str, Any]] = None
    dimension: Optional[int] = None
    distance_function: DistanceFunction = DistanceFunction.EUCLIDEAN
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


@dataclass
class CreateCollectionRequest:
    """Request to create a new collection."""

    name: str
    metadata: Optional[Dict[str, Any]] = None
    embedding_function: Optional[str] = None
    distance_function: DistanceFunction = DistanceFunction.EUCLIDEAN


@dataclass
class Collection:
    """Collection structure."""

    name: str
    id: str
    metadata: Optional[Dict[str, Any]] = None
    dimension: Optional[int] = None
    distance_function: DistanceFunction = DistanceFunction.EUCLIDEAN
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    count: int = 0

    def add(
        self,
        documents: List[str],
        metadatas: Optional[List[Dict[str, Any]]] = None,
        ids: Optional[List[str]] = None,
        embeddings: Optional[List[List[float]]] = None,
        uris: Optional[List[str]] = None,
    ) -> List[str]:
        """Add documents to collection."""
        # This would be implemented by the actual Chroma client
        return []
        pass

    def query(
        self,
        query_texts: Optional[List[str]] = None,
        query_embeddings: Optional[List[List[float]]] = None,
        n_results: int = 10,
        where: Optional[Dict[str, Any]] = None,
        where_document: Optional[Dict[str, Any]] = None,
        include: Optional[Include] = None,
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
        pass

    def get(
        self,
        ids: Optional[List[str]] = None,
        where: Optional[Dict[str, Any]] = None,
        where_document: Optional[Dict[str, Any]] = None,
        include: Optional[Include] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
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
        pass

    def update(
        self,
        ids: List[str],
        documents: Optional[List[str]] = None,
        metadatas: Optional[List[Dict[str, Any]]] = None,
        embeddings: Optional[List[List[float]]] = None,
        uris: Optional[List[str]] = None,
    ) -> None:
        """Update documents in collection."""
        # This would be implemented by the actual Chroma client
        pass

    def delete(
        self,
        ids: Optional[List[str]] = None,
        where: Optional[Dict[str, Any]] = None,
        where_document: Optional[Dict[str, Any]] = None,
    ) -> List[str]:
        """Delete documents from collection."""
        # This would be implemented by the actual Chroma client
        return []
        pass

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

    def __call__(self, input_texts: List[str]) -> List[List[float]]:
        """Generate embeddings for input texts."""
        ...


@dataclass
class EmbeddingFunctionConfig:
    """Configuration for embedding functions."""

    function_type: EmbeddingFunctionType
    model_name: Optional[str] = None
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    custom_function: Optional[EmbeddingFunction] = None
    dimension: Optional[int] = None

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
    username: Optional[str] = None
    password: Optional[str] = None
    token: Optional[str] = None
    ssl_enabled: bool = False
    ssl_cert_path: Optional[str] = None
    ssl_key_path: Optional[str] = None


# ============================================================================
# Client Configuration
# ============================================================================


@dataclass
class ClientConfig:
    """ChromaDB client configuration."""

    host: str = "localhost"
    port: int = 8000
    ssl: bool = False
    headers: Optional[Dict[str, str]] = None
    settings: Optional[Dict[str, Any]] = None
    auth_config: Optional[AuthConfig] = None
    embedding_function: Optional[EmbeddingFunctionConfig] = None


# ============================================================================
# Main Client Structure
# ============================================================================


@dataclass
class ChromaClient:
    """Main ChromaDB client structure."""

    config: ClientConfig
    collections: Dict[str, Collection] = field(default_factory=dict)

    def __post_init__(self):
        if self.config.auth_config is None:
            self.config.auth_config = AuthConfig()

    def create_collection(
        self,
        name: str,
        metadata: Optional[Dict[str, Any]] = None,
        embedding_function: Optional[EmbeddingFunctionConfig] = None,
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

    def get_collection(self, name: str) -> Optional[Collection]:
        """Get collection by name."""
        return self.collections.get(name)

    def list_collections(self) -> List[CollectionMetadata]:
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
        metadata: Optional[Dict[str, Any]] = None,
        embedding_function: Optional[EmbeddingFunctionConfig] = None,
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
    auth_config: Optional[AuthConfig] = None,
    embedding_function: Optional[EmbeddingFunctionConfig] = None,
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
    model_name: Optional[str] = None,
    api_key: Optional[str] = None,
    base_url: Optional[str] = None,
    custom_function: Optional[EmbeddingFunction] = None,
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
    # Enums
    "DistanceFunction",
    "IncludeType",
    "AuthType",
    "EmbeddingFunctionType",
    # Core structures
    "ID",
    "Metadata",
    "Embedding",
    "Document",
    # Filter structures
    "WhereFilter",
    "WhereDocumentFilter",
    "CompositeFilter",
    # Include structure
    "Include",
    # Query structures
    "QueryRequest",
    "QueryResult",
    "QueryResponse",
    # Collection structures
    "CollectionMetadata",
    "CreateCollectionRequest",
    "Collection",
    # Embedding function structures
    "EmbeddingFunction",
    "EmbeddingFunctionConfig",
    # Authentication structures
    "AuthConfig",
    # Client structures
    "ClientConfig",
    "ChromaClient",
    # Utility functions
    "create_client",
    "create_embedding_function",
    # Aliases
    "ChromaDocument",
]


# Aliases for backward compatibility
ChromaDocument = Document
