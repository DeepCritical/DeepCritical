from __future__ import annotations

import hashlib
import os
import pickle
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

        self.index: faiss.IndexIDMap | None = None
        self.documents: dict[str, Document] = {}
        # Map from stable_hash -> doc_id
        self.id_map: dict[int, str] = {}
        self._load()

    def _load(self):
        """Loads the index and document data from disk if they exist."""
        if os.path.exists(self.index_path):
            self.index = faiss.read_index(self.index_path)  # type: ignore
        if os.path.exists(self.data_path):
            with open(self.data_path, "rb") as f:
                self.documents = pickle.load(f)
                # Rebuild id_map
                self.id_map = {
                    _stable_hash(doc_id): doc_id for doc_id in self.documents
                }

    def _save(self):
        """Saves the index and document data to disk."""
        if self.index:
            faiss.write_index(self.index, self.index_path)  # type: ignore
        with open(self.data_path, "wb") as f:
            pickle.dump(self.documents, f)

    async def add_documents(
        self, documents: list[Document], **kwargs: Any
    ) -> list[str]:
        """
        Adds documents to the vector store.
        """
        if not documents:
            return []

        texts = [doc.content for doc in documents]
        embeddings = await self.embeddings.vectorize_documents(texts)

        doc_ids = [doc.id for doc in documents]
        # Use stable hash
        doc_id_vectors = np.array(
            [_stable_hash(doc_id) for doc_id in doc_ids], dtype=np.int64
        )

        for i, doc in enumerate(documents):
            doc.embedding = embeddings[i]
            self.documents[doc.id] = doc
            self.id_map[_stable_hash(doc.id)] = doc.id

        new_vectors = np.array(embeddings, dtype=np.float32)
        if self.index is None:
            dimension = new_vectors.shape[1]
            base_index = faiss.IndexFlatL2(dimension)  # type: ignore
            self.index = faiss.IndexIDMap(base_index)  # type: ignore

        self.index.add_with_ids(new_vectors, doc_id_vectors)  # type: ignore

        self._save()
        return doc_ids

    async def add_document_chunks(
        self, chunks: list[Chunk], **kwargs: Any
    ) -> list[str]:
        """Not yet implemented."""
        raise NotImplementedError

    async def add_document_text_chunks(
        self, document_texts: list[str], **kwargs: Any
    ) -> list[str]:
        """Not yet implemented."""
        raise NotImplementedError

    async def delete_documents(self, document_ids: list[str]) -> bool:
        """
        Deletes documents from the vector store.
        """
        if not document_ids or self.index is None:
            return False

        ids_to_remove = np.array(
            [_stable_hash(doc_id) for doc_id in document_ids], dtype=np.int64
        )
        self.index.remove_ids(ids_to_remove)  # type: ignore

        for doc_id in document_ids:
            if doc_id in self.documents:
                del self.documents[doc_id]
            hashed_id = _stable_hash(doc_id)
            if hashed_id in self.id_map:
                del self.id_map[hashed_id]

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
        query_vector = np.array([query_embedding], dtype=np.float32)

        distances, indices = self.index.search(query_vector, top_k)  # type: ignore

        results = []
        for i in range(len(indices[0])):
            hashed_id = indices[0][i]
            if hashed_id == -1:  # FAISS returns -1 for no match
                continue

            found_doc_id = self.id_map.get(hashed_id)

            if found_doc_id and found_doc_id in self.documents:
                document = self.documents[found_doc_id]
                results.append(
                    SearchResult(
                        document=document,
                        score=float(distances[0][i]),
                        rank=i + 1,
                    )
                )

        return results
