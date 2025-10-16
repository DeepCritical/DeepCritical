#!/usr/bin/env python3
"""
Neo4j Database Orchestrator for DeepCritical.

This script provides a Hydra-driven entrypoint for orchestrating
Neo4j database operations including rebuild, data completion,
author fixes, and vector search setup.
"""

import sys

import hydra
from omegaconf import DictConfig

from DeepResearch.src.datatypes.neo4j_types import Neo4jConnectionConfig
from DeepResearch.src.utils.neo4j_author_fix import fix_author_data
from DeepResearch.src.utils.neo4j_complete_data import complete_database_data
from DeepResearch.src.utils.neo4j_connection_test import test_neo4j_connection
from DeepResearch.src.utils.neo4j_crossref import integrate_crossref_data
from DeepResearch.src.utils.neo4j_rebuild import rebuild_neo4j_database
from DeepResearch.src.utils.neo4j_vector_setup import setup_standard_vector_indexes


def create_neo4j_config(cfg: DictConfig) -> Neo4jConnectionConfig:
    """Create Neo4jConnectionConfig from Hydra config.

    Args:
        cfg: Hydra configuration

    Returns:
        Neo4jConnectionConfig instance
    """
    return Neo4jConnectionConfig(
        uri=getattr(cfg.neo4j, "uri", "neo4j://localhost:7687"),
        username=getattr(cfg.neo4j, "username", "neo4j"),
        password=getattr(cfg.neo4j, "password", ""),
        database=getattr(cfg.neo4j, "database", "neo4j"),
        encrypted=getattr(cfg.neo4j, "encrypted", False),
    )


