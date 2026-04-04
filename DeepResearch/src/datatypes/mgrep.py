"""Datatypes for repo-local mgrep-style semantic search."""

from __future__ import annotations

import hashlib
from datetime import datetime
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from .rag import Document, EmbeddingModelType, EmbeddingsConfig

MANIFEST_VERSION = 1
CHUNKING_STRATEGY_VERSION = "mgrep-v1"
DEFAULT_SUPPORTED_EXTENSIONS = [
    ".py",
    ".md",
    ".txt",
    ".json",
    ".yaml",
    ".yml",
    ".toml",
]


def normalize_supported_extensions(supported_extensions: list[str]) -> list[str]:
    """Normalize extensions for stable manifest comparisons."""
    return sorted({extension.lower() for extension in supported_extensions})


def build_chunk_id(
    *,
    relative_path: str,
    digest: str,
    kind: str,
    symbol_name: str | None,
    line_start: int,
    line_end: int,
) -> str:
    """Build a stable chunk identifier for a file-backed chunk."""
    payload = "|".join(
        [
            relative_path,
            digest,
            kind,
            symbol_name or "",
            str(line_start),
            str(line_end),
        ]
    )
    return f"mgrep_{hashlib.sha1(payload.encode('utf-8')).hexdigest()[:20]}"


class MgrepConfig(BaseModel):
    """Configuration for repo-local semantic search."""

    store_dir: str = Field(".deepcritical/mgrep", description="Relative storage dir")
    supported_extensions: list[str] = Field(
        default_factory=lambda: DEFAULT_SUPPORTED_EXTENSIONS.copy(),
        description="File extensions eligible for indexing",
    )
    max_file_size_bytes: int = Field(
        512_000,
        ge=1,
        description="Largest file that will be indexed in the MVP",
    )
    search_fetch_multiplier: int = Field(
        5,
        ge=1,
        description="Oversampling multiplier before in-memory filtering",
    )
    distance_metric: str = Field(
        "cosine", description="Vector distance metric for semantic search"
    )
    chunking_strategy_version: str = Field(
        CHUNKING_STRATEGY_VERSION, description="Chunking strategy fingerprint"
    )
    embeddings: EmbeddingsConfig = Field(
        default_factory=lambda: EmbeddingsConfig(
            model_type=EmbeddingModelType.SENTENCE_TRANSFORMERS,
            model_name="all-MiniLM-L6-v2",
            num_dimensions=384,
            batch_size=32,
            device="cpu",
        ),
        description="Embeddings configuration for semantic search",
    )


class MgrepManifestEntry(BaseModel):
    """Indexed state for one repository file."""

    relative_path: str
    digest: str
    language: str
    chunk_count: int
    chunk_ids: list[str] = Field(default_factory=list)
    indexed_at: datetime = Field(default_factory=datetime.now)


class MgrepManifest(BaseModel):
    """Persisted manifest for incremental indexing."""

    version: int = Field(MANIFEST_VERSION, description="Manifest schema version")
    repo_root: str
    store_dir: str
    embedding_model_name: str
    embedding_dimensions: int
    distance_metric: str = "cosine"
    chunking_strategy_version: str
    supported_extensions: list[str]
    skipped_file_count: int = 0
    updated_at: datetime = Field(default_factory=datetime.now)
    files: dict[str, MgrepManifestEntry] = Field(default_factory=dict)

    def is_compatible(
        self, config: MgrepConfig, repo_root: Path, store_dir: Path
    ) -> bool:
        """Return whether the manifest can be reused for the given config."""
        return (
            self.version == MANIFEST_VERSION
            and self.repo_root == str(repo_root)
            and self.store_dir == str(store_dir)
            and self.embedding_model_name == config.embeddings.model_name
            and self.embedding_dimensions == config.embeddings.num_dimensions
            and self.distance_metric == config.distance_metric
            and self.chunking_strategy_version == config.chunking_strategy_version
            and normalize_supported_extensions(self.supported_extensions)
            == normalize_supported_extensions(config.supported_extensions)
        )


class MgrepChunk(BaseModel):
    """One searchable chunk extracted from a repository file."""

    id: str
    path: str
    relative_path: str
    language: str
    kind: str
    symbol_name: str | None = None
    line_start: int
    line_end: int
    text: str
    digest: str
    metadata: dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(arbitrary_types_allowed=True)

    def to_document(self) -> Document:
        """Convert the chunk into the repo's shared vector-store document type."""
        metadata = {
            "path": self.path,
            "relative_path": self.relative_path,
            "language": self.language,
            "kind": self.kind,
            "symbol_name": self.symbol_name,
            "line_start": self.line_start,
            "line_end": self.line_end,
            "digest": self.digest,
            **self.metadata,
        }
        return Document(id=self.id, content=self.text, metadata=metadata)


class MgrepSearchRequest(BaseModel):
    """Search request for repo-local semantic search."""

    query: str
    top_k: int = Field(10, ge=1, le=100)
    path: str | None = None
    smart: bool = False


class MgrepSearchHit(BaseModel):
    """One structured semantic search result."""

    chunk_id: str
    path: str
    relative_path: str
    language: str
    kind: str
    symbol_name: str | None = None
    line_start: int
    line_end: int
    score: float
    snippet: str
    digest: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class MgrepSearchResponse(BaseModel):
    """Structured search response."""

    query: str
    search_mode: str
    generated_queries: list[str] = Field(default_factory=list)
    results: list[MgrepSearchHit] = Field(default_factory=list)
    total_results: int = 0


class MgrepStats(BaseModel):
    """Repo-local semantic search stats."""

    repo_root: str
    store_dir: str
    index_path: str
    manifest_version: int
    vector_store_type: str
    embedding_model_name: str
    indexed_file_count: int
    indexed_chunk_count: int
    skipped_file_count: int
    last_sync_time: datetime | None = None
