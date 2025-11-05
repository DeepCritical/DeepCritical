import os
from pathlib import Path

import pytest

from vector_store.src import Chunking, Embedding, VectorStore


@pytest.fixture
def sample_documents():
    return {
        "doc1": "This is the first document.",
        "doc2": "This is the second document.",
        "doc3": "This is the third document, which is about cats.",
    }

@pytest.fixture
def vector_store():
    embedding = Embedding()
    chunking = Chunking(chunk_size=10, chunk_overlap=3)
    return VectorStore(embedding, chunking)

def test_add_and_search_documents(vector_store, sample_documents):
    vector_store.add_documents(sample_documents)
    results = vector_store.search("cats", k=1)
    assert len(results) == 1
    assert results[0][0] == "doc3"
    assert "cats" in results[0][1]

def test_delete_documents(vector_store, sample_documents):
    vector_store.add_documents(sample_documents)
    vector_store.delete_documents(["doc3"])
    results = vector_store.search("cats", k=1)
    assert len(results) == 1
    assert results[0][0] != "doc3"


def test_save_and_load(vector_store, sample_documents):
    index_path = "test_index.faiss"
    metadata_path = "test_metadata.pkl"

    vector_store.add_documents(sample_documents)
    vector_store.save(index_path, metadata_path)

    loaded_store = VectorStore.load(index_path, metadata_path, vector_store.embedding, vector_store.chunking)
    results = loaded_store.search("cats", k=1)
    assert len(results) == 1
    assert results[0][0] == "doc3"
    assert "cats" in results[0][1]

    Path(index_path).unlink()
    Path(metadata_path).unlink()
