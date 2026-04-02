from __future__ import annotations

import pytest

from DeepResearch.src.datatypes.rag import Document, SearchResult
from DeepResearch.src.tools.mgrep.service import MgrepService


@pytest.mark.asyncio
async def test_service_index_search_sync_and_delete(
    tmp_path, mgrep_config, keyword_embeddings, in_memory_vector_store_factory
):
    repo_root = tmp_path
    (repo_root / "parser.py").write_text(
        "def build_parser():\n    return 'semantic parser search'\n",
        encoding="utf-8",
    )
    (repo_root / "guide.md").write_text(
        "# Guide\nworkflow search in markdown\n", encoding="utf-8"
    )

    service = MgrepService(
        repo_root=repo_root,
        config=mgrep_config,
        embeddings=keyword_embeddings,
        vector_store_factory=in_memory_vector_store_factory,
    )

    stats = await service.index()
    assert stats.indexed_file_count == 2
    assert stats.indexed_chunk_count >= 2
    assert stats.store_dir.endswith(".deepcritical/mgrep")

    search_response = await service.search("semantic parser", top_k=5)
    assert search_response.total_results >= 1
    assert search_response.results[0].relative_path == "parser.py"
    assert search_response.results[0].chunk_id.startswith("mgrep_")
    assert search_response.results[0].score > 0

    filtered_response = await service.search("workflow", top_k=5, path="guide")
    assert filtered_response.total_results == 1
    assert filtered_response.results[0].relative_path == "guide.md"

    smart_response = await service.smart_search("semantic-parser", top_k=5)
    assert len(smart_response.generated_queries) >= 2
    assert any(hit.relative_path == "parser.py" for hit in smart_response.results)

    (repo_root / "parser.py").write_text(
        "def build_parser():\n    return 'workflow engine config'\n",
        encoding="utf-8",
    )
    (repo_root / "guide.md").unlink()

    synced = await service.sync()
    assert synced.indexed_file_count == 1

    workflow_response = await service.search("workflow engine", top_k=5)
    assert workflow_response.total_results >= 1
    assert workflow_response.results[0].relative_path == "parser.py"

    deleted_response = await service.search("markdown", top_k=5)
    assert not any(hit.relative_path == "guide.md" for hit in deleted_response.results)


@pytest.mark.asyncio
async def test_smart_search_overfetches_once_per_query(tmp_path, mgrep_config):
    class RecordingVectorStore:
        def __init__(self):
            self.requested_top_k: list[int] = []

        async def search(self, query, search_type, top_k=10, **kwargs):
            self.requested_top_k.append(top_k)
            return [
                SearchResult(
                    document=Document(
                        id="mgrep_stub",
                        content="semantic parser",
                        metadata={
                            "path": str(tmp_path / "parser.py"),
                            "relative_path": "parser.py",
                            "language": "python",
                            "kind": "function",
                            "line_start": 1,
                            "line_end": 2,
                        },
                    ),
                    score=0.8,
                    rank=1,
                )
            ]

    config = mgrep_config.model_copy(update={"search_fetch_multiplier": 3})
    vector_store = RecordingVectorStore()
    service = MgrepService(
        repo_root=tmp_path,
        config=config,
        embeddings=object(),
        vector_store=vector_store,
    )

    response = await service.smart_search("semantic-parser", top_k=2)

    assert response.total_results == 1
    assert vector_store.requested_top_k
    assert set(vector_store.requested_top_k) == {6}


@pytest.mark.asyncio
async def test_sync_preserves_previous_index_when_updated_file_cannot_be_rechunked(
    monkeypatch,
    tmp_path,
    mgrep_config,
    keyword_embeddings,
    in_memory_vector_store_factory,
):
    parser_path = tmp_path / "parser.py"
    parser_path.write_text(
        "def build_parser():\n    return 'semantic parser search'\n",
        encoding="utf-8",
    )

    service = MgrepService(
        repo_root=tmp_path,
        config=mgrep_config,
        embeddings=keyword_embeddings,
        vector_store_factory=in_memory_vector_store_factory,
    )
    await service.index()

    parser_path.write_text(
        "def build_parser():\n    return 'workflow engine config'\n",
        encoding="utf-8",
    )

    original_extract = __import__(
        "DeepResearch.src.tools.mgrep.service",
        fromlist=["extract_chunks_from_file"],
    ).extract_chunks_from_file

    def failing_extract(path, repo_root, digest):
        if path == parser_path:
            raise OSError("file changed during sync")
        return original_extract(path, repo_root, digest)

    monkeypatch.setattr(
        "DeepResearch.src.tools.mgrep.service.extract_chunks_from_file",
        failing_extract,
    )

    stats = await service.sync()
    assert stats.indexed_file_count == 1
    assert stats.skipped_file_count >= 1

    previous_response = await service.search("semantic parser", top_k=5)
    assert previous_response.total_results >= 1
    assert previous_response.results[0].relative_path == "parser.py"
