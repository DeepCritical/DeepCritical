"""
Neo4j author data correction utilities for DeepCritical.

This module provides functions to fix and normalize author data
in Neo4j databases, including name normalization and affiliation corrections.
"""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional, TypedDict

from neo4j import GraphDatabase

from ..datatypes.neo4j_types import Neo4jConnectionConfig


class FixesApplied(TypedDict):
    """Structure for applied fixes."""

    name_fixes: int
    name_normalizations: int
    affiliation_fixes: int
    link_fixes: int
    consolidations: int


class AuthorFixResults(TypedDict, total=False):
    """Structure for author fix operation results."""

    success: bool
    fixes_applied: FixesApplied
    initial_stats: dict[str, Any]
    final_stats: dict[str, Any]
    error: str | None
    traceback: str | None


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


def fix_author_names(driver: Any, database: str) -> int:
    """Fix inconsistent author names and normalize formatting.

    Args:
        driver: Neo4j driver
        database: Database name

    Returns:
        Number of authors fixed
    """
    print("--- FIXING AUTHOR NAMES ---")

    with driver.session(database=database) as session:
        # Find authors with inconsistent names
        result = session.run("""
            MATCH (a:Author)
            WITH a.name AS name, collect(a) AS author_nodes
            WHERE size(author_nodes) > 1
            RETURN name, size(author_nodes) AS count, [node IN author_nodes | node.id] AS ids
            ORDER BY count DESC
            LIMIT 20
        """)

        fixes_applied = 0

        for record in result:
            name = record["name"]
            author_ids = record["ids"]
            count = record["count"]

            print(f"Found {count} authors with name '{name}': {author_ids}")

            # Choose the most common or first author ID as canonical
            canonical_id = min(author_ids)  # Use smallest ID as canonical

            # Merge duplicate authors
            for author_id in author_ids:
                if author_id != canonical_id:
                    session.run(
                        """
                        MATCH (duplicate:Author {id: $duplicate_id})
                        MATCH (canonical:Author {id: $canonical_id})
                        CALL {
                            WITH duplicate, canonical
                            MATCH (duplicate)-[r:AUTHORED]->(p:Publication)
                            MERGE (canonical)-[:AUTHORED]->(p)
                            DELETE r
                        }
                        CALL {
                            WITH duplicate, canonical
                            MATCH (duplicate)-[r:AFFILIATED_WITH]->(aff:Affiliation)
                            MERGE (canonical)-[:AFFILIATED_WITH]->(aff)
                            DELETE r
                        }
                        DETACH DELETE duplicate
                    """,
                        duplicate_id=author_id,
                        canonical_id=canonical_id,
                    )

                    fixes_applied += 1
                    print(f"✓ Merged author {author_id} into {canonical_id}")

        return fixes_applied


def normalize_author_names(driver: Any, database: str) -> int:
    """Normalize author name formatting (capitalization, etc.).

    Args:
        driver: Neo4j driver
        database: Database name

    Returns:
        Number of authors normalized
    """
    print("--- NORMALIZING AUTHOR NAMES ---")

    with driver.session(database=database) as session:
        # Get all authors
        result = session.run("""
            MATCH (a:Author)
            RETURN a.id AS id, a.name AS name
            ORDER BY a.name
        """)

        normalizations = 0

        for record in result:
            author_id = record["id"]
            original_name = record["name"]

            # Apply normalization rules
            normalized_name = normalize_name(original_name)

            if normalized_name != original_name:
                session.run(
                    """
                    MATCH (a:Author {id: $id})
                    SET a.name = $normalized_name,
                        a.original_name = $original_name
                """,
                    id=author_id,
                    normalized_name=normalized_name,
                    original_name=original_name,
                )

                normalizations += 1
                print(f"✓ Normalized '{original_name}' → '{normalized_name}'")

        return normalizations


def normalize_name(name: str) -> str:
    """Normalize author name formatting.

    Args:
        name: Original author name

    Returns:
        Normalized name
    """
    if not name:
        return name

    # Handle common name formats
    parts = name.split()

    if len(parts) >= 2:
        # Assume "First Last" or "First Middle Last" format
        # Capitalize each part
        normalized_parts = []
        for part in parts:
            # Skip very short parts (likely initials)
            if len(part) <= 1:
                normalized_parts.append(part.upper())
            else:
                normalized_parts.append(part.capitalize())

        return " ".join(normalized_parts)
    # Single part name, just capitalize
    return name.capitalize()


