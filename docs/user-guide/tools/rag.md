# RAG Tools

DeepCritical provides comprehensive Retrieval-Augmented Generation (RAG) tools for document processing, vector search, knowledge base management, and intelligent question answering.

## Overview

The RAG tools implement a complete RAG pipeline including document ingestion, chunking, embedding generation, vector storage, semantic search, and response generation with source citations.

## Document Processing

### Document Ingestion
```python
from deepresearch.tools.rag import DocumentIngestionTool

# Initialize document ingestion
ingestion_tool = DocumentIngestionTool()

# Ingest documents from various sources
documents = await ingestion_tool.ingest_documents(
    sources=[
        "https://example.com/research_paper.pdf",
        "./local_documents/",
        "s3://my-bucket/research_docs/"
    ],
    document_types=["pdf", "html", "markdown", "txt"],
    metadata_extraction=True,
    chunking_strategy="semantic"
)

print(f"Ingested {len(documents)} documents")
```

### Document Chunking
```python
from deepresearch.tools.rag import DocumentChunkingTool

# Initialize chunking tool
chunking_tool = DocumentChunkingTool()

# Chunk documents intelligently
chunks = await chunking_tool.chunk_documents(
    documents=documents,
    chunk_size=512,
    chunk_overlap=50,
    strategy="semantic",  # or "fixed", "sentence", "paragraph"
    preserve_structure=True,
    include_metadata=True
)

print(f"Generated {len(chunks)} chunks")
```

## Vector Operations

### Embedding Generation
```python
from deepresearch.tools.rag import EmbeddingTool

# Initialize embedding tool
embedding_tool = EmbeddingTool()

# Generate embeddings
embeddings = await embedding_tool.generate_embeddings(
    chunks=chunks,
    model="all-MiniLM-L6-v2",  # or "text-embedding-ada-002"
    batch_size=32,
    normalize=True,
    store_metadata=True
)

print(f"Generated embeddings for {len(embeddings)} chunks")
```

### Vector Storage
```python
from deepresearch.tools.rag import VectorStoreTool

# Initialize vector store
vector_store = VectorStoreTool()

# Store embeddings
await vector_store.store_embeddings(
    embeddings=embeddings,
    collection_name="research_docs",
    index_name="semantic_search",
    metadata={
        "model": "all-MiniLM-L6-v2",
        "chunk_size": 512,
        "total_chunks": len(chunks)
    }
)

# Create search index
await vector_store.create_search_index(
    collection_name="research_docs",
    index_type="hnsw",  # or "ivf", "flat"
    metric="cosine",    # or "euclidean", "ip"
    parameters={
        "M": 16,
        "efConstruction": 200,
        "ef": 64
    }
)
```

## Semantic Search

### Vector Search
```python
# Perform semantic search
search_results = await vector_store.search(
    query="machine learning applications in healthcare",
    collection_name="research_docs",
    top_k=5,
    score_threshold=0.7,
    include_metadata=True,
    rerank=True
)

for result in search_results:
    print(f"Score: {result.score}")
    print(f"Content: {result.content[:200]}...")
    print(f"Source: {result.metadata['source']}")
    print(f"Chunk ID: {result.chunk_id}")
```

### Hybrid Search
```python
# Combine semantic and keyword search
hybrid_results = await vector_store.hybrid_search(
    query="machine learning applications",
    collection_name="research_docs",
    semantic_weight=0.7,
    keyword_weight=0.3,
    top_k=10,
    rerank_results=True
)

for result in hybrid_results:
    print(f"Hybrid score: {result.hybrid_score}")
    print(f"Semantic score: {result.semantic_score}")
    print(f"Keyword score: {result.keyword_score}")
```

## Response Generation

### RAG Query Processing
```python
from deepresearch.tools.rag import RAGQueryTool

# Initialize RAG query tool
rag_tool = RAGQueryTool()

# Process RAG query
response = await rag_tool.query(
    question="What are the applications of machine learning in healthcare?",
    collection_name="research_docs",
    top_k=5,
    context_window=2000,
    include_citations=True,
    generation_model="anthropic:claude-sonnet-4-0"
)

print(f"Answer: {response.answer}")
print(f"Citations: {len(response.citations)}")
print(f"Confidence: {response.confidence}")
```

### Advanced RAG Features
```python
# Multi-step RAG query
advanced_response = await rag_tool.advanced_query(
    question="Explain machine learning applications in drug discovery",
    collection_name="research_docs",
    reasoning_steps=[
        "Identify key ML techniques",
        "Find drug discovery applications",
        "Analyze success cases",
        "Discuss limitations"
    ],
    include_reasoning=True,
    include_alternatives=True
)

print(f"Reasoning steps: {advanced_response.reasoning}")
print(f"Alternatives: {advanced_response.alternatives}")
```

## Knowledge Base Management

### Knowledge Base Creation
```python
from deepresearch.tools.rag import KnowledgeBaseTool

# Initialize knowledge base tool
kb_tool = KnowledgeBaseTool()

# Create specialized knowledge base
kb_result = await kb_tool.create_knowledge_base(
    name="machine_learning_kb",
    description="Comprehensive ML knowledge base",
    source_collections=["research_docs", "ml_papers", "tutorials"],
    update_strategy="incremental",
    embedding_model="all-MiniLM-L6-v2",
    chunking_strategy="semantic"
)

print(f"Created KB: {kb_result.name}")
print(f"Total chunks: {kb_result.total_chunks}")
print(f"Collections: {kb_result.collections}")
```

