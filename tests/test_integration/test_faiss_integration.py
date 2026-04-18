"""Integration tests for FAISS vector store with embeddings."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import textwrap

import pytest


@pytest.fixture
def temp_faiss_paths():
    """Create temporary paths for FAISS index and data."""
    with tempfile.TemporaryDirectory() as tmpdir:
        index_path = os.path.join(tmpdir, "test_faiss.index")
        data_path = os.path.join(tmpdir, "test_faiss_docs.pkl")
        yield index_path, data_path


def _run_integration_subprocess(script: str) -> dict[str, object]:
    completed = subprocess.run(
        [sys.executable, "-c", script],
        check=True,
        capture_output=True,
        text=True,
    )
    return json.loads(completed.stdout)


def test_persistence(temp_faiss_paths):
    """Test: Add docs, save, restart, search - data persists."""
    index_path, data_path = temp_faiss_paths
    script = textwrap.dedent(
        f"""
        import asyncio
        import json
        import os

        from DeepResearch.src.datatypes.embeddings_factory import create_embeddings
        from DeepResearch.src.datatypes.rag import (
            Document,
            EmbeddingModelType,
            EmbeddingsConfig,
            SearchType,
            VectorStoreType,
        )
        from DeepResearch.src.vector_stores import create_vector_store
        from DeepResearch.src.vector_stores.faiss_config import FAISSVectorStoreConfig

        async def main():
            embeddings = create_embeddings(
                EmbeddingsConfig(
                    model_type=EmbeddingModelType.SENTENCE_TRANSFORMERS,
                    model_name="all-MiniLM-L6-v2",
                    num_dimensions=384,
                    batch_size=32,
                    device="cpu",
                )
            )
            config = FAISSVectorStoreConfig(
                store_type=VectorStoreType.FAISS,
                embedding_dimension=384,
                index_path={index_path!r},
                data_path={data_path!r},
            )

            store = create_vector_store(config, embeddings)
            docs = [
                Document(id="doc1", content="The quick brown fox"),
                Document(id="doc2", content="jumps over the lazy dog"),
                Document(id="doc3", content="machine learning embeddings"),
            ]
            doc_ids = await store.add_documents(docs)

            store2 = create_vector_store(config, embeddings)
            results = await store2.search(
                "machine learning",
                search_type=SearchType.SIMILARITY,
                top_k=1,
            )

            print(
                json.dumps(
                    {{
                        "doc_ids": doc_ids,
                        "index_exists": os.path.exists({index_path!r}),
                        "data_exists": os.path.exists({data_path!r}),
                        "result_count": len(results),
                        "top_id": results[0].document.id if results else None,
                        "top_content": results[0].document.content if results else None,
                    }}
                )
            )

        asyncio.run(main())
        """
    )

    payload = _run_integration_subprocess(script)

    assert len(payload["doc_ids"]) == 3
    assert payload["index_exists"] is True
    assert payload["data_exists"] is True
    assert payload["result_count"] == 1
    assert payload["top_id"] == "doc3"
    assert "machine learning" in payload["top_content"]


def test_determinism(temp_faiss_paths):
    """Test: Same doc IDs -> Same internal IDs (deterministic hashing)."""
    index_path, data_path = temp_faiss_paths
    script = textwrap.dedent(
        f"""
        import asyncio
        import json

        from DeepResearch.src.datatypes.rag import Document, VectorStoreType
        from DeepResearch.src.vector_stores import create_vector_store
        from DeepResearch.src.vector_stores.faiss_config import FAISSVectorStoreConfig
        from DeepResearch.src.vector_stores.faiss_vector_store import _stable_hash

        class DeterministicEmbeddings:
            async def vectorize_documents(self, document_chunks):
                return [
                    [float(len(chunk)), float(index + 1)]
                    for index, chunk in enumerate(document_chunks)
                ]

            async def vectorize_query(self, text):
                return [float(len(text)), 1.0]

        async def main():
            embeddings = DeterministicEmbeddings()
            config = FAISSVectorStoreConfig(
                store_type=VectorStoreType.FAISS,
                embedding_dimension=2,
                index_path={index_path!r},
                data_path={data_path!r},
            )

            store = create_vector_store(config, embeddings)
            await store.add_documents(
                [Document(id="stable_id_123", content="test content")]
            )
            hash1 = _stable_hash("stable_id_123")

            store2 = create_vector_store(config, embeddings)
            await store2.add_documents(
                [Document(id="stable_id_123", content="different content same id")]
            )
            hash2 = _stable_hash("stable_id_123")

            print(
                json.dumps(
                    {{
                        "hash1": hash1,
                        "hash2": hash2,
                        "id_map_value": store2.id_map.get(hash1),
                        "doc_ids": getattr(store2, "doc_ids", []),
                    }}
                )
            )

        asyncio.run(main())
        """
    )

    payload = _run_integration_subprocess(script)

    assert payload["hash1"] == payload["hash2"]
    assert payload["id_map_value"] == "stable_id_123"
    assert payload["doc_ids"] == ["stable_id_123"]
