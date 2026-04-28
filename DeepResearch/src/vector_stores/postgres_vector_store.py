import json
import re
from typing import Any

import asyncpg  # type: ignore[import-not-found]

from ..datatypes.chunk_dataclass import Chunk
from ..datatypes.rag import (
    Document,
    Embeddings,
    SearchResult,
    SearchType,
    VectorStore,
    VectorStoreConfig,
)
from .postgres_config import PostgresVectorStoreConfig


class PostgresVectorStore(VectorStore):
    """Postgres-backed vector store (using pgvector) with async-compatible methods."""

    def __init__(self, config: VectorStoreConfig, embeddings: Embeddings):
        super().__init__(config, embeddings)
        if not isinstance(config, PostgresVectorStoreConfig):
            raise TypeError("config must be an instance of PostgresVectorStoreConfig")

        self.config = config
        self._pool = None

    @staticmethod
    def _score_from_distance(distance: float, metric: str | None) -> float:
        metric_normalized = (metric or "cosine").lower()
        if metric_normalized in {"cosine", "ip", "dot"}:
            return 1.0 - float(distance)
        return 1.0 / (1.0 + float(distance))

    async def _get_pool(self):
        if self._pool is None:
            if not self.config.connection_string:
                raise ValueError(
                    "connection_string is required for PostgresVectorStore"
                )

            self._pool = await asyncpg.create_pool(dsn=self.config.connection_string)
            await self._initialize_schema()
        return self._pool

    async def _initialize_schema(self):
        pool = await self._get_pool()
        async with pool.acquire() as conn:
            await conn.execute("CREATE EXTENSION IF NOT EXISTS vector;")
            await conn.execute(f"""
                CREATE TABLE IF NOT EXISTS {self.config.table_name} (
                    id TEXT PRIMARY KEY,
                    content TEXT NOT NULL,
                    metadata JSONB,
                    embedding vector({self.config.embedding_dimension})
                );
            """)

    async def add_documents(
        self, documents: list[Document], **kwargs: Any
    ) -> list[str]:
        if not documents:
            return []

        contents = [doc.content for doc in documents]
        vectors = await self.embeddings.vectorize_documents(contents)

        pool = await self._get_pool()

        # We need to format the vectors as strings for pgvector, e.g. '[1,2,3]'
        records = []
        for doc, vector in zip(documents, vectors, strict=True):
            metadata_json = json.dumps(doc.metadata) if doc.metadata else "{}"
            vector_str = "[" + ",".join(str(v) for v in vector) + "]"
            records.append((doc.id, doc.content, metadata_json, vector_str))

        async with pool.acquire() as conn:
            query = f"""
                INSERT INTO {self.config.table_name} (id, content, metadata, embedding)
                VALUES ($1, $2, $3::jsonb, $4::vector)
                ON CONFLICT (id) DO UPDATE 
                SET content = EXCLUDED.content, 
                    metadata = EXCLUDED.metadata, 
                    embedding = EXCLUDED.embedding
            """
            await conn.executemany(query, records)

        return [doc.id for doc in documents]

    async def add_document_chunks(
        self, chunks: list[Chunk], **kwargs: Any
    ) -> list[str]:
        docs = [
            Document(
                id=chunk.id,
                content=chunk.text,
                metadata={"chunk_index": chunk.start_index},
            )
            for chunk in chunks
        ]
        return await self.add_documents(docs, **kwargs)

    async def add_document_text_chunks(
        self, document_texts: list[str], **kwargs: Any
    ) -> list[str]:
        from ..datatypes.chunk_dataclass import generate_id

        docs = [
            Document(id=generate_id("chunk"), content=text) for text in document_texts
        ]
        return await self.add_documents(docs, **kwargs)

    async def delete_documents(self, document_ids: list[str]) -> bool:
        if not document_ids:
            return True

        pool = await self._get_pool()
        async with pool.acquire() as conn:
            query = f"DELETE FROM {self.config.table_name} WHERE id = ANY($1)"
            result = await conn.execute(query, document_ids)
            # Returns something like 'DELETE <count>'
            return result.startswith("DELETE")

    async def search(
        self,
        query: str,
        search_type: SearchType,
        retrieval_query: str | None = None,
        **kwargs: Any,
    ) -> list[SearchResult]:
        query_embedding = await self.embeddings.vectorize_query(query)
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
        pool = await self._get_pool()

        top_k = kwargs.get("top_k", 5)
        filters = kwargs.get("filters", {})

        # Format the embedding vector
        vector_str = "[" + ",".join(str(v) for v in query_embedding) + "]"

        where_clauses = []
        params = [vector_str, top_k]
        param_idx = 3

        # Build JSONB filter queries (exact match)
        for key, value in filters.items():
            if not re.match(r"^[a-zA-Z_][a-zA-Z0-9_]*$", key):
                raise ValueError(f"Invalid filter key: {key}")
            where_clauses.append(f"metadata->>'{key}' = ${param_idx}")
            params.append(str(value))
            param_idx += 1

        where_sql = ""
        if where_clauses:
            where_sql = "WHERE " + " AND ".join(where_clauses)

        # Select using <-> operator for L2 distance, or <=> for cosine distance
        operator = "<=>" if self.config.distance_metric == "cosine" else "<->"

        query = f"""
            SELECT id, content, metadata::text as metadata, embedding {operator} $1::vector AS distance
            FROM {self.config.table_name}
            {where_sql}
            ORDER BY distance ASC
            LIMIT $2
        """

        results = []
        async with pool.acquire() as conn:
            rows = await conn.fetch(query, *params)

            for rank, row in enumerate(rows, 1):
                metadata = json.loads(row["metadata"]) if row["metadata"] else {}
                distance = float(row["distance"])
                score = self._score_from_distance(distance, self.config.distance_metric)
                doc = Document(id=row["id"], content=row["content"], metadata=metadata)
                results.append(SearchResult(document=doc, score=score, rank=rank))

        return results

    async def get_document(self, document_id: str) -> Document | None:
        pool = await self._get_pool()
        async with pool.acquire() as conn:
            query = f"SELECT id, content, metadata::text as metadata FROM {self.config.table_name} WHERE id = $1"
            row = await conn.fetchrow(query, document_id)
            if not row:
                return None

            metadata = json.loads(row["metadata"]) if row["metadata"] else {}
            return Document(id=row["id"], content=row["content"], metadata=metadata)

    async def update_document(self, document: Document) -> bool:
        # Since add_documents uses ON CONFLICT DO UPDATE, we can just use that
        added_ids = await self.add_documents([document])
        return len(added_ids) > 0
