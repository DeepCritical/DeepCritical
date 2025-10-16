"""
Neo4j vector search CLI utilities for DeepCritical.

This module provides command-line interface utilities for performing
vector searches in Neo4j databases with various filtering and display options.
"""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

from neo4j import GraphDatabase

from ..datatypes.neo4j_types import Neo4jConnectionConfig


def connect_to_neo4j(config: Neo4jConnectionConfig) -> Any | None:
    """Connect to Neo4j database.

    Args:
        config: Neo4j connection configuration

    Returns:
        Neo4j driver instance or None if connection fails
    """
    try:
        driver = GraphDatabase.driver(
            config.uri,
            auth=(config.username, config.password) if config.username else None,
            encrypted=config.encrypted,
        )
        # Test connection
        with driver.session(database=config.database) as session:
            session.run("RETURN 1")
        return driver
    except Exception as e:
        print(f"Error connecting to Neo4j: {e}")
        return None


def search_publications(
    driver: Any,
    database: str,
    query: str,
    index_name: str = "publication_abstract_vector",
    top_k: int = 10,
    year_filter: int | None = None,
    cited_by_filter: int | None = None,
    include_abstracts: bool = False,
) -> list[dict[str, Any]]:
    """Search publications using vector similarity.

    Args:
        driver: Neo4j driver
        database: Database name
        query: Search query text
        index_name: Vector index name
        top_k: Number of results to return
        year_filter: Filter by publication year
        cited_by_filter: Filter by minimum citation count
        include_abstracts: Whether to include full abstracts in results

    Returns:
        List of search results
    """
    print(f"--- SEARCHING PUBLICATIONS: '{query}' ---")
    print(f"Index: {index_name}, Top-K: {top_k}")

    # For now, we'll use a simple text-based search since we don't have
    # the embeddings interface here. In a real implementation, this would
    # generate embeddings for the query.

    # Placeholder: Use keyword-based search as fallback
    keywords = query.lower().split()

    with driver.session(database=database) as session:
        # Build search query
        cypher_query = """
            MATCH (p:Publication)
            WHERE p.abstract IS NOT NULL
        """

        # Add filters
        params = {"top_k": top_k}

        if year_filter:
            cypher_query += " AND toInteger(p.year) >= $year_filter"
            params["year_filter"] = year_filter

        if cited_by_filter:
            cypher_query += " AND toInteger(p.citedBy) >= $cited_by_filter"
            params["cited_by_filter"] = cited_by_filter

        # Add text matching for keywords
        if keywords:
            keyword_conditions = []
            for i, keyword in enumerate(keywords[:3]):  # Limit to 3 keywords
                keyword_conditions.append(f"toLower(p.title) CONTAINS $keyword_{i}")
                keyword_conditions.append(f"toLower(p.abstract) CONTAINS $keyword_{i}")
                params[f"keyword_{i}"] = keyword

            if keyword_conditions:
                cypher_query += f" AND ({' OR '.join(keyword_conditions)})"

        # Order by relevance (citations as proxy)
        cypher_query += """
            RETURN p.eid AS eid,
                   p.title AS title,
                   p.year AS year,
                   p.citedBy AS citations,
                   p.doi AS doi
        """

        if include_abstracts:
            cypher_query += ", left(p.abstract, 200) AS abstract_preview"

        cypher_query += """
            ORDER BY toInteger(p.citedBy) DESC, toInteger(p.year) DESC
            LIMIT $top_k
        """

        result = session.run(cypher_query, params)

        results = []
        for i, record in enumerate(result, 1):
            result_dict = {
                "rank": i,
                "eid": record["eid"],
                "title": record["title"],
                "year": record["year"],
                "citations": record["citations"],
                "doi": record["doi"],
            }

            if include_abstracts and "abstract_preview" in record:
                result_dict["abstract_preview"] = record["abstract_preview"]

            results.append(result_dict)

        return results


def search_documents(
    driver: Any,
    database: str,
    query: str,
    index_name: str = "document_content_vector",
    top_k: int = 10,
    content_filter: str | None = None,
) -> list[dict[str, Any]]:
    """Search documents using vector similarity.

    Args:
        driver: Neo4j driver
        database: Database name
        query: Search query text
        index_name: Vector index name
        top_k: Number of results to return
        content_filter: Filter by content substring

    Returns:
        List of search results
    """
    print(f"--- SEARCHING DOCUMENTS: '{query}' ---")
    print(f"Index: {index_name}, Top-K: {top_k}")

    # Placeholder implementation using text search
    keywords = query.lower().split()

    with driver.session(database=database) as session:
        cypher_query = """
            MATCH (d:Document)
            WHERE d.content IS NOT NULL
        """

        params = {"top_k": top_k}

        # Add content filter
        if content_filter:
            cypher_query += " AND toLower(d.content) CONTAINS $content_filter"
            params["content_filter"] = content_filter.lower()

        # Add keyword matching
        if keywords:
            keyword_conditions = []
            for i, keyword in enumerate(keywords[:3]):
                keyword_conditions.append(f"toLower(d.content) CONTAINS $keyword_{i}")
                params[f"keyword_{i}"] = keyword

            if keyword_conditions:
                cypher_query += f" AND ({' OR '.join(keyword_conditions)})"

        cypher_query += """
            RETURN d.id AS id,
                   left(d.content, 100) AS content_preview,
                   d.created_at AS created_at,
                   size(d.content) AS content_length
            ORDER BY d.created_at DESC
            LIMIT $top_k
        """

        result = session.run(cypher_query, params)

        results = []
        for i, record in enumerate(result, 1):
            results.append(
                {
                    "rank": i,
                    "id": record["id"],
                    "content_preview": record["content_preview"],
                    "created_at": str(record["created_at"])
                    if record["created_at"]
                    else None,
                    "content_length": record["content_length"],
                }
            )

        return results


