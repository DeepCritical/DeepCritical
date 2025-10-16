"""
Neo4j embeddings utilities for DeepCritical.

This module provides functions to generate and manage embeddings
for Neo4j vector search operations, integrating with VLLM and other
embedding providers.
"""

from __future__ import annotations

import asyncio
from typing import Any, Dict, List, Optional

from neo4j import GraphDatabase

from ..datatypes.neo4j_types import Neo4jConnectionConfig, Neo4jVectorStoreConfig
from ..datatypes.rag import Embeddings as EmbeddingsInterface


class Neo4jEmbeddingsManager:
    """Manager for generating and updating embeddings in Neo4j."""

    def __init__(self, config: Neo4jVectorStoreConfig, embeddings: EmbeddingsInterface):
        """Initialize the embeddings manager.

        Args:
            config: Neo4j vector store configuration
            embeddings: Embeddings interface for generating vectors
        """
        self.config = config
        self.embeddings = embeddings

        # Initialize Neo4j driver
        conn = config.connection
        self.driver = GraphDatabase.driver(
            conn.uri,
            auth=(conn.username, conn.password) if conn.username else None,
            encrypted=conn.encrypted,
        )

    def __del__(self):
        """Clean up Neo4j driver connection."""
        if hasattr(self, "driver"):
            self.driver.close()

    async def generate_publication_embeddings(self, batch_size: int = 50) -> int:
        """Generate embeddings for publications that don't have them.

        Args:
            batch_size: Number of publications to process per batch

        Returns:
            Number of publications processed
        """
        print("--- GENERATING PUBLICATION EMBEDDINGS ---")

        processed = 0

        with self.driver.session(database=self.config.connection.database) as session:
            # Find publications without embeddings
            result = session.run(
                """
                MATCH (p:Publication)
                WHERE p.abstract IS NOT NULL
                AND p.abstract <> ""
                AND p.abstract_embedding IS NULL
                RETURN p.eid AS eid, p.abstract AS abstract, p.title AS title
                LIMIT $batch_size
            """,
                batch_size=batch_size,
            )

            publications = []
            for record in result:
                publications.append(
                    {
                        "eid": record["eid"],
                        "text": f"{record['title']} {record['abstract']}",
                        "title": record["title"],
                    }
                )

            if not publications:
                print("No publications found needing embeddings")
                return 0

            print(f"Processing {len(publications)} publications...")

            # Generate embeddings in batches
            texts = [pub["text"] for pub in publications]

            try:
                embeddings_list = await self.embeddings.vectorize_documents(texts)
                processed = len(embeddings_list)
            except Exception as e:
                print(f"Error generating embeddings: {e}")
                return 0

            # Update Neo4j with embeddings
            for pub, embedding in zip(publications, embeddings_list, strict=False):
                session.run(
                    """
                    MATCH (p:Publication {eid: $eid})
                    SET p.abstract_embedding = $embedding,
                        p.embedding_generated_at = datetime()
                """,
                    eid=pub["eid"],
                    embedding=embedding,
                )

                print(f"✓ Generated embedding for: {pub['title'][:50]}...")

        return processed

    async def generate_document_embeddings(self, batch_size: int = 50) -> int:
        """Generate embeddings for documents that don't have them.

        Args:
            batch_size: Number of documents to process per batch

        Returns:
            Number of documents processed
        """
        print("--- GENERATING DOCUMENT EMBEDDINGS ---")

        processed = 0

        with self.driver.session(database=self.config.connection.database) as session:
            # Find documents without embeddings
            result = session.run(
                """
                MATCH (d:Document)
                WHERE d.content IS NOT NULL
                AND d.content <> ""
                AND d.embedding IS NULL
                RETURN d.id AS id, d.content AS content
                LIMIT $batch_size
            """,
                batch_size=batch_size,
            )

            documents = []
            for record in result:
                documents.append({"id": record["id"], "content": record["content"]})

            if not documents:
                print("No documents found needing embeddings")
                return 0

            print(f"Processing {len(documents)} documents...")

            # Generate embeddings
            texts = [doc["content"] for doc in documents]

            try:
                embeddings_list = await self.embeddings.vectorize_documents(texts)
                processed = len(embeddings_list)
            except Exception as e:
                print(f"Error generating embeddings: {e}")
                return 0

            # Update Neo4j with embeddings
            for doc, embedding in zip(documents, embeddings_list, strict=False):
                session.run(
                    """
                    MATCH (d:Document {id: $id})
                    SET d.embedding = $embedding,
                        d.embedding_generated_at = datetime()
                """,
                    id=doc["id"],
                    embedding=embedding,
                )

                print(f"✓ Generated embedding for document: {doc['id']}")

        return processed

    async def generate_chunk_embeddings(self, batch_size: int = 50) -> int:
        """Generate embeddings for chunks that don't have them.

        Args:
            batch_size: Number of chunks to process per batch

        Returns:
            Number of chunks processed
        """
        print("--- GENERATING CHUNK EMBEDDINGS ---")

        processed = 0

        with self.driver.session(database=self.config.connection.database) as session:
            # Find chunks without embeddings
            result = session.run(
                """
                MATCH (c:Chunk)
                WHERE c.text IS NOT NULL
                AND c.text <> ""
                AND c.embedding IS NULL
                RETURN c.id AS id, c.text AS text
                LIMIT $batch_size
            """,
                batch_size=batch_size,
            )

            chunks = []
            for record in result:
                chunks.append({"id": record["id"], "text": record["text"]})

            if not chunks:
                print("No chunks found needing embeddings")
                return 0

            print(f"Processing {len(chunks)} chunks...")

            # Generate embeddings
            texts = [chunk["text"] for chunk in chunks]

            try:
                embeddings_list = await self.embeddings.vectorize_documents(texts)
                processed = len(embeddings_list)
            except Exception as e:
                print(f"Error generating embeddings: {e}")
                return 0

            # Update Neo4j with embeddings
            for chunk, embedding in zip(chunks, embeddings_list, strict=False):
                session.run(
                    """
                    MATCH (c:Chunk {id: $id})
                    SET c.embedding = $embedding,
                        c.embedding_generated_at = datetime()
                """,
                    id=chunk["id"],
                    embedding=embedding,
                )

                print(f"✓ Generated embedding for chunk: {chunk['id']}")

        return processed

    async def regenerate_embeddings(
        self, node_type: str, node_ids: list[str] | None = None, force: bool = False
    ) -> int:
        """Regenerate embeddings for specific nodes.

        Args:
            node_type: Type of nodes ('Publication', 'Document', or 'Chunk')
            node_ids: Specific node IDs to regenerate (None for all)
            force: Whether to regenerate even if embeddings exist

        Returns:
            Number of embeddings regenerated
        """
        print(f"--- REGENERATING {node_type.upper()} EMBEDDINGS ---")

        processed = 0

        with self.driver.session(database=self.config.connection.database) as session:
            # Build query based on node type
            if node_type == "Publication":
                text_field = "abstract"
                embedding_field = "abstract_embedding"
                id_field = "eid"
            elif node_type == "Document":
                text_field = "content"
                embedding_field = "embedding"
                id_field = "id"
            elif node_type == "Chunk":
                text_field = "text"
                embedding_field = "embedding"
                id_field = "id"
            else:
                print(f"Unsupported node type: {node_type}")
                return 0

            # Build query
            query = f"""
                MATCH (n:{node_type})
                WHERE n.{text_field} IS NOT NULL
                AND n.{text_field} <> ""
            """

            if not force:
                query += f" AND n.{embedding_field} IS NULL"

            if node_ids:
                query += f" AND n.{id_field} IN $node_ids"

            query += f" RETURN n.{id_field} AS id, n.{text_field} AS text"
            query += " LIMIT 100"

            result = session.run(query, node_ids=node_ids if node_ids else [])

            nodes = []
            for record in result:
                nodes.append({"id": record["id"], "text": record["text"]})

            if not nodes:
                print(f"No {node_type.lower()}s found needing embedding regeneration")
                return 0

            print(f"Regenerating embeddings for {len(nodes)} {node_type.lower()}s...")

            # Generate embeddings
            texts = [node["text"] for node in nodes]

            try:
                embeddings_list = await self.embeddings.vectorize_documents(texts)
                processed = len(embeddings_list)
            except Exception as e:
                print(f"Error generating embeddings: {e}")
                return 0

            # Update Neo4j with new embeddings
            for node, embedding in zip(nodes, embeddings_list, strict=False):
                session.run(
                    f"""
                    MATCH (n:{node_type} {{{id_field}: $id}})
                    SET n.{embedding_field} = $embedding,
                        n.embedding_generated_at = datetime()
                """,
                    id=node["id"],
                    embedding=embedding,
                )

                print(f"✓ Regenerated embedding for {node_type.lower()}: {node['id']}")

        return processed

    def get_embedding_statistics(self) -> dict[str, Any]:
        """Get statistics about embeddings in the database.

        Returns:
            Dictionary with embedding statistics
        """
        print("--- GETTING EMBEDDING STATISTICS ---")

        stats = {}

        with self.driver.session(database=self.config.connection.database) as session:
            # Publication embedding stats
            result = session.run("""
                MATCH (p:Publication)
                RETURN count(p) AS total_publications,
                       count(CASE WHEN p.abstract_embedding IS NOT NULL THEN 1 END) AS publications_with_embeddings
            """)

            record = result.single()
            stats["publications"] = {
                "total": record["total_publications"],
                "with_embeddings": record["publications_with_embeddings"],
            }

            # Document embedding stats
            result = session.run("""
                MATCH (d:Document)
                RETURN count(d) AS total_documents,
                       count(CASE WHEN d.embedding IS NOT NULL THEN 1 END) AS documents_with_embeddings
            """)

            record = result.single()
            stats["documents"] = {
                "total": record["total_documents"],
                "with_embeddings": record["documents_with_embeddings"],
            }

            # Chunk embedding stats
            result = session.run("""
                MATCH (c:Chunk)
                RETURN count(c) AS total_chunks,
                       count(CASE WHEN c.embedding IS NOT NULL THEN 1 END) AS chunks_with_embeddings
            """)

            record = result.single()
            stats["chunks"] = {
                "total": record["total_chunks"],
                "with_embeddings": record["chunks_with_embeddings"],
            }

        # Print statistics
        print("Embedding Statistics:")
        for node_type, data in stats.items():
            total = data["total"]
            with_embeddings = data["with_embeddings"]
            percentage = (with_embeddings / total * 100) if total > 0 else 0
            print(
                f"  {node_type.capitalize()}: {with_embeddings}/{total} ({percentage:.1f}%)"
            )

        return stats

    async def generate_all_embeddings(
        self,
        generate_publications: bool = True,
        generate_documents: bool = True,
        generate_chunks: bool = True,
        batch_size: int = 50,
    ) -> dict[str, int]:
        """Generate embeddings for all content types.

        Args:
            generate_publications: Whether to generate publication embeddings
            generate_documents: Whether to generate document embeddings
            generate_chunks: Whether to generate chunk embeddings
            batch_size: Batch size for processing

        Returns:
            Dictionary with counts of generated embeddings
        """
        print("\n" + "=" * 80)
        print("NEO4J EMBEDDINGS GENERATION PROCESS")
        print("=" * 80 + "\n")

        results = {"publications": 0, "documents": 0, "chunks": 0}

        if generate_publications:
            print("Generating publication embeddings...")
            results["publications"] = await self.generate_publication_embeddings(
                batch_size
            )

        if generate_documents:
            print("Generating document embeddings...")
            results["documents"] = await self.generate_document_embeddings(batch_size)

        if generate_chunks:
            print("Generating chunk embeddings...")
            results["chunks"] = await self.generate_chunk_embeddings(batch_size)

        total_generated = sum(results.values())
        print("\n✅ Embeddings generation completed successfully!")
        print(f"Total embeddings generated: {total_generated}")

        # Show final statistics
        self.get_embedding_statistics()

        return results


