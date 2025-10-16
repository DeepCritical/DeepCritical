"""
Neo4j vector index setup utilities for DeepCritical.

This module provides functions to create and manage vector indexes
in Neo4j databases for efficient similarity search operations.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from neo4j import GraphDatabase

from ..datatypes.neo4j_types import (
    Neo4jConnectionConfig,
    VectorIndexConfig,
    VectorIndexMetric,
)
from ..prompts.neo4j_queries import (
    CREATE_VECTOR_INDEX,
    DROP_VECTOR_INDEX,
    LIST_VECTOR_INDEXES,
    VECTOR_INDEX_EXISTS,
)


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


def create_vector_index(
    driver: Any, database: str, index_config: VectorIndexConfig
) -> bool:
    """Create a vector index in Neo4j.

    Args:
        driver: Neo4j driver
        database: Database name
        index_config: Vector index configuration

    Returns:
        True if successful
    """
    print(f"--- CREATING VECTOR INDEX: {index_config.index_name} ---")

    with driver.session(database=database) as session:
        try:
            # Check if index already exists
            result = session.run(
                VECTOR_INDEX_EXISTS, {"index_name": index_config.index_name}
            )
            exists = result.single()["exists"]

            if exists:
                print(f"✓ Vector index '{index_config.index_name}' already exists")
                return True

            # Create the vector index
            session.run(
                CREATE_VECTOR_INDEX,
                {
                    "index_name": index_config.index_name,
                    "node_label": index_config.node_label,
                    "vector_property": index_config.vector_property,
                    "dimensions": index_config.dimensions,
                    "similarity_function": index_config.metric.value,
                },
            )

            print(f"✓ Created vector index '{index_config.index_name}'")
            print(f"  - Label: {index_config.node_label}")
            print(f"  - Property: {index_config.vector_property}")
            print(f"  - Dimensions: {index_config.dimensions}")
            print(f"  - Metric: {index_config.metric.value}")

            return True

        except Exception as e:
            print(f"✗ Error creating vector index: {e}")
            return False


def drop_vector_index(driver: Any, database: str, index_name: str) -> bool:
    """Drop a vector index from Neo4j.

    Args:
        driver: Neo4j driver
        database: Database name
        index_name: Name of the index to drop

    Returns:
        True if successful
    """
    print(f"--- DROPPING VECTOR INDEX: {index_name} ---")

    with driver.session(database=database) as session:
        try:
            # Check if index exists
            result = session.run(VECTOR_INDEX_EXISTS, {"index_name": index_name})
            exists = result.single()["exists"]

            if not exists:
                print(f"✓ Vector index '{index_name}' does not exist")
                return True

            # Drop the vector index
            session.run(DROP_VECTOR_INDEX, {"index_name": index_name})

            print(f"✓ Dropped vector index '{index_name}'")
            return True

        except Exception as e:
            print(f"✗ Error dropping vector index: {e}")
            return False


def list_vector_indexes(driver: Any, database: str) -> list[dict[str, Any]]:
    """List all vector indexes in the database.

    Args:
        driver: Neo4j driver
        database: Database name

    Returns:
        List of vector index information
    """
    print("--- LISTING VECTOR INDEXES ---")

    with driver.session(database=database) as session:
        try:
            result = session.run(LIST_VECTOR_INDEXES)

            indexes = []
            for record in result:
                index_info = {
                    "name": record.get("name"),
                    "labelsOrTypes": record.get("labelsOrTypes"),
                    "properties": record.get("properties"),
                    "state": record.get("state"),
                    "type": record.get("type"),
                }
                indexes.append(index_info)
                print(
                    f"  - {index_info['name']}: {index_info['state']} ({index_info['type']})"
                )

            if not indexes:
                print("  No vector indexes found")

            return indexes

        except Exception as e:
            print(f"✗ Error listing vector indexes: {e}")
            return []


def create_publication_vector_index(driver: Any, database: str) -> bool:
    """Create a standard vector index for publication abstracts.

    Args:
        driver: Neo4j driver
        database: Database name

    Returns:
        True if successful
    """
    print("--- CREATING PUBLICATION VECTOR INDEX ---")

    index_config = VectorIndexConfig(
        index_name="publication_abstract_vector",
        node_label="Publication",
        vector_property="abstract_embedding",
        dimensions=384,  # Default for sentence-transformers
        metric=VectorIndexMetric.COSINE,
    )

    return create_vector_index(driver, database, index_config)


def create_document_vector_index(driver: Any, database: str) -> bool:
    """Create a standard vector index for document content.

    Args:
        driver: Neo4j driver
        database: Database name

    Returns:
        True if successful
    """
    print("--- CREATING DOCUMENT VECTOR INDEX ---")

    index_config = VectorIndexConfig(
        index_name="document_content_vector",
        node_label="Document",
        vector_property="embedding",
        dimensions=384,  # Default for sentence-transformers
        metric=VectorIndexMetric.COSINE,
    )

    return create_vector_index(driver, database, index_config)


def create_chunk_vector_index(driver: Any, database: str) -> bool:
    """Create a standard vector index for text chunks.

    Args:
        driver: Neo4j driver
        database: Database name

    Returns:
        True if successful
    """
    print("--- CREATING CHUNK VECTOR INDEX ---")

    index_config = VectorIndexConfig(
        index_name="chunk_text_vector",
        node_label="Chunk",
        vector_property="embedding",
        dimensions=384,  # Default for sentence-transformers
        metric=VectorIndexMetric.COSINE,
    )

    return create_vector_index(driver, database, index_config)


def validate_vector_index(
    driver: Any, database: str, index_name: str
) -> dict[str, Any]:
    """Validate a vector index and return statistics.

    Args:
        driver: Neo4j driver
        database: Database name
        index_name: Name of the index to validate

    Returns:
        Dictionary with validation results
    """
    print(f"--- VALIDATING VECTOR INDEX: {index_name} ---")

    with driver.session(database=database) as session:
        validation = {
            "index_name": index_name,
            "exists": False,
            "valid": False,
            "stats": {},
        }

        try:
            # Check if index exists
            result = session.run(VECTOR_INDEX_EXISTS, {"index_name": index_name})
            validation["exists"] = result.single()["exists"]

            if not validation["exists"]:
                print(f"✗ Vector index '{index_name}' does not exist")
                return validation

            print(f"✓ Vector index '{index_name}' exists")

            # Get index details
            result = session.run(
                "SHOW INDEXES WHERE name = $index_name", {"index_name": index_name}
            )
            record = result.single()

            if record:
                validation["details"] = {
                    "labelsOrTypes": record.get("labelsOrTypes"),
                    "properties": record.get("properties"),
                    "state": record.get("state"),
                }
                validation["valid"] = record.get("state") == "ONLINE"
                print(f"✓ Index state: {record.get('state')}")

            # Get statistics about indexed nodes
            if record and record.get("labelsOrTypes"):
                label = record["labelsOrTypes"][0]  # Assume single label
                property_name = record["properties"][0]  # Assume single property

                result = session.run(f"""
                    MATCH (n:{label})
                    WHERE n.{property_name} IS NOT NULL
                    RETURN count(n) AS nodes_with_vectors,
                           size(head([n.{property_name} WHERE n.{property_name} IS NOT NULL])) AS vector_dimension
                """)

                record = result.single()
                if record:
                    validation["stats"] = {
                        "nodes_with_vectors": record["nodes_with_vectors"],
                        "vector_dimension": record["vector_dimension"],
                    }
                    print(f"✓ Nodes with vectors: {record['nodes_with_vectors']}")
                    print(f"✓ Vector dimension: {record['vector_dimension']}")

            return validation

        except Exception as e:
            print(f"✗ Error validating vector index: {e}")
            validation["error"] = str(e)
            return validation


def setup_standard_vector_indexes(
    neo4j_config: Neo4jConnectionConfig,
    create_publication_index: bool = True,
    create_document_index: bool = True,
    create_chunk_index: bool = True,
) -> dict[str, Any]:
    """Set up standard vector indexes for the database.

    Args:
        neo4j_config: Neo4j connection configuration
        create_publication_index: Whether to create publication vector index
        create_document_index: Whether to create document vector index
        create_chunk_index: Whether to create chunk vector index

    Returns:
        Dictionary with setup results
    """
    print("\n" + "=" * 80)
    print("NEO4J VECTOR INDEX SETUP PROCESS")
    print("=" * 80 + "\n")

    # Connect to Neo4j
    driver = connect_to_neo4j(neo4j_config)
    if driver is None:
        return {"success": False, "error": "Failed to connect to Neo4j"}

    results: dict[str, Any] = {
        "success": True,
        "indexes_created": [],
        "indexes_failed": [],
        "existing_indexes": [],
        "validations": {},
    }

    try:
        # List existing indexes
        print("Checking existing vector indexes...")
        existing_indexes = list_vector_indexes(driver, neo4j_config.database)
        results["existing_indexes"] = existing_indexes

        # Create indexes
        if create_publication_index:
            if create_publication_vector_index(driver, neo4j_config.database):
                results["indexes_created"].append("publication_abstract_vector")  # type: ignore
            else:
                results["indexes_failed"].append("publication_abstract_vector")  # type: ignore

        if create_document_index:
            if create_document_vector_index(driver, neo4j_config.database):
                results["indexes_created"].append("document_content_vector")  # type: ignore
            else:
                results["indexes_failed"].append("document_content_vector")  # type: ignore

        if create_chunk_index:
            if create_chunk_vector_index(driver, neo4j_config.database):
                results["indexes_created"].append("chunk_text_vector")  # type: ignore
            else:
                results["indexes_failed"].append("chunk_text_vector")  # type: ignore

        # Validate created indexes
        print("\nValidating created indexes...")
        validations = {}
        for index_name in results["indexes_created"]:  # type: ignore
            validations[index_name] = validate_vector_index(
                driver, neo4j_config.database, index_name
            )

        results["validations"] = validations

        # Summary
        total_created = len(results["indexes_created"])  # type: ignore
        total_failed = len(results["indexes_failed"])  # type: ignore

        print("\n✅ Vector index setup completed!")
        print(f"Indexes created: {total_created}")
        print(f"Indexes failed: {total_failed}")

        if total_failed > 0:
            results["success"] = False
            print("Failed indexes:", results["indexes_failed"])

        return results

    except Exception as e:
        print(f"Error during vector index setup: {e}")
        import traceback

        results["success"] = False
        results["error"] = str(e)
        results["traceback"] = traceback.format_exc()
        return results
    finally:
        driver.close()
        print("Neo4j connection closed")
