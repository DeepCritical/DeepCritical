"""
Neo4j connection testing utilities for DeepCritical.

This module provides comprehensive connection testing and diagnostics
for Neo4j databases, including health checks and performance validation.
"""

from __future__ import annotations

import time
from typing import Any, Dict, List, Optional, TypedDict

from neo4j import GraphDatabase

from ..datatypes.neo4j_types import Neo4jConnectionConfig, Neo4jHealthCheck
from ..prompts.neo4j_queries import (
    HEALTH_CHECK_CONNECTION,
    HEALTH_CHECK_DATABASE_SIZE,
    HEALTH_CHECK_VECTOR_INDEX,
    VALIDATE_SCHEMA_CONSTRAINTS,
    VALIDATE_VECTOR_INDEXES,
)


def test_basic_connection(config: Neo4jConnectionConfig) -> dict[str, Any]:
    """Test basic Neo4j connection and authentication.

    Args:
        config: Neo4j connection configuration

    Returns:
        Dictionary with connection test results
    """
    print("--- TESTING BASIC CONNECTION ---")

    result = {
        "connection_success": False,
        "authentication_success": False,
        "database_accessible": False,
        "connection_time": None,
        "error": None,
        "server_info": {},
    }

    start_time = time.time()

    try:
        # Test connection
        driver = GraphDatabase.driver(
            config.uri,
            auth=(config.username, config.password) if config.username else None,
            encrypted=config.encrypted,
        )

        result["connection_success"] = True
        result["authentication_success"] = True

        # Test database access
        with driver.session(database=config.database) as session:
            # Run a simple health check
            record = session.run(HEALTH_CHECK_CONNECTION).single()
            if record:
                result["database_accessible"] = True
                result["server_info"] = dict(record)

        driver.close()

    except Exception as e:
        result["error"] = str(e)
        print(f"✗ Connection test failed: {e}")

    result["connection_time"] = time.time() - start_time

    # Print results
    if result["connection_success"]:
        print("✓ Connection established")
        if result["authentication_success"]:
            print("✓ Authentication successful")
        if result["database_accessible"]:
            print(f"✓ Database '{config.database}' accessible")
        print(f"✓ Connection time: {result['connection_time']:.3f}s")
    else:
        print(f"✗ Connection failed: {result['error']}")

    return result


def test_vector_index_access(
    config: Neo4jConnectionConfig, index_name: str
) -> dict[str, Any]:
    """Test access to a specific vector index.

    Args:
        config: Neo4j connection configuration
        index_name: Name of the vector index to test

    Returns:
        Dictionary with vector index test results
    """
    print(f"--- TESTING VECTOR INDEX: {index_name} ---")

    result = {
        "index_exists": False,
        "index_accessible": False,
        "query_success": False,
        "test_vector": [0.1] * 384,  # Default test vector
        "error": None,
    }

    try:
        driver = GraphDatabase.driver(
            config.uri,
            auth=(config.username, config.password) if config.username else None,
            encrypted=config.encrypted,
        )

        with driver.session(database=config.database) as session:
            # Check if index exists
            record = session.run(
                "SHOW INDEXES WHERE name = $index_name AND type = 'VECTOR'",
                {"index_name": index_name},
            ).single()

            if record:
                result["index_exists"] = True
                result["index_info"] = dict(record)

                # Test vector query
                query_result = session.run(
                    HEALTH_CHECK_VECTOR_INDEX,
                    {"index_name": index_name, "test_vector": result["test_vector"]},
                ).single()

                if query_result:
                    result["query_success"] = True
                    result["query_result"] = dict(query_result)

                print("✓ Vector index accessible and queryable")
            else:
                print(f"✗ Vector index '{index_name}' not found")

        driver.close()

    except Exception as e:
        result["error"] = str(e)
        print(f"✗ Vector index test failed: {e}")

    return result


