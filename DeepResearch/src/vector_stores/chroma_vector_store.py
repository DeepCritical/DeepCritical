from __future__ import annotations

import os
from typing import Any

import chromadb  # type: ignore[import-not-found]

from ..datatypes.rag import (
    Chunk,
    Document,
    Embeddings,
    SearchResult,
    SearchType,
    VectorStore,
    VectorStoreConfig,
)
from .chroma_config import ChromaVectorStoreConfig


class ChromaVectorStore(VectorStore):
    """Chroma-backed vector store with async-compatible methods."""

    def __init__(self, config: VectorStoreConfig, embeddings: Embeddings):
        super().__init__(config, embeddings)
        if not isinstance(config, ChromaVectorStoreConfig):
            raise TypeError("config must be an instance of ChromaVectorStoreConfig")

        self._client = self._create_client(config)
        self._collection = self._get_or_create_collection(config)

    def _init_client(
        self,
        client_factory: Any,
        config: ChromaVectorStoreConfig,
        **kwargs: Any,
    ):
        client_kwargs = dict(kwargs)
        if config.tenant:
            client_kwargs["tenant"] = config.tenant
        if config.database_name:
            client_kwargs["database"] = config.database_name
        try:
            return client_factory(**client_kwargs)
        except TypeError:
            # Older chromadb versions may not support tenant/database kwargs.
            return client_factory(**kwargs)

    def _create_client(self, config: ChromaVectorStoreConfig):
        # Local persistent mode via explicit persist_directory.
        if config.persist_directory:
            os.makedirs(config.persist_directory, exist_ok=True)
            return self._init_client(
                chromadb.PersistentClient,
                config,
                path=config.persist_directory,
            )

        # Treat file:// connection strings as local persistence paths.
        if config.connection_string and config.connection_string.startswith("file://"):
            persist_directory = config.connection_string.removeprefix("file://")
            os.makedirs(persist_directory, exist_ok=True)
            return self._init_client(
                chromadb.PersistentClient,
                config,
                path=persist_directory,
            )

        # Remote/server mode if host is explicitly configured.
        if config.host:
            return self._init_client(
                chromadb.HttpClient,
                config,
                host=config.host,
                port=config.port or 8000,
            )

        # Fallback to ephemeral in-memory client.
        return self._init_client(chromadb.EphemeralClient, config)

    def _get_or_create_collection(self, config: ChromaVectorStoreConfig):
        collection_name = config.collection_name or "research_docs"
        metadata = {}
        if config.distance_metric:
            # Chroma understands hnsw:space = cosine/l2/ip.
            metric_map = {
                "cosine": "cosine",
                "euclidean": "l2",
                "l2": "l2",
                "ip": "ip",
                "dot": "ip",
            }
            metadata["hnsw:space"] = metric_map.get(
                config.distance_metric.lower(), "cosine"
            )

        return self._client.get_or_create_collection(
            name=collection_name,
            metadata=metadata or None,
        )

    @staticmethod
    def _score_from_distance(distance: float, metric: str | None) -> float:
        metric_normalized = (metric or "cosine").lower()
        if metric_normalized in {"cosine", "ip", "dot"}:
            # Distance 0 is best for cosine in Chroma.
            return 1.0 - float(distance)
        # For L2-like distances, convert to bounded similarity.
        return 1.0 / (1.0 + float(distance))

    async def add_documents(
        self, documents: list[Document], **kwargs: Any
    ) -> list[str]:
        if not documents:
            return []

        ids = [doc.id for doc in documents]
        contents = [doc.content for doc in documents]
        metadatas = [doc.metadata or {} for doc in documents]

        embeddings_payload: list[list[float]] = []
        missing_indexes: list[int] = []

        for idx, doc in enumerate(documents):
            if doc.embedding is None:
                missing_indexes.append(idx)
                embeddings_payload.append([])
            else:
                embeddings_payload.append(list(doc.embedding))

        if missing_indexes:
            computed = await self.embeddings.vectorize_documents(
                [documents[idx].content for idx in missing_indexes]
            )
            for position, doc_index in enumerate(missing_indexes):
                vector = list(computed[position])
                documents[doc_index].embedding = vector
                embeddings_payload[doc_index] = vector

        self._collection.upsert(
            ids=ids,
            documents=contents,
            embeddings=embeddings_payload,
            metadatas=metadatas,
        )
        return ids

    async def add_document_chunks(
        self, chunks: list[Chunk], **kwargs: Any
    ) -> list[str]:
        documents = [
            Document(
                id=chunk.id,
                content=chunk.text,
                metadata={
                    "start_index": chunk.start_index,
                    "end_index": chunk.end_index,
                    "token_count": chunk.token_count,
                    "context": chunk.context,
                },
                embedding=chunk.embedding,
            )
            for chunk in chunks
        ]
        return await self.add_documents(documents, **kwargs)

    async def add_document_text_chunks(
        self, document_texts: list[str], **kwargs: Any
    ) -> list[str]:
        documents = [Document(content=text) for text in document_texts]
        return await self.add_documents(documents, **kwargs)

    async def delete_documents(self, document_ids: list[str]) -> bool:
        if not document_ids:
            return False
        self._collection.delete(ids=document_ids)
        return True

    async def search(
        self,
        query: str,
        search_type: SearchType,
        retrieval_query: str | None = None,
        **kwargs: Any,
    ) -> list[SearchResult]:
        query_embedding = await self.embeddings.vectorize_query(query)
        return await self.search_with_embeddings(
            query_embedding,
            search_type=search_type,
            retrieval_query=retrieval_query,
            **kwargs,
        )

    async def search_with_embeddings(
        self,
        query_embedding: list[float],
        search_type: SearchType,
        retrieval_query: str | None = None,
        **kwargs: Any,
    ) -> list[SearchResult]:
        top_k = int(kwargs.get("top_k", 10))
        filters = kwargs.get("filters")

        result = self._collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
            where=filters,
            include=["documents", "metadatas", "distances"],
        )

        ids = (result.get("ids") or [[]])[0]
        docs = (result.get("documents") or [[]])[0]
        metadatas = (result.get("metadatas") or [[]])[0]
        distances = (result.get("distances") or [[]])[0]

        search_results: list[SearchResult] = []
        threshold = kwargs.get("score_threshold")
        metric = getattr(self.config, "distance_metric", "cosine")

        for index, doc_id in enumerate(ids):
            doc_obj = Document(
                id=doc_id,
                content=docs[index] if index < len(docs) else "",
                metadata=metadatas[index] if index < len(metadatas) else {},
            )
            distance = distances[index] if index < len(distances) else 1.0
            score = self._score_from_distance(distance, metric)

            if threshold is not None and score < float(threshold):
                continue

            search_results.append(
                SearchResult(
                    document=doc_obj, score=score, rank=len(search_results) + 1
                )
            )

        return search_results

    async def get_document(self, document_id: str) -> Document | None:
        result = self._collection.get(
            ids=[document_id],
            include=["documents", "metadatas", "embeddings"],
        )
        ids = result.get("ids", [])
        if not ids:
            return None

        documents = result.get("documents", [])
        metadatas = result.get("metadatas", [])
        embeddings = result.get("embeddings", [])

        return Document(
            id=ids[0],
            content=documents[0] if documents else "",
            metadata=metadatas[0] if metadatas else {},
            embedding=embeddings[0] if embeddings else None,
        )

    async def update_document(self, document: Document) -> bool:
        existing = await self.get_document(document.id)
        if existing is None:
            return False

        await self.add_documents([document])
        return True


def create_chroma_vector_store(
    config: ChromaVectorStoreConfig, embeddings: Embeddings
) -> ChromaVectorStore:
    """Factory helper to construct a Chroma vector store."""
    return ChromaVectorStore(config, embeddings)
