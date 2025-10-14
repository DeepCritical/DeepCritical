# Development Setup

This guide covers setting up a development environment for DeepCritical.

## Prerequisites

- **Python 3.10+**: Required for all dependencies
- **Git**: For version control and cloning repositories
- **uv** (Recommended): Fast Python package manager
- **Make**: For running build commands (optional but recommended)

## Quick Setup with uv

```bash
# 1. Clone the repository
git clone https://github.com/DeepCritical/DeepCritical.git
cd DeepCritical

# 2. Install uv (if not already installed)
# Windows:
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"

# macOS/Linux:
curl -LsSf https://astral.sh/uv/install.sh | sh

# 3. Install dependencies
uv sync --dev

# 4. Install pre-commit hooks
make pre-install

# 5. Verify installation
make test
```

## Manual Setup with pip

```bash
# 1. Clone the repository
git clone https://github.com/DeepCritical/DeepCritical.git
cd DeepCritical

# 2. Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# 3. Install dependencies
pip install -e .
pip install -e ".[dev]"

# 4. Install pre-commit hooks
pre-commit install

# 5. Verify installation
python -m pytest tests/ -v
```

## Development Tools Setup

### 1. Code Quality Tools

The project uses several code quality tools that run automatically:

```bash
# Install pre-commit hooks (runs on every commit)
make pre-install

# Run quality checks manually
make quality

# Format code
make format

# Lint code
make lint

# Type check
make type-check
```

### 2. Testing Setup

```bash
# Run all tests
make test

# Run tests with coverage
make test-cov

# Run specific test categories
make test unit_tests
make test integration_tests

# Run tests for specific modules
pytest tests/test_agents.py -v
pytest tests/test_tools.py -v
```

### 3. Documentation Development

```bash
# Start documentation development server
make docs-serve

# Build documentation
make docs-build

# Check documentation links
make docs-check

# Deploy documentation (requires permissions)
make docs-deploy
```

## Environment Configuration

### 1. API Keys Setup

Create a `.env` file or set environment variables:

```bash
# Required for full functionality
export ANTHROPIC_API_KEY="your-anthropic-key"
export OPENAI_API_KEY="your-openai-key"
export SERPER_API_KEY="your-serper-key"

# Optional for enhanced features
export NEO4J_URI="bolt://localhost:7687"
export NEO4J_USER="neo4j"
export NEO4J_PASSWORD="password"
```

### 2. Development Configuration

Create development-specific configuration:

```yaml
# configs/development.yaml
question: "Development test question"
retries: 1
manual_confirm: true

flows:
  prime:
    enabled: true
    params:
      debug: true
      adaptive_replanning: false

logging:
  level: DEBUG
  format: "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
```

## IDE Configuration

### VS Code

Install recommended extensions:
- Python (Microsoft)
- Pylint
- Ruff
- Prettier
- Markdown All in One

Configure settings:

```json
{
  "python.defaultInterpreterPath": ".venv/bin/python",
  "python.linting.enabled": true,
  "python.linting.ruffEnabled": true,
  "python.formatting.provider": "black",
  "editor.formatOnSave": true,
  "files.associations": {
    "*.yaml": "yaml",
    "*.yml": "yaml"
  }
}
```

### PyCharm

1. Open project in PyCharm
2. Set Python interpreter to `.venv/bin/python`
3. Enable Ruff for code quality
4. Configure run configurations for tests and main app

## Database Setup (Optional)

For bioinformatics workflows with Neo4j:

```bash
# Install Neo4j Desktop or Docker
docker run \
  -p 7474:7474 -p 7687:7687 \
  -e NEO4J_AUTH=neo4j/password \
  neo4j:latest

# Verify connection
python -c "
from neo4j import GraphDatabase
driver = GraphDatabase.driver('bolt://localhost:7687', auth=('neo4j', 'password'))
driver.verify_connectivity()
print('Neo4j connected successfully')
"
```

## Vector Database Setup (Optional)

For RAG workflows:

```bash
# Install and run ChromaDB
pip install chromadb
chroma run --host 0.0.0.0 --port 8000

# Or use Qdrant
pip install qdrant-client
docker run -p 6333:6333 qdrant/qdrant
```

## Running the Application

### Basic Usage

```bash
# Run with default configuration
uv run deepresearch question="What is machine learning?"

# Run with specific configuration
uv run deepresearch --config-name=config_with_modes question="Your question"

# Run with overrides
uv run deepresearch \
  question="Research question" \
  flows.prime.enabled=true \
  flows.bioinformatics.enabled=true
```

### Development Mode

```bash
# Run in development mode with logging
uv run deepresearch \
  hydra.verbose=true \
  question="Development test" \
  flows.prime.params.debug=true

# Run with custom configuration
uv run deepresearch \
  --config-path=configs \
  --config-name=development \
  question="Test query"
```

## Troubleshooting

### Common Issues

**Import Errors:**
```bash
# Clear Python cache
find . -name "*.pyc" -delete
find . -name "__pycache__" -delete

# Reinstall dependencies
uv sync --reinstall
```

**Permission Issues:**
```bash
# Use virtual environment
python -m venv .venv && source .venv/bin/activate && uv sync

# Or use --user flag (not recommended)
pip install --user -e .
```

**Memory Issues:**
```bash
# Increase available memory or reduce batch sizes in configuration
# Edit configs/config.yaml and reduce batch_size values
```

### Getting Help

1. **Check Logs**: Look in `outputs/` directory for detailed error messages
2. **Review Configuration**: Validate your Hydra configuration files
3. **Test Components**: Run individual tests to isolate issues
4. **Check Dependencies**: Ensure all dependencies are installed correctly

## Next Steps

After setup, explore:

1. **[Quick Start Guide](../getting-started/quickstart.md)** - Basic usage examples
2. **[Configuration Guide](../getting-started/configuration.md)** - Advanced configuration
3. **[API Reference](../api/index.md)** - Complete API documentation
4. **[Examples](../examples/)** - Usage examples and tutorials
5. **[Contributing Guide](contributing.md)** - How to contribute to the project
