"""Factory for creating embeddings providers."""

from .rag import EmbeddingModelType, Embeddings, EmbeddingsConfig
from .sentence_transformer_embeddings import SentenceTransformerEmbeddings
from .vllm_integration import VLLMEmbeddings


def create_embeddings(config: EmbeddingsConfig) -> Embeddings:
    """
    Factory to instantiate the correct embeddings provider based on config.

    Args:
        config: Embeddings configuration

    Returns:
        Concrete embeddings instance

    Raises:
        ValueError: If provider is unknown
    """
    if config.model_type == EmbeddingModelType.SENTENCE_TRANSFORMERS:
        return SentenceTransformerEmbeddings(config)

    if config.model_type == EmbeddingModelType.MIXEDBREAD:
        # Mixedbread uses SentenceTransformer implementation (self-hosted)
        return SentenceTransformerEmbeddings(config)

    if config.model_type == EmbeddingModelType.VLLM:
        return VLLMEmbeddings(config)

    if config.model_type == EmbeddingModelType.OPENAI:
        # Optional fallback - raise error if not implemented or return class if added
        raise ValueError(
            "OpenAI embeddings not yet implemented. Use sentence_transformers or mixedbread."
        )

    raise ValueError(f"Unknown embedding model type: {config.model_type}")
