import os
from unittest.mock import MagicMock

import faiss  # type: ignore
import numpy as np
import pytest

from DeepResearch.src.datatypes.rag import Document, SearchType, VectorStoreType
from DeepResearch.src.vector_stores.faiss_config import FAISSVectorStoreConfig
from DeepResearch.src.vector_stores.faiss_vector_store import FAISSVectorStore


@pytest.fixture
def mock_embeddings():
    """Fixture for a mock embeddings provider that returns predictable vectors."""
    mock = MagicMock()

    async def vectorize_documents(texts: list[str]) -> list[list[float]]:
        # Simple embedding: index as value, e.g., [[0.0, 0.0], [1.0, 1.0], ...]
        return [[float(i), float(i)] for i, _ in enumerate(texts)]

    async def vectorize_query(text: str) -> list[float]:
        # Fixed query embedding to get predictable search results.
        # This will be most similar to the document at index 1.
        return [1.0, 1.0]

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
    # The mock query vector is [1.0, 1.0].
    # The document vectors are [[0.0, 0.0], [1.0, 1.0], [2.0, 2.0]].
    # The document with id="doc2" will have embedding [1.0, 1.0] and thus a distance of 0.
    assert results[0].document.id == "doc2"


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
