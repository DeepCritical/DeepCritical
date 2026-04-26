from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from DeepResearch.src.datatypes.chunk_dataclass import Chunk
from DeepResearch.src.datatypes.rag import Document, SearchType, VectorStoreType
from DeepResearch.src.vector_stores.chroma_config import ChromaVectorStoreConfig
from DeepResearch.src.vector_stores.chroma_vector_store import ChromaVectorStore
from DeepResearch.src.vector_stores import create_vector_store


class _FakeCollection:
    def __init__(self):
        self.rows: dict[str, dict] = {}

    def upsert(self, ids, documents, embeddings, metadatas):
        for i, row_id in enumerate(ids):
            self.rows[row_id] = {
                "id": row_id,
                "document": documents[i],
                "embedding": embeddings[i],
                "metadata": metadatas[i],
            }

    def delete(self, ids):
        for row_id in ids:
            self.rows.pop(row_id, None)

    def get(self, ids, include):
        matches = [self.rows[row_id] for row_id in ids if row_id in self.rows]
        if not matches:
            return {"ids": [], "documents": [], "metadatas": [], "embeddings": []}
        return {
            "ids": [row["id"] for row in matches],
            "documents": [row["document"] for row in matches],
            "metadatas": [row["metadata"] for row in matches],
            "embeddings": [row["embedding"] for row in matches],
        }

    def query(self, query_embeddings, n_results, where=None, include=None):
        query_embedding = query_embeddings[0]
        results = []
        for row in self.rows.values():
            if where:
                ok = True
                for key, expected in where.items():
                    if row["metadata"].get(key) != expected:
                        ok = False
                        break
                if not ok:
                    continue
            distance = abs(query_embedding[0] - row["embedding"][0])
            results.append((distance, row))

        results.sort(key=lambda x: x[0])
        top = results[:n_results]

        return {
            "ids": [[item[1]["id"] for item in top]],
            "documents": [[item[1]["document"] for item in top]],
            "metadatas": [[item[1]["metadata"] for item in top]],
            "distances": [[item[0] for item in top]],
        }


class _FakeClient:
    def __init__(self):
        self.collections: dict[str, _FakeCollection] = {}

    def get_or_create_collection(self, name, metadata=None):
        if name not in self.collections:
            self.collections[name] = _FakeCollection()
        return self.collections[name]


@pytest.fixture
def mock_embeddings():
    mock = MagicMock()
    vectors = {
        "doc 1": [0.0, 1.0],
        "doc 2": [0.1, 1.0],
        "doc 3": [0.9, 1.0],
        "query": [0.0, 1.0],
        "chunk 1": [0.2, 1.0],
        "chunk 2": [0.3, 1.0],
    }

    async def vectorize_documents(texts: list[str]) -> list[list[float]]:
        return [vectors.get(text, [0.5, 0.5]) for text in texts]

    async def vectorize_query(text: str) -> list[float]:
        return vectors.get(text, [0.5, 0.5])

    mock.vectorize_documents = vectorize_documents
    mock.vectorize_query = vectorize_query
    return mock


@pytest.fixture
def chroma_store(monkeypatch, mock_embeddings):
    fake_client = _FakeClient()
    monkeypatch.setattr(
        ChromaVectorStore, "_create_client", lambda self, config: fake_client
    )
    config = ChromaVectorStoreConfig(
        store_type=VectorStoreType.CHROMA,
        collection_name="unit_test_docs",
        embedding_dimension=2,
        distance_metric="cosine",
    )
    return ChromaVectorStore(config, mock_embeddings)


@pytest.mark.asyncio
async def test_add_documents(chroma_store):
    docs = [Document(id="doc1", content="doc 1"), Document(id="doc2", content="doc 2")]
    added_ids = await chroma_store.add_documents(docs)
    assert added_ids == ["doc1", "doc2"]


@pytest.mark.asyncio
async def test_search(chroma_store):
    docs = [
        Document(id="doc1", content="doc 1", metadata={"source": "a"}),
        Document(id="doc2", content="doc 2", metadata={"source": "a"}),
        Document(id="doc3", content="doc 3", metadata={"source": "b"}),
    ]
    await chroma_store.add_documents(docs)

    results = await chroma_store.search(
        "query", SearchType.SIMILARITY, top_k=2, filters={"source": "a"}
    )
    assert len(results) == 2
    assert results[0].document.id == "doc1"
    assert results[0].score >= results[1].score


@pytest.mark.asyncio
async def test_delete_and_get(chroma_store):
    await chroma_store.add_documents([Document(id="doc1", content="doc 1")])
    retrieved = await chroma_store.get_document("doc1")
    assert retrieved is not None
    assert retrieved.id == "doc1"

    deleted = await chroma_store.delete_documents(["doc1"])
    assert deleted is True
    assert await chroma_store.get_document("doc1") is None


@pytest.mark.asyncio
async def test_update_document(chroma_store):
    await chroma_store.add_documents([Document(id="doc1", content="doc 1")])
    updated = await chroma_store.update_document(
        Document(id="doc1", content="doc 2", metadata={"updated": True})
    )
    assert updated is True
    current = await chroma_store.get_document("doc1")
    assert current is not None
    assert current.content == "doc 2"
    assert current.metadata["updated"] is True


@pytest.mark.asyncio
async def test_chunk_helpers(chroma_store):
    chunks = [
        Chunk(id="chunk-1", text="chunk 1", start_index=0, end_index=7, token_count=2),
        Chunk(id="chunk-2", text="chunk 2", start_index=8, end_index=15, token_count=2),
    ]
    chunk_ids = await chroma_store.add_document_chunks(chunks)
    text_chunk_ids = await chroma_store.add_document_text_chunks(["doc 1", "doc 2"])

    assert chunk_ids == ["chunk-1", "chunk-2"]
    assert len(text_chunk_ids) == 2


def test_factory_creates_chroma_store(monkeypatch, mock_embeddings):
    fake_client = _FakeClient()
    monkeypatch.setattr(
        ChromaVectorStore, "_create_client", lambda self, config: fake_client
    )
    config = ChromaVectorStoreConfig(
        store_type=VectorStoreType.CHROMA,
        collection_name="factory_docs",
        embedding_dimension=2,
    )
    store = create_vector_store(config, mock_embeddings)
    assert isinstance(store, ChromaVectorStore)
