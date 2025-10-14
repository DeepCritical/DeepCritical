# Knowledge Query Tools

This section documents tools for information retrieval and knowledge querying in DeepCritical.

## Overview

Knowledge Query tools provide capabilities for retrieving information from various knowledge sources, including web search, databases, and structured knowledge bases.

## Available Tools

### Web Search Tools

#### WebSearchTool
Performs web searches and retrieves relevant information.

**Location**: `DeepResearch.src.tools.websearch_tools.WebSearchTool`

**Capabilities**:
- Multi-engine search (Google, DuckDuckGo, Bing)
- Content extraction and summarization
- Relevance filtering
- Result ranking and deduplication

**Usage**:
```python
from DeepResearch.src.tools.websearch_tools import WebSearchTool

tool = WebSearchTool()
result = await tool.run({
    "query": "machine learning applications",
    "num_results": 10,
    "engines": ["google", "duckduckgo"]
})
```

**Parameters**:
- `query`: Search query string
- `num_results`: Number of results to return (default: 10)
- `engines`: List of search engines to use
- `max_age_days`: Maximum age of results in days
- `language`: Language for search results

#### ChunkedSearchTool
Performs chunked searches for large query sets.

**Location**: `DeepResearch.src.tools.websearch_tools.ChunkedSearchTool`

**Capabilities**:
- Large-scale search operations
- Query chunking and parallel processing
- Result aggregation and deduplication
- Memory-efficient processing

**Usage**:
```python
from DeepResearch.src.tools.websearch_tools import ChunkedSearchTool

tool = ChunkedSearchTool()
result = await tool.run({
    "queries": ["query1", "query2", "query3"],
    "chunk_size": 5,
    "max_concurrent": 3
})
```

### Database Query Tools

#### DatabaseQueryTool
Executes queries against structured databases.

**Location**: `DeepResearch.src.tools.database_tools.DatabaseQueryTool`

**Capabilities**:
- SQL query execution
- Result formatting and validation
- Connection management
- Query optimization

**Supported Databases**:
- PostgreSQL
- MySQL
- SQLite
- Neo4j (graph database)

**Usage**:
```python
from DeepResearch.src.tools.database_tools import DatabaseQueryTool

tool = DatabaseQueryTool()
result = await tool.run({
    "connection_string": "postgresql://user:pass@localhost/db",
    "query": "SELECT * FROM research_data WHERE topic = %s",
    "parameters": ["machine_learning"],
    "max_rows": 1000
})
```

### Knowledge Base Tools

#### KnowledgeBaseQueryTool
Queries structured knowledge bases and ontologies.

**Location**: `DeepResearch.src.tools.knowledge_base_tools.KnowledgeBaseQueryTool`

**Capabilities**:
- Ontology querying (GO, MeSH, etc.)
- Semantic search
- Relationship traversal
- Knowledge graph navigation

**Usage**:
```python
from DeepResearch.src.tools.knowledge_base_tools import KnowledgeBaseQueryTool

tool = KnowledgeBaseQueryTool()
result = await tool.run({
    "ontology": "GO",
    "query_type": "term_search",
    "search_term": "protein kinase activity",
    "max_results": 50
})
```

### Document Search Tools

#### DocumentSearchTool
Searches through document collections and corpora.

**Location**: `DeepResearch.src.tools.document_tools.DocumentSearchTool`

**Capabilities**:
- Full-text search across documents
- Metadata filtering
- Relevance ranking
- Multi-format support (PDF, DOC, TXT)

**Usage**:
```python
from DeepResearch.src.tools.document_tools import DocumentSearchTool

tool = DocumentSearchTool()
result = await tool.run({
    "collection": "research_papers",
    "query": "deep learning protein structure",
    "filters": {
        "year": {"gte": 2020},
        "journal": "Nature"
    },
    "max_results": 20
})
```

## Tool Integration

### Agent Integration

Knowledge Query tools integrate seamlessly with DeepCritical agents:

```python
from DeepResearch.agents import SearchAgent

agent = SearchAgent()
result = await agent.execute(
    "Find recent papers on CRISPR gene editing",
    dependencies=AgentDependencies()
)
```

### Workflow Integration

Tools can be used in research workflows:

```python
from DeepResearch.app import main

result = await main(
    question="What are the latest developments in quantum computing?",
    flows={"deepsearch": {"enabled": True}},
    tool_config={
        "web_search": {
            "engines": ["google", "arxiv"],
            "max_results": 50
        }
    }
)
```

