"""FAISS-backed vector store implementation."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np

try:
    import faiss  # type: ignore
except ImportError as exc:  # pragma: no cover - handled in test environment
    raise ImportError(
        "faiss-cpu is required to use the FaissVectorStore."
    ) from exc

from ..datatypes.chunk_dataclass import Chunk
from ..datatypes.rag import (
    Document,
    Embeddings,
    SearchResult,
    SearchType,
    VectorStore,
    VectorStoreConfig,
)
from .faiss_config import FaissVectorStoreConfig


class FaissVectorStore(VectorStore):
    """Vector store backed by a FAISS index with JSON metadata persistence."""

    def __init__(self, config: VectorStoreConfig, embeddings: Embeddings):
        if not isinstance(config, FaissVectorStoreConfig):
            config = FaissVectorStoreConfig.model_validate(config.model_dump())

        super().__init__(config, embeddings)
        self.config: FaissVectorStoreConfig = config

        self._index_path = Path(config.index_path) if config.index_path else None
        self._metadata_path = (
            Path(config.metadata_path) if config.metadata_path else None
        )
        self._normalize = (
            config.normalize_vectors
            if config.normalize_vectors is not None
            else (config.distance_metric.lower() == "cosine")
        )
        self._metric = self._resolve_metric(config.distance_metric)

        self._index = self._create_index()
        self._documents: dict[str, Document] = {}
        self._id_to_internal: dict[str, int] = {}
        self._internal_to_id: dict[int, str] = {}
        self._next_internal_id = 1

        self._load_state()

    # ------------------------------------------------------------------
    # Public API implementations
    # ------------------------------------------------------------------
    async def add_documents(
        self, documents: list[Document], **kwargs: Any
    ) -> list[str]:
        document_copies = [doc.model_copy(deep=True) for doc in documents]
        docs_missing_embeddings = [doc for doc in document_copies if doc.embedding is None]

        if docs_missing_embeddings:
            embeddings = await self.embeddings.vectorize_documents(
                [doc.content for doc in docs_missing_embeddings]
            )
            for doc, embedding in zip(docs_missing_embeddings, embeddings, strict=True):
                doc.embedding = embedding

        stored_ids: list[str] = []
        for doc in document_copies:
            vector = self._prepare_vector(doc.embedding)
            doc.embedding = vector.reshape(-1).tolist()

            internal_id = self._id_to_internal.get(doc.id)
            if internal_id is None:
                internal_id = self._generate_internal_id()
            self._id_to_internal[doc.id] = internal_id
            self._internal_to_id[internal_id] = doc.id

            self._documents[doc.id] = doc
            stored_ids.append(doc.id)

        if stored_ids:
            self._rebuild_index()
            self._persist_state()

        return stored_ids

    async def add_document_chunks(
        self, chunks: list[Chunk], **kwargs: Any
    ) -> list[str]:
        documents = [self._chunk_to_document(chunk) for chunk in chunks]
        return await self.add_documents(documents, **kwargs)

    async def add_document_text_chunks(
        self, document_texts: list[str], **kwargs: Any
    ) -> list[str]:
        documents = [
            Document(
                content=text,
                metadata={"source": "text_chunk", "chunk_index": index},
            )
            for index, text in enumerate(document_texts)
        ]
        return await self.add_documents(documents, **kwargs)

    async def delete_documents(self, document_ids: list[str]) -> bool:
        removed = False
        for doc_id in document_ids:
            if doc_id in self._documents:
                internal_id = self._id_to_internal.pop(doc_id, None)
                if internal_id is not None:
                    self._internal_to_id.pop(internal_id, None)
                self._documents.pop(doc_id, None)
                removed = True

        if removed:
            self._rebuild_index()
            self._persist_state()

        return removed

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
        if self._index.ntotal == 0:
            return []

        vector = self._prepare_vector(query_embedding)
        top_k = kwargs.get("top_k", 10)
        score_threshold = kwargs.get("score_threshold")
        filters: dict[str, Any] = kwargs.get("filters", {}) or {}

        distances, indices = self._index.search(vector, top_k)
        scores = distances[0]
        doc_ids = [self._internal_to_id.get(int(idx), "") for idx in indices[0]]

        results: list[SearchResult] = []
        rank = 1
        for score, doc_id in zip(scores, doc_ids, strict=False):
            if not doc_id:
                continue

            document = self._documents.get(doc_id)
            if document is None:
                continue

            if filters and not self._matches_filters(document.metadata, filters):
                continue

            similarity = self._score_from_distance(float(score))

            if score_threshold is not None and similarity < float(score_threshold):
                continue

            results.append(
                SearchResult(
                    document=document.model_copy(deep=True),
                    score=similarity,
                    rank=rank,
                )
            )
            rank += 1

        return results

    async def get_document(self, document_id: str) -> Document | None:
        document = self._documents.get(document_id)
        if document is None:
            return None
        return document.model_copy(deep=True)

    async def update_document(self, document: Document) -> bool:
        if document.id not in self._documents:
            return False
        await self.add_documents([document])
        return True

    async def close(self) -> None:
        self._persist_state()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._persist_state()

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _create_index(self):
        if self._metric == "ip":
            base_index = faiss.IndexFlatIP(self.config.embedding_dimension)
        else:
            base_index = faiss.IndexFlatL2(self.config.embedding_dimension)
        return faiss.IndexIDMap(base_index)

    def _prepare_vector(self, embedding: Any) -> np.ndarray:
        array = np.asarray(embedding, dtype=np.float32)
        if array.ndim == 1:
            array = array.reshape(1, -1)
        if array.ndim != 2:
            raise ValueError("Embeddings must be 1D or 2D arrays")
        if array.shape[1] != self.config.embedding_dimension:
            raise ValueError(
                "Embedding dimension mismatch: expected "
                f"{self.config.embedding_dimension}, got {array.shape[1]}"
            )
        if self._normalize:
            faiss.normalize_L2(array)
        return array

    def _generate_internal_id(self) -> int:
        internal_id = self._next_internal_id
        self._next_internal_id += 1
        return internal_id

    def _rebuild_index(self) -> None:
        self._index = self._create_index()
        if not self._documents:
            return

        vectors: list[np.ndarray] = []
        ids: list[int] = []
        for doc_id, document in self._documents.items():
            internal_id = self._id_to_internal.get(doc_id)
            if internal_id is None:
                continue
            vector = np.asarray(document.embedding, dtype=np.float32)
            if vector.ndim == 1:
                vector = vector.reshape(1, -1)
            if self._normalize:
                faiss.normalize_L2(vector)
            vectors.append(vector)
            ids.append(internal_id)

        if vectors:
            stacked = np.vstack(vectors)
            id_array = np.asarray(ids, dtype=np.int64)
            self._index.add_with_ids(stacked, id_array)

    def _persist_state(self) -> None:
        if self._index_path:
            self._index_path.parent.mkdir(parents=True, exist_ok=True)
            faiss.write_index(self._index, str(self._index_path))

        if self._metadata_path:
            self._metadata_path.parent.mkdir(parents=True, exist_ok=True)
            payload = {
                "id_to_internal": self._id_to_internal,
                "next_internal_id": self._next_internal_id,
                "documents": {
                    doc_id: document.model_dump(mode="json")
                    for doc_id, document in self._documents.items()
                },
            }
            self._metadata_path.write_text(
                json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
            )

    def _load_state(self) -> None:
        if self._metadata_path and self._metadata_path.exists():
            data = json.loads(self._metadata_path.read_text(encoding="utf-8"))
            id_map = data.get("id_to_internal", {})
            self._id_to_internal = {k: int(v) for k, v in id_map.items()}
            self._internal_to_id = {v: k for k, v in self._id_to_internal.items()}
            self._next_internal_id = int(data.get("next_internal_id", 1))

            documents = data.get("documents", {})
            for doc_id, payload in documents.items():
                document = Document.model_validate(payload)
                self._documents[doc_id] = document

        if self._index_path and self._index_path.exists():
            self._index = faiss.read_index(str(self._index_path))
            if not isinstance(self._index, faiss.IndexIDMap):
                self._rebuild_index()
        else:
            self._rebuild_index()

    def _resolve_metric(self, metric: str) -> str:
        metric_lower = metric.lower()
        if metric_lower in {"ip", "inner_product", "cosine"}:
            return "ip"
        return "l2"

    def _score_from_distance(self, distance: float) -> float:
        if self._metric == "ip":
            return distance
        return 1.0 / (1.0 + distance)

    def _chunk_to_document(self, chunk: Chunk) -> Document:
        metadata = {
            "source": "chunk",
            "chunk_id": chunk.id,
            "chunk_start_index": chunk.start_index,
            "chunk_end_index": chunk.end_index,
            "chunk_token_count": chunk.token_count,
        }
        if chunk.context is not None:
            metadata["chunk_context"] = chunk.context

        embedding = None
        if chunk.embedding is not None:
            embedding = (
                chunk.embedding.tolist()
                if hasattr(chunk.embedding, "tolist")
                else chunk.embedding
            )

        return Document(
            id=chunk.id,
            content=chunk.text,
            metadata=metadata,
            embedding=embedding,
        )

    @staticmethod
    def _matches_filters(
        metadata: dict[str, Any], filters: dict[str, Any]
    ) -> bool:
        for key, value in filters.items():
            if isinstance(value, list):
                if metadata.get(key) not in value:
                    return False
            else:
                if metadata.get(key) != value:
                    return False
        return True


__all__ = ["FaissVectorStore"]

