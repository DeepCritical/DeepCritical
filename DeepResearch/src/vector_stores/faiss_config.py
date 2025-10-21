"""Configuration for FAISS-backed vector store."""

from __future__ import annotations

from pydantic import Field

from ..datatypes.rag import VectorStoreConfig, VectorStoreType


class FaissVectorStoreConfig(VectorStoreConfig):
    """Hydra-ready configuration for FAISS vector stores."""

    store_type: VectorStoreType = Field(default=VectorStoreType.FAISS)
    index_path: str | None = Field(
        default=None,
        description="Filesystem path where the FAISS index should be persisted.",
    )
    metadata_path: str | None = Field(
        default=None,
        description="Filesystem path where metadata for stored documents is saved.",
    )
    normalize_vectors: bool | None = Field(
        default=None,
        description=(
            "Whether to L2-normalize vectors before indexing. Defaults to True when "
            "the distance metric is cosine."
        ),
    )