## Configuration

### Tool Configuration

Configure Knowledge Query tools in `configs/tools/knowledge_query.yaml`:

```yaml
knowledge_query:
  web_search:
    default_engines: ["google", "duckduckgo"]
    max_results: 20
    cache_results: true
    cache_ttl_hours: 24

  database:
    connection_pool_size: 10
    query_timeout_seconds: 30
    enable_query_logging: true

  knowledge_base:
    supported_ontologies: ["GO", "MeSH", "ChEBI"]
    default_endpoint: "https://api.geneontology.org"
    cache_enabled: true
```

### Performance Tuning

```yaml
performance:
  search:
    max_concurrent_requests: 5
    request_timeout_seconds: 10
    retry_attempts: 3

  database:
    connection_pool_size: 20
    statement_cache_size: 100
    query_optimization: true

  caching:
    enabled: true
    ttl_seconds: 3600
    max_cache_size_mb: 512
```

## Best Practices

### Search Optimization

1. **Query Formulation**: Use specific, well-formed queries
2. **Result Filtering**: Apply relevance filters to reduce noise
3. **Source Diversity**: Use multiple search engines/sources
4. **Caching**: Enable caching for frequently accessed data

### Database Queries

1. **Parameterized Queries**: Always use parameterized queries
2. **Index Usage**: Ensure proper database indexing
3. **Connection Pooling**: Use connection pooling for efficiency
4. **Query Limits**: Set reasonable result limits

### Knowledge Base Queries

1. **Ontology Awareness**: Understand ontology structure and relationships
2. **Semantic Matching**: Use semantic search capabilities
3. **Result Validation**: Validate ontology term mappings
4. **Version Handling**: Handle ontology version changes

## Error Handling

### Common Errors

**Search Failures**:
```python
try:
    result = await web_search_tool.run({"query": "complex query"})
except SearchTimeoutError:
    # Handle timeout
    result = await web_search_tool.run({
        "query": "complex query",
        "timeout": 60
    })
```

**Database Connection Issues**:
```python
try:
    result = await db_tool.run({"query": "SELECT * FROM data"})
except ConnectionError:
    # Retry with different connection
    result = await db_tool.run({
        "query": "SELECT * FROM data",
        "connection_string": backup_connection
    })
```

**Knowledge Base Unavailability**:
```python
try:
    result = await kb_tool.run({"ontology": "GO", "term": "kinase"})
except OntologyUnavailableError:
    # Fallback to alternative source
    result = await kb_tool.run({
        "ontology": "GO",
        "term": "kinase",
        "fallback_source": "local_cache"
    })
```

## Monitoring and Metrics

### Tool Metrics

Knowledge Query tools provide comprehensive metrics:

```python
# Get tool metrics
metrics = tool.get_metrics()

print(f"Total queries: {metrics['total_queries']}")
print(f"Success rate: {metrics['success_rate']:.2%}")
print(f"Average response time: {metrics['avg_response_time']:.2f}s")
print(f"Cache hit rate: {metrics['cache_hit_rate']:.2%}")
```

### Performance Monitoring

```python
# Enable performance monitoring
tool.enable_monitoring()

# Get performance report
report = tool.get_performance_report()
for query_type, stats in report.items():
    print(f"{query_type}: {stats['count']} queries, "
          f"{stats['avg_time']:.2f}s avg time")
```

## Security Considerations

### Input Validation

All Knowledge Query tools validate inputs:

```python
# Automatic input validation
result = await tool.run({
    "query": user_input,  # Automatically validated
    "max_results": 100    # Range checked
})
```

### Output Sanitization

Results are sanitized to prevent injection:

```python
# Safe result handling
if result.success:
    safe_data = result.get_sanitized_data()
    # Use safe_data for further processing
```

### Access Control

Configure access controls for sensitive data sources:

```yaml
access_control:
  database:
    allowed_queries: ["SELECT", "SHOW"]
    blocked_tables: ["sensitive_data"]
  knowledge_base:
    allowed_ontologies: ["GO", "MeSH"]
    require_authentication: true
```

## Related Documentation

- [Tool Registry](../../user-guide/tools/registry.md) - Tool registration and management
- [Web Search Integration](../../user-guide/tools/search.md) - Web search capabilities
- [RAG Tools](../../user-guide/tools/rag.md) - Retrieval-augmented generation
- [Bioinformatics Tools](../../user-guide/tools/bioinformatics.md) - Domain-specific tools
