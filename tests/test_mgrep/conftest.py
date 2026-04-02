from __future__ import annotations

import re
from collections.abc import Callable
from typing import Any

import numpy as np
import pytest

from DeepResearch.src.datatypes.mgrep import MgrepConfig
from DeepResearch.src.datatypes.rag import (
    Document,
    EmbeddingModelType,
    EmbeddingsConfig,
    SearchResult,
    SearchType,
)


class KeywordEmbeddings:
    """Deterministic test embeddings without external model downloads."""

    def __init__(self):
        self.vocabulary = [
            "semantic",
            "parser",
            "workflow",
            "search",
            "markdown",
            "config",
            "engine",
            "vector",
        ]

    def _embed(self, text: str) -> list[float]:
        normalized = re.sub(r"[^a-z0-9]+", " ", text.lower())
        tokens = normalized.split()
        vector = np.array(
            [float(tokens.count(term)) for term in self.vocabulary], dtype=np.float32
        )
        if not vector.any():
            vector[0] = 1.0
        norm = np.linalg.norm(vector)
        if norm:
            vector = vector / norm
        return vector.tolist()

    async def vectorize_documents(
        self, document_chunks: list[str]
    ) -> list[list[float]]:
        return [self._embed(text) for text in document_chunks]

    async def vectorize_query(self, text: str) -> list[float]:
        return self._embed(text)


class InMemoryVectorStore:
    """Small deterministic vector store for higher-level mgrep tests."""

    def __init__(self, embeddings: KeywordEmbeddings):
        self.embeddings = embeddings
        self.documents: dict[str, Document] = {}

    async def add_documents(
        self, documents: list[Document], **kwargs: Any
    ) -> list[str]:
        embeddings = await self.embeddings.vectorize_documents(
            [document.content for document in documents]
        )
        for document, embedding in zip(documents, embeddings, strict=True):
            document.embedding = embedding
            self.documents[document.id] = document
        return [document.id for document in documents]

    async def delete_documents(self, document_ids: list[str]) -> bool:
        removed = False
        for document_id in document_ids:
            removed = self.documents.pop(document_id, None) is not None or removed
        return removed

    async def search(
        self,
        query: str,
        search_type: SearchType,
        retrieval_query: str | None = None,
        **kwargs: Any,
    ) -> list[SearchResult]:
        query_embedding = np.array(
            await self.embeddings.vectorize_query(query), dtype=np.float32
        )
        top_k = int(kwargs.get("top_k", 10))
        scored: list[tuple[float, Document]] = []

        for document in self.documents.values():
            document_embedding = np.array(document.embedding, dtype=np.float32)
            score = float(np.dot(query_embedding, document_embedding))
            scored.append((score, document))

        scored.sort(key=lambda item: item[0], reverse=True)
        return [
            SearchResult(document=document, score=score, rank=index + 1)
            for index, (score, document) in enumerate(scored[:top_k])
        ]


@pytest.fixture
def keyword_embeddings() -> KeywordEmbeddings:
    return KeywordEmbeddings()


@pytest.fixture
def mgrep_config(keyword_embeddings: KeywordEmbeddings) -> MgrepConfig:
    return MgrepConfig(
        distance_metric="cosine",
        embeddings=EmbeddingsConfig(
            model_type=EmbeddingModelType.SENTENCE_TRANSFORMERS,
            model_name="test-keyword-embeddings",
            num_dimensions=len(keyword_embeddings.vocabulary),
            batch_size=8,
            device="cpu",
        ),
    )


@pytest.fixture
def in_memory_vector_store_factory(
    keyword_embeddings: KeywordEmbeddings,
) -> Callable[[], InMemoryVectorStore]:
    return lambda: InMemoryVectorStore(keyword_embeddings)
