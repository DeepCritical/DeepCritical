from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from typing import Any

from neo4j import AsyncGraphDatabase, GraphDatabase

from ..datatypes.neo4j_types import (
    Neo4jConnectionConfig,
    VectorIndexConfig,
    VectorIndexMetric,
)
from ..datatypes.rag import (
    Chunk,
    Document,
    Embeddings,
    SearchResult,
    SearchType,
    VectorStore,
    VectorStoreConfig,
)
from .neo4j_config import Neo4jVectorStoreConfig


class Neo4jVectorStore(VectorStore):
    """Neo4j-backed vector store using native vector index (Neo4j 5)."""

    def __init__(
        self,
        config: VectorStoreConfig,
        embeddings: Embeddings,
        neo4j_config: Neo4jConnectionConfig | None = None,
    ):
        """Initialize Neo4j vector store.

        Args:
            config: Vector store configuration
            embeddings: Embeddings provider
            neo4j_config: Neo4j connection configuration (optional)
        """
        super().__init__(config, embeddings)

        # Neo4j connection configuration
        if neo4j_config is None:
            # Extract from vector store config if available
            neo4j_config = getattr(config, "connection", None)
            if neo4j_config is None:
                # Create from basic config
                neo4j_config = Neo4jConnectionConfig(
                    uri=config.connection_string or "neo4j://localhost:7687",
                    username="neo4j",
                    password="password",
                    database=config.database or "neo4j",
                )

        self.neo4j_config = neo4j_config

        # Vector index configuration
        index_config = getattr(config, "index", None)
        if index_config is None:
            index_config = VectorIndexConfig(
                index_name=config.collection_name or "document_vectors",
                node_label="Document",
                vector_property="embedding",
                dimensions=config.embedding_dimension,
                metric=VectorIndexMetric(config.distance_metric or "cosine"),
            )

        self.vector_index_config = index_config

        # Sync driver for blocking operations
        self._driver = None
        # Async driver for async operations
        self._async_driver = None

    @property
    def driver(self):
        """Get the Neo4j driver."""
        if self._driver is None:
            self._driver = GraphDatabase.driver(
                self.neo4j_config.uri,
                auth=(
                    self.neo4j_config.username,
                    self.neo4j_config.password,
                )
                if self.neo4j_config.username
                else None,
                encrypted=self.neo4j_config.encrypted,
            )
        return self._driver

    @property
    def async_driver(self):
        """Get the async Neo4j driver."""
        if self._async_driver is None:
            self._async_driver = AsyncGraphDatabase.driver(
                self.neo4j_config.uri,
                auth=(
                    self.neo4j_config.username,
                    self.neo4j_config.password,
                )
                if self.neo4j_config.username
                else None,
                encrypted=self.neo4j_config.encrypted,
            )
        return self._async_driver

    @asynccontextmanager
    async def get_session(self):
        """Get an async Neo4j session."""
        async with self.async_driver.session(
            database=self.neo4j_config.database
        ) as session:
            yield session

    async def _ensure_vector_index(self, session) -> None:
        """Ensure the vector index exists."""
        try:
            # Check if index already exists
            result = await session.run(
                "SHOW INDEXES WHERE name = $index_name",
                {"index_name": self.vector_index_config.index_name},
            )
            index_exists = await result.single()

            if not index_exists:
                # Create vector index
                await session.run(
                    """CALL db.index.vector.createNodeIndex(
                        $index_name, $node_label, $vector_property, $dimensions, $metric
                    )""",
                    {
                        "index_name": self.vector_index_config.index_name,
                        "node_label": self.vector_index_config.node_label,
                        "vector_property": self.vector_index_config.vector_property,
                        "dimensions": self.vector_index_config.dimensions,
                        "metric": self.vector_index_config.metric.value,
                    },
                )
        except Exception as e:
            # Index might already exist, continue
            if "already exists" not in str(e).lower():
                raise

    async def add_documents(
        self, documents: list[Document], **kwargs: Any
    ) -> list[str]:
        """Add documents to the vector store."""
        document_ids = []

        async with self.get_session() as session:
            await self._ensure_vector_index(session)

            for doc in documents:
                # Generate embedding if not present
                if doc.embedding is None:
                    embeddings = await self.embeddings.vectorize_documents(
                        [doc.content]
                    )
                    doc.embedding = embeddings[0]

                # Store document with vector
                result = await session.run(
                    """MERGE (d:Document {id: $id})
                    SET d.content = $content,
                        d.metadata = $metadata,
                        d.embedding = $embedding,
                        d.created_at = datetime()
                    RETURN d.id""",
                    {
                        "id": doc.id,
                        "content": doc.content,
                        "metadata": doc.metadata,
                        "embedding": doc.embedding,
                    },
                )

                record = await result.single()
                if record:
                    document_ids.append(record["d.id"])

        return document_ids

    async def add_document_chunks(
        self, chunks: list[Chunk], **kwargs: Any
    ) -> list[str]:
        """Add document chunks to the vector store."""
        chunk_ids = []

        async with self.get_session() as session:
            await self._ensure_vector_index(session)

            for chunk in chunks:
                # Generate embedding if not present
                if chunk.embedding is None:
                    embeddings = await self.embeddings.vectorize_documents([chunk.text])
                    chunk.embedding = embeddings[0]

                # Store chunk with vector
                result = await session.run(
                    """MERGE (c:Chunk {id: $id})
                    SET c.content = $content,
                        c.metadata = $metadata,
                        c.embedding = $embedding,
                        c.start_index = $start_index,
                        c.end_index = $end_index,
                        c.token_count = $token_count,
                        c.context = $context,
                        c.created_at = datetime()
                    RETURN c.id""",
                    {
                        "id": chunk.id,
                        "content": chunk.text,
                        "metadata": chunk.context or {},
                        "embedding": chunk.embedding,
                        "start_index": chunk.start_index,
                        "end_index": chunk.end_index,
                        "token_count": chunk.token_count,
                        "context": chunk.context,
                    },
                )

                record = await result.single()
                if record:
                    chunk_ids.append(record["c.id"])

        return chunk_ids

    async def add_document_text_chunks(
        self, document_texts: list[str], **kwargs: Any
    ) -> list[str]:
        """Add document text chunks to the vector store."""
        # Convert text chunks to Document objects
        documents = [
            Document(
                id=f"chunk_{i}",
                content=text,
                metadata={"chunk_index": i, "type": "text_chunk"},
            )
            for i, text in enumerate(document_texts)
        ]

        return await self.add_documents(documents, **kwargs)

    async def delete_documents(self, document_ids: list[str]) -> bool:
        """Delete documents by their IDs."""
        async with self.get_session() as session:
            result = await session.run(
                "MATCH (d:Document) WHERE d.id IN $ids DETACH DELETE d",
                {"ids": document_ids},
            )
            # Return True if any nodes were deleted
            return bool(await result.single())

    async def search(
        self,
        query: str,
        search_type: SearchType,
        retrieval_query: str | None = None,
        **kwargs: Any,
    ) -> list[SearchResult]:
        """Search for documents using text query."""
        # Generate embedding for the query
        query_embedding = await self.embeddings.vectorize_query(query)

        # Use embedding-based search
        return await self.search_with_embeddings(
            query_embedding, search_type, retrieval_query, **kwargs
        )

    async def search_with_embeddings(
        self,
        query_embedding: list[float],
        search_type: SearchType,
        retrieval_query: str | None = None,
        **kwargs: Any,
    ) -> list[SearchResult]:
        """Search for documents using embedding vector."""
        top_k = kwargs.get("top_k", 10)
        score_threshold = kwargs.get("score_threshold")

        async with self.get_session() as session:
            # Build query with optional filters
            cypher_query = """
                CALL db.index.vector.queryNodes(
                    $index_name, $top_k, $query_vector
                ) YIELD node, score
                WHERE node.embedding IS NOT NULL
            """

            # Add score threshold if specified
            if score_threshold is not None:
                cypher_query += " AND score >= $score_threshold"

            # Add optional filters
            filters = []
            params = {
                "index_name": self.vector_index_config.index_name,
                "top_k": top_k,
                "query_vector": query_embedding,
            }

            if score_threshold is not None:
                params["score_threshold"] = score_threshold

            # Add metadata filters if provided
            metadata_filters = kwargs.get("filters", {})
            for key, value in metadata_filters.items():
                if isinstance(value, list):
                    filters.append(f"node.metadata.{key} IN $filter_{key}")
                    params[f"filter_{key}"] = value
                else:
                    filters.append(f"node.metadata.{key} = $filter_{key}")
                    params[f"filter_{key}"] = value

            if filters:
                cypher_query += " AND " + " AND ".join(filters)

            cypher_query += """
                RETURN node.id AS id,
                       node.content AS content,
                       node.metadata AS metadata,
                       score
                ORDER BY score DESC
                LIMIT $limit
            """

            params["limit"] = top_k

            result = await session.run(cypher_query, params)

            search_results = []
            async for record in result:
                doc = Document(
                    id=record["id"],
                    content=record["content"],
                    metadata=record["metadata"] or {},
                )

                search_results.append(
                    SearchResult(
                        document=doc,
                        score=float(record["score"]),
                        rank=len(search_results) + 1,
                    )
                )

            return search_results

    async def get_document(self, document_id: str) -> Document | None:
        """Retrieve a document by its ID."""
        async with self.get_session() as session:
            result = await session.run(
                """MATCH (d:Document {id: $id})
                RETURN d.id AS id, d.content AS content, d.metadata AS metadata,
                       d.embedding AS embedding, d.created_at AS created_at""",
                {"id": document_id},
            )

            record = await result.single()
            if record:
                return Document(
                    id=record["id"],
                    content=record["content"],
                    metadata=record["metadata"] or {},
                    embedding=record["embedding"],
                    created_at=record["created_at"],
                )

        return None

    async def update_document(self, document: Document) -> bool:
        """Update an existing document."""
        async with self.get_session() as session:
            result = await session.run(
                """MATCH (d:Document {id: $id})
                SET d.content = $content, d.metadata = $metadata,
                    d.embedding = $embedding, d.updated_at = datetime()
                RETURN d.id""",
                {
                    "id": document.id,
                    "content": document.content,
                    "metadata": document.metadata,
                    "embedding": document.embedding,
                },
            )

            record = await result.single()
            return bool(record)

    async def count_documents(self) -> int:
        """Count total documents in the vector store."""
        async with self.get_session() as session:
            result = await session.run(
                "MATCH (d:Document) WHERE d.embedding IS NOT NULL RETURN count(d) AS count"
            )
            record = await result.single()
            return record["count"] if record else 0

    async def get_documents_by_metadata(
        self, metadata_filter: dict[str, Any], limit: int = 100
    ) -> list[Document]:
        """Get documents by metadata filter."""
        async with self.get_session() as session:
            # Build metadata filter query
            filter_conditions = []
            params = {"limit": limit}

            for key, value in metadata_filter.items():
                if isinstance(value, list):
                    filter_conditions.append(f"d.metadata.{key} IN $filter_{key}")
                    params[f"filter_{key}"] = value
                else:
                    filter_conditions.append(f"d.metadata.{key} = $filter_{key}")
                    params[f"filter_{key}"] = value

            filter_str = " AND ".join(filter_conditions)

            cypher_query = f"""
                MATCH (d:Document)
                WHERE {filter_str}
                RETURN d.id AS id, d.content AS content, d.metadata AS metadata,
                       d.embedding AS embedding, d.created_at AS created_at
                LIMIT $limit
            """

            result = await session.run(cypher_query, params)

            documents = []
            async for record in result:
                doc = Document(
                    id=record["id"],
                    content=record["content"],
                    metadata=record["metadata"] or {},
                    embedding=record["embedding"],
                    created_at=record["created_at"],
                )
                documents.append(doc)

            return documents

    async def close(self) -> None:
        """Close the vector store connections."""
        if self._driver:
            self._driver.close()
            self._driver = None

        if self._async_driver:
            await self._async_driver.close()
            self._async_driver = None

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        # Close sync driver if it was created
        if hasattr(self, "_driver") and self._driver:
            self._driver.close()
            self._driver = None

    async def __aenter__(self):
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()


# Factory function for creating Neo4j vector store
def create_neo4j_vector_store(
    config: VectorStoreConfig,
    embeddings: Embeddings,
    neo4j_config: Neo4jConnectionConfig | None = None,
) -> Neo4jVectorStore:
    """Create a Neo4j vector store instance."""
    return Neo4jVectorStore(config, embeddings, neo4j_config)
