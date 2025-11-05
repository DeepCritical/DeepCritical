"""Tests for the asynchronous RAG agent integration."""

from __future__ import annotations

import asyncio
import importlib.util
import sys
import types
from pathlib import Path

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
_ensure_package("DeepResearch.src.agents", SRC_ROOT / "agents")
_ensure_package("DeepResearch.datatypes", SRC_ROOT / "datatypes")

_load_module("DeepResearch.src.vector_stores.faiss_config", "vector_stores/faiss_config.py")
_load_module("DeepResearch.src.vector_stores.faiss_vector_store", "vector_stores/faiss_vector_store.py")
sys.modules["DeepResearch.src.faiss_config"] = sys.modules[
    "DeepResearch.src.vector_stores.faiss_config"
]
sys.modules["DeepResearch.src.faiss_vector_store"] = sys.modules[
    "DeepResearch.src.vector_stores.faiss_vector_store"
]
sys.modules.pop("DeepResearch.src.vector_stores", None)
_load_module("DeepResearch.src.vector_stores", "vector_stores/__init__.py")

research_agent_stub = types.ModuleType("DeepResearch.src.agents.research_agent")


class _ResearchAgentBase:
    def __init__(self, *args, **kwargs):
        self.cfg = kwargs.get("cfg")


research_agent_stub.ResearchAgent = _ResearchAgentBase
sys.modules["DeepResearch.src.agents.research_agent"] = research_agent_stub

rag_module = _load_module("DeepResearch.src.datatypes.rag", "datatypes/rag.py")
faiss_config_module = sys.modules["DeepResearch.src.vector_stores.faiss_config"]
faiss_vector_module = sys.modules["DeepResearch.src.vector_stores.faiss_vector_store"]
rag_agent_module = _load_module(
    "DeepResearch.src.agents.rag_agent", "agents/rag_agent.py"
)

Document = rag_module.Document
EmbeddingModelType = rag_module.EmbeddingModelType
EmbeddingsConfig = rag_module.EmbeddingsConfig
RAGQuery = rag_module.RAGQuery
SearchType = rag_module.SearchType
DeterministicEmbeddings = _load_module(
    "DeepResearch.src.datatypes.vllm_integration", "datatypes/vllm_integration.py"
).DeterministicEmbeddings
FaissVectorStoreConfig = faiss_config_module.FaissVectorStoreConfig
FaissVectorStore = faiss_vector_module.FaissVectorStore
RAGAgent = rag_agent_module.RAGAgent


@pytest.fixture()
def embeddings() -> DeterministicEmbeddings:
    config = EmbeddingsConfig(
        model_type=EmbeddingModelType.CUSTOM,
        model_name="deterministic-test",
        base_url="http://localhost:8001",
        num_dimensions=8,
    )
    return DeterministicEmbeddings(config)


@pytest.fixture()
def faiss_store(tmp_path, embeddings: DeterministicEmbeddings) -> FaissVectorStore:
    config = FaissVectorStoreConfig(
        index_path=str(tmp_path / "agent_index.faiss"),
        metadata_path=str(tmp_path / "agent_metadata.json"),
        embedding_dimension=embeddings.num_dimensions,
        distance_metric="cosine",
    )
    store = FaissVectorStore(config, embeddings)
    yield store
    asyncio.run(store.close())


def test_rag_agent_adds_and_queries_documents(
    embeddings: DeterministicEmbeddings, faiss_store: FaissVectorStore
) -> None:
    async def run_test() -> None:
        agent = RAGAgent(embeddings=embeddings, vector_store=faiss_store)

        documents = [
            Document(id="doc_alpha", content="Alpha gene research"),
            Document(id="doc_beta", content="Beta cell study"),
        ]

        add_result = await agent.add_documents(documents)
        assert add_result is True

        query = RAGQuery(
            text="Alpha gene research",
            search_type=SearchType.SIMILARITY,
            top_k=2,
        )

        response = await agent.execute_rag_query(query)

        assert response.retrieved_documents
        assert response.retrieved_documents[0].document.id == "doc_alpha"
        assert "Alpha gene research" in response.generated_answer

    asyncio.run(run_test())
