# Search Tools

DeepCritical provides comprehensive web search and information retrieval tools, integrating multiple search engines and advanced content processing capabilities.

## Overview

The search tools enable comprehensive web research by integrating multiple search engines, content extraction, duplicate removal, and quality filtering for reliable information gathering.

## Search Engines

### Google Search
```python
from deepresearch.tools.search import GoogleSearchTool

# Initialize Google search tool
google_tool = GoogleSearchTool()

# Perform search
results = await google_tool.search(
    query="machine learning applications",
    num_results=20,
    site_search=None,  # Limit to specific site
    date_restrict="y",  # Last year
    language="en"
)

# Process results
for result in results:
    print(f"Title: {result.title}")
    print(f"URL: {result.url}")
    print(f"Snippet: {result.snippet}")
    print(f"Display Link: {result.display_link}")
```

### DuckDuckGo Search
```python
from deepresearch.tools.search import DuckDuckGoTool

# Initialize DuckDuckGo tool
ddg_tool = DuckDuckGoTool()

# Privacy-focused search
results = await ddg_tool.search(
    query="quantum computing research",
    region="us-en",
    safesearch="moderate",
    timelimit="y"
)

# Handle instant answers
if results.instant_answer:
    print(f"Instant Answer: {results.instant_answer}")

for result in results.web_results:
    print(f"Title: {result.title}")
    print(f"URL: {result.url}")
    print(f"Body: {result.body}")
```

### Bing Search
```python
from deepresearch.tools.search import BingSearchTool

# Initialize Bing tool
bing_tool = BingSearchTool()

# Microsoft Bing search
results = await bing_tool.search(
    query="artificial intelligence ethics",
    count=20,
    offset=0,
    market="en-US",
    freshness="month"
)

# Access rich snippets
for result in results:
    print(f"Title: {result.title}")
    print(f"URL: {result.url}")
    print(f"Description: {result.description}")

    if result.rich_snippet:
        print(f"Rich data: {result.rich_snippet}")
```

## Content Processing

### Content Extraction
```python
from deepresearch.tools.search import ContentExtractorTool

# Initialize content extractor
extractor = ContentExtractorTool()

# Extract full content from URLs
extracted_content = await extractor.extract(
    urls=["https://example.com/article1", "https://example.com/article2"],
    include_metadata=True,
    remove_boilerplate=True,
    extract_tables=True,
    max_content_length=50000
)

# Process extracted content
for content in extracted_content:
    print(f"Title: {content.title}")
    print(f"Text length: {len(content.text)}")
    print(f"Language: {content.language}")
    print(f"Publish date: {content.publish_date}")
```

### Duplicate Detection
```python
from deepresearch.tools.search import DuplicateDetectionTool

# Initialize duplicate detection
dedup_tool = DuplicateDetectionTool()

# Remove duplicate content
unique_content = await dedup_tool.remove_duplicates(
    content_list=extracted_content,
    similarity_threshold=0.85,
    method="semantic"  # or "exact", "fuzzy"
)

print(f"Original content: {len(extracted_content)}")
print(f"Unique content: {len(unique_content)}")
print(f"Duplicates removed: {len(extracted_content) - len(unique_content)}")
```

### Quality Filtering
```python
from deepresearch.tools.search import QualityFilterTool

# Initialize quality filter
quality_tool = QualityFilterTool()

# Filter low-quality content
quality_content = await quality_tool.filter(
    content_list=unique_content,
    min_length=500,
    max_length=50000,
    min_readability_score=30,
    require_images=False,
    check_freshness=True,
    max_age_days=365
)

print(f"Quality content: {len(quality_content)}")
print(f"Filtered out: {len(unique_content) - len(quality_content)}")
```

## Advanced Search Features

### Multi-Engine Search
```python
from deepresearch.tools.search import MultiEngineSearchTool

# Initialize multi-engine search
multi_search = MultiEngineSearchTool()

# Search across multiple engines
results = await multi_search.search_multiple_engines(
    query="machine learning applications",
    engines=["google", "duckduckgo", "bing"],
    max_results_per_engine=10,
    combine_results=True,
    remove_duplicates=True
)

print(f"Total unique results: {len(results)}")
print(f"Search engines used: {results.engines_used}")
```

### Search Strategy Optimization
```python
# Define search strategy
strategy = {
    "initial_search": {
        "query": "machine learning applications",
        "engines": ["google", "duckduckgo"],
        "num_results": 15
    },
    "follow_up_queries": [
        "machine learning in healthcare",
        "machine learning in finance",
        "machine learning in autonomous vehicles"
    ],
    "deep_dive": {
        "academic_sources": True,
        "recent_publications": True,
        "technical_reports": True
    }
}

# Execute strategy
results = await strategy_tool.execute_search_strategy(strategy)
```

### Content Analysis
```python
from deepresearch.tools.search import ContentAnalysisTool

# Initialize content analyzer
analyzer = ContentAnalysisTool()

# Analyze content
analysis = await analyzer.analyze(
    content_list=quality_content,
    analysis_types=["sentiment", "topics", "entities", "summary"],
    model="anthropic:claude-sonnet-4-0"
)

# Extract insights
print(f"Main topics: {analysis.topics}")
print(f"Sentiment distribution: {analysis.sentiment}")
print(f"Key entities: {analysis.entities}")
print(f"Content summary: {analysis.summary}")
```

## RAG Integration

