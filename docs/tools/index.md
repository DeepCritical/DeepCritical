# Tools

This section contains documentation for all tool implementations.

## Base Tool Classes

The `ToolRunner` base class provides the foundation for all tool implementations with:

- Standardized execution interface
- Parameter validation
- Error handling and retry logic
- Result formatting

## Bioinformatics Tools

Specialized tools for bioinformatics data analysis:

- **Gene Ontology Tools**: GO annotation retrieval and analysis
- **PubMed Tools**: Literature search and abstract processing
- **Sequence Analysis Tools**: BLAST, HMMER, protein sequence analysis
- **Structure Prediction Tools**: AlphaFold2, ESMFold integration
- **Molecular Docking Tools**: AutoDock Vina, DiffDock

## Search Tools

Web search and information retrieval tools:

- **Web Search**: Google/Bing search integration
- **Deep Search**: Iterative research with reflection
- **Content Extraction**: Web page parsing and cleaning
- **Search Analytics**: Result ranking and relevance scoring

## RAG Tools

Retrieval-Augmented Generation tools:

- **Document Processing**: Text chunking and embedding
- **Vector Stores**: ChromaDB, FAISS integration
- **Retrieval**: Semantic search and document ranking
- **Generation**: Context-aware answer generation
