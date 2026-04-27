from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from DeepResearch.src.datatypes.chunk_dataclass import Chunk
from DeepResearch.src.datatypes.rag import Document, SearchType, VectorStoreType
from DeepResearch.src.vector_stores import create_vector_store
from DeepResearch.src.vector_stores.pinecone_config import PineconeVectorStoreConfig
from DeepResearch.src.vector_stores.pinecone_vector_store import PineconeVectorStore


class _FakeIndex:
    def __init__(self):
        self.rows = {}

    def upsert(self, vectors):
        for v in vectors:
            self.rows[v["id"]] = v

    def delete(self, ids):
        for row_id in ids:
            self.rows.pop(row_id, None)

    def fetch(self, ids):
        matches = {row_id: self.rows[row_id] for row_id in ids if row_id in self.rows}
        return {"vectors": matches}

    def query(self, vector, top_k, filter=None, include_metadata=False):
        results = []
        for row in self.rows.values():
            if filter:
                ok = True
                for key, expected in filter.items():
                    if row["metadata"].get(key) != expected:
                        ok = False
                        break
                if not ok:
                    continue
            distance = abs(vector[0] - row["values"][0])
            score = 1.0 - distance
            results.append(
                {"id": row["id"], "score": score, "metadata": row["metadata"]}
            )
        results.sort(key=lambda x: x["score"], reverse=True)
        return {"matches": results[:top_k]}


class _FakePinecone:
    def __init__(self, api_key=None):
        self.api_key = api_key
        self.indexes = {}

    def Index(self, name):
        if name not in self.indexes:
            self.indexes[name] = _FakeIndex()
        return self.indexes[name]


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
def pinecone_store(monkeypatch, mock_embeddings):
    fake_pinecone = _FakePinecone()
    monkeypatch.setattr("pinecone.Pinecone", lambda **kwargs: fake_pinecone)
    config = PineconeVectorStoreConfig(
        store_type=VectorStoreType.PINECONE,
        index_name="unit_test_docs",
        embedding_dimension=2,
    )
    return PineconeVectorStore(config, mock_embeddings)


@pytest.mark.asyncio
async def test_add_documents(pinecone_store):
    docs = [Document(id="doc1", content="doc 1"), Document(id="doc2", content="doc 2")]
    added_ids = await pinecone_store.add_documents(docs)
    assert added_ids == ["doc1", "doc2"]


@pytest.mark.asyncio
async def test_search(pinecone_store):
    docs = [
        Document(id="doc1", content="doc 1", metadata={"source": "a"}),
        Document(id="doc2", content="doc 2", metadata={"source": "a"}),
        Document(id="doc3", content="doc 3", metadata={"source": "b"}),
    ]
    await pinecone_store.add_documents(docs)
    results = await pinecone_store.search(
        "query", SearchType.SIMILARITY, top_k=2, filters={"source": "a"}
    )
    assert len(results) == 2
    assert results[0].document.id == "doc1"
    assert results[0].score >= results[1].score


@pytest.mark.asyncio
async def test_delete_and_get(pinecone_store):
    await pinecone_store.add_documents([Document(id="doc1", content="doc 1")])
    retrieved = await pinecone_store.get_document("doc1")
    assert retrieved is not None
    deleted = await pinecone_store.delete_documents(["doc1"])
    assert deleted is True
    assert await pinecone_store.get_document("doc1") is None


@pytest.mark.asyncio
async def test_update_document(pinecone_store):
    await pinecone_store.add_documents([Document(id="doc1", content="doc 1")])
    updated = await pinecone_store.update_document(
        Document(id="doc1", content="doc 2", metadata={"updated": True})
    )
    assert updated is True
    current = await pinecone_store.get_document("doc1")
    assert current is not None
    assert current.content == "doc 2"
    assert current.metadata["updated"] is True


@pytest.mark.asyncio
async def test_chunk_helpers(pinecone_store):
    chunks = [
        Chunk(id="chunk-1", text="chunk 1", start_index=0, end_index=7, token_count=2)
    ]
    chunk_ids = await pinecone_store.add_document_chunks(chunks)
    assert chunk_ids == ["chunk-1"]


def test_factory_creates_pinecone_store(monkeypatch, mock_embeddings):
    fake_pinecone = _FakePinecone()
    monkeypatch.setattr("pinecone.Pinecone", lambda **kwargs: fake_pinecone)
    config = PineconeVectorStoreConfig(
        store_type=VectorStoreType.PINECONE,
        index_name="unit_test_docs",
        embedding_dimension=2,
    )
    store = create_vector_store(config, mock_embeddings)
    assert isinstance(store, PineconeVectorStore)
