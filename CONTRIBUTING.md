# Contributing to DeepCritical

Thank you for your interest in contributing to DeepCritical! This document provides guidelines and information for contributors.

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Setup](#development-setup)
- [Contributing Process](#contributing-process)
- [Code Style](#code-style)
- [Testing](#testing)
- [Documentation](#documentation)
- [Issue Guidelines](#issue-guidelines)
- [Pull Request Guidelines](#pull-request-guidelines)
- [Release Process](#release-process)

## Code of Conduct

This project adheres to a code of conduct. By participating, you are expected to uphold this code. Please report unacceptable behavior to [conduct@deepcritical.dev](mailto:conduct@deepcritical.dev).

## Getting Started

### Prerequisites

- Python 3.10 or higher
- [uv](https://github.com/astral-sh/uv) (recommended) or pip
- Git

### Fork and Clone

1. Fork the repository on GitHub
2. Clone your fork locally:
   ```bash
   git clone https://github.com/DeepCritical/DeepCritical.git
   cd DeepCritical
   ```

## Development Setup

### Using uv (Recommended)

```bash
# Install uv if not already installed
# Windows:
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"

# macOS/Linux:
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install dependencies
uv sync --dev

# 🚨 CRITICAL: Install pre-commit hooks (primary quality assurance)
make pre-install

# Run tests to verify setup
uv run pytest tests/

# Show all available development commands
make help
```

### Using pip (Alternative)

```bash
# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install package in development mode
pip install -e .

# Install development dependencies
pip install -e ".[dev]"

# Install additional type checking tools
pip install ty

# Run tests to verify setup
pytest tests/
```

## Contributing Process

### 1. Create a Branch

```bash
git checkout -b feature/your-feature-name
# or
git checkout -b bugfix/issue-number
```

### 2. Make Changes

- Write your code following our [Code Style](#code-style) guidelines
- Add tests for new functionality
- Update documentation as needed
- Ensure all tests pass

### 3. Test Your Changes

#### Cross-Platform Testing

DeepCritical supports comprehensive testing across multiple platforms with Windows-specific PowerShell integration.

**For Windows Development:**
```bash
# Basic tests (always available)
make test-unit-win
make test-pydantic-ai-win
make test-performance-win

# Containerized tests (requires Docker)
$env:DOCKER_TESTS = "true"
make test-containerized-win
make test-docker-win
make test-bioinformatics-win
```

**For GitHub Contributors (Cross-Platform):**
```bash
# Basic tests (works on all platforms)
make test-unit
make test-pydantic-ai
make test-performance

# Containerized tests (works when Docker available)
DOCKER_TESTS=true make test-containerized
DOCKER_TESTS=true make test-docker
DOCKER_TESTS=true make test-bioinformatics
```

#### Test Categories

DeepCritical includes comprehensive test coverage:

- **Unit Tests**: Basic functionality testing
- **Pydantic AI Tests**: Agent workflows and tool integration
- **Performance Tests**: Response time and memory usage testing
- **LLM Framework Tests**: VLLM and LLaMACPP containerized testing
- **Bioinformatics Tests**: BWA, SAMtools, BEDTools, STAR, HISAT2, FreeBayes testing
- **Docker Sandbox Tests**: Container isolation and security testing

#### Quality Checks

```bash
# Run linting and formatting
uv run ruff check .
uv run ruff format --check .


# Run type checking
uvx ty check

# Run all quality checks
uv run ruff check . && uv run ruff format --check . && uvx ty check

# Show all available commands
make help
```

### 4. Commit Your Changes

```bash
git add .
git commit -m "feat: add new feature description"
```

Use conventional commit messages:
- `feat:` for new features
- `fix:` for bug fixes
- `docs:` for documentation changes
- `style:` for formatting changes
- `refactor:` for code refactoring
- `test:` for test additions/changes
- `chore:` for maintenance tasks

### 5. Pre-commit Hooks

Pre-commit hooks are the **primary quality assurance mechanism** for DeepCritical. They automatically run comprehensive quality checks before every commit to ensure consistent code standards across all contributors.

```bash
# Install pre-commit hooks (essential - runs automatically on every commit)
make pre-install

# Run all hooks manually (for validation before committing)
make pre-commit

# What pre-commit hooks do automatically:
# ✅ Ruff linting and formatting (fast Python linter)
# ✅ Type checking with ty (catches type errors)
# ❌ Security scanning with bandit (disabled in pre-commit; run manually via `make security`)
# ✅ YAML/TOML validation (config file integrity)
# ✅ Trailing whitespace removal (code cleanliness)
# ✅ Debug statement detection (production readiness)
# ✅ Large file detection (repository hygiene)
# ✅ AST validation (syntax checking)

# 💡 Pre-commit runs ALL quality checks automatically on every commit
#    Manual quality checks (make quality, make dev) are redundant but available
```

### 6. Makefile

The Makefile provides convenient shortcuts for development tasks, but pre-commit hooks are the primary quality assurance mechanism:

#### Cross-Platform Testing Support

DeepCritical supports both cross-platform (GitHub contributors) and Windows-specific testing:

**For GitHub Contributors (Cross-Platform):**
```bash
# Show all available commands
make help

# Basic tests (works on all platforms)
make test-unit
make test-pydantic-ai
make test-performance

# Containerized tests (works when Docker available)
DOCKER_TESTS=true make test-containerized
DOCKER_TESTS=true make test-docker
DOCKER_TESTS=true make test-bioinformatics

# Quick development cycle (when not using pre-commit)
make dev

# Manual quality validation (redundant with pre-commit, but available)
make quality

# Research application testing
make examples
```

**For Windows Development:**
```bash
# Basic tests (always available)
make test-unit-win
make test-pydantic-ai-win
make test-performance-win

# Containerized tests (requires Docker)
$env:DOCKER_TESTS = "true"
make test-containerized-win
make test-docker-win
make test-bioinformatics-win

# Quick development cycle (when not using pre-commit)
make dev

# Manual quality validation (redundant with pre-commit, but available)
make quality

# Research application testing
make examples
```

### 7. Push and Create Pull Request

```bash
git push origin feature/your-feature-name
```

Then create a pull request on GitHub.

## Code Style

### Python Style

We use these tools to ensure code quality:

- **[Ruff](https://github.com/astral-sh/ruff)**: Fast Python linter and formatter
- **[ty](https://github.com/astral-sh/ty)**: Type checker for Python

```bash
# Check code style (Ruff)
uv run ruff check .

# Format code (Ruff)
uv run ruff format .

# Check type annotations
uvx ty check

# Auto-fix linting issues
uv run ruff check . --fix

# Auto-fix formatting (Ruff)
uv run ruff format .
```

### Code Guidelines

1. **Type Hints**: Use type hints for all function parameters and return values
2. **Docstrings**: Use Google-style docstrings for all public functions and classes
3. **Imports**: Use absolute imports and organize them properly
4. **Naming**: Use descriptive names for variables, functions, and classes
5. **Error Handling**: Use appropriate exception handling with meaningful error messages

### Quality Assurance Tools

We use a comprehensive set of tools to ensure code quality:

- **Ruff**: Fast linter and formatter that catches common mistakes and enforces consistent style
- **ty**: Type checker that validates type annotations and catches type-related errors
- **pytest**: Testing framework for running unit and integration tests

These tools complement each other:
- Ruff provides fast feedback on code issues and ensures consistent formatting
- ty catches type-related bugs before runtime
- pytest ensures functionality works as expected

### Example Code Style

```python
from typing import Dict, List, Optional
from pydantic import BaseModel, Field

class ExampleModel(BaseModel):
    """Example model for demonstration.

    Args:
        name: The name of the example
        value: The value associated with the example
    """
    name: str = Field(..., description="The name of the example")
    value: Optional[int] = Field(None, description="The value associated with the example")

def example_function(data: Dict[str, str]) -> List[str]:
    """Process example data and return results.

    Args:
        data: Dictionary containing input data

    Returns:
        List of processed strings

    Raises:
        ValueError: If data is invalid
    """
    if not data:
        raise ValueError("Data cannot be empty")

    return [f"processed_{key}" for key in data.keys()]
```

## Testing

### Test Structure

```
tests/
├── unit/           # Unit tests
├── integration/    # Integration tests
├── fixtures/       # Test fixtures
└── conftest.py     # Pytest configuration
```

### Writing Tests

```python
import pytest
from DeepResearch.example_module import example_function

def test_example_function():
    """Test example function with valid input."""
    data = {"key1": "value1", "key2": "value2"}
    result = example_function(data)
    assert len(result) == 2
    assert "processed_key1" in result

def test_example_function_empty_data():
    """Test example function with empty input."""
    with pytest.raises(ValueError, match="Data cannot be empty"):
        example_function({})
```

### Running Tests

```bash
# Run all tests
uv run pytest tests/ -v

# Run with coverage
uv run pytest tests/ --cov=DeepResearch --cov-report=html

# Run specific test file
uv run pytest tests/unit/test_example.py -v

# Run tests matching pattern
uv run pytest tests/ -k "test_example" -v
```

## Documentation

### Documentation Structure

- `README.md`: Main project documentation
- `docs/`: Detailed documentation
- `CONTRIBUTING.md`: This file
- `SECURITY.md`: Security policy
- Code docstrings: Inline documentation

### Writing Documentation

1. **README Updates**: Update README.md for user-facing changes
2. **API Documentation**: Use docstrings for all public APIs
3. **Configuration Documentation**: Document new configuration options
4. **Examples**: Provide usage examples for new features

### Documentation Style

- Use clear, concise language
- Provide code examples
- Include configuration examples
- Update related documentation when making changes

## Issue Guidelines

### Before Creating an Issue

1. Search existing issues to avoid duplicates
2. Check if the issue is already fixed in the latest version
3. Gather relevant information (environment, steps to reproduce, etc.)

### Issue Types

- **Bug Report**: Use the bug report template
- **Feature Request**: Use the feature request template
- **Documentation**: Use the documentation template
- **Performance**: Use the performance template
- **Question**: Use the question template
- **Bioinformatics**: Use the bioinformatics template for domain-specific issues

### Issue Labels

We use labels to categorize issues:
- `priority: critical/high/medium/low`
- `type: bug/enhancement/documentation/performance/question`
- `component: core/prime/bioinformatics/deepsearch/challenge/tools/agents/config/graph/docs`
- `status: needs-triage/in-progress/blocked/needs-review/ready-for-testing/resolved`

## Pull Request Guidelines

### Before Submitting

1. Ensure all tests pass
2. Run all quality checks (linting, formatting, type checking) and fix any issues
3. Update documentation as needed
4. Add tests for new functionality
5. Update CHANGELOG.md if applicable

### Pull Request Template

Use the provided pull request template and fill out all relevant sections.

### Review Process

1. **Automated Checks**: All CI checks must pass
2. **Code Review**: At least one maintainer must approve
3. **Testing**: Changes must be tested
4. **Documentation**: Documentation must be updated

### Merge Requirements

- All CI checks pass (including tests, linting, formatting, and type checking)
- At least one approval from maintainers
- No merge conflicts
- Up-to-date with main branch

## Release Process

### Version Numbering

We use [Semantic Versioning](https://semver.org/):
- `MAJOR.MINOR.PATCH` (e.g., 1.0.0)
- `MAJOR`: Breaking changes
- `MINOR`: New features (backward compatible)
- `PATCH`: Bug fixes (backward compatible)

### Release Types

- **Patch Release**: Bug fixes and minor improvements
- **Minor Release**: New features and enhancements
- **Major Release**: Breaking changes and major new features

### Release Checklist

1. Update version in `pyproject.toml`
2. Update `CHANGELOG.md`
3. Create release branch
4. Run full test suite
5. Create GitHub release
6. Publish to PyPI
7. Update documentation

## Component-Specific Guidelines

### Core Workflow Engine

- Follow Pydantic Graph patterns
- Use proper state management
- Implement error handling and recovery

### PRIME Flow

- Follow PRIME architecture principles
- Implement proper tool validation
- Use scientific grounding approaches

### Bioinformatics Flow

- Follow data fusion patterns
- Implement proper evidence validation
- Use integrative reasoning approaches

### Tool Development

- Follow ToolSpec patterns
- Implement proper input/output validation
- Use registry integration

### Agent Development

- Follow Pydantic AI patterns
- Implement proper dependency management
- Use typed contexts

## Getting Help

### Communication Channels

- **GitHub Issues**: For bug reports and feature requests
- **GitHub Discussions**: For questions and general discussion
- **Email**: [maintainers@deepcritical.dev](mailto:maintainers@deepcritical.dev)

### Resources

- [Project Documentation](README.md)
- [API Documentation](docs/)
- [Configuration Guide](configs/)
- [Examples](example/)

## Recognition

Contributors will be recognized in:
- Release notes
- CONTRIBUTORS.md file
- GitHub contributors page

Thank you for contributing to DeepCritical! 🚀
