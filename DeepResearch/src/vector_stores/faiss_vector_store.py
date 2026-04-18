from __future__ import annotations

import hashlib
import os
import pickle
from pathlib import Path
from typing import Any

import faiss  # type: ignore
import numpy as np

from ..datatypes.rag import (
    Chunk,
    Document,
    Embeddings,
    SearchResult,
    SearchType,
    VectorStore,
    VectorStoreConfig,
)
from .faiss_config import FAISSVectorStoreConfig


def _stable_hash(doc_id: str) -> int:
    """Generate a stable 64-bit signed integer hash for a document ID."""
    # SHA-256 -> hex -> int
    hex_hash = hashlib.sha256(doc_id.encode("utf-8")).hexdigest()
    # Take first 16 hex chars (64 bits)
    int_hash = int(hex_hash[:16], 16)
    # Mask to 63 bits to ensure it fits in signed 64-bit integer (positive)
    # FAISS IDMap expects int64.
    return int_hash & 0x7FFFFFFFFFFFFFFF


class FAISSVectorStore(VectorStore):
    """A standalone vector store using FAISS for indexing and search."""

    def __init__(
        self,
        config: VectorStoreConfig,
        embeddings: Embeddings,
    ):
        """
        Initializes the FAISS vector store.
        """
        super().__init__(config, embeddings)
        if not isinstance(config, FAISSVectorStoreConfig):
            raise TypeError("config must be an instance of FAISSVectorStoreConfig")

        self.index_path = config.index_path
        self.data_path = config.data_path

        self.index: Any | None = None
        self.documents: dict[str, Document] = {}
        self.doc_ids: list[str] = []
        # Map from stable_hash -> doc_id
        self.id_map: dict[int, str] = {}
        self._load()

    def _uses_cosine_metric(self) -> bool:
        return getattr(self.config, "distance_metric", "cosine").lower() == "cosine"

    def _normalize_vectors(self, vectors: np.ndarray) -> np.ndarray:
        vectors = np.ascontiguousarray(vectors, dtype=np.float32)
        norms = np.linalg.norm(vectors, axis=1, keepdims=True).astype(np.float32)
        norms = np.where(norms == 0, 1.0, norms)
        normalized = vectors / norms
        return np.ascontiguousarray(normalized, dtype=np.float32)

    def _build_base_index(self, dimension: int) -> Any:
        if self._uses_cosine_metric():
            return faiss.IndexFlatIP(dimension)  # type: ignore
        return faiss.IndexFlatL2(dimension)  # type: ignore

    def _to_user_score(self, raw_score: float) -> float:
        if self._uses_cosine_metric():
            return raw_score
        return 1.0 / (1.0 + raw_score)

    def _load(self):
        """Loads the index and document data from disk if they exist."""
        if os.path.exists(self.data_path):
            with open(self.data_path, "rb") as f:
                payload = pickle.load(f)
            if isinstance(payload, dict) and "documents" in payload:
                self.documents = payload["documents"]
                self.doc_ids = payload.get("doc_ids", list(self.documents))
            else:
                self.documents = payload
                self.doc_ids = list(self.documents)
            self.id_map = {_stable_hash(doc_id): doc_id for doc_id in self.doc_ids}
            self._rebuild_index_from_documents()

    def _save(self):
        """Saves the index and document data to disk."""
        index_dir = os.path.dirname(self.index_path)
        data_dir = os.path.dirname(self.data_path)
        if index_dir:
            os.makedirs(index_dir, exist_ok=True)
        if data_dir:
            os.makedirs(data_dir, exist_ok=True)
        if self.index:
            faiss.write_index(self.index, self.index_path)  # type: ignore
        with open(self.data_path, "wb") as f:
            pickle.dump(
                {"documents": self.documents, "doc_ids": self.doc_ids},
                f,
            )

    def _rebuild_index_from_documents(self) -> None:
        """Rebuild the FAISS index from the stored document embeddings."""
        if not self.doc_ids:
            self.index = None
            return

        ordered_embeddings = [
            self.documents[doc_id].embedding
            for doc_id in self.doc_ids
            if doc_id in self.documents
        ]
        if not ordered_embeddings:
            self.index = None
            return

        vectors = np.ascontiguousarray(np.array(ordered_embeddings, dtype=np.float32))
        if self._uses_cosine_metric():
            vectors = self._normalize_vectors(vectors)

        dimension = vectors.shape[1]
        self.index = self._build_base_index(dimension)
        self.index.add(vectors)  # type: ignore

    def clear(self) -> None:
        """Reset in-memory state and remove any persisted FAISS artifacts."""
        self.index = None
        self.documents = {}
        self.doc_ids = []
        self.id_map = {}
        for path in (self.index_path, self.data_path):
            if path and os.path.exists(path):
                Path(path).unlink()

    async def add_documents(
        self, documents: list[Document], **kwargs: Any
    ) -> list[str]:
        """
        Adds documents to the vector store.
        """
        if not documents:
            return []

        existing_ids = [doc.id for doc in documents if doc.id in self.documents]
        if existing_ids:
            await self.delete_documents(existing_ids)

        texts = [doc.content for doc in documents]
        embeddings = await self.embeddings.vectorize_documents(texts)

        doc_ids = [doc.id for doc in documents]

        for i, doc in enumerate(documents):
            doc.embedding = embeddings[i]
            self.documents[doc.id] = doc
            self.id_map[_stable_hash(doc.id)] = doc.id
            self.doc_ids.append(doc.id)

        new_vectors = np.ascontiguousarray(np.array(embeddings, dtype=np.float32))
        if self._uses_cosine_metric():
            new_vectors = self._normalize_vectors(new_vectors)
        if self.index is None:
            dimension = new_vectors.shape[1]
            self.index = self._build_base_index(dimension)

        self.index.add(new_vectors)  # type: ignore

        self._save()
        return doc_ids

    async def add_document_chunks(
        self, chunks: list[Chunk], **kwargs: Any
    ) -> list[str]:
        """Adds chunk dataclasses by converting them to vector-store documents."""
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
            )
            for chunk in chunks
        ]
        return await self.add_documents(documents, **kwargs)

    async def add_document_text_chunks(
        self, document_texts: list[str], **kwargs: Any
    ) -> list[str]:
        """Adds raw text chunks by wrapping them in documents."""
        documents = [Document(content=text) for text in document_texts]
        return await self.add_documents(documents, **kwargs)

    async def delete_documents(self, document_ids: list[str]) -> bool:
        """
        Deletes documents from the vector store.
        """
        if not document_ids or not self.documents:
            return False

        removed_ids = set(document_ids)
        if not removed_ids.intersection(self.documents):
            return False

        self.doc_ids = [doc_id for doc_id in self.doc_ids if doc_id not in removed_ids]
        self.documents = {
            doc_id: self.documents[doc_id]
            for doc_id in self.doc_ids
            if doc_id in self.documents
        }

        for doc_id in document_ids:
            hashed_id = _stable_hash(doc_id)
            if hashed_id in self.id_map:
                del self.id_map[hashed_id]

        self._rebuild_index_from_documents()
        self._save()
        return True

    async def get_document(self, document_id: str) -> Document | None:
        """
        Retrieves a document by its ID.
        """
        return self.documents.get(document_id)

    async def update_document(self, document: Document) -> bool:
        """
        Updates an existing document.
        """
        if document.id not in self.documents:
            return False

        # For simplicity, we'll re-add the document.
        # This is not the most efficient way, but it's safe.
        await self.delete_documents([document.id])
        await self.add_documents([document])
        return True

    async def search(
        self,
        query: str,
        search_type: SearchType,
        retrieval_query: str | None = None,
        **kwargs: Any,
    ) -> list[SearchResult]:
        """
        Searches the vector store for a given query.
        """
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
        """
        Searches the vector store for a given query.
        """
        if self.index is None:
            return []

        top_k = kwargs.get("top_k", 10)
        top_k = min(int(top_k), int(self.index.ntotal))
        if top_k <= 0:
            return []
        query_vector = np.ascontiguousarray(
            np.array([query_embedding], dtype=np.float32)
        )
        if self._uses_cosine_metric():
            query_vector = self._normalize_vectors(query_vector)

        distances, indices = self.index.search(query_vector, top_k)  # type: ignore

        results = []
        for i in range(len(indices[0])):
            doc_index = int(indices[0][i])
            if doc_index == -1:  # FAISS returns -1 for no match
                continue

            if doc_index >= len(self.doc_ids):
                continue

            found_doc_id = self.doc_ids[doc_index]

            if found_doc_id and found_doc_id in self.documents:
                document = self.documents[found_doc_id]
                results.append(
                    SearchResult(
                        document=document,
                        score=float(self._to_user_score(float(distances[0][i]))),
                        rank=i + 1,
                    )
                )

        return results
