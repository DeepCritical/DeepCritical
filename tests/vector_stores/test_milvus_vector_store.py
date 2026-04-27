from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from DeepResearch.src.datatypes.chunk_dataclass import Chunk
from DeepResearch.src.datatypes.rag import Document, SearchType, VectorStoreType
from DeepResearch.src.vector_stores import create_vector_store
from DeepResearch.src.vector_stores.milvus_config import MilvusVectorStoreConfig
from DeepResearch.src.vector_stores.milvus_vector_store import MilvusVectorStore


class _FakeMilvusClient:
    def __init__(self, uri=None, token=None):
        self.uri = uri
        self.token = token
        self.collections = {}

    def has_collection(self, collection_name):
        return collection_name in self.collections

    def create_collection(self, collection_name, **kwargs):
        self.collections[collection_name] = {}

    def insert(self, collection_name, data):
        for row in data:
            self.collections[collection_name][row["id"]] = row

    def delete(self, collection_name, pks):
        for row_id in pks:
            self.collections[collection_name].pop(row_id, None)

    def query(self, collection_name, filter, output_fields):
        doc_id = filter.split("==")[1].strip().strip("'")
        row = self.collections[collection_name].get(doc_id)
        if not row:
            return []
        return [row.copy()]

    def search(self, collection_name, data, limit, filter, output_fields):
        vector = data[0]
        results = []
        for row in self.collections[collection_name].values():
            if filter:
                k, v = filter.split("==")
                k = k.strip()
                v = v.strip().strip("'")
                if str(row.get(k)) != v:
                    continue
            distance = abs(vector[0] - row["embedding"][0])
            score = 1.0 - distance
            hit = {"id": row["id"], "distance": score, "entity": row.copy()}
            results.append(hit)
        results.sort(key=lambda x: x["distance"], reverse=True)
        return [results[:limit]]


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
def milvus_store(monkeypatch, mock_embeddings):
    fake_client = _FakeMilvusClient()
    monkeypatch.setattr("pymilvus.MilvusClient", lambda **kwargs: fake_client)
    config = MilvusVectorStoreConfig(
        store_type=VectorStoreType.MILVUS,
        uri="http://localhost:19530",
        embedding_dimension=2,
    )
    return MilvusVectorStore(config, mock_embeddings)


@pytest.mark.asyncio
async def test_add_documents(milvus_store):
    docs = [Document(id="doc1", content="doc 1"), Document(id="doc2", content="doc 2")]
    added_ids = await milvus_store.add_documents(docs)
    assert added_ids == ["doc1", "doc2"]


@pytest.mark.asyncio
async def test_search(milvus_store):
    docs = [
        Document(id="doc1", content="doc 1", metadata={"source": "a"}),
        Document(id="doc2", content="doc 2", metadata={"source": "a"}),
        Document(id="doc3", content="doc 3", metadata={"source": "b"}),
    ]
    await milvus_store.add_documents(docs)
    results = await milvus_store.search(
        "query", SearchType.SIMILARITY, top_k=2, filters={"source": "a"}
    )
    assert len(results) == 2
    assert results[0].document.id == "doc1"
    assert results[0].score >= results[1].score


@pytest.mark.asyncio
async def test_delete_and_get(milvus_store):
    await milvus_store.add_documents([Document(id="doc1", content="doc 1")])
    retrieved = await milvus_store.get_document("doc1")
    assert retrieved is not None
    deleted = await milvus_store.delete_documents(["doc1"])
    assert deleted is True
    assert await milvus_store.get_document("doc1") is None


@pytest.mark.asyncio
async def test_update_document(milvus_store):
    await milvus_store.add_documents([Document(id="doc1", content="doc 1")])
    updated = await milvus_store.update_document(
        Document(id="doc1", content="doc 2", metadata={"updated": True})
    )
    assert updated is True
    current = await milvus_store.get_document("doc1")
    assert current is not None
    assert current.content == "doc 2"
    assert current.metadata["updated"] is True


@pytest.mark.asyncio
async def test_chunk_helpers(milvus_store):
    chunks = [
        Chunk(id="chunk-1", text="chunk 1", start_index=0, end_index=7, token_count=2)
    ]
    chunk_ids = await milvus_store.add_document_chunks(chunks)
    assert chunk_ids == ["chunk-1"]


def test_factory_creates_milvus_store(monkeypatch, mock_embeddings):
    fake_client = _FakeMilvusClient()
    monkeypatch.setattr("pymilvus.MilvusClient", lambda **kwargs: fake_client)
    config = MilvusVectorStoreConfig(
        store_type=VectorStoreType.MILVUS,
        collection_name="unit_test_docs",
        embedding_dimension=2,
    )
    store = create_vector_store(config, mock_embeddings)
    assert isinstance(store, MilvusVectorStore)
