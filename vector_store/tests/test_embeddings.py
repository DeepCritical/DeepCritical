import pytest

from vector_store.src.embeddings import Embedding


def test_embedding():
    """
    Tests that the embed method returns a list of embeddings with the correct dimensions.
    """
    embedding_model = Embedding()
    texts = ["This is a test sentence.", "This is another test sentence."]
    embeddings = embedding_model.embed(texts)

    assert isinstance(embeddings, list)
    assert len(embeddings) == len(texts)
    assert all(isinstance(emb, list) for emb in embeddings)
    assert all(len(emb) > 0 for emb in embeddings)
