import pytest

from DeepResearch.src.datatypes.rag import EmbeddingModelType, EmbeddingsConfig
from DeepResearch.src.datatypes.sentence_transformer_embeddings import (
    SentenceTransformerEmbeddings,
)


@pytest.mark.asyncio
async def test_mixedbread_config():
    """Test that Mixedbread configuration works as expected."""
    config = EmbeddingsConfig(
        model_type=EmbeddingModelType.MIXEDBREAD,
        model_name="mixedbread-ai/mxbai-embed-large-v1",
        num_dimensions=1024,
        batch_size=32,
        device="cpu",
        query_instruction="Represent this sentence for searching relevant passages: ",
    )

    # We can't easily download the 1024 dim model in CI/test environment without
    # potentially hitting timeouts or large downloads.
    # So we will verify the class instantiation and logic,
    # but maybe use a smaller model for the actual 'encode' call if we want to test execution,
    # or just verify the instruction logic which we already did in the main test.

    # However, since this is a specific validation test for Phase 4D, let's trust
    # the unit tests for 'SentenceTransformerEmbeddings' covered the logic.
    # Here we just want to ensure the factory treats it correctly.

    from DeepResearch.src.datatypes.embeddings_factory import create_embeddings

    embeddings = create_embeddings(config)

    assert isinstance(embeddings, SentenceTransformerEmbeddings)
    assert (
        embeddings.query_instruction
        == "Represent this sentence for searching relevant passages: "
    )
    assert embeddings.model_name == "mixedbread-ai/mxbai-embed-large-v1"

    # If we were to run it, it would download the model.
    # For now, let's just pass.
