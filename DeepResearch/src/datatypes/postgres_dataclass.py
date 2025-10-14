"""
Comprehensive PostgREST API dataclass implementation covering all functionality.

This module provides complete dataclass representations of all PostgREST API components
as documented in the official PostgREST API reference: https://docs.postgrest.org/en/v13/references/api.html

Based on the official PostgREST API documentation and OpenAPI specification.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

# ============================================================================
# Core Enums and Types
# ============================================================================


class HTTPMethod(str, Enum):
    """HTTP methods supported by PostgREST."""

    GET = "GET"
    POST = "POST"
    PUT = "PUT"
    PATCH = "PATCH"
    DELETE = "DELETE"
    HEAD = "HEAD"
    OPTIONS = "OPTIONS"


class MediaType(str, Enum):
    """Media types supported by PostgREST."""

    JSON = "application/json"
    CSV = "text/csv"
    TEXT = "text/plain"
    HTML = "text/html"
    XML = "application/xml"
    BINARY = "application/octet-stream"


class PreferHeader(str, Enum):
    """Prefer header values for PostgREST."""

    RETURN_MINIMAL = "return=minimal"
    RETURN_REPRESENTATION = "return=representation"
    RESOLUTION_IGNORE_DUPLICATES = "resolution=ignore-duplicates"
    RESOLUTION_MERGE_DUPLICATES = "resolution=merge-duplicates"


class FilterOperator(str, Enum):
    """Filter operators supported by PostgREST."""

    EQUALS = "eq"
    NOT_EQUALS = "neq"
    GREATER_THAN = "gt"
    GREATER_THAN_OR_EQUAL = "gte"
    LESS_THAN = "lt"
    LESS_THAN_OR_EQUAL = "lte"
    LIKE = "like"
    ILIKE = "ilike"
    IS = "is"
    IN = "in"
    CONTAINS = "cs"
    CONTAINED_BY = "cd"
    OVERLAPS = "ov"
    STRICT_LEFT = "sl"
    STRICT_RIGHT = "sr"
    NOT_EXTEND_RIGHT = "nxr"
    NOT_EXTEND_LEFT = "nxl"
    ADJACENT = "adj"
    MATCH = "match"
    NOT = "not"
    OR = "or"
    AND = "and"


class OrderDirection(str, Enum):
    """Order direction for sorting."""

    ASCENDING = "asc"
    DESCENDING = "desc"
    ASCENDING_NULLS_FIRST = "asc.nullsfirst"
    ASCENDING_NULLS_LAST = "asc.nullslast"
    DESCENDING_NULLS_FIRST = "desc.nullsfirst"
    DESCENDING_NULLS_LAST = "desc.nullslast"


class AggregateFunction(str, Enum):
    """Aggregate functions supported by PostgREST."""

    COUNT = "count"
    SUM = "sum"
    AVG = "avg"
    MAX = "max"
    MIN = "min"
    STDDEV = "stddev"
    VARIANCE = "variance"
    BIT_AND = "bit_and"
    BIT_OR = "bit_or"
    BOOL_AND = "bool_and"
    BOOL_OR = "bool_or"
    STRING_AGG = "string_agg"
    ARRAY_AGG = "array_agg"
    JSON_AGG = "json_agg"
    JSONB_AGG = "jsonb_agg"


class SchemaVisibility(str, Enum):
    """Schema visibility options."""

    PUBLIC = "public"
    PRIVATE = "private"
    EXPOSED = "exposed"


# ============================================================================
# Core Data Structures
# ============================================================================


@dataclass
class PostgRESTID:
    """PostgREST resource ID structure."""

    value: str | int

    def __post_init__(self):
        if self.value is None:
            self.value = str(uuid.uuid4())

    def __str__(self) -> str:
        return str(self.value)


@dataclass
class Column:
    """Database column structure."""

    name: str
    data_type: str
    is_nullable: bool = True
    is_primary_key: bool = False
    is_foreign_key: bool = False
    default_value: Any | None = None
    constraints: list[str] = field(default_factory=list)
    description: str | None = None


@dataclass
class Table:
    """Database table structure."""

    name: str
    schema: str = "public"
    columns: list[Column] = field(default_factory=list)
    primary_keys: list[str] = field(default_factory=list)
    foreign_keys: dict[str, str] = field(default_factory=dict)
    indexes: list[str] = field(default_factory=list)
    description: str | None = None

    def get_column(self, name: str) -> Column | None:
        """Get column by name."""
        for col in self.columns:
            if col.name == name:
                return col
        return None


@dataclass
class View:
    """Database view structure."""

    name: str
    definition: str
    schema: str = "public"
    columns: list[Column] = field(default_factory=list)
    is_updatable: bool = False
    description: str | None = None


@dataclass
class Function:
    """Database function structure."""

    name: str
    return_type: str
    schema: str = "public"
    parameters: list[dict[str, Any]] = field(default_factory=list)
    is_volatile: bool = False
    is_security_definer: bool = False
    language: str = "sql"
    definition: str | None = None
    description: str | None = None


@dataclass
class Schema:
    """Database schema structure."""

    name: str
    owner: str | None = None
    tables: list[Table] = field(default_factory=list)
    views: list[View] = field(default_factory=list)
    functions: list[Function] = field(default_factory=list)
    visibility: SchemaVisibility = SchemaVisibility.PUBLIC
    description: str | None = None


# ============================================================================
# Filter Structures
# ============================================================================


@dataclass
class Filter:
    """Single filter condition."""

    column: str
    operator: FilterOperator
    value: Any

    def to_query_param(self) -> str:
        """Convert to query parameter format."""
        if self.operator == FilterOperator.IN and isinstance(self.value, list):
            return f"{self.column}={self.operator.value}.({','.join(map(str, self.value))})"
        if self.operator == FilterOperator.IS:
            return f"{self.column}={self.operator.value}.{self.value}"
        return f"{self.column}={self.operator.value}.{self.value}"


@dataclass
class CompositeFilter:
    """Composite filter combining multiple conditions."""

    and_conditions: list[Filter] | None = None
    or_conditions: list[Filter] | None = None

    def to_query_params(self) -> list[str]:
        """Convert to query parameters."""
        params = []
        if self.and_conditions:
            for condition in self.and_conditions:
                params.append(condition.to_query_param())
        if self.or_conditions:
            or_param = f"or=({','.join(condition.to_query_param() for condition in self.or_conditions)})"
            params.append(or_param)
        return params


@dataclass
class OrderBy:
    """Order by clause."""

    column: str
    direction: OrderDirection = OrderDirection.ASCENDING
    nulls_first: bool | None = None

    def to_query_param(self) -> str:
        """Convert to query parameter."""
        if self.nulls_first is not None:
            if self.nulls_first:
                direction = f"{self.direction.value}.nullsfirst"
            else:
                direction = f"{self.direction.value}.nullslast"
        else:
            direction = self.direction.value
        return f"order={self.column}.{direction}"


# ============================================================================
# Select and Embedding Structures
# ============================================================================


@dataclass
class SelectClause:
    """SELECT clause specification."""

    columns: list[str] = field(default_factory=lambda: ["*"])
    distinct: bool = False

    def to_query_param(self) -> str:
        """Convert to query parameter."""
        if self.distinct:
            return f"select={','.join(self.columns)}"
        return f"select={','.join(self.columns)}"


@dataclass
class Embedding:
    """Resource embedding specification."""

    relation: str
    columns: list[str] | None = None
    filters: list[Filter] | None = None
    order_by: list[OrderBy] | None = None
    limit: int | None = None
    offset: int | None = None

    def to_query_param(self) -> str:
        """Convert to query parameter."""
        parts = [self.relation]
        if self.columns:
            parts.append(f"select({','.join(self.columns)})")
        if self.filters:
            filter_parts = [
                f"{f.column}.{f.operator.value}.{f.value}" for f in self.filters
            ]
            parts.append(f"filter({','.join(filter_parts)})")
        if self.order_by:
            order_parts = [f"{o.column}.{o.direction.value}" for o in self.order_by]
            parts.append(f"order({','.join(order_parts)})")
        if self.limit:
            parts.append(f"limit({self.limit})")
        if self.offset:
            parts.append(f"offset({self.offset})")
        return f"select={','.join(parts)}"


@dataclass
class ComputedField:
    """Computed field specification."""

    name: str
    expression: str
    alias: str | None = None

    def to_query_param(self) -> str:
        """Convert to query parameter."""
        if self.alias:
            return f"select={self.name}:{self.expression} as {self.alias}"
        return f"select={self.name}:{self.expression}"


# ============================================================================
# Pagination Structures
# ============================================================================


@dataclass
class Pagination:
    """Pagination specification."""

    limit: int | None = None
    offset: int | None = None
    page: int | None = None
    page_size: int | None = None

    def to_query_params(self) -> list[str]:
        """Convert to query parameters."""
        params = []
        if self.limit:
            params.append(f"limit={self.limit}")
        if self.offset:
            params.append(f"offset={self.offset}")
        if self.page and self.page_size:
            offset = (self.page - 1) * self.page_size
            params.append(f"offset={offset}")
            params.append(f"limit={self.page_size}")
        return params


@dataclass
class CountHeader:
    """Count header specification."""

    exact: bool = False
    planned: bool = False
    estimated: bool = False

    def to_header_value(self) -> str:
        """Convert to header value."""
        if self.exact:
            return "exact"
        if self.planned:
            return "planned"
        if self.estimated:
            return "estimated"
        return "none"


# ============================================================================
# Query Request/Response Structures
# ============================================================================


@dataclass
class QueryRequest:
    """Query request structure."""

    table: str
    schema: str = "public"
    select: SelectClause | None = None
    filters: list[Filter] | None = None
    order_by: list[OrderBy] | None = None
    pagination: Pagination | None = None
    embeddings: list[Embedding] | None = None
    computed_fields: list[ComputedField] | None = None
    aggregates: dict[str, AggregateFunction] | None = None
    method: HTTPMethod = HTTPMethod.GET
    headers: dict[str, str] = field(default_factory=dict)
    prefer: PreferHeader | None = None

    def __post_init__(self):
        if self.select is None:
            self.select = SelectClause()

    def to_url_params(self) -> str:
        """Convert to URL query parameters."""
        params = []

        if self.select:
            params.append(self.select.to_query_param())

        if self.filters:
            for filter_ in self.filters:
                params.append(filter_.to_query_param())

        if self.order_by:
            for order in self.order_by:
                params.append(order.to_query_param())

        if self.pagination:
            params.extend(self.pagination.to_query_params())

        if self.embeddings:
            for embedding in self.embeddings:
                params.append(embedding.to_query_param())

        if self.computed_fields:
            for field in self.computed_fields:
                params.append(field.to_query_param())

        if self.aggregates:
            for column, func in self.aggregates.items():
                params.append(f"select={func.value}({column})")

        return "&".join(params)


@dataclass
class QueryResponse:
    """Query response structure."""

    data: list[dict[str, Any]]
    count: int | None = None
    content_range: str | None = None
    content_type: MediaType = MediaType.JSON
    status_code: int = 200
    headers: dict[str, str] = field(default_factory=dict)

    def get_total_count(self) -> int | None:
        """Extract total count from content-range header."""
        if self.content_range:
            # Format: "0-9/100" or "items 0-9/100"
            parts = self.content_range.split("/")
            if len(parts) == 2:
                try:
                    return int(parts[1])
                except ValueError:
                    pass
        return self.count


# ============================================================================
# CRUD Operation Structures
# ============================================================================


@dataclass
class InsertRequest:
    """Insert operation request."""

    table: str
    data: dict[str, Any] | list[dict[str, Any]]
    schema: str = "public"
    columns: list[str] | None = None
    prefer: PreferHeader = PreferHeader.RETURN_REPRESENTATION
    headers: dict[str, str] = field(default_factory=dict)

    def to_json(self) -> dict[str, Any] | list[dict[str, Any]]:
        """Convert to JSON format."""
        if isinstance(self.data, list):
            if self.columns:
                return [
                    {col: item.get(col) for col in self.columns} for item in self.data
                ]
            return self.data
        if self.columns:
            return {col: self.data.get(col) for col in self.columns}
        return self.data


@dataclass
class UpdateRequest:
    """Update operation request."""

    table: str
    data: dict[str, Any]
    filters: list[Filter]
    schema: str = "public"
    prefer: PreferHeader = PreferHeader.RETURN_REPRESENTATION
    headers: dict[str, str] = field(default_factory=dict)

    def to_url_params(self) -> str:
        """Convert filters to URL parameters."""
        return "&".join(filter_.to_query_param() for filter_ in self.filters)


@dataclass
class DeleteRequest:
    """Delete operation request."""

    table: str
    filters: list[Filter]
    schema: str = "public"
    prefer: PreferHeader = PreferHeader.RETURN_MINIMAL
    headers: dict[str, str] = field(default_factory=dict)

    def to_url_params(self) -> str:
        """Convert filters to URL parameters."""
        return "&".join(filter_.to_query_param() for filter_ in self.filters)


@dataclass
class UpsertRequest:
    """Upsert operation request."""

    table: str
    data: dict[str, Any] | list[dict[str, Any]]
    schema: str = "public"
    on_conflict: str | None = None
    prefer: PreferHeader = PreferHeader.RESOLUTION_MERGE_DUPLICATES
    headers: dict[str, str] = field(default_factory=dict)


# ============================================================================
# RPC (Remote Procedure Call) Structures
# ============================================================================


@dataclass
class RPCRequest:
    """RPC (stored function) request."""

    function: str
    schema: str = "public"
    parameters: dict[str, Any] = field(default_factory=dict)
    method: HTTPMethod = HTTPMethod.POST
    prefer: PreferHeader = PreferHeader.RETURN_REPRESENTATION
    headers: dict[str, str] = field(default_factory=dict)

    def to_json(self) -> dict[str, Any]:
        """Convert parameters to JSON format."""
        return self.parameters


@dataclass
class RPCResponse:
    """RPC response structure."""

    data: Any
    content_type: MediaType = MediaType.JSON
    status_code: int = 200
    headers: dict[str, str] = field(default_factory=dict)


# ============================================================================
# Authentication and Authorization Structures
# ============================================================================


@dataclass
class AuthConfig:
    """Authentication configuration."""

    auth_type: str = "bearer"  # bearer, basic, api_key
    token: str | None = None
    username: str | None = None
    password: str | None = None
    api_key: str | None = None
    api_key_header: str = "X-API-Key"

    def get_auth_header(self) -> tuple[str, str] | None:
        """Get authentication header."""
        if self.auth_type == "bearer" and self.token:
            return ("Authorization", f"Bearer {self.token}")
        if self.auth_type == "basic" and self.username and self.password:
            import base64

            credentials = base64.b64encode(
                f"{self.username}:{self.password}".encode()
            ).decode()
            return ("Authorization", f"Basic {credentials}")
        if self.auth_type == "api_key" and self.api_key:
            return (self.api_key_header, self.api_key)
        return None


@dataclass
class RoleConfig:
    """Database role configuration."""

    role: str
    permissions: list[str] = field(default_factory=list)
    row_level_security: bool = False
    policies: list[str] = field(default_factory=list)


# ============================================================================
# Client Configuration
# ============================================================================


@dataclass
class PostgRESTConfig:
    """PostgREST client configuration."""

    base_url: str
    schema: str = "public"
    auth: AuthConfig | None = None
    default_headers: dict[str, str] = field(default_factory=dict)
    timeout: float = 30.0
    max_retries: int = 3
    verify_ssl: bool = True
    connection_pool_size: int = 10

    def __post_init__(self):
        if not self.base_url.endswith("/"):
            self.base_url += "/"


# ============================================================================
# Main Client Structure
# ============================================================================


@dataclass
class PostgRESTClient:
    """Main PostgREST client structure."""

    config: PostgRESTConfig
    schemas: dict[str, Schema] = field(default_factory=dict)

    def __post_init__(self):
        if self.config.auth is None:
            self.config.auth = AuthConfig()

    def get_url(self, resource: str, schema: str | None = None) -> str:
        """Get full URL for a resource."""
        schema = schema or self.config.schema
        return f"{self.config.base_url}{schema}/{resource}"

    def get_headers(
        self, additional_headers: dict[str, str] | None = None
    ) -> dict[str, str]:
        """Get request headers."""
        headers = self.config.default_headers.copy()

        # Add auth header
        auth_header = self.config.auth.get_auth_header()
        if auth_header:
            headers[auth_header[0]] = auth_header[1]

        # Add additional headers
        if additional_headers:
            headers.update(additional_headers)

        return headers

    def query(self, _request: QueryRequest) -> QueryResponse:
        """Execute a query request."""
        # This would be implemented by the actual PostgREST client
        return QueryResponse(data=[], count=0, status_code=501)

    def insert(self, _request: InsertRequest) -> QueryResponse:
        """Execute an insert request."""
        # This would be implemented by the actual PostgREST client
        return QueryResponse(data=[], count=0, status_code=501)

    def update(self, _request: UpdateRequest) -> QueryResponse:
        """Execute an update request."""
        # This would be implemented by the actual PostgREST client
        return QueryResponse(data=[], count=0, status_code=501)

    def delete(self, _request: DeleteRequest) -> QueryResponse:
        """Execute a delete request."""
        # This would be implemented by the actual PostgREST client
        return QueryResponse(data=[], count=0, status_code=501)

    def upsert(self, _request: UpsertRequest) -> QueryResponse:
        """Execute an upsert request."""
        # This would be implemented by the actual PostgREST client
        return QueryResponse(data=[], count=0, status_code=501)

    def rpc(self, _request: RPCRequest) -> RPCResponse:
        """Execute an RPC request."""
        # This would be implemented by the actual PostgREST client
        return RPCResponse(data=[], status_code=501)

    def get_schema(self, schema_name: str) -> Schema | None:
        """Get schema by name."""
        return self.schemas.get(schema_name)

    def list_schemas(self) -> list[Schema]:
        """List all available schemas."""
        return list(self.schemas.values())

    def get_table(
        self, table_name: str, schema_name: str | None = None
    ) -> Table | None:
        """Get table by name."""
        schema_name = schema_name or self.config.schema
        schema = self.get_schema(schema_name)
        if schema:
            for table in schema.tables:
                if table.name == table_name:
                    return table
        return None

    def get_view(self, view_name: str, schema_name: str | None = None) -> View | None:
        """Get view by name."""
        schema_name = schema_name or self.config.schema
        schema = self.get_schema(schema_name)
        if schema:
            for view in schema.views:
                if view.name == view_name:
                    return view
        return None

    def get_function(
        self, function_name: str, schema_name: str | None = None
    ) -> Function | None:
        """Get function by name."""
        schema_name = schema_name or self.config.schema
        schema = self.get_schema(schema_name)
        if schema:
            for func in schema.functions:
                if func.name == function_name:
                    return func
        return None


# ============================================================================
# Error Handling Structures
# ============================================================================


@dataclass
class PostgRESTError:
    """PostgREST error structure."""

    code: str
    message: str
    details: str | None = None
    hint: str | None = None
    status_code: int = 400

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "code": self.code,
            "message": self.message,
            "details": self.details,
            "hint": self.hint,
            "status_code": self.status_code,
        }


@dataclass
class PostgRESTException(Exception):
    """PostgREST exception."""

    error: PostgRESTError

    def __str__(self) -> str:
        return f"PostgREST Error {self.error.status_code}: {self.error.message}"


# ============================================================================
# Utility Functions
# ============================================================================


def create_client(
    base_url: str, schema: str = "public", auth: AuthConfig | None = None, **kwargs
) -> PostgRESTClient:
    """Create a new PostgREST client."""
    config = PostgRESTConfig(base_url=base_url, schema=schema, auth=auth, **kwargs)
    return PostgRESTClient(config=config)


def create_filter(column: str, operator: FilterOperator, value: Any) -> Filter:
    """Create a filter condition."""
    return Filter(column=column, operator=operator, value=value)


def create_order_by(
    column: str, direction: OrderDirection = OrderDirection.ASCENDING
) -> OrderBy:
    """Create an order by clause."""
    return OrderBy(column=column, direction=direction)


def create_pagination(
    limit: int | None = None, offset: int | None = None
) -> Pagination:
    """Create pagination specification."""
    return Pagination(limit=limit, offset=offset)


def create_embedding(
    relation: str,
    columns: list[str] | None = None,
    filters: list[Filter] | None = None,
) -> Embedding:
    """Create an embedding specification."""
    return Embedding(relation=relation, columns=columns, filters=filters)


# ============================================================================
# Export all classes and functions
# ============================================================================

__all__ = [
    "AggregateFunction",
    # Authentication structures
    "AuthConfig",
    "Column",
    "CompositeFilter",
    "ComputedField",
    "CountHeader",
    "DeleteRequest",
    "Embedding",
    # Filter structures
    "Filter",
    "FilterOperator",
    "Function",
    # Enums
    "HTTPMethod",
    # CRUD structures
    "InsertRequest",
    "MediaType",
    "OrderBy",
    "OrderDirection",
    # Pagination structures
    "Pagination",
    "PostgRESTClient",
    # Client structures
    "PostgRESTConfig",
    # Error structures
    "PostgRESTError",
    "PostgRESTException",
    # Core structures
    "PostgRESTID",
    # Document structures
    "PostgresDocument",
    "PreferHeader",
    # Query structures
    "QueryRequest",
    "QueryResponse",
    # RPC structures
    "RPCRequest",
    "RPCResponse",
    "RoleConfig",
    "Schema",
    "SchemaVisibility",
    # Select and embedding structures
    "SelectClause",
    "Table",
    "UpdateRequest",
    "UpsertRequest",
    "View",
    # Utility functions
    "create_client",
    "create_embedding",
    "create_filter",
    "create_order_by",
    "create_pagination",
]


@dataclass
class PostgresDocument:
    """Document structure for PostgreSQL storage."""

    id: str
    content: str
    metadata: dict[str, Any] | None = None
    embedding: list[float] | None = None
    created_at: str | None = None
    updated_at: str | None = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}
        if self.created_at is None:
            self.created_at = str(uuid.uuid4())