def test_database_performance(config: Neo4jConnectionConfig) -> dict[str, Any]:
    """Test database performance metrics.

    Args:
        config: Neo4j connection configuration

    Returns:
        Dictionary with performance test results
    """
    print("--- TESTING DATABASE PERFORMANCE ---")

    result: dict[str, Any] = {
        "node_count": 0,
        "relationship_count": 0,
        "database_size": {},
        "query_times": {},
        "error": None,
    }

    try:
        driver = GraphDatabase.driver(
            config.uri,
            auth=(config.username, config.password) if config.username else None,
            encrypted=config.encrypted,
        )

        with driver.session(database=config.database) as session:
            # Test basic counts
            start_time = time.time()
            record = session.run(HEALTH_CHECK_DATABASE_SIZE).single()
            result["query_times"]["basic_count"] = time.time() - start_time  # type: ignore

            if record:
                result["database_size"] = dict(record)

            # Test simple node count
            start_time = time.time()
            record = session.run("MATCH (n) RETURN count(n) AS node_count").single()
            result["query_times"]["node_count"] = time.time() - start_time  # type: ignore
            result["node_count"] = record["node_count"] if record else 0

            # Test relationship count
            start_time = time.time()
            record = session.run(
                "MATCH ()-[r]->() RETURN count(r) AS relationship_count"
            ).single()
            result["query_times"]["relationship_count"] = time.time() - start_time  # type: ignore
            result["relationship_count"] = record["relationship_count"] if record else 0

        driver.close()

        print("✓ Performance test completed")
        print(f"  Nodes: {result['node_count']}")
        print(f"  Relationships: {result['relationship_count']}")
        print(f"  Query times: {result['query_times']}")

    except Exception as e:
        result["error"] = str(e)
        print(f"✗ Performance test failed: {e}")

    return result


def validate_schema_integrity(config: Neo4jConnectionConfig) -> dict[str, Any]:
    """Validate database schema integrity.

    Args:
        config: Neo4j connection configuration

    Returns:
        Dictionary with schema validation results
    """
    print("--- VALIDATING SCHEMA INTEGRITY ---")

    result = {
        "constraints_valid": False,
        "indexes_valid": False,
        "vector_indexes_valid": False,
        "constraints": [],
        "indexes": [],
        "vector_indexes": [],
        "error": None,
    }

    try:
        driver = GraphDatabase.driver(
            config.uri,
            auth=(config.username, config.password) if config.username else None,
            encrypted=config.encrypted,
        )

        with driver.session(database=config.database) as session:
            # Check constraints
            constraints_result = session.run(VALIDATE_SCHEMA_CONSTRAINTS)
            result["constraints"] = [dict(record) for record in constraints_result]
            result["constraints_valid"] = len(result["constraints"]) > 0

            # Check indexes
            indexes_result = session.run("SHOW INDEXES WHERE type <> 'VECTOR'")
            result["indexes"] = [dict(record) for record in indexes_result]

            # Check vector indexes
            vector_indexes_result = session.run(VALIDATE_VECTOR_INDEXES)
            result["vector_indexes"] = [
                dict(record) for record in vector_indexes_result
            ]
            result["vector_indexes_valid"] = len(result["vector_indexes"]) > 0

        driver.close()

        print("✓ Schema validation completed")
        print(f"  Constraints: {len(result['constraints'])}")
        print(f"  Indexes: {len(result['indexes'])}")
        print(f"  Vector indexes: {len(result['vector_indexes'])}")

    except Exception as e:
        result["error"] = str(e)
        print(f"✗ Schema validation failed: {e}")

    return result


def run_comprehensive_health_check(
    config: Neo4jConnectionConfig, health_config: Neo4jHealthCheck | None = None
) -> dict[str, Any]:
    """Run comprehensive health check on Neo4j database.

    Args:
        config: Neo4j connection configuration
        health_config: Health check configuration

    Returns:
        Dictionary with comprehensive health check results
    """
    print("\n" + "=" * 80)
    print("NEO4J COMPREHENSIVE HEALTH CHECK")
    print("=" * 80 + "\n")

    if health_config is None:
        health_config = Neo4jHealthCheck()

    results: dict[str, Any] = {
        "timestamp": time.time(),
        "overall_status": "unknown",
        "connection_test": {},
        "performance_test": {},
        "schema_validation": {},
        "vector_indexes": {},
        "recommendations": [],
    }

    # Basic connection test
    print("1. Testing basic connection...")
    results["connection_test"] = test_basic_connection(config)

    if not results["connection_test"]["connection_success"]:
        results["overall_status"] = "critical"
        results["recommendations"].append("Fix connection issues before proceeding")  # type: ignore
        return results

    # Performance test
    print("\n2. Testing performance...")
    results["performance_test"] = test_database_performance(config)

    # Schema validation
    print("\n3. Validating schema...")
    results["schema_validation"] = validate_schema_integrity(config)

    # Vector index tests
    print("\n4. Testing vector indexes...")
    vector_indexes = results["schema_validation"].get("vector_indexes", [])
    results["vector_indexes"] = {}

    for v_index in vector_indexes:
        index_name = v_index.get("name")
        if index_name:
            results["vector_indexes"][index_name] = test_vector_index_access(
                config, index_name
            )

    # Determine overall status
    all_tests_passed = (
        results["connection_test"]["connection_success"]
        and results["schema_validation"]["constraints_valid"]
        and len(results["vector_indexes"]) > 0
    )

    if all_tests_passed:
        results["overall_status"] = "healthy"
    elif results["connection_test"]["connection_success"]:
        results["overall_status"] = "degraded"
    else:
        results["overall_status"] = "critical"

    # Generate recommendations
    if results["overall_status"] == "critical":
        results["recommendations"].append("Critical: Database connection failed")  # type: ignore
    elif results["overall_status"] == "degraded":
        if not results["schema_validation"]["constraints_valid"]:
            results["recommendations"].append("Create missing database constraints")  # type: ignore
        if not results["vector_indexes"]:
            results["recommendations"].append(  # type: ignore
                "Create vector indexes for search functionality"
            )
        if results["performance_test"]["query_times"].get("basic_count", 0) > 5.0:
            results["recommendations"].append("Optimize database performance")  # type: ignore

    # Print summary
    print("\n📊 Health Check Summary:")
    print(f"Status: {results['overall_status'].upper()}")
    print(
        f"Connection: {'✓' if results['connection_test']['connection_success'] else '✗'}"
    )
    print(
        f"Constraints: {'✓' if results['schema_validation']['constraints_valid'] else '✗'}"
    )
    print(f"Vector Indexes: {len(results['vector_indexes'])}")

    if results["recommendations"]:
        print("\n💡 Recommendations:")
        for rec in results["recommendations"]:  # type: ignore
            print(f"  - {rec}")

    return results


