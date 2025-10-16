"""
Neo4j CrossRef data integration utilities for DeepCritical.

This module provides functions to fetch and integrate CrossRef data
with Neo4j databases, including DOI resolution and citation linking.
"""

from __future__ import annotations

import json
import time
from typing import Any, Dict, List, Optional

import requests
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


def fetch_crossref_work(doi: str) -> dict[str, Any] | None:
    """Fetch work data from CrossRef API.

    Args:
        doi: DOI identifier

    Returns:
        CrossRef work data or None if not found
    """
    try:
        # Rate limiting
        time.sleep(0.1)

        url = f"https://api.crossref.org/works/{doi}"
        response = requests.get(url, timeout=10)

        if response.status_code == 200:
            data = response.json()
            return data.get("message")
        print(f"CrossRef API error for {doi}: {response.status_code}")
        return None
    except Exception as e:
        print(f"Error fetching CrossRef data for {doi}: {e}")
        return None


def enrich_publications_with_crossref(
    driver: Any, database: str, batch_size: int = 10
) -> int:
    """Enrich publications with CrossRef data.

    Args:
        driver: Neo4j driver
        database: Database name
        batch_size: Number of publications to process per batch

    Returns:
        Number of publications enriched
    """
    print("--- ENRICHING PUBLICATIONS WITH CROSSREF DATA ---")

    with driver.session(database=database) as session:
        # Find publications with DOIs but missing CrossRef data
        result = session.run(
            """
            MATCH (p:Publication)
            WHERE p.doi IS NOT NULL
            AND p.doi <> ""
            AND (p.crossref_enriched IS NULL OR p.crossref_enriched = false)
            RETURN p.eid AS eid, p.doi AS doi, p.title AS title
            LIMIT $batch_size
        """,
            batch_size=batch_size,
        )

        enriched = 0

        for record in result:
            eid = record["eid"]
            doi = record["doi"]
            title = record["title"]

            print(f"Processing CrossRef data for: {title[:50]}...")

            # Fetch CrossRef data
            crossref_data = fetch_crossref_work(doi)

            if crossref_data:
                # Update publication with CrossRef data
                session.run(
                    """
                    MATCH (p:Publication {eid: $eid})
                    SET p.crossref_enriched = true,
                        p.crossref_data = $crossref_data,
                        p.publisher = $publisher,
                        p.journal_issn = $issn,
                        p.publication_date = $published,
                        p.crossref_retrieved_at = datetime()
                """,
                    eid=eid,
                    crossref_data=json.dumps(crossref_data),
                    publisher=crossref_data.get("publisher"),
                    issn=crossref_data.get("ISSN", [None])[0]
                    if crossref_data.get("ISSN")
                    else None,
                    published=crossref_data.get(
                        "published-print", crossref_data.get("published-online")
                    ),
                )

                # Add CrossRef citations if available
                if crossref_data.get("reference"):
                    citations_added = add_crossref_citations(
                        session, eid, crossref_data["reference"]
                    )
                    print(f"✓ Added {citations_added} CrossRef citations")

                enriched += 1
                print("✓ Enriched with CrossRef data")
            else:
                # Mark as attempted but failed
                session.run(
                    """
                    MATCH (p:Publication {eid: $eid})
                    SET p.crossref_attempted = true,
                        p.crossref_enriched = false
                """,
                    eid=eid,
                )
                print("✗ Could not fetch CrossRef data")

        return enriched


def add_crossref_citations(
    session: Any, citing_eid: str, references: list[dict[str, Any]]
) -> int:
    """Add CrossRef citation relationships.

    Args:
        session: Neo4j session
        citing_eid: EID of citing publication
        references: List of CrossRef references

    Returns:
        Number of citation relationships added
    """
    citations_added = 0

    for ref in references[:20]:  # Limit to avoid overwhelming the graph
        # Try to extract DOI from reference
        ref_doi = None
        if "DOI" in ref:
            ref_doi = ref["DOI"]
        elif "doi" in ref:
            ref_doi = ref["doi"]

        if ref_doi:
            # Create cited publication if it doesn't exist
            session.run(
                """
                MERGE (cited:Publication {doi: $doi})
                ON CREATE SET cited.title = $title,
                              cited.year = $year,
                              cited.crossref_cited_only = true
                WITH cited
                MATCH (citing:Publication {eid: $citing_eid})
                MERGE (citing)-[:CITES]->(cited)
            """,
                doi=ref_doi,
                title=ref.get("article-title", ref.get("title", "")),
                year=ref.get("year"),
                citing_eid=citing_eid,
            )

            citations_added += 1

    return citations_added


