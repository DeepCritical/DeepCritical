"""
Cypher query templates for Neo4j vector store and knowledge graph operations.

This module contains parameterized Cypher queries for setup, search, upsert,
migration, and analytics operations in Neo4j. All queries are designed for
Neo4j 5.11+ with native vector index support.
"""

from __future__ import annotations

# ============================================================================
# VECTOR INDEX OPERATIONS
# ============================================================================

CREATE_VECTOR_INDEX = """
CALL db.index.vector.createNodeIndex($index_name, $node_label, $vector_property, $dimensions, $similarity_function)
"""

DROP_VECTOR_INDEX = """
CALL db.index.vector.drop($index_name)
"""

LIST_VECTOR_INDEXES = """
SHOW INDEXES WHERE type = 'VECTOR'
"""

VECTOR_INDEX_EXISTS = """
SHOW INDEXES WHERE name = $index_name AND type = 'VECTOR'
YIELD name
RETURN count(name) > 0 AS exists
"""

# ============================================================================
# VECTOR SEARCH OPERATIONS
# ============================================================================

VECTOR_SIMILARITY_SEARCH = """
CALL db.index.vector.queryNodes($index_name, $top_k, $query_embedding)
YIELD node, score
WHERE node.embedding IS NOT NULL
RETURN node.id AS id,
       node.content AS content,
       node.metadata AS metadata,
       score
ORDER BY score DESC
LIMIT $limit
"""

VECTOR_SEARCH_WITH_FILTERS = """
CALL db.index.vector.queryNodes($index_name, $top_k, $query_embedding)
YIELD node, score
WHERE node.embedding IS NOT NULL
  AND node.metadata[$filter_key] = $filter_value
RETURN node.id AS id,
       node.content AS content,
       node.metadata AS metadata,
       score
ORDER BY score DESC
LIMIT $limit
"""

VECTOR_SEARCH_RANGE_FILTER = """
CALL db.index.vector.queryNodes($index_name, $top_k, $query_embedding)
YIELD node, score
WHERE node.embedding IS NOT NULL
  AND toFloat(node.metadata[$range_key]) >= $min_value
  AND toFloat(node.metadata[$range_key]) <= $max_value
RETURN node.id AS id,
       node.content AS content,
       node.metadata AS metadata,
       score
ORDER BY score DESC
LIMIT $limit
"""

VECTOR_HYBRID_SEARCH = """
CALL db.index.vector.queryNodes($index_name, $top_k, $query_embedding)
YIELD node, score AS vector_score
WHERE node.embedding IS NOT NULL
MATCH (node)
WITH node, vector_score,
     toFloat(node.metadata.citation_score) AS citation_score,
     toFloat(node.metadata.importance_score) AS importance_score
WITH node, vector_score, citation_score, importance_score,
     ($vector_weight * vector_score +
      $citation_weight * citation_score +
      $importance_weight * importance_score) AS hybrid_score
RETURN node.id AS id,
       node.content AS content,
       node.metadata AS metadata,
       vector_score,
       citation_score,
       importance_score,
       hybrid_score
ORDER BY hybrid_score DESC
LIMIT $limit
"""

# ============================================================================
# DOCUMENT OPERATIONS
# ============================================================================

UPSERT_DOCUMENT = """
MERGE (d:Document {id: $id})
SET d.content = $content,
    d.metadata = $metadata,
    d.embedding = $embedding,
    d.created_at = $created_at,
    d.updated_at = datetime()
RETURN d.id
"""

UPSERT_CHUNK = """
MERGE (c:Chunk {id: $id})
SET c.content = $content,
    c.metadata = $metadata,
    c.embedding = $embedding,
    c.start_index = $start_index,
    c.end_index = $end_index,
    c.token_count = $token_count,
    c.created_at = $created_at,
    c.updated_at = datetime()
RETURN c.id
"""

DELETE_DOCUMENTS_BY_IDS = """
MATCH (d:Document)
WHERE d.id IN $document_ids
DETACH DELETE d
"""

