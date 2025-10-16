from __future__ import annotations

from contextlib import contextmanager

from neo4j import GraphDatabase

from ..datatypes.neo4j_types import Neo4jConnectionConfig


@contextmanager
def neo4j_session(cfg: Neo4jConnectionConfig):
    driver = GraphDatabase.driver(
        cfg.uri,
        auth=(cfg.username, cfg.password) if cfg.username else None,
        encrypted=cfg.encrypted,
    )
    try:
        with driver.session(database=cfg.database) as session:
            yield session
    finally:
        driver.close()
