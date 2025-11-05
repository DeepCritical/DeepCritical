from __future__ import annotations

from pydantic import BaseModel, Field


class FAISSVectorStoreConfig(BaseModel):
    """Configuration for the FAISS vector store."""

    index_path: str = Field(
        description="File path to save or load the FAISS index."
    )
    data_path: str = Field(
        description="File path to save or load the document data."
    )