DELETE_CHUNKS_BY_IDS = """
MATCH (c:Chunk)
WHERE c.id IN $chunk_ids
DETACH DELETE c
"""

GET_DOCUMENT_BY_ID = """
MATCH (d:Document {id: $id})
RETURN d.id AS id,
       d.content AS content,
       d.metadata AS metadata,
       d.embedding AS embedding,
       d.created_at AS created_at,
       d.updated_at AS updated_at
"""

GET_CHUNK_BY_ID = """
MATCH (c:Chunk {id: $id})
RETURN c.id AS id,
       c.content AS content,
       c.metadata AS metadata,
       c.embedding AS embedding,
       c.start_index AS start_index,
       c.end_index AS end_index,
       c.token_count AS token_count,
       c.created_at AS created_at,
       c.updated_at AS updated_at
"""

UPDATE_DOCUMENT_CONTENT = """
MATCH (d:Document {id: $id})
SET d.content = $content,
    d.updated_at = datetime()
RETURN d.id
"""

UPDATE_DOCUMENT_METADATA = """
MATCH (d:Document {id: $id})
SET d.metadata = $metadata,
    d.updated_at = datetime()
RETURN d.id
"""

# ============================================================================
# BATCH OPERATIONS
# ============================================================================

BATCH_UPSERT_DOCUMENTS = """
UNWIND $documents AS doc
MERGE (d:Document {id: doc.id})
SET d.content = doc.content,
    d.metadata = doc.metadata,
    d.embedding = doc.embedding,
    d.created_at = datetime(),
    d.updated_at = datetime()
RETURN count(d) AS created_count
"""

BATCH_UPSERT_CHUNKS = """
UNWIND $chunks AS chunk
MERGE (c:Chunk {id: chunk.id})
SET c.content = chunk.content,
    c.metadata = chunk.metadata,
    c.embedding = chunk.embedding,
    c.start_index = chunk.start_index,
    c.end_index = chunk.end_index,
    c.token_count = chunk.token_count,
    c.created_at = datetime(),
    c.updated_at = datetime()
RETURN count(c) AS created_count
"""

BATCH_DELETE_DOCUMENTS = """
MATCH (d:Document)
WHERE d.id IN $document_ids
WITH d LIMIT $batch_size
DETACH DELETE d
RETURN count(d) AS deleted_count
"""

# ============================================================================
# SCHEMA AND CONSTRAINT OPERATIONS
# ============================================================================

CREATE_CONSTRAINTS = [
    "CREATE CONSTRAINT document_id_unique IF NOT EXISTS FOR (d:Document) REQUIRE d.id IS UNIQUE",
    "CREATE CONSTRAINT chunk_id_unique IF NOT EXISTS FOR (c:Chunk) REQUIRE c.id IS UNIQUE",
    "CREATE CONSTRAINT publication_eid_unique IF NOT EXISTS FOR (p:Publication) REQUIRE p.eid IS UNIQUE",
    "CREATE CONSTRAINT author_id_unique IF NOT EXISTS FOR (a:Author) REQUIRE a.id IS UNIQUE",
    "CREATE CONSTRAINT journal_name_unique IF NOT EXISTS FOR (j:Journal) REQUIRE j.name IS UNIQUE",
    "CREATE CONSTRAINT country_name_unique IF NOT EXISTS FOR (c:Country) REQUIRE c.name IS UNIQUE",
    "CREATE CONSTRAINT institution_name_unique IF NOT EXISTS FOR (i:Institution) REQUIRE i.name IS UNIQUE",
]

CREATE_INDEXES = [
    "CREATE INDEX document_created_at IF NOT EXISTS FOR (d:Document) ON (d.created_at)",
    "CREATE INDEX document_updated_at IF NOT EXISTS FOR (d:Document) ON (d.updated_at)",
    "CREATE INDEX chunk_created_at IF NOT EXISTS FOR (c:Chunk) ON (c.created_at)",
    "CREATE INDEX publication_year IF NOT EXISTS FOR (p:Publication) ON (p.year)",
    "CREATE INDEX publication_cited_by IF NOT EXISTS FOR (p:Publication) ON (p.citedBy)",
    "CREATE INDEX author_name IF NOT EXISTS FOR (a:Author) ON (a.name)",
    "CREATE INDEX journal_name IF NOT EXISTS FOR (j:Journal) ON (j.name)",
]

