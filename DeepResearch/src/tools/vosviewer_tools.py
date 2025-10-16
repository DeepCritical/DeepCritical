from __future__ import annotations

from typing import Any

from neo4j import GraphDatabase

from ..datatypes.neo4j_types import Neo4jConnectionConfig
from .base import ExecutionResult, ToolRunner, ToolSpec, registry


class VOSViewerExportTool(ToolRunner):
    def __init__(self, conn_cfg: Neo4jConnectionConfig | None = None):
        super().__init__(
            ToolSpec(
                name="vosviewer_export",
                description="Export co-author / keyword / citation networks for VOSviewer",
                inputs={
                    "network_type": "TEXT",
                    "limit": "INT",
                    "min_connections": "INT",
                },
                outputs={"graph": "JSON"},
            )
        )
        self._conn = conn_cfg

    def run(self, params: dict[str, Any]) -> ExecutionResult:
        ok, err = self.validate(params)
        if not ok:
            return ExecutionResult(success=False, error=err or "invalid params")
        if not self._conn:
            return ExecutionResult(
                success=False, error="Neo4j connection not configured"
            )

        network_type = params.get("network_type", "coauthor")
        limit = params.get("limit", 100)
        min_connections = params.get("min_connections", 1)

        try:
            driver = GraphDatabase.driver(
                self._conn.uri,
                auth=(self._conn.username, self._conn.password)
                if self._conn.username
                else None,
                encrypted=self._conn.encrypted,
            )

            with driver.session(database=self._conn.database) as session:
                if network_type == "coauthor":
                    graph = self._export_coauthor_network(
                        session, limit, min_connections
                    )
                elif network_type == "keyword":
                    graph = self._export_keyword_network(
                        session, limit, min_connections
                    )
                elif network_type == "citation":
                    graph = self._export_citation_network(
                        session, limit, min_connections
                    )
                else:
                    return ExecutionResult(
                        success=False,
                        error=f"Unsupported network type: {network_type}. Use 'coauthor', 'keyword', or 'citation'",
                    )

            driver.close()
            return ExecutionResult(success=True, data={"graph": graph})

        except Exception as e:
            return ExecutionResult(success=False, error=f"Network export failed: {e!s}")

    def _export_coauthor_network(self, session, limit: int, min_connections: int):
        """Export co-author network for VOSviewer."""
        # Get authors and their co-authorship relationships
        query = """
        MATCH (a1:Author)-[:AUTHORED]->(:Publication)<-[:AUTHORED]-(a2:Author)
        WHERE a1.id < a2.id
        WITH a1, a2, count(*) AS collaborations
        WHERE collaborations >= $min_connections
        RETURN a1.id AS source_id, a1.name AS source_name,
               a2.id AS target_id, a2.name AS target_name,
               collaborations AS weight
        ORDER BY collaborations DESC
        LIMIT $limit
        """

        result = session.run(query, limit=limit, min_connections=min_connections)

        nodes = {}
        edges = []

        for record in result:
            # Add source node
            source_id = record["source_id"]
            if source_id not in nodes:
                nodes[source_id] = {
                    "id": source_id,
                    "label": record["source_name"] or source_id,
                    "weight": 0,
                }

            # Add target node
            target_id = record["target_id"]
            if target_id not in nodes:
                nodes[target_id] = {
                    "id": target_id,
                    "label": record["target_name"] or target_id,
                    "weight": 0,
                }

            # Add edge
            edges.append(
                {
                    "source": source_id,
                    "target": target_id,
                    "weight": record["weight"],
                }
            )

            # Update node weights
            nodes[source_id]["weight"] += record["weight"]
            nodes[target_id]["weight"] += record["weight"]

        return {
            "nodes": list(nodes.values()),
            "edges": edges,
            "network_type": "coauthor",
        }

    def _export_keyword_network(self, session, limit: int, min_connections: int):
        """Export keyword co-occurrence network for VOSviewer."""
        # This is a simplified implementation - in reality, keywords need to be properly extracted
        # For now, return empty network with note
        return {
            "nodes": [],
            "edges": [],
            "network_type": "keyword",
            "note": "Keyword network requires keyword extraction implementation",
        }

    def _export_citation_network(self, session, limit: int, min_connections: int):
        """Export citation network for VOSviewer."""
        query = """
        MATCH (citing:Publication)-[:CITES]->(cited:Publication)
        WITH citing, cited, count(*) AS citations
        WHERE citations >= $min_connections
        RETURN citing.eid AS source_id, citing.title AS source_title,
               cited.eid AS target_id, cited.title AS target_title,
               citations AS weight
        ORDER BY citations DESC
        LIMIT $limit
        """

        result = session.run(query, limit=limit, min_connections=min_connections)

        nodes = {}
        edges = []

        for record in result:
            # Add source node
            source_id = record["source_id"]
            if source_id not in nodes:
                nodes[source_id] = {
                    "id": source_id,
                    "label": record["source_title"][:50] + "..."
                    if record["source_title"] and len(record["source_title"]) > 50
                    else record["source_title"] or source_id,
                    "weight": 0,
                }

            # Add target node
            target_id = record["target_id"]
            if target_id not in nodes:
                nodes[target_id] = {
                    "id": target_id,
                    "label": record["target_title"][:50] + "..."
                    if record["target_title"] and len(record["target_title"]) > 50
                    else record["target_title"] or target_id,
                    "weight": 0,
                }

            # Add edge
            edges.append(
                {
                    "source": source_id,
                    "target": target_id,
                    "weight": record["weight"],
                }
            )

            # Update node weights
            nodes[source_id]["weight"] += record["weight"]
            nodes[target_id]["weight"] += record["weight"]

        return {
            "nodes": list(nodes.values()),
            "edges": edges,
            "network_type": "citation",
        }


def _register() -> None:
    registry.register("vosviewer_export", lambda: VOSViewerExportTool())


_register()
