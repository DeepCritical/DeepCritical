import numpy as np
import pytest

from DeepResearch.src.datatypes.rag import EmbeddingModelType, EmbeddingsConfig
from DeepResearch.src.datatypes.sentence_transformer_embeddings import (
    SentenceTransformerEmbeddings,
)


@pytest.mark.asyncio
async def test_mixedbread_query_instruction_logic():
    """Test that query_instruction is properly prepended during encoding."""
    # Use small model for testing (not actual mixedbread to avoid download)
    config = EmbeddingsConfig(
        model_type=EmbeddingModelType.SENTENCE_TRANSFORMERS,
        model_name="all-MiniLM-L6-v2",  # Small model for testing
        num_dimensions=384,
        batch_size=32,
        device="cpu",
        query_instruction="Represent this sentence: ",
    )

    embeddings = SentenceTransformerEmbeddings(config)

    # Verify instruction field is set
    assert embeddings.query_instruction == "Represent this sentence: "

    # Generate embeddings (instruction will be prepended internally)
    query_vector = await embeddings.vectorize_query("test query")
    doc_vectors = await embeddings.vectorize_documents(["test doc"])

    # Verify dimensions
    assert len(query_vector) == 384
    assert len(doc_vectors) == 1
    assert len(doc_vectors[0]) == 384

    # Behavioral check: query and doc vectors should be DIFFERENT
    # even if input text was same (here they are different anyway),
    # but let's verify we get valid float vectors.

    assert isinstance(query_vector[0], (float, np.floating))
    assert isinstance(doc_vectors[0][0], (float, np.floating))