DROP_CONSTRAINT = """
DROP CONSTRAINT $constraint_name IF EXISTS
"""

DROP_INDEX = """
DROP INDEX $index_name IF EXISTS
"""

# ============================================================================
# PUBLICATION KNOWLEDGE GRAPH OPERATIONS
# ============================================================================

UPSERT_PUBLICATION = """
MERGE (p:Publication {eid: $eid})
SET p.doi = $doi,
    p.title = $title,
    p.year = $year,
    p.abstract = $abstract,
    p.citedBy = $cited_by,
    p.created_at = datetime(),
    p.updated_at = datetime()
RETURN p.eid
"""

UPSERT_AUTHOR = """
MERGE (a:Author {id: $author_id})
SET a.name = $author_name,
    a.updated_at = datetime()
RETURN a.id
"""

UPSERT_JOURNAL = """
MERGE (j:Journal {name: $journal_name})
SET j.updated_at = datetime()
RETURN j.name
"""

UPSERT_INSTITUTION = """
MERGE (i:Institution {name: $institution_name})
SET i.country = $country,
    i.city = $city,
    i.updated_at = datetime()
RETURN i.name
"""

UPSERT_COUNTRY = """
MERGE (c:Country {name: $country_name})
SET c.updated_at = datetime()
RETURN c.name
"""

CREATE_AUTHORED_RELATIONSHIP = """
MATCH (a:Author {id: $author_id})
MATCH (p:Publication {eid: $publication_eid})
MERGE (a)-[:AUTHORED]->(p)
"""

CREATE_PUBLISHED_IN_RELATIONSHIP = """
MATCH (p:Publication {eid: $publication_eid})
MATCH (j:Journal {name: $journal_name})
MERGE (p)-[:PUBLISHED_IN]->(j)
"""

CREATE_AFFILIATED_WITH_RELATIONSHIP = """
MATCH (a:Author {id: $author_id})
MATCH (i:Institution {name: $institution_name})
MERGE (a)-[:AFFILIATED_WITH]->(i)
"""

CREATE_LOCATED_IN_RELATIONSHIP = """
MATCH (i:Institution {name: $institution_name})
MATCH (c:Country {name: $country_name})
MERGE (i)-[:LOCATED_IN]->(c)
"""

CREATE_CITES_RELATIONSHIP = """
MATCH (citing:Publication {eid: $citing_eid})
MATCH (cited:Publication {eid: $cited_eid})
MERGE (citing)-[:CITES]->(cited)
"""

# ============================================================================
# ANALYTICS AND STATISTICS
# ============================================================================

COUNT_DOCUMENTS = """
MATCH (d:Document)
RETURN count(d) AS total_documents
"""

COUNT_CHUNKS = """
MATCH (c:Chunk)
RETURN count(c) AS total_chunks
"""

COUNT_DOCUMENTS_WITH_EMBEDDINGS = """
MATCH (d:Document)
WHERE d.embedding IS NOT NULL
RETURN count(d) AS documents_with_embeddings
"""

COUNT_PUBLICATIONS = """
MATCH (p:Publication)
RETURN count(p) AS total_publications
"""

GET_DATABASE_STATISTICS = """
MATCH (d:Document)
OPTIONAL MATCH (c:Chunk)
OPTIONAL MATCH (p:Publication)
OPTIONAL MATCH (a:Author)
OPTIONAL MATCH (j:Journal)
OPTIONAL MATCH (i:Institution)
OPTIONAL MATCH (co:Country)
RETURN {
    documents: count(DISTINCT d),
    chunks: count(DISTINCT c),
    publications: count(DISTINCT p),
    authors: count(DISTINCT a),
    journals: count(DISTINCT j),
    institutions: count(DISTINCT i),
    countries: count(DISTINCT co)
} AS statistics
"""

