"""Chunking configuration utilities for RAG workflows."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, model_validator


class ChunkingConfig(BaseModel):
    """Configuration describing how documents should be chunked."""

    chunk_size: int = Field(
        1000,
        ge=1,
        description="Maximum number of characters per chunk.",
    )
    chunk_overlap: int = Field(
        200,
        ge=0,
        description="Number of overlapping characters between consecutive chunks.",
    )

    @model_validator(mode="after")
    def validate_overlap(self) -> "ChunkingConfig":
        """Ensure the configured overlap cannot exceed the chunk size."""

        if self.chunk_overlap >= self.chunk_size:
            msg = "chunk_overlap must be smaller than chunk_size"
            raise ValueError(msg)
        return self

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "chunk_size": 1000,
                "chunk_overlap": 200,
            }
        }
    )

