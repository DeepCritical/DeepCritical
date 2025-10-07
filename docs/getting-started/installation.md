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
pip install chromadb qdrant-client

# For advanced visualization
pip install plotly matplotlib
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