GET_EMBEDDING_STATISTICS = """
MATCH (d:Document)
WHERE d.embedding IS NOT NULL
WITH size(d.embedding) AS embedding_dim, count(d) AS count
RETURN embedding_dim, count
ORDER BY count DESC
LIMIT 1
"""

# ============================================================================
# ADVANCED SEARCH AND FILTERING
# ============================================================================

SEARCH_DOCUMENTS_BY_METADATA = """
MATCH (d:Document)
WHERE d.metadata[$key] = $value
RETURN d.id AS id,
       d.content AS content,
       d.metadata AS metadata,
       d.created_at AS created_at
ORDER BY d.created_at DESC
LIMIT $limit
"""

SEARCH_DOCUMENTS_BY_DATE_RANGE = """
MATCH (d:Document)
WHERE d.created_at >= datetime($start_date)
  AND d.created_at <= datetime($end_date)
RETURN d.id AS id,
       d.content AS content,
       d.metadata AS metadata,
       d.created_at AS created_at
ORDER BY d.created_at DESC
"""

SEARCH_PUBLICATIONS_BY_AUTHOR = """
MATCH (a:Author)-[:AUTHORED]->(p:Publication)
WHERE toLower(a.name) CONTAINS toLower($author_name)
RETURN p.eid AS eid,
       p.title AS title,
       p.year AS year,
       p.citedBy AS citations,
       a.name AS author_name
ORDER BY p.citedBy DESC
LIMIT $limit
"""

SEARCH_PUBLICATIONS_BY_YEAR_RANGE = """
MATCH (p:Publication)
WHERE toInteger(p.year) >= $start_year
  AND toInteger(p.year) <= $end_year
RETURN p.eid AS eid,
       p.title AS title,
       p.year AS year,
       p.citedBy AS citations
ORDER BY p.year DESC, p.citedBy DESC
LIMIT $limit
"""

# ============================================================================
# MAINTENANCE AND CLEANUP
# ============================================================================

DELETE_ORPHANED_NODES = """
MATCH (n)
WHERE NOT (n)--()
AND NOT n:Document
AND NOT n:Chunk
AND NOT n:Publication
DELETE n
RETURN count(n) AS deleted_count
"""

DELETE_OLD_EMBEDDINGS = """
MATCH (d:Document)
WHERE d.created_at < datetime() - duration($days + 'D')
  AND d.embedding IS NOT NULL
SET d.embedding = null
RETURN count(d) AS updated_count
"""

OPTIMIZE_DATABASE = """
CALL db.resample.index.all()
YIELD name, entityType, status, failureMessage
RETURN name, entityType, status, failureMessage
"""

# ============================================================================
# HEALTH CHECKS
# ============================================================================

HEALTH_CHECK_CONNECTION = """
RETURN 'healthy' AS status, datetime() AS timestamp
"""

HEALTH_CHECK_VECTOR_INDEX = """
CALL db.index.vector.queryNodes($index_name, 1, $test_vector)
YIELD node, score
RETURN count(node) AS result_count
"""

HEALTH_CHECK_DATABASE_SIZE = """
MATCH (n)
RETURN labels(n) AS labels, count(n) AS count
ORDER BY count DESC
LIMIT 10
"""

# ============================================================================
# MIGRATION HELPERS
# ============================================================================

MIGRATE_DOCUMENT_EMBEDDINGS = """
MATCH (d:Document)
WHERE d.embedding IS NULL
  AND d.content IS NOT NULL
WITH d LIMIT $batch_size
SET d.embedding = $default_embedding,
    d.updated_at = datetime()
RETURN count(d) AS migrated_count
"""

VALIDATE_SCHEMA_CONSTRAINTS = """
CALL db.constraints()
YIELD name, labelsOrTypes, properties, ownedIndex
RETURN name, labelsOrTypes, properties, ownedIndex
ORDER BY name
"""

VALIDATE_VECTOR_INDEXES = """
SHOW INDEXES
WHERE type = 'VECTOR'
RETURN name, labelsOrTypes, properties, state
ORDER BY name
"""
