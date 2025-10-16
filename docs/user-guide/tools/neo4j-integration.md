# Neo4j Integration Guide

DeepCritical integrates Neo4j as a native vector store for graph-enhanced RAG (Retrieval-Augmented Generation) capabilities. This guide covers Neo4j setup, configuration, and usage within the DeepCritical ecosystem.

## Overview

Neo4j provides unique advantages for RAG applications:

- **Graph-based relationships**: Connect documents, authors, citations, and concepts
- **Native vector search**: Built-in vector indexing with Cypher queries
- **Knowledge graphs**: Rich semantic relationships between entities
- **ACID compliance**: Reliable transactions for production use
- **Cypher queries**: Powerful graph query language for complex searches

## Architecture

DeepCritical's Neo4j integration consists of:

- **Vector Store**: `Neo4jVectorStore` implementing the `VectorStore` interface
- **Graph Schema**: Publication knowledge graph with documents, authors, citations
- **Cypher Templates**: Parameterized queries for vector operations
- **Migration Tools**: Schema setup and data migration utilities
- **Health Monitoring**: Connection and performance monitoring

## Quick Start

### 1. Start Neo4j

```bash
# Using Docker
docker run \
    --name neo4j-vector \
    -p7474:7474 -p7687:7687 \
    -d \
    -e NEO4J_AUTH=neo4j/password \
    neo4j:5.18
```

### 2. Configure DeepCritical

```yaml
# config.yaml
defaults:
  - rag/vector_store: neo4j
  - db: neo4j
```

### 3. Run Pipeline

```bash
# Build knowledge graph
uv run python scripts/neo4j_orchestrator.py operation=rebuild

# Run RAG query
uv run deepresearch question="machine learning applications" flows.rag.enabled=true
```

## Configuration

### Vector Store Configuration

```yaml
# configs/rag/vector_store/neo4j.yaml
vector_store:
  type: "neo4j"

  # Connection settings
  connection:
    uri: "neo4j://localhost:7687"
    username: "neo4j"
    password: "password"
    database: "neo4j"
    encrypted: false

  # Vector index settings
  index:
    index_name: "document_vectors"
    node_label: "Document"
    vector_property: "embedding"
    dimensions: 384
    metric: "cosine"  # cosine, euclidean

  # Search parameters
  search:
    top_k: 10
    score_threshold: 0.0
    include_metadata: true
    include_scores: true

  # Batch operations
  batch_size: 100
  max_connections: 10

  # Health monitoring
  health:
    enabled: true
    interval_seconds: 60
    timeout_seconds: 10
    max_failures: 3
```

### Database Configuration

```yaml
# configs/db/neo4j.yaml
uri: "neo4j://localhost:7687"
username: "neo4j"
password: "password"
database: "neo4j"
encrypted: false
max_connection_pool_size: 10
connection_timeout: 30
max_transaction_retry_time: 30
```

## Usage Examples

### Basic Vector Operations

```python
from deepresearch.vector_stores.neo4j_vector_store import Neo4jVectorStore
from deepresearch.datatypes.rag import Document, VectorStoreConfig
import asyncio

async def demo():
    # Initialize vector store
    config = VectorStoreConfig(store_type="neo4j")
    store = Neo4jVectorStore(config)

    # Add documents
    docs = [
        Document(id="doc1", content="Machine learning is...", metadata={"type": "ml"}),
        Document(id="doc2", content="Deep learning uses...", metadata={"type": "dl"})
    ]

    ids = await store.add_documents(docs)
    print(f"Added documents: {ids}")

    # Search
    results = await store.search("machine learning", top_k=5)
    for result in results:
        print(f"Score: {result.score}, Content: {result.document.content[:50]}...")

asyncio.run(demo())
```

### Graph-Enhanced Search

```python
# Search with graph relationships
graph_results = await store.search_with_graph_context(
    query="machine learning applications",
    include_citations=True,
    include_authors=True,
    relationship_depth=2
)

for result in graph_results:
    print(f"Document: {result.document.id}")
    print(f"Related authors: {result.related_authors}")
    print(f"Citations: {result.citations}")
```

### Knowledge Graph Queries

```python
from deepresearch.prompts.neo4j_queries import SEARCH_PUBLICATIONS_BY_AUTHOR

# Query publications by author
results = await store.run_cypher_query(
    SEARCH_PUBLICATIONS_BY_AUTHOR,
    {"author_name": "Smith", "limit": 10}
)

for record in results:
    print(f"Title: {record['title']}, Year: {record['year']}")
```

## Schema Design

### Core Entities

```
(Document) -[:HAS_CHUNK]-> (Chunk)
    |
    v
  embedding: vector
 metadata: map

(Author) -[:AUTHORED]-> (Publication)
    |
    v
 affiliation: string
 name: string

(Publication) -[:CITES]-> (Publication)
    |
    v
 title: string
 abstract: string
 year: int
 doi: string
```

### Vector Indexes

- **Document Vectors**: Full document embeddings for general search
- **Chunk Vectors**: Semantic chunk embeddings for precise retrieval
- **Publication Vectors**: Abstract embeddings for literature search

## Pipeline Operations

### Data Ingestion Pipeline

```python
from deepresearch.utils import (
    neo4j_rebuild,
    neo4j_complete_data,
    neo4j_embeddings,
    neo4j_vector_setup
)

# 1. Initial data import
await neo4j_rebuild.rebuild_database(
    query="machine learning",
    max_papers=1000
)

# 2. Data enrichment
await neo4j_complete_data.enrich_publications(
    enrich_abstracts=True,
    enrich_authors=True
)

# 3. Generate embeddings
await neo4j_embeddings.generate_embeddings(
    target_nodes=["Publication", "Document"],
    batch_size=50
)

# 4. Setup vector indexes
await neo4j_vector_setup.create_vector_indexes()
```