@hydra.main(version_base=None, config_path="../configs", config_name="config")
def main(cfg: DictConfig) -> None:
    """Main entrypoint for Neo4j orchestration.

    Args:
        cfg: Hydra configuration
    """
    print("🔄 Neo4j Database Orchestrator")
    print("=" * 50)

    # Extract operation from config
    operation = getattr(cfg, "operation", "test_connection")

    print(f"Operation: {operation}")

    # Create Neo4j config
    neo4j_config = create_neo4j_config(cfg)

    # Execute operation
    if operation == "test_connection":
        success = test_neo4j_connection(neo4j_config)
        if success:
            print("✅ Neo4j connection test successful")
        else:
            print("❌ Neo4j connection test failed")
            sys.exit(1)

    elif operation == "rebuild_database":
        # Rebuild database operation
        search_query = getattr(cfg.rebuild, "search_query", "machine learning")
        data_dir = getattr(cfg.rebuild, "data_dir", "data")
        max_papers_search = getattr(cfg.rebuild, "max_papers_search", None)
        max_papers_enrich = getattr(cfg.rebuild, "max_papers_enrich", None)
        max_papers_import = getattr(cfg.rebuild, "max_papers_import", None)
        clear_database_first = getattr(cfg.rebuild, "clear_database_first", False)

        result = rebuild_neo4j_database(
            neo4j_config=neo4j_config,
            search_query=search_query,
            data_dir=data_dir,
            max_papers_search=max_papers_search,
            max_papers_enrich=max_papers_enrich,
            max_papers_import=max_papers_import,
            clear_database_first=clear_database_first,
        )

        if result:
            print("✅ Database rebuild completed successfully")
        else:
            print("❌ Database rebuild failed")
            sys.exit(1)

    elif operation == "complete_data":
        # Data completion operation
        enrich_abstracts = getattr(cfg.complete, "enrich_abstracts", True)
        enrich_citations = getattr(cfg.complete, "enrich_citations", True)
        enrich_authors = getattr(cfg.complete, "enrich_authors", True)
        add_semantic_keywords = getattr(cfg.complete, "add_semantic_keywords", True)
        update_metrics = getattr(cfg.complete, "update_metrics", True)
        validate_only = getattr(cfg.complete, "validate_only", False)

        result = complete_database_data(
            neo4j_config=neo4j_config,
            enrich_abstracts=enrich_abstracts,
            enrich_citations=enrich_citations,
            enrich_authors=enrich_authors,
            add_semantic_keywords_flag=add_semantic_keywords,
            update_metrics=update_metrics,
            validate_only=validate_only,
        )

        if result["success"]:
            print("✅ Data completion completed successfully")
        else:
            print(f"❌ Data completion failed: {result.get('error', 'Unknown error')}")
            sys.exit(1)

    elif operation == "fix_authors":
        # Author data fixing operation
        fix_names = getattr(cfg.fix_authors, "fix_names", True)
        normalize_names = getattr(cfg.fix_authors, "normalize_names", True)
        fix_affiliations = getattr(cfg.fix_authors, "fix_affiliations", True)
        fix_links = getattr(cfg.fix_authors, "fix_links", True)
        consolidate_duplicates = getattr(
            cfg.fix_authors, "consolidate_duplicates", True
        )
        validate_only = getattr(cfg.fix_authors, "validate_only", False)

        result = fix_author_data(
            neo4j_config=neo4j_config,
            fix_names=fix_names,
            normalize_names=normalize_names,
            fix_affiliations=fix_affiliations,
            fix_links=fix_links,
            consolidate_duplicates=consolidate_duplicates,
            validate_only=validate_only,
        )

        if result["success"]:
            fixes_applied = result.get("fixes_applied", {})
            total_fixes = sum(fixes_applied.values())
            print("✅ Author data fixing completed successfully")
            print(f"Total fixes applied: {total_fixes}")
        else:
            print(
                f"❌ Author data fixing failed: {result.get('error', 'Unknown error')}"
            )
            sys.exit(1)

    elif operation == "integrate_crossref":
        # CrossRef integration operation
        enrich_publications = getattr(cfg.crossref, "enrich_publications", True)
        update_metadata = getattr(cfg.crossref, "update_metadata", True)
        validate_only = getattr(cfg.crossref, "validate_only", False)

        result = integrate_crossref_data(
            neo4j_config=neo4j_config,
            enrich_publications=enrich_publications,
            update_metadata=update_metadata,
            validate_only=validate_only,
        )

        if result["success"]:
            integrations = result.get("integrations", {})
            total_integrations = sum(integrations.values())
            print("✅ CrossRef integration completed successfully")
            print(f"Total integrations applied: {total_integrations}")
        else:
            print(
                f"❌ CrossRef integration failed: {result.get('error', 'Unknown error')}"
            )
            sys.exit(1)

    elif operation == "setup_vector_indexes":
        # Vector index setup operation
        create_publication_index = getattr(
            cfg.vector_indexes, "create_publication_index", True
        )
        create_document_index = getattr(
            cfg.vector_indexes, "create_document_index", True
        )
        create_chunk_index = getattr(cfg.vector_indexes, "create_chunk_index", True)

        result = setup_standard_vector_indexes(
            neo4j_config=neo4j_config,
            create_publication_index=create_publication_index,
            create_document_index=create_document_index,
            create_chunk_index=create_chunk_index,
        )

        if result["success"]:
            indexes_created = result.get("indexes_created", [])
            print("✅ Vector index setup completed successfully")
            print(f"Indexes created: {len(indexes_created)}")
            for index in indexes_created:
                print(f"  - {index}")
        else:
            print("❌ Vector index setup failed")
            failed_indexes = result.get("indexes_failed", [])
            if failed_indexes:
                print(f"Failed indexes: {failed_indexes}")
            sys.exit(1)

    elif operation == "full_pipeline":
        # Full pipeline operation - run all operations in sequence
        print("🚀 Starting full Neo4j pipeline...")

        # 1. Test connection
        print("\n1. Testing Neo4j connection...")
        if not test_neo4j_connection(neo4j_config):
            print("❌ Connection test failed")
            sys.exit(1)

        # 2. Rebuild database (if configured)
        if hasattr(cfg, "rebuild") and getattr(cfg.rebuild, "enabled", False):
            print("\n2. Rebuilding database...")
            result = rebuild_neo4j_database(
                neo4j_config=neo4j_config,
                search_query=getattr(cfg.rebuild, "search_query", "machine learning"),
                data_dir=getattr(cfg.rebuild, "data_dir", "data"),
                clear_database_first=getattr(
                    cfg.rebuild, "clear_database_first", False
                ),
            )
            if not result:
                print("❌ Database rebuild failed")
                sys.exit(1)

        # 3. Complete data
        if hasattr(cfg, "complete") and getattr(cfg.complete, "enabled", True):
            print("\n3. Completing data...")
            result = complete_database_data(neo4j_config=neo4j_config)
            if not result["success"]:
                print("❌ Data completion failed")
                sys.exit(1)

        # 4. Fix authors
        if hasattr(cfg, "fix_authors") and getattr(cfg.fix_authors, "enabled", True):
            print("\n4. Fixing author data...")
            result = fix_author_data(neo4j_config=neo4j_config)
            if not result["success"]:
                print("❌ Author data fixing failed")
                sys.exit(1)

        # 5. Integrate CrossRef
        if hasattr(cfg, "crossref") and getattr(cfg.crossref, "enabled", True):
            print("\n5. Integrating CrossRef data...")
            result = integrate_crossref_data(neo4j_config=neo4j_config)
            if not result["success"]:
                print("❌ CrossRef integration failed")
                sys.exit(1)

        # 6. Setup vector indexes
        if hasattr(cfg, "vector_indexes") and getattr(
            cfg.vector_indexes, "enabled", True
        ):
            print("\n6. Setting up vector indexes...")
            result = setup_standard_vector_indexes(neo4j_config=neo4j_config)
            if not result["success"]:
                print("❌ Vector index setup failed")
                sys.exit(1)

        print("\n🎉 Full Neo4j pipeline completed successfully!")

    else:
        print(f"❌ Unknown operation: {operation}")
        print("Available operations:")
        print("  - test_connection")
        print("  - rebuild_database")
        print("  - complete_data")
        print("  - fix_authors")
        print("  - integrate_crossref")
        print("  - setup_vector_indexes")
        print("  - full_pipeline")
        sys.exit(1)


if __name__ == "__main__":
    main()
