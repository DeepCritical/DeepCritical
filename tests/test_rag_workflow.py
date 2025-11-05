"""End-to-end tests for the RAG workflow state machine."""

from __future__ import annotations

import asyncio
import importlib.util
import sys
import types
from dataclasses import dataclass, field
from pathlib import Path
from types import SimpleNamespace
from typing import Any

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
_ensure_package("DeepResearch.src.statemachines", SRC_ROOT / "statemachines")
_ensure_package("DeepResearch.src.agents", SRC_ROOT / "agents")
_ensure_package("DeepResearch.src.utils", SRC_ROOT / "utils")
_ensure_package("DeepResearch.datatypes", SRC_ROOT / "datatypes")

research_agent_stub = types.ModuleType("DeepResearch.src.agents.research_agent")
research_agent_stub.ResearchAgent = type("_ResearchAgentBase", (), {})
sys.modules["DeepResearch.src.agents.research_agent"] = research_agent_stub

rag_module = _load_module("DeepResearch.src.datatypes.rag", "datatypes/rag.py")
faiss_config_module = _load_module(
    "DeepResearch.src.vector_stores.faiss_config", "vector_stores/faiss_config.py"
)
faiss_vector_module = _load_module(
    "DeepResearch.src.vector_stores.faiss_vector_store", "vector_stores/faiss_vector_store.py"
)
_load_module("DeepResearch.src.vector_stores.faiss_config", "vector_stores/faiss_config.py")
_load_module(
    "DeepResearch.src.vector_stores.faiss_vector_store", "vector_stores/faiss_vector_store.py"
)
sys.modules["DeepResearch.src.faiss_config"] = sys.modules[
    "DeepResearch.src.vector_stores.faiss_config"
]
sys.modules["DeepResearch.src.faiss_vector_store"] = sys.modules[
    "DeepResearch.src.vector_stores.faiss_vector_store"
]
sys.modules.pop("DeepResearch.src.vector_stores", None)
_load_module("DeepResearch.src.vector_stores", "vector_stores/__init__.py")
_load_module("DeepResearch.src.utils.execution_status", "utils/execution_status.py")
workflow_module = _load_module(
    "DeepResearch.src.statemachines.rag_workflow", "statemachines/rag_workflow.py"
)

faiss_config_module = sys.modules["DeepResearch.src.vector_stores.faiss_config"]
faiss_vector_module = sys.modules["DeepResearch.src.vector_stores.faiss_vector_store"]

GenerateResponse = workflow_module.GenerateResponse
InitializeRAG = workflow_module.InitializeRAG
LoadDocuments = workflow_module.LoadDocuments
ProcessDocuments = workflow_module.ProcessDocuments
QueryRAG = workflow_module.QueryRAG
RAGState = workflow_module.RAGState
StoreDocuments = workflow_module.StoreDocuments


@dataclass
class DummyContext:
    state: RAGState
    _store: dict[str, Any] = field(default_factory=dict)

    def set(self, key: str, value: Any) -> None:
        self._store[key] = value

    def get(self, key: str, default: Any | None = None) -> Any | None:
        return self._store.get(key, default)


def test_rag_workflow_stores_and_queries(tmp_path) -> None:
    async def run_test() -> None:
        rag_config = {
            "embeddings": {
                "model_type": "custom",
                "model_name": "deterministic-test",
                "base_url": "http://localhost:8001",
                "num_dimensions": 8,
            },
            "llm": {
                "model_type": "custom",
                "model_name": "test-llm",
                "host": "localhost",
                "port": 8000,
            },
            "vector_store": {
                "store_type": "faiss",
                "embedding_dimension": 8,
                "index_path": str(tmp_path / "workflow.faiss"),
                "metadata_path": str(tmp_path / "workflow.json"),
            },
            "chunking": {"chunk_size": 64, "chunk_overlap": 8},
        }

        config = SimpleNamespace(rag=rag_config)
        state = RAGState(question="What is machine learning?", config=config)
        ctx = DummyContext(state)

        next_node = await asyncio.wait_for(InitializeRAG().run(ctx), timeout=5)
        assert isinstance(next_node, LoadDocuments)

        next_node = await asyncio.wait_for(next_node.run(ctx), timeout=5)
        assert isinstance(next_node, ProcessDocuments)

        next_node = await asyncio.wait_for(next_node.run(ctx), timeout=5)
        assert isinstance(next_node, StoreDocuments)
        assert ctx.state.documents

        next_node = await asyncio.wait_for(next_node.run(ctx), timeout=5)
        assert ctx.state.errors == [], ctx.state.errors
        assert isinstance(next_node, QueryRAG)

        rag_system = ctx.get("rag_system")
        assert rag_system is not None and rag_system.vector_store is not None

        next_node = await asyncio.wait_for(next_node.run(ctx), timeout=5)
        assert isinstance(next_node, GenerateResponse)

        assert ctx.state.rag_response is not None
        assert ctx.state.rag_response.retrieved_documents
        assert any("stored_" in step for step in ctx.state.processing_steps)

    asyncio.run(run_test())
