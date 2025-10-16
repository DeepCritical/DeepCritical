from __future__ import annotations

from typing import Any

from neo4j import GraphDatabase

from ..datatypes.neo4j_types import Neo4jConnectionConfig
from ..datatypes.rag import SearchType
from .base import ExecutionResult, ToolRunner, ToolSpec, registry


class Neo4jVectorSearchTool(ToolRunner):
    def __init__(
        self,
        conn_cfg: Neo4jConnectionConfig | None = None,
        index_name: str | None = None,
    ):
        super().__init__(
            ToolSpec(
                name="neo4j_vector_search",
                description="Vector similarity search over Neo4j native vector index",
                inputs={
                    "query": "TEXT",
                    "top_k": "INT",
                },
                outputs={"results": "JSON"},
            )
        )
        self._conn = conn_cfg
        self._index = index_name

    def run(self, params: dict[str, Any]) -> ExecutionResult:
        ok, err = self.validate(params)
        if not ok:
            return ExecutionResult(success=False, error=err or "invalid params")
        if not self._conn or not self._index:
            return ExecutionResult(success=False, error="connection not configured")

        from ..datatypes.rag import EmbeddingModelType, EmbeddingsConfig
        from ..datatypes.vllm_integration import (
            VLLMEmbeddings,
        )  # reuse existing embedding wrapper if available

        # For simplicity, use sentence-transformers via VLLMEmbeddings if configured, else fallback to OpenAI
        emb = VLLMEmbeddings(
            EmbeddingsConfig(
                model_type=EmbeddingModelType.SENTENCE_TRANSFORMERS,
                model_name="sentence-transformers/all-MiniLM-L6-v2",
                num_dimensions=384,
            )
        )
        qvec = emb.vectorize_query_sync(params["query"])  # type: ignore[arg-type]

        driver = GraphDatabase.driver(
            self._conn.uri,
            auth=(self._conn.username, self._conn.password)
            if self._conn.username
            else None,
            encrypted=self._conn.encrypted,
        )
        try:
            with driver.session(database=self._conn.database) as session:
                rs = session.run(
                    "CALL db.index.vector.queryNodes($index, $k, $q) YIELD node, score "
                    "RETURN node, score ORDER BY score DESC",
                    {
                        "index": self._index,
                        "k": int(params.get("top_k", 10)),
                        "q": qvec,
                    },
                )
                out = []
                for rec in rs:
                    node = rec["node"]
                    out.append(
                        {
                            "id": node.get("id"),
                            "content": node.get("content", ""),
                            "metadata": node.get("metadata", {}),
                            "score": float(rec["score"]),
                        }
                    )
                return ExecutionResult(success=True, data={"results": out})
        finally:
            driver.close()


def _register() -> None:
    registry.register("neo4j_vector_search", lambda: Neo4jVectorSearchTool())


_register()
