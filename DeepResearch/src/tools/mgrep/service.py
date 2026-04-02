"""Shared service for repo-local mgrep-style semantic search."""

from __future__ import annotations

import re
from collections.abc import Callable
from datetime import datetime
from pathlib import Path
from typing import Any

from DeepResearch.src.datatypes.embeddings_factory import create_embeddings
from DeepResearch.src.datatypes.mgrep import (
    MANIFEST_VERSION,
    MgrepConfig,
    MgrepManifest,
    MgrepManifestEntry,
    MgrepSearchHit,
    MgrepSearchResponse,
    MgrepStats,
)
from DeepResearch.src.datatypes.rag import SearchResult, SearchType
from DeepResearch.src.vector_stores import create_vector_store
from DeepResearch.src.vector_stores.faiss_config import FAISSVectorStoreConfig

from .chunking import extract_chunks_from_file
from .discovery import compute_file_digest, discover_repository_files


class MgrepService:
    """Owns discovery, chunking, indexing, and semantic search for one repo."""

    def __init__(
        self,
        repo_root: str | Path,
        config: MgrepConfig | None = None,
        *,
        embeddings: Any | None = None,
        vector_store: Any | None = None,
        vector_store_factory: Callable[[], Any] | None = None,
    ):
        self.repo_root = Path(repo_root).resolve()
        self.config = config or MgrepConfig()
        self.store_dir = (self.repo_root / self.config.store_dir).resolve()
        self.store_dir.mkdir(parents=True, exist_ok=True)
        self.manifest_path = self.store_dir / "manifest.json"
        self.index_path = self.store_dir / "index.faiss"
        self.data_path = self.store_dir / "documents.pkl"

        self.embeddings = embeddings or create_embeddings(self.config.embeddings)
        if vector_store_factory is not None:
            self._vector_store_factory = vector_store_factory
        elif vector_store is not None:
            self._vector_store_factory = lambda: vector_store
        else:
            self._vector_store_factory = self._build_vector_store

        self.vector_store = self._vector_store_factory()
        self.manifest = self._load_manifest()

    def _build_vector_store(self) -> Any:
        return create_vector_store(
            FAISSVectorStoreConfig(
                store_type="faiss",
                embedding_dimension=self.config.embeddings.num_dimensions,
                distance_metric=self.config.distance_metric,
                index_path=str(self.index_path),
                data_path=str(self.data_path),
            ),
            self.embeddings,
        )

    def _new_manifest(self) -> MgrepManifest:
        return MgrepManifest(
            version=MANIFEST_VERSION,
            repo_root=str(self.repo_root),
            store_dir=str(self.store_dir),
            embedding_model_name=self.config.embeddings.model_name,
            embedding_dimensions=self.config.embeddings.num_dimensions,
            distance_metric=self.config.distance_metric,
            chunking_strategy_version=self.config.chunking_strategy_version,
            supported_extensions=[
                ext.lower() for ext in self.config.supported_extensions
            ],
        )

    def _load_manifest(self) -> MgrepManifest:
        if self.manifest_path.exists():
            try:
                return MgrepManifest.model_validate_json(
                    self.manifest_path.read_text(encoding="utf-8")
                )
            except Exception:
                return self._new_manifest()
        return self._new_manifest()

    def _save_manifest(self) -> None:
        self.manifest.updated_at = datetime.now()
        self.manifest_path.write_text(
            self.manifest.model_dump_json(indent=2), encoding="utf-8"
        )

    def _manifest_is_compatible(self) -> bool:
        return self.manifest.is_compatible(self.config, self.repo_root, self.store_dir)

    def _reset_storage(self) -> None:
        for path in (self.manifest_path, self.index_path, self.data_path):
            if path.exists():
                path.unlink()
        new_vector_store = self._vector_store_factory()
        if new_vector_store is self.vector_store:
            if hasattr(new_vector_store, "documents"):
                new_vector_store.documents = {}
            if hasattr(new_vector_store, "id_map"):
                new_vector_store.id_map = {}
            if hasattr(new_vector_store, "index"):
                new_vector_store.index = None
        self.vector_store = new_vector_store
        self.manifest = self._new_manifest()

    async def index(self) -> MgrepStats:
        """Force a full rebuild of the local semantic search index."""
        return await self._sync(force_rebuild=True)

    async def sync(self) -> MgrepStats:
        """Incrementally sync the local semantic search index."""
        return await self._sync(force_rebuild=False)

    async def _sync(self, *, force_rebuild: bool) -> MgrepStats:
        if force_rebuild or not self._manifest_is_compatible():
            self._reset_storage()

        discovery = discover_repository_files(self.repo_root, self.config)
        extra_skipped = 0
        current_paths = {
            path.relative_to(self.repo_root).as_posix(): path
            for path in discovery.files
        }
        existing_paths = set(self.manifest.files)

        removed_paths = sorted(existing_paths - set(current_paths))
        for relative_path in removed_paths:
            entry = self.manifest.files.pop(relative_path)
            if entry.chunk_ids:
                await self.vector_store.delete_documents(entry.chunk_ids)

        for relative_path, path in current_paths.items():
            try:
                digest = compute_file_digest(path)
            except OSError:
                extra_skipped += 1
                continue
            existing_entry = self.manifest.files.get(relative_path)
            if existing_entry and existing_entry.digest == digest:
                continue

            try:
                chunks = extract_chunks_from_file(path, self.repo_root, digest)
            except OSError:
                extra_skipped += 1
                continue
            documents = [chunk.to_document() for chunk in chunks]

            if existing_entry and existing_entry.chunk_ids:
                await self.vector_store.delete_documents(existing_entry.chunk_ids)
            if documents:
                await self.vector_store.add_documents(documents)

            self.manifest.files[relative_path] = MgrepManifestEntry(
                relative_path=relative_path,
                digest=digest,
                language=chunks[0].language if chunks else path.suffix.lstrip("."),
                chunk_count=len(documents),
                chunk_ids=[document.id for document in documents],
            )

        self.manifest.skipped_file_count = discovery.skipped_count + extra_skipped
        self._save_manifest()
        return self.get_stats()

    async def search(
        self, query: str, *, top_k: int = 10, path: str | None = None
    ) -> MgrepSearchResponse:
        """Perform semantic search over the current local index."""
        normalized_query = " ".join(query.split())
        if not normalized_query:
            return MgrepSearchResponse(query=query, search_mode="search")

        hits = await self._search_hits(normalized_query, top_k=top_k, path=path)
        return MgrepSearchResponse(
            query=normalized_query,
            search_mode="search",
            generated_queries=[normalized_query],
            results=hits,
            total_results=len(hits),
        )

    async def smart_search(
        self, query: str, *, top_k: int = 10, path: str | None = None
    ) -> MgrepSearchResponse:
        """Perform a lightly expanded semantic search over the current local index."""
        queries = self._expand_queries(query)
        deduped: dict[tuple[str, int, int], MgrepSearchHit] = {}

        for expanded_query in queries:
            for hit in await self._search_hits(
                expanded_query,
                top_k=top_k,
                path=path,
            ):
                key = (hit.relative_path, hit.line_start, hit.line_end)
                existing = deduped.get(key)
                if existing is None or hit.score > existing.score:
                    deduped[key] = hit

        hits = sorted(deduped.values(), key=lambda hit: hit.score, reverse=True)[:top_k]
        return MgrepSearchResponse(
            query=" ".join(query.split()),
            search_mode="smart_search",
            generated_queries=queries,
            results=hits,
            total_results=len(hits),
        )

    async def _search_hits(
        self, query: str, *, top_k: int, path: str | None = None
    ) -> list[MgrepSearchHit]:
        fetch_limit = max(top_k * max(self.config.search_fetch_multiplier, 1), top_k)
        raw_results: list[SearchResult] = await self.vector_store.search(
            query=query,
            search_type=SearchType.SEMANTIC,
            top_k=fetch_limit,
        )

        normalized_path_filter = path.lower() if path else None
        hits: list[MgrepSearchHit] = []
        for result in raw_results:
            metadata = result.document.metadata
            relative_path = str(metadata.get("relative_path", ""))
            if (
                normalized_path_filter
                and normalized_path_filter not in relative_path.lower()
            ):
                continue
            snippet = result.document.content.strip()
            hits.append(
                MgrepSearchHit(
                    chunk_id=result.document.id,
                    path=str(metadata.get("path", "")),
                    relative_path=relative_path,
                    language=str(metadata.get("language", "")),
                    kind=str(metadata.get("kind", "")),
                    symbol_name=metadata.get("symbol_name"),
                    line_start=int(metadata.get("line_start", 1)),
                    line_end=int(metadata.get("line_end", 1)),
                    score=float(result.score),
                    snippet=snippet[:400],
                    digest=metadata.get("digest"),
                    metadata=dict(metadata),
                )
            )
            if len(hits) >= top_k:
                break

        return hits

    def _expand_queries(self, query: str) -> list[str]:
        normalized = " ".join(query.split())
        if not normalized:
            return []

        variants = [normalized]
        for candidate in (
            normalized.replace("_", " "),
            normalized.replace("-", " "),
            re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", normalized),
        ):
            candidate = " ".join(candidate.split())
            if candidate and candidate not in variants:
                variants.append(candidate)
        return variants

    def get_stats(self) -> MgrepStats:
        """Return index and manifest stats."""
        indexed_chunk_count = sum(
            entry.chunk_count for entry in self.manifest.files.values()
        )
        return MgrepStats(
            repo_root=str(self.repo_root),
            store_dir=str(self.store_dir),
            index_path=str(self.index_path),
            manifest_version=self.manifest.version,
            vector_store_type="faiss",
            embedding_model_name=self.config.embeddings.model_name,
            indexed_file_count=len(self.manifest.files),
            indexed_chunk_count=indexed_chunk_count,
            skipped_file_count=self.manifest.skipped_file_count,
            last_sync_time=self.manifest.updated_at,
        )