def fix_missing_author_affiliations(driver: Any, database: str) -> int:
    """Fix authors missing affiliations by linking to institutions.

    Args:
        driver: Neo4j driver
        database: Database name

    Returns:
        Number of affiliations fixed
    """
    print("--- FIXING MISSING AUTHOR AFFILIATIONS ---")

    with driver.session(database=database) as session:
        # Find authors without affiliations
        result = session.run("""
            MATCH (a:Author)
            WHERE NOT (a)-[:AFFILIATED_WITH]->(:Institution)
            RETURN a.id AS id, a.name AS name
            LIMIT 50
        """)

        fixes = 0

        for record in result:
            author_id = record["id"]
            author_name = record["name"]

            # Try to find affiliation from co-authors or publication metadata
            affiliation_found = find_affiliation_for_author(session, author_id)

            if affiliation_found:
                session.run(
                    """
                    MATCH (a:Author {id: $author_id})
                    MATCH (i:Institution {name: $institution_name})
                    MERGE (a)-[:AFFILIATED_WITH]->(i)
                """,
                    author_id=author_id,
                    institution_name=affiliation_found,
                )

                fixes += 1
                print(f"✓ Added affiliation '{affiliation_found}' to {author_name}")
            else:
                print(f"✗ Could not find affiliation for {author_name}")

        return fixes


def find_affiliation_for_author(session: Any, author_id: str) -> str | None:
    """Find affiliation for an author through co-authors or publications.

    Args:
        session: Neo4j session
        author_id: Author ID

    Returns:
        Institution name or None
    """
    # Try to find affiliation through co-authors
    result = session.run(
        """
        MATCH (a:Author {id: $author_id})-[:AUTHORED]->(p:Publication)<-[:AUTHORED]-(co_author:Author)
        WHERE (co_author)-[:AFFILIATED_WITH]->(:Institution)
        MATCH (co_author)-[:AFFILIATED_WITH]->(i:Institution)
        RETURN i.name AS institution, count(*) AS frequency
        ORDER BY frequency DESC
        LIMIT 1
    """,
        author_id=author_id,
    )

    record = result.single()
    if record:
        return record["institution"]

    # Try to find through publication metadata
    result = session.run(
        """
        MATCH (a:Author {id: $author_id})-[:AUTHORED]->(p:Publication)
        WHERE p.affiliation IS NOT NULL
        RETURN p.affiliation AS affiliation
        LIMIT 1
    """,
        author_id=author_id,
    )

    record = result.single()
    if record:
        return record["affiliation"]

    return None


def fix_author_publication_links(driver: Any, database: str) -> int:
    """Fix broken author-publication relationships.

    Args:
        driver: Neo4j driver
        database: Database name

    Returns:
        Number of links fixed
    """
    print("--- FIXING AUTHOR-PUBLICATION LINKS ---")

    with driver.session(database=database) as session:
        # Find publications missing author links
        result = session.run("""
            MATCH (p:Publication)
            WHERE NOT (p)<-[:AUTHORED]-(:Author)
            RETURN p.eid AS eid, p.title AS title
            LIMIT 20
        """)

        fixes = 0

        for record in result:
            eid = record["eid"]
            title = record["title"]

            # Try to link authors based on publication metadata
            if link_authors_to_publication(session, eid):
                fixes += 1
                print(f"✓ Linked authors to publication: {title[:50]}...")
            else:
                print(f"✗ Could not link authors to publication: {title[:50]}...")

        return fixes


def link_authors_to_publication(session: Any, publication_eid: str) -> bool:
    """Link authors to a publication based on available metadata.

    Args:
        session: Neo4j session
        publication_eid: Publication EID

    Returns:
        True if authors were linked
    """
    # This would typically involve parsing stored author data
    # For now, return False as this requires more complex logic
    # based on the original script's approach
    return False


def consolidate_duplicate_authors(driver: Any, database: str) -> int:
    """Consolidate authors with similar names but different IDs.

    Args:
        driver: Neo4j driver
        database: Database name

    Returns:
        Number of authors consolidated
    """
    print("--- CONSOLIDATING DUPLICATE AUTHORS ---")

    with driver.session(database=database) as session:
        # Find potentially duplicate authors (similar names)
        result = session.run("""
            MATCH (a1:Author), (a2:Author)
            WHERE id(a1) < id(a2)
            AND a1.name = a2.name
            AND a1.id <> a2.id
            RETURN a1.id AS id1, a2.id AS id2, a1.name AS name
            LIMIT 20
        """)

        consolidations = 0

        for record in result:
            id1 = record["id1"]
            id2 = record["id2"]
            name = record["name"]

            # Choose the smaller ID as canonical
            canonical_id = min(id1, id2)
            duplicate_id = max(id1, id2)

            session.run(
                """
                MATCH (duplicate:Author {id: $duplicate_id})
                MATCH (canonical:Author {id: $canonical_id})
                CALL {
                    WITH duplicate, canonical
                    MATCH (duplicate)-[r:AUTHORED]->(p:Publication)
                    MERGE (canonical)-[:AUTHORED]->(p)
                    DELETE r
                }
                CALL {
                    WITH duplicate, canonical
                    MATCH (duplicate)-[r:AFFILIATED_WITH]->(i:Institution)
                    MERGE (canonical)-[:AFFILIATED_WITH]->(i)
                    DELETE r
                }
                DETACH DELETE duplicate
            """,
                duplicate_id=duplicate_id,
                canonical_id=canonical_id,
            )

            consolidations += 1
            print(f"✓ Consolidated author {duplicate_id} into {canonical_id} ({name})")

        return consolidations


