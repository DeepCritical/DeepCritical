from __future__ import annotations

from pydantic import Field

from ..datatypes.rag import VectorStoreConfig, VectorStoreType


class FAISSVectorStoreConfig(VectorStoreConfig):
    """Configuration for the FAISS vector store."""

    store_type: VectorStoreType = Field(default=VectorStoreType.FAISS, Literal=True)
    index_path: str = Field(description="File path to save or load the FAISS index.")
    data_path: str = Field(description="File path to save or load the document data.")
