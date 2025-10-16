"""
Neo4j database rebuild utilities for DeepCritical.

This module provides functions to rebuild and populate Neo4j databases
with publication data from Scopus and Crossref APIs. It handles data
enrichment, constraint creation, and batch processing without interactive prompts.
"""

from __future__ import annotations

import hashlib
import json
import os
import time
from datetime import datetime
from typing import Any, Dict, List, Optional

import pandas as pd
from neo4j import GraphDatabase

from ..datatypes.neo4j_types import (
    Neo4jConnectionConfig,
    Neo4jMigrationConfig,
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


def clear_database(driver: Any, database: str) -> bool:
    """Clear the entire database.

    Args:
        driver: Neo4j driver
        database: Database name

    Returns:
        True if successful
    """
    print("--- CLEARING DATABASE ---")

    with driver.session(database=database) as session:
        try:
            session.run("MATCH (n) DETACH DELETE n")
            print("Database cleared successfully")
            return True
        except Exception as e:
            print(f"Error clearing database: {e}")
            return False


def create_constraints(driver: Any, database: str) -> bool:
    """Create database constraints and indexes.

    Args:
        driver: Neo4j driver
        database: Database name

    Returns:
        True if successful
    """
    print("--- CREATING CONSTRAINTS AND INDEXES ---")

    constraints = [
        "CREATE CONSTRAINT IF NOT EXISTS FOR (p:Publication) REQUIRE p.eid IS UNIQUE",
        "CREATE CONSTRAINT IF NOT EXISTS FOR (a:Author) REQUIRE a.id IS UNIQUE",
        "CREATE CONSTRAINT IF NOT EXISTS FOR (k:Keyword) REQUIRE k.name IS UNIQUE",
        "CREATE CONSTRAINT IF NOT EXISTS FOR (sk:SemanticKeyword) REQUIRE sk.name IS UNIQUE",
        "CREATE CONSTRAINT IF NOT EXISTS FOR (j:Journal) REQUIRE j.name IS UNIQUE",
        "CREATE CONSTRAINT IF NOT EXISTS FOR (c:Country) REQUIRE c.name IS UNIQUE",
        "CREATE CONSTRAINT IF NOT EXISTS FOR (i:Institution) REQUIRE i.name IS UNIQUE",
        "CREATE CONSTRAINT IF NOT EXISTS FOR (g:Grant) REQUIRE (g.agency, g.string) IS UNIQUE",
        "CREATE CONSTRAINT IF NOT EXISTS FOR (fa:FundingAgency) REQUIRE fa.name IS UNIQUE",
    ]

    indexes = [
        "CREATE INDEX IF NOT EXISTS FOR (p:Publication) ON (p.year)",
        "CREATE INDEX IF NOT EXISTS FOR (p:Publication) ON (p.citedBy)",
        "CREATE INDEX IF NOT EXISTS FOR (j:Journal) ON (j.name)",
        "CREATE INDEX IF NOT EXISTS FOR (p:Publication) ON (p.year, p.citedBy)",
        "CREATE INDEX IF NOT EXISTS FOR (k:Keyword) ON (k.name)",
        "CREATE INDEX IF NOT EXISTS FOR (i:Institution) ON (i.name)",
    ]

    with driver.session(database=database) as session:
        success = True

        for constraint in constraints:
            try:
                session.run(constraint)
                print(f"✓ Created constraint: {constraint.split('FOR')[1].strip()}")
            except Exception as e:
                print(f"✗ Error creating constraint: {e}")
                success = False

        for index in indexes:
            try:
                session.run(index)
                print(f"✓ Created index: {index.split('ON')[1].strip()}")
            except Exception as e:
                print(f"✗ Error creating index: {e}")
                success = False

        return success


def initialize_search(
    query: str, data_dir: str, max_papers: int | None = None
) -> pd.DataFrame | None:
    """Initialize search and return results DataFrame.

    Args:
        query: Search query
        data_dir: Directory to store results
        max_papers: Maximum number of papers to retrieve

    Returns:
        DataFrame with search results or None if failed
    """
    print("--- INITIALIZING SCOPUS SEARCH ---")

    # Create unique hash for this query
    query_hash = hashlib.md5(query.encode()).hexdigest()[:8]
    search_file = os.path.join(data_dir, f"search_results_{query_hash}.json")

    print(f"Query hash: {query_hash}")
    print(f"Results file: {search_file}")

    if os.path.exists(search_file):
        print(f"Using cached search results: {search_file}")
        try:
            results_df = pd.read_json(search_file)
            print(f"Loaded {len(results_df)} cached results")
            return results_df
        except Exception as e:
            print(f"Error loading cached results: {e}")

    try:
        from pybliometrics.scopus import ScopusSearch  # type: ignore

        print(f"Executing Scopus search: {query}")

        # Use COMPLETE view for comprehensive data
        search_results = ScopusSearch(query, refresh=True, view="COMPLETE")

        if not hasattr(search_results, "results"):
            print("Search returned no results object")
            return None

        if hasattr(search_results, "get_results_size"):
            results_size = search_results.get_results_size()
            print(f"Found {results_size} results")

        results_df = pd.DataFrame(search_results.results)

        if results_df is None or results_df.empty:
            print("Search returned empty DataFrame")
            return None

        # Limit results if specified
        if max_papers and len(results_df) > max_papers:
            results_df = results_df.head(max_papers)
            print(f"Limited to {max_papers} papers")

        results_df.to_json(search_file)
        print(f"Search results saved to: {search_file}")

        return results_df

    except Exception as e:
        print(f"Error during Scopus search: {e}")
        import traceback

        print(f"Traceback: {traceback.format_exc()}")
        return None


def enrich_publication_data(
    df: pd.DataFrame,
    data_dir: str,
    max_papers: int | None = None,
    query_hash: str = "default",
) -> pd.DataFrame | None:
    """Enrich publication data with additional information.

    Args:
        df: DataFrame with search results
        data_dir: Directory for storing enriched data
        max_papers: Maximum papers to enrich
        query_hash: Query hash for caching

    Returns:
        DataFrame with enriched data or None if failed
    """
    print("--- ENRICHING PUBLICATION DATA ---")

    enriched_file = os.path.join(data_dir, f"enriched_data_{query_hash}.json")

    if os.path.exists(enriched_file):
        print(f"Using cached enriched data: {enriched_file}")
        try:
            enriched_df = pd.read_json(enriched_file)
            print(f"Loaded {len(enriched_df)} enriched records")
            return enriched_df
        except Exception as e:
            print(f"Error loading cached enriched data: {e}")

    if df is None or len(df) == 0:
        print("No data to enrich")
        return None

    try:
        from pybliometrics.scopus import AbstractRetrieval  # type: ignore

        enriched_data = []
        papers_to_process = len(df) if max_papers is None else min(len(df), max_papers)
        print(f"Enriching data for {papers_to_process} publications...")

        for i, row in df.iloc[:papers_to_process].iterrows():
            try:
                print(
                    f"Processing {i + 1}/{papers_to_process}: {row.get('title', 'No title')[:50]}..."
                )

                # Extract authors and affiliations
                authors_data = extract_authors_and_affiliations_from_search(row)

                # Extract keywords
                keywords = []
                if hasattr(row, "authkeywords") and row.authkeywords:
                    keywords.extend(row.authkeywords.split(";"))
                if hasattr(row, "idxterms") and row.idxterms:
                    keywords.extend(row.idxterms.split(";"))

                keywords = [k.strip().lower() for k in keywords if k and k.strip()]

                # Extract affiliations
                institutions = []
                countries = []
                affiliations_detailed = []

                for author_data in authors_data:
                    for aff_id in author_data["affiliations"]:
                        if aff_id:
                            aff_details = get_affiliation_details(aff_id)
                            if aff_details:
                                affiliations_detailed.append(aff_details)
                                if aff_details["name"]:
                                    institutions.append(aff_details["name"])
                                if aff_details["country"]:
                                    countries.append(aff_details["country"])

                # Remove duplicates
                institutions = list(set(institutions))
                countries = list(set(countries))

                # Try to get abstract and funding info
                abstract_text = ""
                grants = []
                funding_agencies = []
                identifier = row.get("doi", row.get("eid", None))

                if identifier:
                    try:
                        time.sleep(0.5)  # Rate limiting
                        ab = AbstractRetrieval(identifier, view="FULL")

                        if hasattr(ab, "abstract") and ab.abstract:
                            abstract_text = ab.abstract
                        elif hasattr(ab, "description") and ab.description:
                            abstract_text = ab.description

                        # Extract funding information
                        if hasattr(ab, "funding") and ab.funding:
                            for funding in ab.funding:
                                grant_info = {
                                    "agency": getattr(funding, "agency", ""),
                                    "agency_id": getattr(funding, "agency_id", ""),
                                    "string": getattr(funding, "string", ""),
                                    "acronym": getattr(funding, "acronym", ""),
                                }
                                grants.append(grant_info)

                                if grant_info["agency"]:
                                    funding_agencies.append(grant_info["agency"])

                    except Exception as e:
                        print(f"Could not retrieve abstract for {identifier}: {e}")

                # Create enriched record
                record = {
                    "eid": row.get("eid", ""),
                    "doi": row.get("doi", ""),
                    "title": row.get("title", ""),
                    "authors": [author["name"] for author in authors_data],
                    "author_ids": [author["id"] for author in authors_data],
                    "year": row.get("coverDate", "")[:4]
                    if row.get("coverDate")
                    else "",
                    "source_title": row.get("publicationName", ""),
                    "cited_by": int(row.get("citedby_count", 0))
                    if row.get("citedby_count")
                    else 0,
                    "abstract": abstract_text,
                    "keywords": keywords,
                    "affiliations": affiliations_detailed,
                    "institutions": institutions,
                    "countries": countries,
                    "grants": grants,
                    "funding_agencies": funding_agencies,
                    "affiliation": countries[0] if countries else "",
                    "source_id": row.get("source_id", ""),
                    "authors_with_affiliations": authors_data,
                }

                enriched_data.append(record)

                title_str = str(record.get("title", "No title"))
                print(f"✓ Title: {title_str[:50]}...")
                print(f"✓ Authors: {len(authors_data)} found")
                print(
                    f"✓ Abstract: {'Yes' if abstract_text else 'No'} ({len(abstract_text)} chars)"
                )
                print(f"✓ Keywords: {len(keywords)} found")
                print(f"✓ Institutions: {len(institutions)} found")
                print(f"✓ Countries: {len(countries)} found")

                # Save checkpoint every 5 records
                if (len(enriched_data) % 5 == 0) or (i + 1 == papers_to_process):
                    temp_df = pd.DataFrame(enriched_data)
                    temp_file = os.path.join(
                        data_dir,
                        f"enriched_data_temp_{query_hash}_{len(enriched_data)}.json",
                    )
                    temp_df.to_json(temp_file)
                    print(f"Checkpoint saved: {temp_file}")

            except Exception as e:
                print(f"Error processing publication {i}: {e}")
                import traceback

                print(f"Traceback: {traceback.format_exc()}")
                continue

        if not enriched_data:
            print("No publications could be enriched")
            return None

        enriched_df = pd.DataFrame(enriched_data)
        enriched_df.to_json(enriched_file)
        print(f"Enriched data saved to: {enriched_file}")

        return enriched_df

    except ImportError as e:
        print(f"Import error: {e}. Installing pybliometrics...")
        try:
            import subprocess

            subprocess.check_call(["pip", "install", "pybliometrics"])
            print("pybliometrics installed, retrying enrichment...")
            return enrich_publication_data(df, data_dir, max_papers, query_hash)
        except Exception as install_e:
            print(f"Could not install pybliometrics: {install_e}")
            return None
    except Exception as e:
        print(f"General error during enrichment: {e}")
        import traceback

        print(f"Traceback: {traceback.format_exc()}")
        return None


def extract_authors_and_affiliations_from_search(
    pub: pd.Series,
) -> list[dict[str, Any]]:
    """Extract authors and affiliations from ScopusSearch result.

    Args:
        pub: Publication row from DataFrame

    Returns:
        List of author data dictionaries
    """
    authors_data = []

    if not hasattr(pub, "author_ids") or not pub.author_ids:
        print("No author_ids found in publication")
        return authors_data

    # Split author IDs and affiliations
    authors = pub.author_ids.split(";") if pub.author_ids else []
    affs = (
        pub.author_afids.split(";")
        if hasattr(pub, "author_afids") and pub.author_afids
        else []
    )

    # Get author names
    author_names = []
    if hasattr(pub, "author_names") and pub.author_names:
        author_names = pub.author_names.split(";")
    elif hasattr(pub, "authors") and pub.authors:
        author_names = pub.authors.split(";")

    # Clean data
    authors = [a.strip() for a in authors if a.strip()]
    affs = [a.strip() for a in affs if a.strip()]
    author_names = [a.strip() for a in author_names if a.strip()]

    # Ensure lists have same length
    max_len = max(len(authors), len(author_names))
    while len(authors) < max_len:
        authors.append("")
    while len(author_names) < max_len:
        author_names.append("")
    while len(affs) < max_len:
        affs.append("")

    # Create author data
    for i in range(max_len):
        if authors[i]:  # Only process if we have an author ID
            author_affs = affs[i].split("-") if affs[i] else []
            author_affs = [aff.strip() for aff in author_affs if aff.strip()]

            authors_data.append(
                {
                    "id": authors[i],
                    "name": author_names[i]
                    if i < len(author_names)
                    else f"Author_{authors[i]}",
                    "affiliations": author_affs,
                }
            )

    return authors_data


def get_affiliation_details(affiliation_id: str) -> dict[str, str] | None:
    """Get detailed affiliation information.

    Args:
        affiliation_id: Scopus affiliation ID

    Returns:
        Dictionary with affiliation details or None if failed
    """
    try:
        from pybliometrics.scopus import AffiliationRetrieval  # type: ignore

        if not affiliation_id or affiliation_id == "":
            return None

        aff = AffiliationRetrieval(affiliation_id)

        return {
            "id": affiliation_id,
            "name": getattr(aff, "affiliation_name", ""),
            "country": getattr(aff, "country", ""),
            "city": getattr(aff, "city", ""),
            "address": getattr(aff, "address", ""),
        }
    except Exception as e:
        print(f"Could not get affiliation details for {affiliation_id}: {e}")
        return {
            "id": affiliation_id,
            "name": f"Institution_{affiliation_id}",
            "country": "",
            "city": "",
            "address": "",
        }


def import_data_to_neo4j(
    driver: Any,
    data_df: pd.DataFrame,
    database: str,
    query_hash: str = "default",
    batch_size: int = 50,
) -> int:
    """Import enriched data to Neo4j.

    Args:
        driver: Neo4j driver
        data_df: DataFrame with enriched publication data
        database: Database name
        query_hash: Query hash for progress tracking
        batch_size: Batch size for processing

    Returns:
        Number of publications imported
    """
    print("--- IMPORTING DATA TO NEO4J ---")

    if data_df is None or len(data_df) == 0:
        print("No data to import")
        return 0

    progress_file = os.path.join("data", f"import_progress_{query_hash}.json")
    start_index = 0

    # Load progress if exists
    if os.path.exists(progress_file):
        try:
            with open(progress_file) as f:
                progress_data = json.load(f)
                start_index = progress_data.get("last_index", 0)
        except Exception as e:
            print(f"Error loading progress: {e}")

    total_publications = len(data_df)
    end_index = total_publications

    print(
        f"Importing publications {start_index + 1}-{end_index} of {total_publications}"
    )

    with driver.session(database=database) as session:
        for i in range(start_index, end_index, batch_size):
            batch_end = min(i + batch_size, end_index)
            batch = data_df.iloc[i:batch_end]

            with session.begin_transaction() as tx:
                for _, pub in batch.iterrows():
                    eid = pub.get("eid", "")
                    if not eid:
                        continue

                    # Create publication
                    tx.run(
                        """
                        MERGE (p:Publication {eid: $eid})
                        SET p.title = $title,
                            p.year = $year,
                            p.doi = $doi,
                            p.citedBy = $cited_by,
                            p.abstract = $abstract
                    """,
                        eid=eid,
                        title=pub.get("title", ""),
                        year=pub.get("year", ""),
                        doi=pub.get("doi", ""),
                        cited_by=int(pub.get("cited_by", 0)),
                        abstract=pub.get("abstract", ""),
                    )

                    # Create journal
                    journal_name = pub.get("source_title")
                    if journal_name:
                        tx.run(
                            """
                            MERGE (j:Journal {name: $journal_name})
                            WITH j
                            MATCH (p:Publication {eid: $eid})
                            MERGE (p)-[:PUBLISHED_IN]->(j)
                        """,
                            journal_name=journal_name,
                            eid=eid,
                        )

                    # Create authors with affiliations
                    authors_with_affs = pub.get("authors_with_affiliations", [])
                    if authors_with_affs:
                        for author_data in authors_with_affs:
                            author_id = author_data.get("id")
                            author_name = author_data.get("name")

                            if author_id and author_name:
                                # Create author
                                tx.run(
                                    """
                                    MERGE (a:Author {id: $author_id})
                                    SET a.name = $author_name
                                    WITH a
                                    MATCH (p:Publication {eid: $eid})
                                    MERGE (a)-[:AUTHORED]->(p)
                                """,
                                    author_id=author_id,
                                    author_name=author_name,
                                    eid=eid,
                                )

                                # Create affiliations
                                for aff_id in author_data.get("affiliations", []):
                                    if aff_id:
                                        tx.run(
                                            """
                                            MERGE (a:Author {id: $author_id})
                                            MERGE (aff:Affiliation {id: $aff_id})
                                            MERGE (a)-[:AFFILIATED_WITH]->(aff)
                                        """,
                                            author_id=author_id,
                                            aff_id=aff_id,
                                        )

                    # Create keywords
                    keywords = pub.get("keywords", [])
                    if isinstance(keywords, list):
                        for keyword in keywords:
                            if keyword and isinstance(keyword, str):
                                tx.run(
                                    """
                                    MERGE (k:Keyword {name: $keyword})
                                    WITH k
                                    MATCH (p:Publication {eid: $eid})
                                    MERGE (p)-[:HAS_KEYWORD]->(k)
                                """,
                                    keyword=keyword.lower(),
                                    eid=eid,
                                )

                    # Create institutions and countries
                    affiliations_detailed = pub.get("affiliations", [])
                    if isinstance(affiliations_detailed, list):
                        for aff in affiliations_detailed:
                            if isinstance(aff, dict) and aff.get("name"):
                                tx.run(
                                    """
                                    MERGE (i:Institution {name: $institution})
                                    SET i.id = $aff_id,
                                        i.country = $country,
                                        i.city = $city,
                                        i.address = $address
                                    WITH i
                                    MATCH (p:Publication {eid: $eid})
                                    MERGE (p)-[:AFFILIATED_WITH]->(i)
                                """,
                                    institution=aff["name"],
                                    aff_id=aff.get("id", ""),
                                    country=aff.get("country", ""),
                                    city=aff.get("city", ""),
                                    address=aff.get("address", ""),
                                    eid=eid,
                                )

                                # Create country relationship
                                if aff.get("country"):
                                    tx.run(
                                        """
                                        MERGE (c:Country {name: $country})
                                        MERGE (i:Institution {name: $institution})
                                        MERGE (i)-[:LOCATED_IN]->(c)
                                        WITH c
                                        MATCH (p:Publication {eid: $eid})
                                        MERGE (p)-[:AFFILIATED_WITH]->(c)
                                    """,
                                        country=aff["country"],
                                        institution=aff["name"],
                                        eid=eid,
                                    )

            # Save progress
            with open(progress_file, "w") as f:
                json.dump({"last_index": batch_end}, f)

            print(f"Imported publications {i + 1}-{batch_end}/{end_index}")

    return end_index


def rebuild_neo4j_database(
    neo4j_config: Neo4jConnectionConfig,
    search_query: str,
    data_dir: str = "data",
    max_papers_search: int | None = None,
    max_papers_enrich: int | None = None,
    max_papers_import: int | None = None,
    clear_database_first: bool = False,
) -> bool:
    """Complete Neo4j database rebuild process.

    Args:
        neo4j_config: Neo4j connection configuration
        search_query: Scopus search query
        data_dir: Directory for data storage
        max_papers_search: Maximum papers from search
        max_papers_enrich: Maximum papers to enrich
        max_papers_import: Maximum papers to import
        clear_database_first: Whether to clear database before import

    Returns:
        True if successful
    """
    print("\n" + "=" * 80)
    print("NEO4J DATABASE REBUILD PROCESS")
    print("=" * 80 + "\n")

    # Create query hash
    query_hash = hashlib.md5(search_query.encode()).hexdigest()[:8]
    print(f"Query hash: {query_hash}")

    # Ensure data directory exists
    os.makedirs(data_dir, exist_ok=True)

    # Connect to Neo4j
    driver = connect_to_neo4j(neo4j_config)
    if driver is None:
        print("Failed to connect to Neo4j")
        return False

    try:
        # Clear database if requested
        if clear_database_first:
            if not clear_database(driver, neo4j_config.database):
                return False

        # Create constraints and indexes
        if not create_constraints(driver, neo4j_config.database):
            return False

        # Initialize search
        search_results = initialize_search(search_query, data_dir, max_papers_search)
        if search_results is None:
            print("Search failed")
            return False

        # Enrich publication data
        enriched_df = enrich_publication_data(
            search_results, data_dir, max_papers_enrich, query_hash
        )
        if enriched_df is None:
            print("Data enrichment failed")
            return False

        # Import to Neo4j
        imported_count = import_data_to_neo4j(
            driver, enriched_df, neo4j_config.database, query_hash
        )

        print("\n✅ Database rebuild completed successfully!")
        print(f"Imported {imported_count} publications")
        return True

    except Exception as e:
        print(f"Error during database rebuild: {e}")
        import traceback

        print(f"Traceback: {traceback.format_exc()}")
        return False
    finally:
        driver.close()
        print("Neo4j connection closed")