def validate_crossref_data(driver: Any, database: str) -> dict[str, int]:
    """Validate CrossRef data integrity.

    Args:
        driver: Neo4j driver
        database: Database name

    Returns:
        Dictionary with validation statistics
    """
    print("--- VALIDATING CROSSREF DATA INTEGRITY ---")

    with driver.session(database=database) as session:
        stats = {}

        # Count publications with DOIs
        result = session.run("""
            MATCH (p:Publication)
            WHERE p.doi IS NOT NULL AND p.doi <> ""
            RETURN count(p) AS count
        """)
        stats["publications_with_doi"] = result.single()["count"]

        # Count publications enriched with CrossRef
        result = session.run("""
            MATCH (p:Publication)
            WHERE p.crossref_enriched = true
            RETURN count(p) AS count
        """)
        stats["publications_crossref_enriched"] = result.single()["count"]

        # Count CrossRef citation relationships
        result = session.run("""
            MATCH ()-[:CITES]->(p:Publication)
            WHERE p.crossref_cited_only = true
            RETURN count(*) AS count
        """)
        stats["crossref_citation_relationships"] = result.single()["count"]

        print("CrossRef Data Statistics:")
        for key, value in stats.items():
            print(f"  {key}: {value}")

        return stats


def update_crossref_metadata(driver: Any, database: str, batch_size: int = 20) -> int:
    """Update CrossRef metadata for existing publications.

    Args:
        driver: Neo4j driver
        database: Database name
        batch_size: Number of publications to process per batch

    Returns:
        Number of publications updated
    """
    print("--- UPDATING CROSSREF METADATA ---")

    with driver.session(database=database) as session:
        # Find publications that need CrossRef metadata updates
        result = session.run(
            """
            MATCH (p:Publication)
            WHERE p.crossref_enriched = true
            AND (p.crossref_last_updated IS NULL
                 OR p.crossref_last_updated < datetime() - duration('P90D'))
            RETURN p.eid AS eid, p.doi AS doi, p.title AS title
            LIMIT $batch_size
        """,
            batch_size=batch_size,
        )

        updated = 0

        for record in result:
            eid = record["eid"]
            doi = record["doi"]
            title = record["title"]

            print(f"Updating CrossRef metadata for: {title[:50]}...")

            # Fetch updated CrossRef data
            crossref_data = fetch_crossref_work(doi)

            if crossref_data:
                # Update publication metadata
                session.run(
                    """
                    MATCH (p:Publication {eid: $eid})
                    SET p.crossref_data = $crossref_data,
                        p.publisher = $publisher,
                        p.journal_issn = $issn,
                        p.publication_date = $published,
                        p.crossref_last_updated = datetime()
                """,
                    eid=eid,
                    crossref_data=json.dumps(crossref_data),
                    publisher=crossref_data.get("publisher"),
                    issn=crossref_data.get("ISSN", [None])[0]
                    if crossref_data.get("ISSN")
                    else None,
                    published=crossref_data.get(
                        "published-print", crossref_data.get("published-online")
                    ),
                )

                updated += 1
                print("✓ Updated CrossRef metadata")
            else:
                print("✗ Could not fetch updated CrossRef data")

        return updated


def integrate_crossref_data(
    neo4j_config: Neo4jConnectionConfig,
    enrich_publications: bool = True,
    update_metadata: bool = True,
    validate_only: bool = False,
) -> dict[str, Any]:
    """Complete CrossRef data integration process.

    Args:
        neo4j_config: Neo4j connection configuration
        enrich_publications: Whether to enrich publications with CrossRef data
        update_metadata: Whether to update existing CrossRef metadata
        validate_only: Only validate without making changes

    Returns:
        Dictionary with integration results and statistics
    """
    print("\n" + "=" * 80)
    print("NEO4J CROSSREF DATA INTEGRATION PROCESS")
    print("=" * 80 + "\n")

    # Connect to Neo4j
    driver = connect_to_neo4j(neo4j_config)
    if driver is None:
        return {"success": False, "error": "Failed to connect to Neo4j"}

    results: dict[str, Any] = {
        "success": True,
        "integrations": {
            "publications_enriched": 0,
            "metadata_updated": 0,
        },
        "initial_stats": {},
        "final_stats": {},
    }

    try:
        # Validate current state
        print("Validating current CrossRef data...")
        initial_stats = validate_crossref_data(driver, neo4j_config.database)
        results["initial_stats"] = initial_stats

        if validate_only:
            results["final_stats"] = initial_stats
            return results

        # Apply integrations
        if enrich_publications:
            count = enrich_publications_with_crossref(driver, neo4j_config.database)
            results["integrations"]["publications_enriched"] = count  # type: ignore

        if update_metadata:
            count = update_crossref_metadata(driver, neo4j_config.database)
            results["integrations"]["metadata_updated"] = count  # type: ignore

        # Final validation
        print("\nValidating final CrossRef data...")
        final_stats = validate_crossref_data(driver, neo4j_config.database)
        results["final_stats"] = final_stats

        total_integrations = sum(results["integrations"].values())  # type: ignore
        print("\n✅ CrossRef data integration completed successfully!")
        print(f"Total integrations applied: {total_integrations}")

        return results

    except Exception as e:
        print(f"Error during CrossRef integration: {e}")
        import traceback

        results["success"] = False
        results["error"] = str(e)
        results["traceback"] = traceback.format_exc()
        return results
    finally:
        driver.close()
        print("Neo4j connection closed")