### Document Search
```python
from deepresearch.tools.search import DocumentSearchTool

# Initialize document search
doc_search = DocumentSearchTool()

# Search within documents
search_results = await doc_search.search_documents(
    query="machine learning applications",
    document_collection="research_papers",
    top_k=5,
    similarity_threshold=0.7
)

for result in search_results:
    print(f"Document: {result.document_title}")
    print(f"Score: {result.similarity_score}")
    print(f"Content snippet: {result.content_snippet}")
```

### Knowledge Base Queries
```python
from deepresearch.tools.search import KnowledgeBaseTool

# Initialize knowledge base tool
kb_tool = KnowledgeBaseTool()

# Query knowledge base
answers = await kb_tool.query_knowledge_base(
    question="What are the applications of machine learning?",
    knowledge_sources=["research_papers", "technical_docs", "books"],
    context_window=2000,
    include_citations=True
)

for answer in answers:
    print(f"Answer: {answer.text}")
    print(f"Citations: {answer.citations}")
    print(f"Confidence: {answer.confidence}")
```

## Configuration

### Search Engine Configuration
```yaml
# configs/search_engines.yaml
search_engines:
  google:
    enabled: true
    api_key: "${oc.env:GOOGLE_API_KEY}"
    search_engine_id: "${oc.env:GOOGLE_SEARCH_ENGINE_ID}"
    max_results: 20
    request_delay: 1.0

  duckduckgo:
    enabled: true
    region: "us-en"
    safesearch: "moderate"
    max_results: 15
    request_delay: 0.5

  bing:
    enabled: false
    api_key: "${oc.env:BING_API_KEY}"
    market: "en-US"
    max_results: 20
    request_delay: 1.0
```

### Content Processing Configuration
```yaml
# configs/content_processing.yaml
content_processing:
  extraction:
    include_metadata: true
    remove_boilerplate: true
    extract_tables: true
    max_content_length: 50000

  duplicate_detection:
    enabled: true
    similarity_threshold: 0.85
    method: "semantic"

  quality_filtering:
    enabled: true
    min_length: 500
    max_length: 50000
    min_readability_score: 30
    require_images: false
    check_freshness: true
    max_age_days: 365

  analysis:
    model: "anthropic:claude-sonnet-4-0"
    analysis_types: ["sentiment", "topics", "entities"]
    confidence_threshold: 0.7
```

## Usage Examples

### Academic Research
```python
# Comprehensive academic research workflow
async def academic_research(topic: str):
    # Multi-engine search
    search_results = await multi_search.search_multiple_engines(
        query=f"{topic} academic research",
        engines=["google", "duckduckgo"],
        max_results_per_engine=20
    )

    # Extract content
    extracted_content = await extractor.extract(
        urls=[result.url for result in search_results[:10]]
    )

    # Remove duplicates
    unique_content = await dedup_tool.remove_duplicates(extracted_content)

    # Filter quality
    quality_content = await quality_tool.filter(unique_content)

    # Analyze content
    analysis = await analyzer.analyze(quality_content)

    return {
        "search_results": search_results,
        "quality_content": quality_content,
        "analysis": analysis
    }
```

### Market Research
```python
# Market research workflow
async def market_research(product_category: str):
    # Search for market trends
    market_results = await google_tool.search(
        query=f"{product_category} market trends 2024",
        num_results=30,
        site_search="marketresearch.com OR statista.com"
    )

    # Extract market data
    market_data = await extractor.extract(
        urls=[result.url for result in market_results if "statista" in result.url or "marketresearch" in result.url]
    )

    # Analyze market insights
    market_analysis = await analyzer.analyze(
        market_data,
        analysis_types=["sentiment", "trends", "statistics"]
    )

    return market_analysis
```

## Integration Examples

### With DeepSearch Flow
```python
# Integrated with DeepSearch workflow
results = await deepsearch_workflow.execute({
    "query": "machine learning applications",
    "search_strategy": "comprehensive",
    "content_processing": "full",
    "analysis": "detailed"
})
```

### With RAG System
```python
# Search results for RAG augmentation
search_context = await search_tool.gather_context(
    query="machine learning applications",
    num_sources=10,
    quality_threshold=0.8
)

# Use in RAG system
rag_response = await rag_system.query(
    question="What are ML applications?",
    context=search_context
)
```

## Best Practices

1. **Query Optimization**: Use specific, well-formed queries
2. **Source Diversification**: Use multiple search engines for comprehensive coverage
3. **Content Quality**: Enable quality filtering to avoid low-value content
4. **Rate Limiting**: Respect API rate limits and implement delays
5. **Error Handling**: Handle API failures and network issues gracefully
6. **Caching**: Cache results to improve performance and reduce API calls

## Troubleshooting

### Common Issues

**API Rate Limits:**
```python
# Implement request delays
google_tool.configure_request_delay(1.0)
ddg_tool.configure_request_delay(0.5)
```

**Content Quality Issues:**
```python
# Adjust quality thresholds
quality_tool.update_thresholds(
    min_length=300,
    min_readability_score=25,
    max_age_days=730
)
```

**Search Result Relevance:**
```python
# Improve search strategy
multi_search.optimize_strategy(
    query_expansion=True,
    semantic_search=True,
    domain_filtering=True
)
```

For more detailed information, see the [Tool Development Guide](../../development/tool-development.md) and [RAG Tools Documentation](rag.md).