def validate_author_data_integrity(driver: Any, database: str) -> dict[str, int]:
    """Validate author data integrity and return statistics.

    Args:
        driver: Neo4j driver
        database: Database name

    Returns:
        Dictionary with validation statistics
    """
    print("--- VALIDATING AUTHOR DATA INTEGRITY ---")

    with driver.session(database=database) as session:
        stats = {}

        # Count total authors
        result = session.run("MATCH (a:Author) RETURN count(a) AS count")
        stats["total_authors"] = result.single()["count"]

        # Count authors with publications
        result = session.run("""
            MATCH (a:Author)-[:AUTHORED]->(p:Publication)
            RETURN count(DISTINCT a) AS count
        """)
        stats["authors_with_publications"] = result.single()["count"]

        # Count authors with affiliations
        result = session.run("""
            MATCH (a:Author)-[:AFFILIATED_WITH]->(i:Institution)
            RETURN count(DISTINCT a) AS count
        """)
        stats["authors_with_affiliations"] = result.single()["count"]

        # Count authors without affiliations
        result = session.run("""
            MATCH (a:Author)
            WHERE NOT (a)-[:AFFILIATED_WITH]->(:Institution)
            RETURN count(a) AS count
        """)
        stats["authors_without_affiliations"] = result.single()["count"]

        # Count duplicate author names
        result = session.run("""
            MATCH (a:Author)
            WITH a.name AS name, collect(a) AS authors
            WHERE size(authors) > 1
            RETURN count(*) AS count
        """)
        stats["duplicate_names"] = result.single()["count"]

        # Count orphaned authors (no publications, no affiliations)
        result = session.run("""
            MATCH (a:Author)
            WHERE NOT (a)-[:AUTHORED]->() AND NOT (a)-[:AFFILIATED_WITH]->()
            RETURN count(a) AS count
        """)
        stats["orphaned_authors"] = result.single()["count"]

        print("Author data statistics:")
        for key, value in stats.items():
            print(f"  {key}: {value}")

        return stats


def fix_author_data(
    neo4j_config: Neo4jConnectionConfig,
    fix_names: bool = True,
    normalize_names: bool = True,
    fix_affiliations: bool = True,
    fix_links: bool = True,
    consolidate_duplicates: bool = True,
    validate_only: bool = False,
) -> AuthorFixResults:
    """Complete author data fixing process.

    Args:
        neo4j_config: Neo4j connection configuration
        fix_names: Whether to fix inconsistent author names
        normalize_names: Whether to normalize name formatting
        fix_affiliations: Whether to fix missing affiliations
        fix_links: Whether to fix broken author-publication links
        consolidate_duplicates: Whether to consolidate duplicate authors
        validate_only: Only validate without making changes

    Returns:
        Dictionary with results and statistics
    """
    print("\n" + "=" * 80)
    print("NEO4J AUTHOR DATA FIXING PROCESS")
    print("=" * 80 + "\n")

    # Connect to Neo4j
    driver = connect_to_neo4j(neo4j_config)
    if driver is None:
        return {"success": False, "error": "Failed to connect to Neo4j"}

    results: AuthorFixResults = {
        "success": True,
        "fixes_applied": {
            "name_fixes": 0,
            "name_normalizations": 0,
            "affiliation_fixes": 0,
            "link_fixes": 0,
            "consolidations": 0,
        },
        "initial_stats": {},
        "final_stats": {},
        "error": None,
    }

    try:
        # Validate current state
        print("Validating current author data...")
        initial_stats = validate_author_data_integrity(driver, neo4j_config.database)
        results["initial_stats"] = initial_stats

        if validate_only:
            results["final_stats"] = initial_stats
            return results

        # Apply fixes
        if fix_names:
            fixes = fix_author_names(driver, neo4j_config.database)
            results["fixes_applied"]["name_fixes"] = fixes

        if normalize_names:
            fixes = normalize_author_names(driver, neo4j_config.database)
            results["fixes_applied"]["name_normalizations"] = fixes

        if fix_affiliations:
            fixes = fix_missing_author_affiliations(driver, neo4j_config.database)
            results["fixes_applied"]["affiliation_fixes"] = fixes

        if fix_links:
            fixes = fix_author_publication_links(driver, neo4j_config.database)
            results["fixes_applied"]["link_fixes"] = fixes

        if consolidate_duplicates:
            fixes = consolidate_duplicate_authors(driver, neo4j_config.database)
            results["fixes_applied"]["consolidations"] = fixes

        # Final validation
        print("\nValidating final author data...")
        final_stats = validate_author_data_integrity(driver, neo4j_config.database)
        results["final_stats"] = final_stats

        total_fixes = sum(results["fixes_applied"].values())
        print("\n✅ Author data fixing completed successfully!")
        print(f"Total fixes applied: {total_fixes}")

        return results

    except Exception as e:
        print(f"Error during author data fixing: {e}")
        import traceback

        results["success"] = False
        results["error"] = str(e)
        results["traceback"] = traceback.format_exc()
        return results
    finally:
        driver.close()
        print("Neo4j connection closed")
