from __future__ import annotations

from ..datatypes.neo4j_types import VectorIndexConfig
from ..prompts.neo4j_queries import CREATE_VECTOR_INDEX
from .neo4j_connection import neo4j_session


def setup_vector_index(conn_cfg, index_cfg: VectorIndexConfig) -> None:
    with neo4j_session(conn_cfg) as session:
        session.run(
            CREATE_VECTOR_INDEX,
            {
                "index_name": index_cfg.index_name,
                "label": index_cfg.node_label,
                "prop": index_cfg.vector_property,
                "dims": index_cfg.dimensions,
                "metric": index_cfg.metric.value,
            },
        )