### Maintenance Operations

```python
from deepresearch.utils.neo4j_migrations import Neo4jMigrationManager

# Run schema migrations
migrator = Neo4jMigrationManager()
await migrator.run_migrations()

# Health check
health_status = await migrator.health_check()
print(f"Database healthy: {health_status.healthy}")

# Optimize indexes
await migrator.optimize_indexes()
```

## Advanced Features

### Hybrid Search

Combine vector similarity with graph relationships:

```python
# Hybrid search combining semantic and citation-based relevance
hybrid_results = await store.hybrid_search(
    query="neural networks",
    vector_weight=0.7,
    citation_weight=0.2,
    author_weight=0.1,
    top_k=10
)
```

### Temporal Queries

Search with time-based filters:

```python
# Find recent publications on a topic
recent_papers = await store.search_with_temporal_filter(
    query="transformer models",
    date_range=("2023-01-01", "2024-12-31"),
    top_k=20
)
```

### Multi-Hop Reasoning

Leverage graph relationships for complex queries:

```python
# Find papers by authors who cited a specific work
related_work = await store.multi_hop_search(
    start_paper_id="paper123",
    relationship_path=["CITES", "AUTHORED_BY"],
    query="similar research",
    max_hops=3
)
```

## Performance Optimization

### Index Tuning

```yaml
# Optimized configuration
index:
  index_name: "publication_vectors"
  dimensions: 384
  metric: "cosine"
  # Neo4j-specific parameters
  m: 16          # HNSW parameter
  ef_construction: 200
  ef: 64         # Search parameter
```

### Connection Pooling

```yaml
# Production configuration
connection:
  max_connection_pool_size: 50
  connection_timeout: 60
  max_transaction_retry_time: 60
  connection_acquisition_timeout: 120
```

### Batch Operations

```python
# Efficient bulk operations
await store.batch_add_documents(
    documents=document_list,
    batch_size=500,
    concurrent_batches=4
)
```

## Monitoring and Observability

### Health Checks

```python
from deepresearch.utils.neo4j_connection import Neo4jConnectionManager

# Monitor connection health
monitor = Neo4jConnectionManager()
status = await monitor.check_health()

print(f"Connected: {status.connected}")
print(f"Vector index healthy: {status.vector_index_exists}")
print(f"Response time: {status.response_time_ms}ms")
```

### Performance Metrics

```python
# Query performance statistics
stats = await store.get_performance_stats()

print(f"Average query time: {stats.avg_query_time_ms}ms")
print(f"Cache hit rate: {stats.cache_hit_rate}%")
print(f"Index size: {stats.index_size_mb}MB")
```

## Troubleshooting

### Common Issues

**Connection Refused:**
```bash
# Check Neo4j status
docker ps | grep neo4j

# Verify credentials
curl -u neo4j:password http://localhost:7474/db/neo4j/tx/commit \
  -H "Content-Type: application/json" \
  -d '{"statements":[{"statement":"RETURN 1"}]}'
```

**Vector Index Errors:**
```cypher
// Check index status
SHOW INDEXES WHERE type = 'VECTOR';

// Recreate index if needed
DROP INDEX document_vectors IF EXISTS;
CALL db.index.vector.createNodeIndex(
  'document_vectors', 'Document', 'embedding', 384, 'cosine'
);
```

**Memory Issues:**
```yaml
# Adjust JVM settings
docker run -e NEO4J_dbms_memory_heap_initial__size=2G \
           -e NEO4J_dbms_memory_heap_max__size=4G \
           neo4j:5.18
```

### Debug Queries

```python
# Enable query logging
import logging
logging.getLogger("neo4j").setLevel(logging.DEBUG)

# Inspect queries
with store.get_session() as session:
    result = await session.run("EXPLAIN CALL db.index.vector.queryNodes($index, 5, $vector)",
                              {"index": "document_vectors", "vector": [0.1]*384})
    explanation = await result.single()
    print(explanation)
```

## Integration Examples

### With DeepSearch Flow

```python
# Enhanced search with graph context
search_config = {
    "query": "quantum computing applications",
    "use_graph_context": True,
    "relationship_depth": 2,
    "include_citations": True,
    "vector_store": "neo4j"
}

results = await deepsearch_flow.execute(search_config)
```

### With Bioinformatics Flow

```python
# Literature analysis with citation networks
bio_config = {
    "query": "CRISPR gene editing",
    "literature_search": True,
    "citation_analysis": True,
    "author_network": True,
    "vector_store": "neo4j"
}

analysis = await bioinformatics_flow.execute(bio_config)
```

## Best Practices

1. **Schema Design**: Plan your graph schema before implementation
2. **Index Strategy**: Use appropriate indexes for your query patterns
3. **Batch Operations**: Process data in batches for efficiency
4. **Connection Management**: Use connection pooling for production workloads
5. **Monitoring**: Implement comprehensive health checks and metrics
6. **Backup Strategy**: Regular backups for production databases
7. **Query Optimization**: Profile and optimize Cypher queries

## Migration from Other Stores

### From Chroma

```python
from deepresearch.migrations import migrate_from_chroma

# Migrate existing data
await migrate_from_chroma(
    chroma_path="./chroma_db",
    neo4j_config=neo4j_config,
    batch_size=1000
)
```

### From Qdrant

```python
from deepresearch.migrations import migrate_from_qdrant

# Migrate with graph relationships
await migrate_from_qdrant(
    qdrant_url="http://localhost:6333",
    neo4j_config=neo4j_config,
    preserve_relationships=True
)
```

For more information, see the [RAG Tools Guide](rag.md) and [Configuration Guide](../../getting-started/configuration.md).