def test_neo4j_connection(config: Neo4jConnectionConfig) -> bool:
    """Simple connection test for Neo4j.

    Args:
        config: Neo4j connection configuration

    Returns:
        True if connection successful
    """
    try:
        driver = GraphDatabase.driver(
            config.uri,
            auth=(config.username, config.password) if config.username else None,
            encrypted=config.encrypted,
        )

        with driver.session(database=config.database) as session:
            session.run("RETURN 1")

        driver.close()
        return True

    except Exception:
        return False


def benchmark_connection_pooling(
    config: Neo4jConnectionConfig, num_connections: int = 10, num_queries: int = 100
) -> dict[str, Any]:
    """Benchmark connection pooling performance.

    Args:
        config: Neo4j connection configuration
        num_connections: Number of concurrent connections to test
        num_queries: Number of queries per connection

    Returns:
        Dictionary with benchmarking results
    """
    print(
        f"--- BENCHMARKING CONNECTION POOLING ({num_connections} connections, {num_queries} queries) ---"
    )

    import asyncio
    import concurrent.futures

    result: dict[str, Any] = {
        "total_queries": num_connections * num_queries,
        "successful_queries": 0,
        "failed_queries": 0,
        "total_time": 0.0,
        "avg_query_time": 0.0,
        "qps": 0.0,  # queries per second
        "errors": [],
    }

    def run_queries(connection_id: int) -> dict[str, Any]:
        """Run queries for a single connection."""
        conn_result = {"queries": 0, "errors": 0, "time": 0}

        try:
            driver = GraphDatabase.driver(
                config.uri,
                auth=(config.username, config.password) if config.username else None,
                encrypted=config.encrypted,
            )

            start_time = time.time()

            with driver.session(database=config.database) as session:
                for i in range(num_queries):
                    try:
                        session.run(
                            "RETURN $id", {"id": f"conn_{connection_id}_query_{i}"}
                        )
                        conn_result["queries"] += 1
                    except Exception as e:
                        conn_result["errors"] += 1
                        conn_result.setdefault("error_details", []).append(str(e))  # type: ignore

            conn_result["time"] = time.time() - start_time
            driver.close()

        except Exception as e:
            conn_result["errors"] += num_queries
            conn_result["error_details"] = [str(e)]

        return conn_result

    # Run benchmark
    start_time = time.time()

    with concurrent.futures.ThreadPoolExecutor(max_workers=num_connections) as executor:
        futures = [executor.submit(run_queries, i) for i in range(num_connections)]
        conn_results = [
            future.result() for future in concurrent.futures.as_completed(futures)
        ]

    result["total_time"] = time.time() - start_time

    # Aggregate results
    for conn_result in conn_results:
        result["successful_queries"] += conn_result["queries"]
        result["failed_queries"] += conn_result["errors"]
        if "error_details" in conn_result:
            result["errors"].extend(conn_result["error_details"])  # type: ignore

    # Calculate metrics
    if result["total_time"] > 0:
        result["avg_query_time"] = result["total_time"] / result["successful_queries"]  # type: ignore
        result["qps"] = result["successful_queries"] / result["total_time"]  # type: ignore

    print("✓ Benchmarking completed")
    print(f"  Total queries: {result['successful_queries']}/{result['total_queries']}")
    print(f"  Total time: {result['total_time']:.2f}s")
    print(f"  QPS: {result['qps']:.1f}")
    print(f"  Avg query time: {result['avg_query_time'] * 1000:.2f}ms")

    return result
