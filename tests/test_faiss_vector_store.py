"""Tests for the FAISS vector store backend."""

from __future__ import annotations

import asyncio
import importlib.util
import sys
import types
from pathlib import Path
from typing import Any

import pytest

SRC_ROOT = Path(__file__).resolve().parents[1] / "DeepResearch" / "src"


def _ensure_package(name: str, path: Path) -> None:
    if name in sys.modules:
        return
    module = types.ModuleType(name)
    module.__path__ = [str(path)]  # type: ignore[attr-defined]
    sys.modules[name] = module


def _load_module(module_name: str, relative_path: str):
    if module_name in sys.modules:
        return sys.modules[module_name]
    file_path = SRC_ROOT / relative_path
    package_name = module_name.rpartition(".")[0]
    if package_name:
        package_parts = package_name.split(".")
        current_path = SRC_ROOT
        base_package = []
        for part in package_parts[2:]:
            base_package.append(part)
            pkg_name = "DeepResearch.src." + ".".join(base_package)
            current_path = current_path / part
            _ensure_package(pkg_name, current_path)
    spec = importlib.util.spec_from_file_location(module_name, file_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load module {module_name}")
    module = importlib.util.module_from_spec(spec)
    module.__package__ = package_name
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


_ensure_package("DeepResearch", Path("DeepResearch"))
_ensure_package("DeepResearch.src", SRC_ROOT)
_ensure_package("DeepResearch.src.datatypes", SRC_ROOT / "datatypes")
_ensure_package("DeepResearch.src.vector_stores", SRC_ROOT / "vector_stores")

chunk_module = _load_module(
    "DeepResearch.src.datatypes.chunk_dataclass", "datatypes/chunk_dataclass.py"
)
rag_module = _load_module("DeepResearch.src.datatypes.rag", "datatypes/rag.py")
faiss_config_module = _load_module(
    "DeepResearch.src.vector_stores.faiss_config", "vector_stores/faiss_config.py"
)
faiss_vector_module = _load_module(
    "DeepResearch.src.vector_stores.faiss_vector_store", "vector_stores/faiss_vector_store.py"
)

Chunk = chunk_module.Chunk
Document = rag_module.Document
Embeddings = rag_module.Embeddings
SearchType = rag_module.SearchType
FaissVectorStoreConfig = faiss_config_module.FaissVectorStoreConfig
FaissVectorStore = faiss_vector_module.FaissVectorStore


class MockEmbeddings(Embeddings):
    """Deterministic embedding generator for testing."""

    def __init__(self, dimension: int = 8):
        self.dimension = dimension

    def _encode(self, text: str) -> list[float]:
        vector = [0.05] * self.dimension
        for index, character in enumerate(text[: self.dimension - 1]):
            vector[index] = ((ord(character) % 256) + 1) / 300.0
        vector[-1] = len(text) / 50.0 + 0.1
        return vector

    async def vectorize_documents(self, document_chunks: list[str]) -> list[list[float]]:
        return [self._encode(text) for text in document_chunks]

    def vectorize_documents_sync(self, document_chunks: list[str]) -> list[list[float]]:
        return [self._encode(text) for text in document_chunks]

    async def vectorize_query(self, text: str) -> list[float]:
        return self._encode(text)

    def vectorize_query_sync(self, text: str) -> list[float]:
        return self._encode(text)


@pytest.fixture
def mock_embeddings() -> MockEmbeddings:
    return MockEmbeddings(dimension=8)


@pytest.fixture
def faiss_config(tmp_path) -> FaissVectorStoreConfig:
    index_path = tmp_path / "test_index.faiss"
    metadata_path = tmp_path / "test_metadata.json"
    return FaissVectorStoreConfig(
        index_path=str(index_path),
        metadata_path=str(metadata_path),
        embedding_dimension=8,
        distance_metric="cosine",
    )


@pytest.fixture
def faiss_store(
    faiss_config: FaissVectorStoreConfig, mock_embeddings: MockEmbeddings
) -> Any:
    store = FaissVectorStore(faiss_config, mock_embeddings)
    yield store
    asyncio.run(store.close())


def test_add_and_search_documents(faiss_store: FaissVectorStore) -> None:
    async def run_test() -> None:
        documents = [
            Document(
                id="doc_alpha",
                content="Alpha gene research",
                metadata={"category": "science"},
            ),
            Document(
                id="doc_beta",
                content="Beta cell study",
                metadata={"category": "biology"},
            ),
        ]

        await faiss_store.add_documents(documents)

        results = await faiss_store.search(
            "Alpha gene research", SearchType.SIMILARITY, top_k=2
        )

        assert results
        assert results[0].document.id == "doc_alpha"
        assert results[0].rank == 1
        assert results[0].score > 0.0

    asyncio.run(run_test())


def test_delete_documents_removes_from_index(faiss_store: FaissVectorStore) -> None:
    async def run_test() -> None:
        documents = [
            Document(id="doc_alpha", content="Alpha gene research"),
            Document(id="doc_beta", content="Beta cell study"),
        ]
        await faiss_store.add_documents(documents)

        removed = await faiss_store.delete_documents(["doc_alpha"])
        assert removed is True

        results = await faiss_store.search("Alpha", SearchType.SIMILARITY, top_k=2)
        assert all(result.document.id != "doc_alpha" for result in results)

    asyncio.run(run_test())


def test_persistence_round_trip(tmp_path, mock_embeddings: MockEmbeddings) -> None:
    async def run_test() -> None:
        config = FaissVectorStoreConfig(
            index_path=str(tmp_path / "roundtrip.faiss"),
            metadata_path=str(tmp_path / "roundtrip.json"),
            embedding_dimension=8,
            distance_metric="cosine",
        )

        store = FaissVectorStore(config, mock_embeddings)
        await store.add_documents(
            [
                Document(
                    id="doc_alpha",
                    content="Alpha gene research",
                    metadata={"category": "science"},
                )
            ]
        )
        await store.close()

        reloaded_store = FaissVectorStore(config, MockEmbeddings(dimension=8))
        results = await reloaded_store.search(
            "Alpha gene", SearchType.SIMILARITY, top_k=1
        )
        assert results and results[0].document.id == "doc_alpha"
        await reloaded_store.close()

    asyncio.run(run_test())


def test_add_document_chunks(faiss_store: FaissVectorStore) -> None:
    async def run_test() -> None:
        chunk = Chunk(
            text="Segment about proteins", start_index=0, end_index=21, token_count=4
        )

        ids = await faiss_store.add_document_chunks([chunk])
        assert ids == [chunk.id]

        results = await faiss_store.search("proteins", SearchType.SIMILARITY, top_k=1)
        assert results
        assert results[0].document.metadata.get("source") == "chunk"
        assert results[0].document.metadata.get("chunk_id") == chunk.id

    asyncio.run(run_test())


def test_add_document_text_chunks_returns_ids(
    faiss_store: FaissVectorStore,
) -> None:
    async def run_test() -> None:
        ids = await faiss_store.add_document_text_chunks(
            ["Introductory passage", "Detailed follow up"]
        )

        assert len(ids) == 2
        assert ids[0] != ids[1]

        results = await faiss_store.search(
            "Detailed follow up", SearchType.SIMILARITY, top_k=2
        )
        assert any(result.document.id == ids[1] for result in results)

    asyncio.run(run_test())


def test_search_with_filters(faiss_store: FaissVectorStore) -> None:
    async def run_test() -> None:
        documents = [
            Document(
                id="doc_math",
                content="Algebra foundations",
                metadata={"category": "math"},
            ),
            Document(
                id="doc_science",
                content="Cellular biology basics",
                metadata={"category": "science"},
            ),
        ]
        await faiss_store.add_documents(documents)

        results = await faiss_store.search(
            "foundations",
            SearchType.SIMILARITY,
            top_k=5,
            filters={"category": "math"},
        )

        assert len(results) == 1
        assert results[0].document.id == "doc_math"

    asyncio.run(run_test())


def test_update_document_replaces_embedding(faiss_store: FaissVectorStore) -> None:
    async def run_test() -> None:
        original = Document(id="doc_alpha", content="Alpha gene research")
        await faiss_store.add_documents([original])

        updated = Document(
            id="doc_alpha",
            content="Gamma protein analysis",
            metadata={"category": "science"},
        )
        update_result = await faiss_store.update_document(updated)
        assert update_result is True

        stored = await faiss_store.get_document("doc_alpha")
        assert stored is not None
        assert stored.content == "Gamma protein analysis"
        assert stored.metadata.get("category") == "science"

        results = await faiss_store.search(
            "Gamma protein analysis", SearchType.SIMILARITY, top_k=1
        )
        assert results and results[0].document.id == "doc_alpha"

    asyncio.run(run_test())
