from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, HttpUrl


class Neo4jAuthType(str, Enum):
    BASIC = "basic"
    NONE = "none"


class Neo4jConnectionConfig(BaseModel):
    """Connection settings for Neo4j database."""

    uri: str = Field(
        ..., description="Neo4j bolt/neo4j URI, e.g. neo4j://localhost:7687"
    )
    username: str = Field("neo4j", description="Neo4j username")
    password: str = Field("", description="Neo4j password")
    database: str = Field("neo4j", description="Neo4j database name")
    auth_type: Neo4jAuthType = Field(Neo4jAuthType.BASIC, description="Auth type")
    encrypted: bool = Field(False, description="Enable TLS encryption")


class VectorIndexMetric(str, Enum):
    COSINE = "cosine"
    EUCLIDEAN = "euclidean"


class VectorIndexConfig(BaseModel):
    """Configuration for a Neo4j vector index."""

    index_name: str = Field(..., description="Vector index name")
    node_label: str = Field(..., description="Label of nodes to index")
    vector_property: str = Field(..., description="Property key storing the vector")
    dimensions: int = Field(..., gt=0, description="Embedding dimensions")
    metric: VectorIndexMetric = Field(
        VectorIndexMetric.COSINE, description="Similarity metric"
    )


class Neo4jQuery(BaseModel):
    """Parameterized Cypher query wrapper."""

    cypher: str
    params: dict[str, Any] = Field(default_factory=dict)


class Neo4jResult(BaseModel):
    """Query result wrapper (rows as dictionaries)."""

    rows: list[dict[str, Any]] = Field(default_factory=list)
    summary: dict[str, Any] = Field(default_factory=dict)


class HostedVectorStoreRef(BaseModel):
    """Reference to a vector store hosted in Neo4j."""

    index_name: str
    database: str = "neo4j"
    api_url: HttpUrl | None = None


class Neo4jVectorStoreConfig(BaseModel):
    """Configuration for Neo4j vector store integration."""

    connection: Neo4jConnectionConfig = Field(
        ..., description="Neo4j connection settings"
    )
    index: VectorIndexConfig = Field(..., description="Vector index configuration")
    search_defaults: VectorSearchDefaults = Field(
        default_factory=lambda: VectorSearchDefaults(),
        description="Default search parameters",
    )
    batch_size: int = Field(100, gt=0, description="Batch size for bulk operations")
    max_connections: int = Field(10, gt=0, description="Maximum connection pool size")


class VectorSearchDefaults(BaseModel):
    """Default parameters for vector search operations."""

    top_k: int = Field(10, gt=0, description="Default number of results to return")
    score_threshold: float = Field(
        0.0, ge=0.0, le=1.0, description="Minimum similarity score"
    )
    max_results: int = Field(1000, gt=0, description="Maximum results to retrieve")
    include_metadata: bool = Field(
        True, description="Include metadata in search results"
    )
    include_scores: bool = Field(True, description="Include similarity scores")


class Neo4jMigrationConfig(BaseModel):
    """Configuration for Neo4j database migrations."""

    create_constraints: bool = Field(True, description="Create database constraints")
    create_indexes: bool = Field(True, description="Create database indexes")
    vector_indexes: list[VectorIndexConfig] = Field(
        default_factory=list, description="Vector indexes to create"
    )
    schema_validation: bool = Field(True, description="Validate schema after migration")
    backup_before_migration: bool = Field(
        False, description="Create backup before migration"
    )