async def generate_neo4j_embeddings(
    neo4j_config: Neo4jConnectionConfig,
    embeddings: EmbeddingsInterface,
    generate_publications: bool = True,
    generate_documents: bool = True,
    generate_chunks: bool = True,
    batch_size: int = 50,
) -> dict[str, int]:
    """Generate embeddings for Neo4j content.

    Args:
        neo4j_config: Neo4j connection configuration
        embeddings: Embeddings interface
        generate_publications: Whether to generate publication embeddings
        generate_documents: Whether to generate document embeddings
        generate_chunks: Whether to generate chunk embeddings
        batch_size: Batch size for processing

    Returns:
        Dictionary with counts of generated embeddings
    """
    # Create vector store config (minimal for this operation)
    from ..datatypes.neo4j_types import VectorIndexConfig, VectorIndexMetric

    vector_config = VectorIndexConfig(
        index_name="temp_index",
        node_label="Document",
        vector_property="embedding",
        dimensions=384,  # Default
        metric=VectorIndexMetric.COSINE,
    )

    store_config = Neo4jVectorStoreConfig(connection=neo4j_config, index=vector_config)

    manager = Neo4jEmbeddingsManager(store_config, embeddings)

    try:
        return await manager.generate_all_embeddings(
            generate_publications=generate_publications,
            generate_documents=generate_documents,
            generate_chunks=generate_chunks,
            batch_size=batch_size,
        )
    finally:
        # Manager cleanup happens in __del__
        pass
