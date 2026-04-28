from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from DeepResearch.src.datatypes.chunk_dataclass import Chunk
from DeepResearch.src.datatypes.rag import Document, SearchType, VectorStoreType
from DeepResearch.src.vector_stores import create_vector_store
from DeepResearch.src.vector_stores.postgres_config import PostgresVectorStoreConfig
from DeepResearch.src.vector_stores.postgres_vector_store import PostgresVectorStore


class _FakeConnection:
    def __init__(self, rows):
        self.rows = rows

    async def execute(self, query, *args):
        if query.startswith("CREATE"):
            return None
        if query.startswith("DELETE"):
            ids = args[0]
            for doc_id in ids:
                self.rows.pop(doc_id, None)
            return f"DELETE {len(ids)}"
        return "OK"

    async def executemany(self, query, args_list):
        for args in args_list:
            doc_id, content, metadata, embedding = args
            self.rows[doc_id] = {
                "id": doc_id,
                "content": content,
                "metadata": metadata,
                "embedding": embedding,
            }
        return "OK"

    async def fetch(self, query, *args):
        if query.strip().startswith("SELECT"):
            results = []
            for row in self.rows.values():
                results.append(
                    {
                        "id": row["id"],
                        "content": row["content"],
                        "metadata": row["metadata"],
                        "distance": 0.1,
                    }
                )
            return results
        return []

    async def fetchrow(self, query, *args):
        doc_id = args[0]
        return self.rows.get(doc_id)


class _FakePool:
    def __init__(self):
        self.rows = {}

    def acquire(self):
        class _ContextManager:
            def __init__(self, rows):
                self.conn = _FakeConnection(rows)

            async def __aenter__(self):
                return self.conn

            async def __aexit__(self, exc_type, exc, tb):
                pass

        return _ContextManager(self.rows)


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
def postgres_store(monkeypatch, mock_embeddings):
    fake_pool = _FakePool()

    async def mock_get_pool(self):
        self._pool = fake_pool
        return fake_pool

    monkeypatch.setattr(PostgresVectorStore, "_get_pool", mock_get_pool)
    config = PostgresVectorStoreConfig(
        store_type=VectorStoreType.POSTGRES,
        connection_string="postgresql://test:test@localhost:5432/test",
        embedding_dimension=2,
    )
    return PostgresVectorStore(config, mock_embeddings)


@pytest.mark.asyncio
async def test_add_documents(postgres_store):
    docs = [Document(id="doc1", content="doc 1"), Document(id="doc2", content="doc 2")]
    added_ids = await postgres_store.add_documents(docs)
    assert added_ids == ["doc1", "doc2"]


@pytest.mark.asyncio
async def test_search(postgres_store):
    docs = [
        Document(id="doc1", content="doc 1", metadata={"source": "a"}),
        Document(id="doc2", content="doc 2", metadata={"source": "a"}),
    ]
    await postgres_store.add_documents(docs)
    results = await postgres_store.search("query", SearchType.SIMILARITY, top_k=2)
    assert len(results) == 2
    assert results[0].document.id == "doc1"


@pytest.mark.asyncio
async def test_delete_and_get(postgres_store):
    await postgres_store.add_documents([Document(id="doc1", content="doc 1")])
    retrieved = await postgres_store.get_document("doc1")
    assert retrieved is not None
    deleted = await postgres_store.delete_documents(["doc1"])
    assert deleted is True
    assert await postgres_store.get_document("doc1") is None


@pytest.mark.asyncio
async def test_update_document(postgres_store):
    await postgres_store.add_documents([Document(id="doc1", content="doc 1")])
    updated = await postgres_store.update_document(
        Document(id="doc1", content="doc 2", metadata={"updated": True})
    )
    assert updated is True
    current = await postgres_store.get_document("doc1")
    assert current is not None
    assert current.content == "doc 2"


@pytest.mark.asyncio
async def test_chunk_helpers(postgres_store):
    chunks = [
        Chunk(id="chunk-1", text="chunk 1", start_index=0, end_index=7, token_count=2)
    ]
    chunk_ids = await postgres_store.add_document_chunks(chunks)
    assert chunk_ids == ["chunk-1"]


def test_factory_creates_postgres_store(monkeypatch, mock_embeddings):
    fake_pool = _FakePool()

    async def mock_get_pool(self):
        return fake_pool

    monkeypatch.setattr(PostgresVectorStore, "_get_pool", mock_get_pool)
    config = PostgresVectorStoreConfig(
        store_type=VectorStoreType.POSTGRES,
        connection_string="test",
        embedding_dimension=2,
    )
    store = create_vector_store(config, mock_embeddings)
    assert isinstance(store, PostgresVectorStore)
