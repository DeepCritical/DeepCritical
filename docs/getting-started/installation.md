# Installation

## Prerequisites

- Python 3.10 or higher
- [uv](https://docs.astral.sh/uv/) (recommended) or pip

## Using uv (Recommended)

```bash
# Install uv if not already installed
# Windows:
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"

# macOS/Linux:
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install dependencies and create virtual environment
uv sync

# Verify installation
uv run deepresearch --help
```

## Using pip (Alternative)

```bash
# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install package
pip install -e .

# Verify installation
deepresearch --help
```

## Development Installation

```bash
# Install with development dependencies
uv sync --dev

# Install pre-commit hooks
make pre-install

# Run tests to verify setup
make test
```

## System Requirements

- **Operating System**: Linux, macOS, or Windows
- **Python Version**: 3.10 or higher
- **Memory**: At least 4GB RAM recommended for large workflows
- **Storage**: 1GB+ free space for dependencies and cache

## Optional Dependencies

For enhanced functionality, consider installing:

```bash
# For bioinformatics workflows
pip install neo4j biopython

# For vector databases (RAG)
pip install chromadb qdrant-client neo4j  # Neo4j for graph-based vector storage

# For advanced visualization
pip install plotly matplotlib
```

## Neo4j Setup (Optional)

Neo4j provides graph-based vector storage for enhanced RAG capabilities. To use Neo4j as a vector store:

### 1. Install Neo4j

**Using Docker (Recommended):**
```bash
# Pull and run Neo4j with vector index support (Neo4j 5.11+)
docker run \
    --name neo4j-vector \
    -p7474:7474 -p7687:7687 \
    -d \
    -e NEO4J_AUTH=neo4j/password \
    -e NEO4J_PLUGINS='["graph-data-science"]' \
    neo4j:5.18
```

**Using Desktop:**
- Download from [neo4j.com/download](https://neo4j.com/download/)
- Create a new project
- Install "Graph Data Science" plugin for vector operations

### 2. Verify Installation

```bash
# Test connection
curl -u neo4j:password http://localhost:7474/db/neo4j/tx/commit \
  -H "Content-Type: application/json" \
  -d '{"statements":[{"statement":"RETURN '\''Neo4j is running'\''"}]}'
```

### 3. Configure DeepCritical

Update your configuration to use Neo4j:

```yaml
# configs/rag/vector_store/neo4j.yaml
vector_store:
  type: "neo4j"
  connection:
    uri: "neo4j://localhost:7687"
    username: "neo4j"
    password: "password"
    database: "neo4j"
    encrypted: false

  index:
    index_name: "document_vectors"
    node_label: "Document"
    vector_property: "embedding"
    dimensions: 384
    metric: "cosine"
```

### 4. Test Vector Operations

```bash
# Test Neo4j vector store
uv run python -c "
from deepresearch.vector_stores.neo4j_vector_store import Neo4jVectorStore
from deepresearch.datatypes.rag import VectorStoreConfig
import asyncio

async def test():
    config = VectorStoreConfig(store_type='neo4j')
    store = Neo4jVectorStore(config)
    count = await store.count_documents()
    print(f'Documents in store: {count}')

asyncio.run(test())
"
```

## Troubleshooting

### Common Installation Issues

**Permission denied errors:**
```bash
# Use sudo if needed (not recommended)
sudo uv sync

# Or use virtual environment
python -m venv .venv && source .venv/bin/activate && uv sync
```

**Dependency conflicts:**
```bash
# Clear uv cache
uv cache clean

# Reinstall with fresh lockfile
uv sync --reinstall
```

**Python version issues:**
```bash
# Check Python version
python --version

# Install Python 3.10+ if needed
# On Ubuntu/Debian:
sudo add-apt-repository ppa:deadsnakes/ppa
sudo apt update
sudo apt install python3.10 python3.10-venv
```

### Verification

After installation, verify everything works:

```bash
# Check that the command is available
uv run deepresearch --help

# Run a simple test
uv run deepresearch question="What is machine learning?" flows.prime.enabled=false

# Check available flows
uv run deepresearch --help
```
