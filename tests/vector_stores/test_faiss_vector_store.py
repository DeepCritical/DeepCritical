import os
from unittest.mock import MagicMock

import faiss  # type: ignore
import pytest

from DeepResearch.src.datatypes.chunk_dataclass import Chunk
from DeepResearch.src.datatypes.rag import Document, SearchType, VectorStoreType
from DeepResearch.src.vector_stores.faiss_config import FAISSVectorStoreConfig
from DeepResearch.src.vector_stores.faiss_vector_store import FAISSVectorStore


@pytest.fixture
def mock_embeddings():
    """Fixture for a mock embeddings provider that returns predictable vectors."""
    mock = MagicMock()
    vectors = {
        "doc 1": [1.0, 0.0],
        "doc 2": [0.0, 1.0],
        "doc 3": [1.0, 1.0],
        "query": [0.0, 1.0],
        "chunk 1": [1.0, 0.0],
        "chunk 2": [0.0, 1.0],
    }

    async def vectorize_documents(texts: list[str]) -> list[list[float]]:
        return [vectors.get(text, [0.5, 0.5]) for text in texts]

    async def vectorize_query(text: str) -> list[float]:
        return vectors.get(text, [0.5, 0.5])

    mock.vectorize_documents = vectorize_documents
    mock.vectorize_query = vectorize_query
    return mock


@pytest.fixture
def faiss_store(tmp_path, mock_embeddings):
    """Fixture for a FAISSVectorStore instance using a temporary path."""
    index_path = str(tmp_path / "test.index")
    data_path = str(tmp_path / "test.data")
    config = FAISSVectorStoreConfig(
        store_type=VectorStoreType.FAISS,
        index_path=index_path,
        data_path=data_path,
    )
    return FAISSVectorStore(config, mock_embeddings)


@pytest.mark.asyncio
async def test_add_documents(faiss_store):
    """Tests adding documents to the store."""
    docs_to_add = [
        Document(id="doc1", content="doc 1"),
        Document(id="doc2", content="doc 2"),
    ]
    added_ids = await faiss_store.add_documents(docs_to_add)

    assert len(added_ids) == 2
    assert faiss_store.index.ntotal == 2
    assert len(faiss_store.documents) == 2
    assert "doc1" in faiss_store.documents


@pytest.mark.asyncio
async def test_search(faiss_store):
    """Tests searching for documents and getting predictable results."""
    docs_to_add = [
        Document(id="doc1", content="doc 1"),
        Document(id="doc2", content="doc 2"),
        Document(id="doc3", content="doc 3"),
    ]
    await faiss_store.add_documents(docs_to_add)

    results = await faiss_store.search("query", SearchType.SIMILARITY, top_k=2)

    assert len(results) == 2
    assert results[0].document.id == "doc2"
    assert results[0].score >= results[1].score


@pytest.mark.asyncio
async def test_delete_documents(faiss_store):
    """Tests deleting documents from the store."""
    docs_to_add = [
        Document(id="doc1", content="doc 1"),
        Document(id="doc2", content="doc 2"),
    ]
    await faiss_store.add_documents(docs_to_add)
    assert faiss_store.index.ntotal == 2
    assert "doc1" in faiss_store.documents

    await faiss_store.delete_documents(["doc1"])

    assert faiss_store.index.ntotal == 1
    assert "doc1" not in faiss_store.documents
    assert "doc2" in faiss_store.documents


@pytest.mark.asyncio
async def test_get_document(faiss_store):
    """Tests retrieving a document by its ID."""
    doc = Document(id="doc1", content="doc 1")
    await faiss_store.add_documents([doc])

    retrieved_doc = await faiss_store.get_document("doc1")
    assert retrieved_doc is not None
    assert retrieved_doc.id == "doc1"

    non_existent_doc = await faiss_store.get_document("doc_not_exist")
    assert non_existent_doc is None


@pytest.mark.asyncio
async def test_update_document(faiss_store):
    """Tests updating an existing document."""
    doc = Document(id="doc1", content="original content")
    await faiss_store.add_documents([doc])

    updated_doc = Document(id="doc1", content="updated content")
    update_result = await faiss_store.update_document(updated_doc)
    assert update_result is True

    retrieved_doc = await faiss_store.get_document("doc1")
    assert retrieved_doc is not None
    assert retrieved_doc.content == "updated content"


@pytest.mark.asyncio
async def test_save_and_load(tmp_path, mock_embeddings):
    """Tests that data is correctly saved to and loaded from disk."""
    index_path = str(tmp_path / "test.index")
    data_path = str(tmp_path / "test.data")
    config = FAISSVectorStoreConfig(
        store_type=VectorStoreType.FAISS,
        index_path=index_path,
        data_path=data_path,
    )

    # Create a store and add documents to it. This will trigger a save.
    store1 = FAISSVectorStore(config, mock_embeddings)
    docs_to_add = [Document(id="doc1", content="doc 1")]
    await store1.add_documents(docs_to_add)

    # Verify that the index and data files were actually created.
    assert os.path.exists(index_path)
    assert os.path.exists(data_path)

    # Create a new store instance from the same config. It should load the data.
    store2 = FAISSVectorStore(config, mock_embeddings)
    assert store2.index is not None
    assert store2.index.ntotal == 1
    assert len(store2.documents) == 1
    assert store2.documents["doc1"].id == "doc1"


@pytest.mark.asyncio
async def test_add_document_chunks(faiss_store):
    """Tests adding chunk dataclasses by converting them to documents."""
    chunks = [
        Chunk(id="chunk-1", text="chunk 1", start_index=0, end_index=7, token_count=2),
        Chunk(id="chunk-2", text="chunk 2", start_index=8, end_index=15, token_count=2),
    ]

    added_ids = await faiss_store.add_document_chunks(chunks)

    assert added_ids == ["chunk-1", "chunk-2"]
    assert await faiss_store.get_document("chunk-1") is not None


@pytest.mark.asyncio
async def test_add_document_text_chunks(faiss_store):
    """Tests adding raw text chunks."""
    added_ids = await faiss_store.add_document_text_chunks(["chunk 1", "chunk 2"])

    assert len(added_ids) == 2
    assert faiss_store.index is not None
    assert faiss_store.index.ntotal == 2
