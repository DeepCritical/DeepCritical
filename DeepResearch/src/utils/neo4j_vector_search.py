"""
Neo4j vector search utilities for DeepCritical.

This module provides advanced vector search functionality for Neo4j databases,
including similarity search, hybrid search, and filtered search capabilities.
"""

from __future__ import annotations

import asyncio
from typing import Any, Dict, List, Optional

from neo4j import GraphDatabase

from ..datatypes.neo4j_types import Neo4jConnectionConfig, Neo4jVectorStoreConfig
from ..datatypes.rag import Embeddings as EmbeddingsInterface
from ..datatypes.rag import SearchResult
from ..prompts.neo4j_queries import (
    VECTOR_HYBRID_SEARCH,
    VECTOR_SEARCH_RANGE_FILTER,
    VECTOR_SEARCH_WITH_FILTERS,
    VECTOR_SIMILARITY_SEARCH,
)


class Neo4jVectorSearch:
    """Advanced vector search functionality for Neo4j."""

    def __init__(self, config: Neo4jVectorStoreConfig, embeddings: EmbeddingsInterface):
        """Initialize vector search.

        Args:
            config: Neo4j vector store configuration
            embeddings: Embeddings interface for generating vectors
        """
        self.config = config
        self.embeddings = embeddings

        # Initialize Neo4j driver
        self.driver = GraphDatabase.driver(
            config.connection.uri,
            auth=(config.connection.username, config.connection.password)
            if config.connection.username
            else None,
            encrypted=config.connection.encrypted,
        )

    def __del__(self):
        """Clean up Neo4j driver connection."""
        if hasattr(self, "driver"):
            self.driver.close()

    async def search_similar(
        self, query: str, top_k: int = 10, filters: dict[str, Any] | None = None
    ) -> list[SearchResult]:
        """Perform similarity search using vector embeddings.

        Args:
            query: Search query text
            top_k: Number of results to return
            filters: Optional metadata filters

        Returns:
            List of search results
        """
        print(f"--- VECTOR SIMILARITY SEARCH: '{query}' ---")

        # Generate embedding for query
        query_embedding = await self.embeddings.vectorize_query(query)

        with self.driver.session(database=self.config.connection.database) as session:
            if filters:
                # Use filtered search
                filter_key = list(filters.keys())[0]
                filter_value = filters[filter_key]

                result = session.run(
                    VECTOR_SEARCH_WITH_FILTERS,
                    {
                        "index_name": self.config.index.index_name,
                        "top_k": min(top_k, self.config.search_defaults.max_results),
                        "query_embedding": query_embedding,
                        "filter_key": filter_key,
                        "filter_value": filter_value,
                        "limit": min(top_k, self.config.search_defaults.max_results),
                    },
                )
            else:
                # Use basic similarity search
                result = session.run(
                    VECTOR_SIMILARITY_SEARCH,
                    {
                        "index_name": self.config.index.index_name,
                        "top_k": min(top_k, self.config.search_defaults.max_results),
                        "query_embedding": query_embedding,
                        "limit": min(top_k, self.config.search_defaults.max_results),
                    },
                )

            search_results = []
            for record in result:
                # Create SearchResult object
                doc_data = {
                    "id": record["id"],
                    "content": record["content"],
                    "metadata": record["metadata"],
                }

                # Create a basic Document-like object
                from ..datatypes.rag import Document

                doc = Document(**doc_data)

                search_result = SearchResult(
                    document=doc, score=record["score"], rank=len(search_results) + 1
                )
                search_results.append(search_result)

            return search_results

    async def search_with_range_filter(
        self,
        query: str,
        range_key: str,
        min_value: float,
        max_value: float,
        top_k: int = 10,
    ) -> list[SearchResult]:
        """Perform vector search with range filtering.

        Args:
            query: Search query text
            range_key: Metadata key for range filtering
            min_value: Minimum value for range
            max_value: Maximum value for range
            top_k: Number of results to return

        Returns:
            List of search results
        """
        print(
            f"--- VECTOR RANGE SEARCH: '{query}' (filter: {range_key} {min_value}-{max_value}) ---"
        )

        # Generate embedding for query
        query_embedding = await self.embeddings.vectorize_query(query)

        with self.driver.session(database=self.config.connection.database) as session:
            result = session.run(
                VECTOR_SEARCH_RANGE_FILTER,
                {
                    "index_name": self.config.index.index_name,
                    "top_k": min(top_k, self.config.search_defaults.max_results),
                    "query_embedding": query_embedding,
                    "range_key": range_key,
                    "min_value": min_value,
                    "max_value": max_value,
                    "limit": min(top_k, self.config.search_defaults.max_results),
                },
            )

            search_results = []
            for record in result:
                doc_data = {
                    "id": record["id"],
                    "content": record["content"],
                    "metadata": record["metadata"],
                }

                from ..datatypes.rag import Document

                doc = Document(**doc_data)

                search_result = SearchResult(
                    document=doc, score=record["score"], rank=len(search_results) + 1
                )
                search_results.append(search_result)

            return search_results

    async def hybrid_search(
        self,
        query: str,
        vector_weight: float = 0.6,
        citation_weight: float = 0.2,
        importance_weight: float = 0.2,
        top_k: int = 10,
    ) -> list[SearchResult]:
        """Perform hybrid search combining vector similarity with other metrics.

        Args:
            query: Search query text
            vector_weight: Weight for vector similarity (0-1)
            citation_weight: Weight for citation count (0-1)
            importance_weight: Weight for importance score (0-1)
            top_k: Number of results to return

        Returns:
            List of search results with hybrid scores
        """
        print(f"--- HYBRID SEARCH: '{query}' ---")
        print(
            f"Weights: Vector={vector_weight}, Citations={citation_weight}, Importance={importance_weight}"
        )

        # Generate embedding for query
        query_embedding = await self.embeddings.vectorize_query(query)

        with self.driver.session(database=self.config.connection.database) as session:
            result = session.run(
                VECTOR_HYBRID_SEARCH,
                {
                    "index_name": self.config.index.index_name,
                    "top_k": min(top_k, self.config.search_defaults.max_results),
                    "query_embedding": query_embedding,
                    "vector_weight": vector_weight,
                    "citation_weight": citation_weight,
                    "importance_weight": importance_weight,
                    "limit": min(top_k, self.config.search_defaults.max_results),
                },
            )

            search_results = []
            for record in result:
                doc_data = {
                    "id": record["id"],
                    "content": record["content"],
                    "metadata": record["metadata"],
                }

                from ..datatypes.rag import Document

                doc = Document(**doc_data)

                # Use hybrid score as the primary score
                search_result = SearchResult(
                    document=doc,
                    score=record["hybrid_score"],
                    rank=len(search_results) + 1,
                )

                # Add additional score information to metadata
                if search_result.document.metadata is None:
                    search_result.document.metadata = {}

                search_result.document.metadata.update(
                    {
                        "vector_score": record["vector_score"],
                        "citation_score": record["citation_score"],
                        "importance_score": record["importance_score"],
                        "hybrid_score": record["hybrid_score"],
                    }
                )

                search_results.append(search_result)

            return search_results

    async def batch_search(
        self, queries: list[str], top_k: int = 10, search_type: str = "similarity"
    ) -> dict[str, list[SearchResult]]:
        """Perform batch search for multiple queries.

        Args:
            queries: List of search queries
            top_k: Number of results per query
            search_type: Type of search ('similarity', 'hybrid')

        Returns:
            Dictionary mapping queries to search results
        """
        print(f"--- BATCH SEARCH: {len(queries)} queries ---")

        results = {}

        for query in queries:
            print(f"Searching: {query}")

            if search_type == "hybrid":
                query_results = await self.hybrid_search(query, top_k=top_k)
            else:
                query_results = await self.search_similar(query, top_k=top_k)

            results[query] = query_results

        return results

    def get_search_statistics(self) -> dict[str, Any]:
        """Get statistics about the search index and data.

        Returns:
            Dictionary with search statistics
        """
        print("--- SEARCH STATISTICS ---")

        stats = {}

        with self.driver.session(database=self.config.connection.database) as session:
            # Get vector index information
            try:
                result = session.run(
                    "SHOW INDEXES WHERE name = $index_name",
                    {"index_name": self.config.index.index_name},
                )
                record = result.single()

                if record:
                    stats["index_info"] = {
                        "name": record.get("name"),
                        "state": record.get("state"),
                        "type": record.get("type"),
                        "labels": record.get("labelsOrTypes"),
                        "properties": record.get("properties"),
                    }
                else:
                    stats["index_info"] = {"error": "Index not found"}
            except Exception as e:
                stats["index_info"] = {"error": str(e)}

            # Get data statistics
            result = session.run(f"""
                MATCH (n:{self.config.index.node_label})
                WHERE n.{self.config.index.vector_property} IS NOT NULL
                RETURN count(n) AS nodes_with_vectors,
                       avg(size(n.{self.config.index.vector_property})) AS avg_vector_size
            """)

            record = result.single()
            if record:
                stats["data_stats"] = {
                    "nodes_with_vectors": record["nodes_with_vectors"],
                    "avg_vector_size": record["avg_vector_size"],
                }

            # Get search configuration
            stats["search_config"] = {
                "index_name": self.config.index.index_name,
                "node_label": self.config.index.node_label,
                "vector_property": self.config.index.vector_property,
                "dimensions": self.config.index.dimensions,
                "similarity_metric": self.config.index.metric.value,
                "default_top_k": self.config.search_defaults.top_k,
                "max_results": self.config.search_defaults.max_results,
            }

        return stats

    async def validate_search_functionality(self) -> dict[str, Any]:
        """Validate that search functionality is working correctly.

        Returns:
            Dictionary with validation results
        """
        print("--- VALIDATING SEARCH FUNCTIONALITY ---")

        validation: dict[str, Any] = {
            "index_exists": False,
            "has_vector_data": False,
            "search_works": False,
            "errors": [],
        }

        try:
            # Check if index exists
            stats = self.get_search_statistics()
            if "error" not in stats.get("index_info", {}):
                validation["index_exists"] = True
                if stats["index_info"].get("state") == "ONLINE":
                    validation["index_online"] = True

            # Check if there's vector data
            if stats.get("data_stats", {}).get("nodes_with_vectors", 0) > 0:
                validation["has_vector_data"] = True

            # Try a test search
            if validation["index_exists"] and validation["has_vector_data"]:
                try:
                    test_results = await self.search_similar("test query", top_k=1)
                    if test_results:
                        validation["search_works"] = True
                except Exception as e:
                    validation["errors"].append(f"Search test failed: {e}")  # type: ignore

        except Exception as e:
            validation["errors"].append(f"Validation failed: {e}")  # type: ignore

        # Print validation results
        print("Validation Results:")
        for key, value in validation.items():
            if key != "errors":
                status = "✓" if value else "✗"
                print(f"  {key}: {status}")

        if validation["errors"]:
            print("Errors:")
            for error in validation["errors"]:  # type: ignore
                print(f"  - {error}")

        return validation