class Neo4jPublicationSchema(BaseModel):
    """Schema definition for publication data in Neo4j."""

    node_labels: dict[str, list[str]] = Field(
        default_factory=lambda: {
            "Publication": ["eid", "doi", "title", "year", "abstract", "citedBy"],
            "Author": ["id", "name"],
            "Journal": ["name"],
            "Institution": ["name", "country", "city"],
            "Country": ["name"],
            "Keyword": ["name"],
            "Grant": ["agency", "string"],
            "FundingAgency": ["name"],
            "Document": ["id", "content"],
        },
        description="Node labels and their properties",
    )

    relationship_types: dict[str, tuple[str, str]] = Field(
        default_factory=lambda: {
            "AUTHORED": ("Author", "Publication"),
            "PUBLISHED_IN": ("Publication", "Journal"),
            "AFFILIATED_WITH": ("Author", "Institution"),
            "LOCATED_IN": ("Institution", "Country"),
            "HAS_KEYWORD": ("Publication", "Keyword"),
            "CITES": ("Publication", "Publication"),
            "FUNDED_BY": ("Publication", "Grant"),
            "PROVIDED_BY": ("Grant", "FundingAgency"),
            "HAS_DOCUMENT": ("Publication", "Document"),
        },
        description="Relationship types and their connected node types",
    )


class Neo4jSearchRequest(BaseModel):
    """Request parameters for Neo4j vector search."""

    query: str | None = Field(None, description="Text query for semantic search")
    query_embedding: list[float] | None = Field(
        None, description="Pre-computed embedding vector"
    )
    top_k: int = Field(10, gt=0, description="Number of results to return")
    score_threshold: float = Field(
        0.0, ge=0.0, le=1.0, description="Minimum similarity score"
    )
    filters: dict[str, Any] = Field(
        default_factory=dict, description="Metadata filters to apply"
    )
    include_metadata: bool = Field(True, description="Include metadata in results")
    include_scores: bool = Field(True, description="Include similarity scores")
    search_type: str = Field("similarity", description="Type of search to perform")


class Neo4jSearchResponse(BaseModel):
    """Response from Neo4j vector search."""

    results: list[dict[str, Any]] = Field(
        default_factory=list, description="Search results with documents and metadata"
    )
    total_found: int = Field(0, description="Total number of results found")
    search_time: float = Field(0.0, description="Search execution time in seconds")
    query_processed: bool = Field(
        True, description="Whether the query was successfully processed"
    )


class Neo4jBatchOperation(BaseModel):
    """Configuration for batch operations in Neo4j."""

    operation_type: str = Field(..., description="Type of batch operation")
    batch_size: int = Field(100, gt=0, description="Size of each batch")
    max_retries: int = Field(3, ge=0, description="Maximum retry attempts per batch")
    retry_delay: float = Field(
        1.0, gt=0, description="Delay between retries in seconds"
    )
    continue_on_error: bool = Field(
        False, description="Continue processing if batch fails"
    )
    progress_callback: str | None = Field(
        None, description="Callback function for progress updates"
    )


class Neo4jHealthCheck(BaseModel):
    """Health check configuration for Neo4j connections."""

    enabled: bool = Field(True, description="Enable health checks")
    interval_seconds: int = Field(60, gt=0, description="Health check interval")
    timeout_seconds: int = Field(10, gt=0, description="Health check timeout")
    max_failures: int = Field(3, ge=0, description="Maximum consecutive failures")
    retry_delay_seconds: float = Field(5.0, gt=0, description="Delay before retry")


class Neo4jVectorSearchConfig(BaseModel):
    """Comprehensive configuration for Neo4j vector search operations."""

    connection: Neo4jConnectionConfig = Field(
        ..., description="Database connection settings"
    )
    index: VectorIndexConfig = Field(..., description="Vector index configuration")
    search: VectorSearchDefaults = Field(
        default_factory=lambda: VectorSearchDefaults(),
        description="Search operation defaults",
    )
    batch: Neo4jBatchOperation = Field(
        default_factory=lambda: Neo4jBatchOperation(operation_type="search"),
        description="Batch operation settings",
    )
    health: Neo4jHealthCheck = Field(
        default_factory=lambda: Neo4jHealthCheck(),
        description="Health check configuration",
    )
    migration: Neo4jMigrationConfig = Field(
        default_factory=lambda: Neo4jMigrationConfig(), description="Migration settings"
    )
    publication_schema: Neo4jPublicationSchema = Field(
        default_factory=lambda: Neo4jPublicationSchema(),
        description="Database schema definition",
    )