### Knowledge Base Querying
```python
# Query knowledge base
kb_response = await kb_tool.query_knowledge_base(
    question="What are the latest advances in transformer models?",
    knowledge_base="machine_learning_kb",
    context_sources=["research_papers", "conference_proceedings"],
    time_filter="last_2_years",
    include_citations=True,
    max_context_length=3000
)

print(f"Answer: {kb_response.answer}")
print(f"Source count: {len(kb_response.sources)}")
```

## Configuration

### RAG System Configuration
```yaml
# configs/rag/default.yaml
rag:
  enabled: true

  document_processing:
    chunk_size: 512
    chunk_overlap: 50
    chunking_strategy: "semantic"
    preserve_structure: true

  embeddings:
    model: "all-MiniLM-L6-v2"
    dimension: 384
    batch_size: 32
    normalize: true

  vector_store:
    type: "chroma"  # or "qdrant", "weaviate", "pinecone"
    collection_name: "deepcritical_docs"
    persist_directory: "./chroma_db"

    search:
      top_k: 5
      score_threshold: 0.7
      rerank: true

  generation:
    model: "anthropic:claude-sonnet-4-0"
    temperature: 0.3
    max_tokens: 1000
    context_window: 4000

  knowledge_bases:
    machine_learning:
      collections: ["ml_papers", "tutorials", "research_docs"]
      update_frequency: "weekly"

    bioinformatics:
      collections: ["bio_papers", "go_annotations", "protein_data"]
      update_frequency: "daily"
```

### Vector Store Configuration
```yaml
# configs/rag/vector_store/chroma.yaml
vector_store:
  type: "chroma"
  collection_name: "deepcritical_docs"
  persist_directory: "./chroma_db"

  embedding:
    model: "all-MiniLM-L6-v2"
    dimension: 384
    batch_size: 32

  search:
    k: 5
    score_threshold: 0.7
    include_metadata: true
    rerank: true

  index:
    algorithm: "hnsw"
    metric: "cosine"
    parameters:
      M: 16
      efConstruction: 200
```

## Usage Examples

### Basic RAG Query
```python
# Simple RAG query
response = await rag_tool.query(
    question="What are the main applications of machine learning?",
    collection_name="research_docs",
    top_k=3,
    include_citations=True
)

print(f"Answer: {response.answer}")
for citation in response.citations:
    print(f"Source: {citation.source}")
    print(f"Page: {citation.page}")
    print(f"Relevance: {citation.relevance}")
```

### Document Ingestion Pipeline
```python
# Complete document ingestion workflow
async def ingest_documents_pipeline(source_urls: List[str]):
    # Ingest documents
    documents = await ingestion_tool.ingest_documents(
        sources=source_urls,
        document_types=["pdf", "html", "markdown"]
    )

    # Chunk documents
    chunks = await chunking_tool.chunk_documents(
        documents=documents,
        chunk_size=512,
        strategy="semantic"
    )

    # Generate embeddings
    embeddings = await embedding_tool.generate_embeddings(chunks)

    # Store in vector database
    await vector_store.store_embeddings(embeddings)

    return {
        "documents": len(documents),
        "chunks": len(chunks),
        "embeddings": len(embeddings)
    }
```

### Advanced RAG with Reasoning
```python
# Multi-step RAG with reasoning
response = await rag_tool.multi_step_query(
    question="Explain how machine learning is used in drug discovery",
    steps=[
        "Identify key ML techniques in drug discovery",
        "Find specific applications and case studies",
        "Analyze challenges and limitations",
        "Discuss future directions"
    ],
    collection_name="research_docs",
    reasoning_model="anthropic:claude-sonnet-4-0",
    include_intermediate_steps=True
)

for step in response.steps:
    print(f"Step: {step.description}")
    print(f"Answer: {step.answer}")
    print(f"Citations: {len(step.citations)}")
```

## Integration Examples

### With DeepSearch Flow
```python
# Use RAG for enhanced search results
enhanced_results = await rag_enhanced_search.execute({
    "query": "machine learning applications",
    "search_sources": ["web", "documents", "knowledge_base"],
    "rag_context": True,
    "citation_generation": True
})
```

### With Bioinformatics Flow
```python
# RAG for biological literature analysis
bio_rag_response = await bioinformatics_rag.query(
    question="What is the function of TP53 in cancer?",
    literature_sources=["pubmed", "go_annotations", "protein_databases"],
    include_structural_data=True,
    confidence_threshold=0.8
)
```

## Best Practices

1. **Chunk Size Optimization**: Choose appropriate chunk sizes for your domain
2. **Embedding Model Selection**: Use domain-specific embedding models when available
3. **Index Optimization**: Tune search indices for query performance
4. **Context Window Management**: Balance context length with response quality
5. **Citation Accuracy**: Ensure proper source attribution and relevance scoring

## Troubleshooting

### Common Issues

**Low Search Quality:**
```python
# Improve search parameters
vector_store.update_search_config(
    top_k=10,
    score_threshold=0.6,
    rerank=True
)
```

**Memory Issues:**
```python
# Optimize batch processing
embedding_tool.configure_batch_size(16)
chunking_tool.configure_chunk_size(256)
```

**Slow Queries:**
```python
# Optimize vector store performance
vector_store.optimize_index(
    index_type="hnsw",
    parameters={"ef": 128}
)
```

For more detailed information, see the [Tool Development Guide](../../development/tool-development.md) and [Configuration Guide](../../getting-started/configuration.md).