async def perform_vector_search(
    neo4j_config: Neo4jConnectionConfig,
    embeddings: EmbeddingsInterface,
    query: str,
    search_type: str = "similarity",
    top_k: int = 10,
    **search_params,
) -> list[SearchResult]:
    """Perform vector search with Neo4j.

    Args:
        neo4j_config: Neo4j connection configuration
        embeddings: Embeddings interface
        query: Search query
        search_type: Type of search ('similarity', 'hybrid', 'range')
        top_k: Number of results to return
        **search_params: Additional search parameters

    Returns:
        List of search results
    """
    # Create vector store config (minimal for search)
    from ..datatypes.neo4j_types import VectorIndexConfig, VectorIndexMetric

    vector_config = VectorIndexConfig(
        index_name=search_params.get("index_name", "publication_abstract_vector"),
        node_label="Publication",
        vector_property="abstract_embedding",
        dimensions=384,  # Default
        metric=VectorIndexMetric.COSINE,
    )

    store_config = Neo4jVectorStoreConfig(connection=neo4j_config, index=vector_config)

    search_engine = Neo4jVectorSearch(store_config, embeddings)

    try:
        if search_type == "hybrid":
            return await search_engine.hybrid_search(
                query,
                vector_weight=search_params.get("vector_weight", 0.6),
                citation_weight=search_params.get("citation_weight", 0.2),
                importance_weight=search_params.get("importance_weight", 0.2),
                top_k=top_k,
            )
        if search_type == "range":
            return await search_engine.search_with_range_filter(
                query,
                range_key=search_params["range_key"],
                min_value=search_params["min_value"],
                max_value=search_params["max_value"],
                top_k=top_k,
            )
        # similarity
        return await search_engine.search_similar(
            query, top_k=top_k, filters=search_params.get("filters")
        )
    finally:
        # Cleanup happens in __del__
        pass
