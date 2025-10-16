"""
Neo4j data completion utilities for DeepCritical.

This module provides functions to complete missing data in Neo4j databases,
including fetching additional publication details, cross-referencing data,
and enriching existing records.
"""

from __future__ import annotations

import json
import time
from typing import Any, Dict, List, Optional, TypedDict

from neo4j import GraphDatabase

from ..datatypes.neo4j_types import Neo4jConnectionConfig


class CompletionsApplied(TypedDict):
    """Structure for applied completions."""

    abstracts_added: int
    citations_added: int
    authors_enriched: int
    semantic_keywords_added: int
    metrics_updated: Any


class CompleteDataResults(TypedDict, total=False):
    """Structure for data completion operation results."""

    success: bool
    completions: CompletionsApplied
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


def enrich_publications_with_abstracts(
    driver: Any, database: str, batch_size: int = 10
) -> int:
    """Enrich publications with missing abstracts.

    Args:
        driver: Neo4j driver
        database: Database name
        batch_size: Number of publications to process per batch

    Returns:
        Number of publications enriched
    """
    print("--- ENRICHING PUBLICATIONS WITH ABSTRACTS ---")

    with driver.session(database=database) as session:
        # Find publications without abstracts
        result = session.run(
            """
            MATCH (p:Publication)
            WHERE p.abstract IS NULL OR p.abstract = ""
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

            print(f"Processing: {title[:50]}...")

            # Try to get abstract from DOI or EID
            abstract = fetch_abstract(eid, doi)

            if abstract:
                session.run(
                    """
                    MATCH (p:Publication {eid: $eid})
                    SET p.abstract = $abstract
                """,
                    eid=eid,
                    abstract=abstract,
                )

                enriched += 1
                print(f"✓ Added abstract ({len(abstract)} chars)")
            else:
                print("✗ Could not fetch abstract")

            # Rate limiting
            time.sleep(0.5)

        return enriched


def fetch_abstract(eid: str, doi: str | None = None) -> str | None:
    """Fetch abstract for a publication.

    Args:
        eid: Scopus EID
        doi: DOI if available

    Returns:
        Abstract text or None if not found
    """
    try:
        from pybliometrics.scopus import AbstractRetrieval  # type: ignore

        identifier = doi if doi else eid

        # Rate limiting
        time.sleep(0.5)

        ab = AbstractRetrieval(identifier, view="FULL")

        if hasattr(ab, "abstract") and ab.abstract:
            return ab.abstract
        if hasattr(ab, "description") and ab.description:
            return ab.description

        return None
    except Exception as e:
        print(f"Error fetching abstract for {identifier}: {e}")
        return None


def enrich_publications_with_citations(
    driver: Any, database: str, batch_size: int = 20
) -> int:
    """Enrich publications with citation relationships.

    Args:
        driver: Neo4j driver
        database: Database name
        batch_size: Number of publications to process per batch

    Returns:
        Number of citation relationships created
    """
    print("--- ENRICHING PUBLICATIONS WITH CITATIONS ---")

    with driver.session(database=database) as session:
        # Find publications without citation relationships
        result = session.run(
            """
            MATCH (p:Publication)
            WHERE NOT (p)-[:CITES]->()
            RETURN p.eid AS eid, p.doi AS doi, p.title AS title
            LIMIT $batch_size
        """,
            batch_size=batch_size,
        )

        citations_added = 0

        for record in result:
            eid = record["eid"]
            doi = record["doi"]
            title = record["title"]

            print(f"Processing citations for: {title[:50]}...")

            # Fetch references/citations
            references = fetch_references(eid, doi)

            if references:
                for ref in references[:50]:  # Limit to avoid overwhelming the graph
                    # Create cited publication if it exists
                    cited_eid = ref.get("eid") or ref.get("doi")
                    if cited_eid:
                        session.run(
                            """
                            MERGE (cited:Publication {eid: $cited_eid})
                            SET cited.title = $cited_title,
                                cited.year = $cited_year
                            WITH cited
                            MATCH (citing:Publication {eid: $citing_eid})
                            MERGE (citing)-[:CITES]->(cited)
                        """,
                            cited_eid=cited_eid,
                            cited_title=ref.get("title", ""),
                            cited_year=ref.get("year", ""),
                            citing_eid=eid,
                        )

                        citations_added += 1

                print(f"✓ Added {len(references)} citation relationships")
            else:
                print("✗ No references found")

        return citations_added


def fetch_references(eid: str, doi: str | None = None) -> list[dict[str, Any]] | None:
    """Fetch references for a publication.

    Args:
        eid: Scopus EID
        doi: DOI if available

    Returns:
        List of reference dictionaries or None if not found
    """
    try:
        from pybliometrics.scopus import AbstractRetrieval  # type: ignore

        identifier = doi if doi else eid

        # Rate limiting
        time.sleep(0.5)

        ab = AbstractRetrieval(identifier, view="FULL")

        references = []

        if hasattr(ab, "references") and ab.references:
            for ref in ab.references:
                ref_data = {
                    "eid": getattr(ref, "eid", None),
                    "doi": getattr(ref, "doi", None),
                    "title": getattr(ref, "title", ""),
                    "year": getattr(ref, "year", ""),
                    "authors": getattr(ref, "authors", ""),
                }
                references.append(ref_data)

        return references if references else None
    except Exception as e:
        print(f"Error fetching references for {identifier}: {e}")
        return None


def enrich_authors_with_details(
    driver: Any, database: str, batch_size: int = 15
) -> int:
    """Enrich authors with additional details from Scopus.

    Args:
        driver: Neo4j driver
        database: Database name
        batch_size: Number of authors to process per batch

    Returns:
        Number of authors enriched
    """
    print("--- ENRICHING AUTHORS WITH DETAILS ---")

    with driver.session(database=database) as session:
        # Find authors without detailed information
        result = session.run(
            """
            MATCH (a:Author)
            WHERE a.orcid IS NULL AND a.affiliation IS NULL
            RETURN a.id AS author_id, a.name AS name
            LIMIT $batch_size
        """,
            batch_size=batch_size,
        )

        enriched = 0

        for record in result:
            author_id = record["author_id"]
            name = record["name"]

            print(f"Processing author: {name}")

            # Fetch author details
            author_details = fetch_author_details(author_id)

            if author_details:
                session.run(
                    """
                    MATCH (a:Author {id: $author_id})
                    SET a.orcid = $orcid,
                        a.h_index = $h_index,
                        a.citation_count = $citation_count,
                        a.document_count = $document_count,
                        a.affiliation = $affiliation,
                        a.country = $country
                """,
                    author_id=author_id,
                    orcid=author_details.get("orcid"),
                    h_index=author_details.get("h_index"),
                    citation_count=author_details.get("citation_count"),
                    document_count=author_details.get("document_count"),
                    affiliation=author_details.get("affiliation"),
                    country=author_details.get("country"),
                )

                enriched += 1
                print(f"✓ Enriched author with {len(author_details)} fields")
            else:
                print("✗ Could not fetch author details")

            # Rate limiting
            time.sleep(0.3)

        return enriched


def fetch_author_details(author_id: str) -> dict[str, Any] | None:
    """Fetch detailed information for an author.

    Args:
        author_id: Scopus author ID

    Returns:
        Dictionary with author details or None if not found
    """
    try:
        from pybliometrics.scopus import AuthorRetrieval  # type: ignore

        # Rate limiting
        time.sleep(0.3)

        author = AuthorRetrieval(author_id)

        details = {}

        if hasattr(author, "orcid"):
            details["orcid"] = author.orcid

        if hasattr(author, "h_index"):
            details["h_index"] = author.h_index

        if hasattr(author, "citation_count"):
            details["citation_count"] = author.citation_count

        if hasattr(author, "document_count"):
            details["document_count"] = author.document_count

        if hasattr(author, "affiliation_current"):
            affiliation = author.affiliation_current
            if affiliation:
                details["affiliation"] = (
                    getattr(affiliation[0], "name", "") if affiliation else None
                )
                details["country"] = (
                    getattr(affiliation[0], "country", "") if affiliation else None
                )

        return details if details else None
    except Exception as e:
        print(f"Error fetching author details for {author_id}: {e}")
        return None


def add_semantic_keywords(driver: Any, database: str, batch_size: int = 10) -> int:
    """Add semantic keywords to publications.

    Args:
        driver: Neo4j driver
        database: Database name
        batch_size: Number of publications to process per batch

    Returns:
        Number of semantic keywords added
    """
    print("--- ADDING SEMANTIC KEYWORDS ---")

    with driver.session(database=database) as session:
        # Find publications without semantic keywords
        result = session.run(
            """
            MATCH (p:Publication)
            WHERE NOT (p)-[:HAS_SEMANTIC_KEYWORD]->()
            AND p.abstract IS NOT NULL
            RETURN p.eid AS eid, p.abstract AS abstract, p.title AS title
            LIMIT $batch_size
        """,
            batch_size=batch_size,
        )

        keywords_added = 0

        for record in result:
            eid = record["eid"]
            abstract = record["abstract"]
            title = record["title"]

            print(f"Processing: {title[:50]}...")

            # Extract semantic keywords
            keywords = extract_semantic_keywords(title, abstract)

            if keywords:
                for keyword in keywords:
                    session.run(
                        """
                        MERGE (sk:SemanticKeyword {name: $keyword})
                        WITH sk
                        MATCH (p:Publication {eid: $eid})
                        MERGE (p)-[:HAS_SEMANTIC_KEYWORD]->(sk)
                    """,
                        keyword=keyword.lower(),
                        eid=eid,
                    )

                    keywords_added += 1

                print(f"✓ Added {len(keywords)} semantic keywords")
            else:
                print("✗ No semantic keywords extracted")

        return keywords_added


def extract_semantic_keywords(title: str, abstract: str) -> list[str]:
    """Extract semantic keywords from title and abstract.

    Args:
        title: Publication title
        abstract: Publication abstract

    Returns:
        List of semantic keywords
    """
    # Simple keyword extraction - could be enhanced with NLP
    text = f"{title} {abstract}".lower()

    # Remove common stop words
    stop_words = {
        "the",
        "a",
        "an",
        "and",
        "or",
        "but",
        "in",
        "on",
        "at",
        "to",
        "for",
        "of",
        "with",
        "by",
        "is",
        "are",
        "was",
        "were",
        "be",
        "been",
        "being",
        "have",
        "has",
        "had",
        "do",
        "does",
        "did",
        "will",
        "would",
        "could",
        "should",
        "may",
        "might",
        "must",
        "can",
        "this",
        "that",
        "these",
        "those",
        "i",
        "you",
        "he",
        "she",
        "it",
        "we",
        "they",
        "me",
        "him",
        "her",
        "us",
        "them",
        "my",
        "your",
        "his",
        "its",
        "our",
        "their",
    }

    words = []
    for word in text.split():
        word = word.strip(".,!?;:()[]{}\"'")
        if len(word) > 3 and word not in stop_words:
            words.append(word)

    # Get most frequent meaningful words
    word_freq = {}
    for word in words:
        word_freq[word] = word_freq.get(word, 0) + 1

    # Return top keywords
    sorted_words = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)
    return [word for word, freq in sorted_words[:10] if freq > 1]


def update_publication_metrics(driver: Any, database: str) -> dict[str, int]:
    """Update publication metrics like citation counts.

    Args:
        driver: Neo4j driver
        database: Database name

    Returns:
        Dictionary with update statistics
    """
    print("--- UPDATING PUBLICATION METRICS ---")

    stats = {"publications_updated": 0, "errors": 0}

    with driver.session(database=database) as session:
        # Find publications that need metric updates
        result = session.run("""
            MATCH (p:Publication)
            WHERE p.last_metrics_update IS NULL
            OR p.last_metrics_update < datetime() - duration('P30D')
            RETURN p.eid AS eid, p.doi AS doi, p.citedBy AS current_citations
            LIMIT 50
        """)

        for record in result:
            eid = record["eid"]
            doi = record["doi"]
            current_citations = record["current_citations"]

            print(f"Updating metrics for: {eid}")

            # Fetch updated metrics
            metrics = fetch_publication_metrics(eid, doi)

            if metrics:
                session.run(
                    """
                    MATCH (p:Publication {eid: $eid})
                    SET p.citedBy = $cited_by,
                        p.last_metrics_update = datetime(),
                        p.metrics_source = $source
                """,
                    eid=eid,
                    cited_by=metrics.get("cited_by", current_citations),
                    source=metrics.get("source", "unknown"),
                )

                stats["publications_updated"] += 1
                print(f"✓ Updated metrics: {metrics}")
            else:
                stats["errors"] += 1
                print("✗ Could not fetch updated metrics")

            # Rate limiting
            time.sleep(0.5)

        return stats


def fetch_publication_metrics(
    eid: str, doi: str | None = None
) -> dict[str, Any] | None:
    """Fetch updated metrics for a publication.

    Args:
        eid: Scopus EID
        doi: DOI if available

    Returns:
        Dictionary with metrics or None if not found
    """
    try:
        from pybliometrics.scopus import AbstractRetrieval  # type: ignore

        identifier = doi if doi else eid

        # Rate limiting
        time.sleep(0.5)

        ab = AbstractRetrieval(identifier, view="FULL")

        metrics = {}

        if hasattr(ab, "citedby_count"):
            metrics["cited_by"] = ab.citedby_count

        metrics["source"] = "scopus"

        return metrics if metrics else None
    except Exception as e:
        print(f"Error fetching metrics for {identifier}: {e}")
        return None


def validate_data_completeness(driver: Any, database: str) -> dict[str, Any]:
    """Validate data completeness and return statistics.

    Args:
        driver: Neo4j driver
        database: Database name

    Returns:
        Dictionary with completeness statistics
    """
    print("--- VALIDATING DATA COMPLETENESS ---")

    with driver.session(database=database) as session:
        stats = {}

        # Publication completeness
        result = session.run("""
            MATCH (p:Publication)
            RETURN count(p) AS total_publications,
                   count(CASE WHEN p.abstract IS NOT NULL AND p.abstract <> '' THEN 1 END) AS publications_with_abstracts,
                   count(CASE WHEN p.doi IS NOT NULL THEN 1 END) AS publications_with_doi,
                   count(CASE WHEN (p)-[:CITES]->() THEN 1 END) AS publications_with_citations
        """)

        record = result.single()
        stats["publications"] = {
            "total": record["total_publications"],
            "with_abstracts": record["publications_with_abstracts"],
            "with_doi": record["publications_with_doi"],
            "with_citations": record["publications_with_citations"],
        }

        # Author completeness
        result = session.run("""
            MATCH (a:Author)
            RETURN count(a) AS total_authors,
                   count(CASE WHEN a.orcid IS NOT NULL THEN 1 END) AS authors_with_orcid,
                   count(CASE WHEN (a)-[:AFFILIATED_WITH]->() THEN 1 END) AS authors_with_affiliations
        """)

        record = result.single()
        stats["authors"] = {
            "total": record["total_authors"],
            "with_orcid": record["authors_with_orcid"],
            "with_affiliations": record["authors_with_affiliations"],
        }

        # Relationship counts
        result = session.run("""
            MATCH ()-[r:AUTHORED]->() RETURN count(r) AS authored_relationships
        """)
        stats["authored_relationships"] = result.single()["authored_relationships"]

        result = session.run("""
            MATCH ()-[r:CITES]->() RETURN count(r) AS citation_relationships
        """)
        stats["citation_relationships"] = result.single()["citation_relationships"]

        result = session.run("""
            MATCH ()-[r:HAS_KEYWORD]->() RETURN count(r) AS keyword_relationships
        """)
        stats["keyword_relationships"] = result.single()["keyword_relationships"]

        # Print statistics
        print("Data Completeness Statistics:")
        print(f"Publications: {stats['publications']['total']}")
        print(
            f"  With abstracts: {stats['publications']['with_abstracts']} ({stats['publications']['with_abstracts'] / max(stats['publications']['total'], 1) * 100:.1f}%)"
        )
        print(
            f"  With DOI: {stats['publications']['with_doi']} ({stats['publications']['with_doi'] / max(stats['publications']['total'], 1) * 100:.1f}%)"
        )
        print(
            f"  With citations: {stats['publications']['with_citations']} ({stats['publications']['with_citations'] / max(stats['publications']['total'], 1) * 100:.1f}%)"
        )
        print(f"Authors: {stats['authors']['total']}")
        print(
            f"  With ORCID: {stats['authors']['with_orcid']} ({stats['authors']['with_orcid'] / max(stats['authors']['total'], 1) * 100:.1f}%)"
        )
        print(
            f"  With affiliations: {stats['authors']['with_affiliations']} ({stats['authors']['with_affiliations'] / max(stats['authors']['total'], 1) * 100:.1f}%)"
        )
        print(
            f"Relationships: {stats['authored_relationships']} authored, {stats['citation_relationships']} citations, {stats['keyword_relationships']} keywords"
        )

        return stats


def complete_database_data(
    neo4j_config: Neo4jConnectionConfig,
    enrich_abstracts: bool = True,
    enrich_citations: bool = True,
    enrich_authors: bool = True,
    add_semantic_keywords_flag: bool = True,
    update_metrics: bool = True,
    validate_only: bool = False,
) -> CompleteDataResults:
    """Complete missing data in the Neo4j database.

    Args:
        neo4j_config: Neo4j connection configuration
        enrich_abstracts: Whether to enrich publications with abstracts
        enrich_citations: Whether to add citation relationships
        enrich_authors: Whether to enrich author details
        add_semantic_keywords_flag: Whether to add semantic keywords
        update_metrics: Whether to update publication metrics
        validate_only: Only validate without making changes

    Returns:
        Dictionary with completion results and statistics
    """
    print("\n" + "=" * 80)
    print("NEO4J DATA COMPLETION PROCESS")
    print("=" * 80 + "\n")

    # Connect to Neo4j
    driver = connect_to_neo4j(neo4j_config)
    if driver is None:
        return {"success": False, "error": "Failed to connect to Neo4j"}

    results: CompleteDataResults = {
        "success": True,
        "completions": {
            "abstracts_added": 0,
            "citations_added": 0,
            "authors_enriched": 0,
            "semantic_keywords_added": 0,
            "metrics_updated": {},
        },
        "initial_stats": {},
        "final_stats": {},
        "error": None,
    }

    try:
        # Validate current completeness
        print("Validating current data completeness...")
        initial_stats = validate_data_completeness(driver, neo4j_config.database)
        results["initial_stats"] = initial_stats

        if validate_only:
            results["final_stats"] = initial_stats
            return results

        # Apply completions
        if enrich_abstracts:
            count = enrich_publications_with_abstracts(driver, neo4j_config.database)
            results["completions"]["abstracts_added"] = count

        if enrich_citations:
            count = enrich_publications_with_citations(driver, neo4j_config.database)
            results["completions"]["citations_added"] = count

        if enrich_authors:
            count = enrich_authors_with_details(driver, neo4j_config.database)
            results["completions"]["authors_enriched"] = count

        if add_semantic_keywords_flag:
            count = add_semantic_keywords(driver, neo4j_config.database)
            results["completions"]["semantic_keywords_added"] = count

        if update_metrics:
            metrics_stats = update_publication_metrics(driver, neo4j_config.database)
            results["completions"]["metrics_updated"] = metrics_stats

        # Final validation
        print("\nValidating final data completeness...")
        final_stats = validate_data_completeness(driver, neo4j_config.database)
        results["final_stats"] = final_stats

        total_completions = sum(
            count for count in results["completions"].values() if isinstance(count, int)
        )
        print("\n✅ Data completion completed successfully!")
        print(f"Total completions applied: {total_completions}")

        return results

    except Exception as e:
        print(f"Error during data completion: {e}")
        import traceback

        results["success"] = False
        results["error"] = str(e)
        results["traceback"] = traceback.format_exc()
        return results
    finally:
        driver.close()
        print("Neo4j connection closed")