def display_search_results(
    results: list[dict[str, Any]], result_type: str = "publication"
) -> None:
    """Display search results in a formatted way.

    Args:
        results: Search results to display
        result_type: Type of results ('publication' or 'document')
    """
    if not results:
        print("No results found.")
        return

    print(f"\n📊 Found {len(results)} {result_type}s:\n")

    for result in results:
        print(f"#{result['rank']}")

        if result_type == "publication":
            print(f"  Title: {result['title']}")
            print(f"  Year: {result.get('year', 'Unknown')}")
            print(f"  Citations: {result.get('citations', 0)}")
            if result.get("doi"):
                print(f"  DOI: {result['doi']}")
            if result.get("abstract_preview"):
                print(f"  Abstract: {result['abstract_preview']}...")
        elif result_type == "document":
            print(f"  ID: {result['id']}")
            print(f"  Content: {result['content_preview']}...")
            print(f"  Created: {result.get('created_at', 'Unknown')}")
            print(f"  Length: {result['content_length']} chars")

        print()  # Empty line between results


def interactive_search(
    neo4j_config: Neo4jConnectionConfig,
    search_type: str = "publication",
    index_name: str | None = None,
) -> None:
    """Run an interactive search session.

    Args:
        neo4j_config: Neo4j connection configuration
        search_type: Type of search ('publication' or 'document')
        index_name: Vector index name (optional)
    """
    print("🔍 Neo4j Vector Search CLI")
    print("=" * 40)

    # Connect to Neo4j
    driver = connect_to_neo4j(neo4j_config)
    if driver is None:
        print("Failed to connect to Neo4j")
        return

    try:
        # Set defaults
        if index_name is None:
            if search_type == "publication":
                index_name = "publication_abstract_vector"
            else:
                index_name = "document_content_vector"

        while True:
            print(f"\nCurrent search type: {search_type} (index: {index_name})")
            print(
                "Commands: 'search <query>', 'type <publication|document>', 'index <name>', 'quit'"
            )

            try:
                command = input("\n> ").strip()

                if not command:
                    continue

                if command.lower() == "quit":
                    break

                parts = command.split(maxsplit=1)
                cmd = parts[0].lower()

                if cmd == "search" and len(parts) > 1:
                    query = parts[1]

                    if search_type == "publication":
                        results = search_publications(
                            driver, neo4j_config.database, query, index_name
                        )
                        display_search_results(results, "publication")
                    else:
                        results = search_documents(
                            driver, neo4j_config.database, query, index_name
                        )
                        display_search_results(results, "document")

                elif cmd == "type" and len(parts) > 1:
                    new_type = parts[1].lower()
                    if new_type in ["publication", "document"]:
                        search_type = new_type
                        if index_name is None or index_name.startswith(
                            "publication" if new_type == "document" else "document"
                        ):
                            index_name = f"{new_type}_content_vector"
                        print(f"Switched to {search_type} search")
                    else:
                        print("Invalid type. Use 'publication' or 'document'")

                elif cmd == "index" and len(parts) > 1:
                    index_name = parts[1]
                    print(f"Switched to index: {index_name}")

                else:
                    print(
                        "Unknown command. Use 'search <query>', 'type <type>', 'index <name>', or 'quit'"
                    )

            except KeyboardInterrupt:
                print("\nInterrupted. Type 'quit' to exit.")
            except EOFError:
                break

    finally:
        driver.close()
        print("Neo4j connection closed")


def batch_search_publications(
    neo4j_config: Neo4jConnectionConfig,
    queries: list[str],
    output_file: str | None = None,
    **search_kwargs,
) -> dict[str, list[dict[str, Any]]]:
    """Perform batch search for multiple queries.

    Args:
        neo4j_config: Neo4j connection configuration
        queries: List of search queries
        output_file: File to save results (optional)
        **search_kwargs: Additional search parameters

    Returns:
        Dictionary mapping queries to results
    """
    print(f"--- BATCH SEARCH: {len(queries)} queries ---")

    driver = connect_to_neo4j(neo4j_config)
    if driver is None:
        return {}

    results = {}

    try:
        for query in queries:
            print(f"Searching: {query}")
            query_results = search_publications(
                driver, neo4j_config.database, query, **search_kwargs
            )
            results[query] = query_results

        # Save to file if requested
        if output_file:
            with open(output_file, "w") as f:
                json.dump(results, f, indent=2)
            print(f"Results saved to: {output_file}")

        return results

    finally:
        driver.close()


def export_search_results(
    results: dict[str, list[dict[str, Any]]], output_file: str, format: str = "json"
) -> None:
    """Export search results to file.

    Args:
        results: Search results dictionary
        output_file: Output file path
        format: Export format ('json' or 'csv')
    """
    if format.lower() == "json":
        with open(output_file, "w") as f:
            json.dump(results, f, indent=2)
    elif format.lower() == "csv":
        # Flatten results for CSV export
        import csv

        with open(output_file, "w", newline="") as f:
            writer = None

            for query, query_results in results.items():
                for result in query_results:
                    result["query"] = query

                    if writer is None:
                        writer = csv.DictWriter(f, fieldnames=result.keys())
                        writer.writeheader()

                    writer.writerow(result)
    else:
        raise ValueError(f"Unsupported format: {format}")

    print(f"Results exported to {output_file} in {format.upper()} format")
