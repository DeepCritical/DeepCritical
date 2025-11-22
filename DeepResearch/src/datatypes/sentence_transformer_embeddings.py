"""Sentence-transformers based embeddings (local, offline-capable)."""

import asyncio
import logging
from typing import Any

from sentence_transformers import SentenceTransformer  # type: ignore

from .rag import Embeddings, EmbeddingsConfig

logger = logging.getLogger(__name__)


class SentenceTransformerEmbeddings(Embeddings):
    """Local embeddings using sentence-transformers library.

    Runs entirely offline after initial model download. Supports CPU and GPU.
    Handles both standard models (e.g. all-MiniLM-L6-v2) and instruction-tuned
    models (e.g. mixedbread-ai/mxbai-embed-large-v1).
    """

    def __init__(self, config: EmbeddingsConfig):
        """Initialize with configuration."""
        super().__init__(config)
        self._model = None
        self.model_name = config.model_name
        self.device = config.device or "cpu"
        self.batch_size = config.batch_size
        self.query_instruction = config.query_instruction

    @property
    def model(self) -> SentenceTransformer:
        """Lazy load the model."""
        if self._model is None:
            try:
                logger.info(
                    f"Loading sentence-transformers model '{self.model_name}' on {self.device}..."
                )
                self._model = SentenceTransformer(self.model_name, device=self.device)
                logger.info(
                    f"Loaded model '{self.model_name}' "
                    f"(dim: {self._model.get_sentence_embedding_dimension()})"
                )
            except Exception as e:
                logger.error(
                    f"Failed to load sentence-transformers model '{self.model_name}': {e}\n"
                    f"Try manual download:\n"
                    f"  python -m sentence_transformers.download '{self.model_name}'"
                )
                raise
        return self._model

    async def vectorize_documents(
        self, document_chunks: list[str]
    ) -> list[list[float]]:
        """Generate document embeddings asynchronously."""
        if not document_chunks:
            return []

        return await asyncio.to_thread(
            self._encode_sync, document_chunks, is_query=False
        )

    async def vectorize_query(self, text: str) -> list[float]:
        """Generate query embedding asynchronously."""
        if not text.strip():
            # Return zero vector or raise? ABC says return list[float].
            # Raise to be safe.
            raise ValueError("Cannot vectorize empty query")

        result = await asyncio.to_thread(self._encode_sync, [text], is_query=True)
        return result[0]

    def _encode_sync(self, texts: list[str], is_query: bool) -> list[list[float]]:
        """Synchronous encoding logic."""
        # Prepend instruction if it's a query and instruction is configured
        if is_query and self.query_instruction:
            texts = [f"{self.query_instruction}{t}" for t in texts]

        embeddings = self.model.encode(
            texts,
            batch_size=self.batch_size,
            show_progress_bar=False,
            convert_to_numpy=True,
            normalize_embeddings=True,
        )
        return embeddings.tolist()

    def vectorize_documents_sync(self, document_chunks: list[str]) -> list[list[float]]:
        """Synchronous wrapper for vectorize_documents."""
        if not document_chunks:
            return []
        # Direct call to _encode_sync avoids event loop overhead for sync usage
        return self._encode_sync(document_chunks, is_query=False)

    def vectorize_query_sync(self, text: str) -> list[float]:
        """Synchronous wrapper for vectorize_query."""
        if not text.strip():
            raise ValueError("Cannot vectorize empty query")
        result = self._encode_sync([text], is_query=True)
        return result[0]
