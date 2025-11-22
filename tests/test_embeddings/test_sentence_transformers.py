import numpy as np
import pytest

from DeepResearch.src.datatypes.rag import EmbeddingModelType, EmbeddingsConfig
from DeepResearch.src.datatypes.sentence_transformer_embeddings import (
    SentenceTransformerEmbeddings,
)


@pytest.fixture
def config():
    return EmbeddingsConfig(
        model_type=EmbeddingModelType.SENTENCE_TRANSFORMERS,
        model_name="all-MiniLM-L6-v2",
        num_dimensions=384,
        batch_size=32,
        device="cpu",
    )


@pytest.fixture
def embeddings(config):
    return SentenceTransformerEmbeddings(config)


@pytest.mark.asyncio
async def test_dimensions(embeddings):
    """Test that embeddings have correct dimensions."""
    vector = await embeddings.vectorize_query("test")
    assert len(vector) == 384
    assert isinstance(vector, list)
    assert isinstance(vector[0], float)


@pytest.mark.asyncio
async def test_vectorize_documents(embeddings):
    """Test vectorizing a list of documents."""
    docs = ["doc1", "doc2", "doc3"]
    vectors = await embeddings.vectorize_documents(docs)
    assert len(vectors) == 3
    assert len(vectors[0]) == 384
    assert isinstance(vectors, list)
    assert isinstance(vectors[0], list)


def test_sync_methods(embeddings):
    """Test synchronous methods."""
    vector = embeddings.vectorize_query_sync("test")
    assert len(vector) == 384

    vectors = embeddings.vectorize_documents_sync(["doc1"])
    assert len(vectors) == 1
    assert len(vectors[0]) == 384


@pytest.mark.asyncio
async def test_query_instruction():
    """Test that query instruction doesn't break execution."""
    config = EmbeddingsConfig(
        model_type=EmbeddingModelType.SENTENCE_TRANSFORMERS,
        model_name="all-MiniLM-L6-v2",
        num_dimensions=384,
        query_instruction="Represent: ",
    )
    emb = SentenceTransformerEmbeddings(config)
    # We can't easily verify the instruction was used without mocking the model
    # But we can verify it runs without error
    vector = await emb.vectorize_query("test")
    assert len(vector) == 384


@pytest.mark.asyncio
async def test_empty_input(embeddings):
    """Test handling of empty inputs."""
    with pytest.raises(ValueError, match="Cannot vectorize empty query"):
        await embeddings.vectorize_query("")

    vectors = await embeddings.vectorize_documents([])
    assert vectors == []
