# Makefile Usage Guide

This guide documents the comprehensive Makefile system used for DeepCritical development, testing, and deployment workflows.

## Overview

The Makefile provides a unified interface for all development operations, ensuring consistency across different environments and platforms.

## Core Commands

### Development Setup

```bash
# Install all dependencies and setup development environment
make install

# Install with development dependencies
make install-dev

# Install pre-commit hooks
make pre-install

# Setup complete development environment
make setup
```

### Quality Assurance

```bash
# Run all quality checks (linting, formatting, type checking)
make quality

# Individual quality tools
make lint          # Ruff linting
make format        # Code formatting with Ruff
make type-check    # Type checking with pyright/ty

# Format and fix code automatically
make format-fix
```

### Testing

```bash
# Run complete test suite
make test

# Run tests with coverage
make test-cov

# Run specific test categories
make test-unit         # Unit tests only
make test-integration  # Integration tests only
make test-performance  # Performance tests only

# Run tests excluding slow/optional tests
make test-fast

# Generate coverage reports
make coverage-html
make coverage-xml
```

### Documentation

```bash
# Build documentation
make docs-build

# Serve documentation locally
make docs-serve

# Check documentation links and structure
make docs-check

# Deploy documentation
make docs-deploy
```

### Development Workflow

```bash
# Quick development cycle (format, test, quality)
make dev

# Run examples and demos
make examples

# Clean build artifacts and cache
make clean

# Deep clean (remove all generated files)
make clean-all
```

## Platform-Specific Commands

### Windows Support

```bash
# Windows-specific test commands
make test-unit-win
make test-pydantic-ai-win
make test-performance-win
make test-containerized-win
make test-docker-win
make test-bioinformatics-win

# Windows quality checks
make format-win
make lint-win
make type-check-win
```

### Branch-Specific Testing

```bash
# Main branch testing (includes all tests)
make test-main
make test-main-cov

# Development branch testing (excludes optional tests)
make test-dev
make test-dev-cov

# Optional tests (CI, performance, containers)
make test-optional
make test-optional-cov
```

## Configuration and Environment

### Environment Variables

The Makefile respects several environment variables for customization:

```bash
# Control optional test execution
DOCKER_TESTS=true     # Enable Docker/container tests
VLLM_TESTS=true       # Enable VLLM tests
PERFORMANCE_TESTS=true # Enable performance tests

# Python and tool versions
PYTHON_VERSION=3.11
RUFF_VERSION=0.1.0

# Build and deployment
BUILD_VERSION=1.0.0
DOCKER_TAG=latest
```

### Configuration Files

Key configuration files used by the Makefile:

- `pyproject.toml` - Python project configuration
- `Makefile` - Build system configuration
- `tox.ini` - Testing environment configuration
- `pytest.ini` - Pytest configuration
- `.pre-commit-config.yaml` - Pre-commit hooks configuration

## Command Reference

### Quality Assurance Targets

| Target | Description | Dependencies |
|--------|-------------|--------------|
| `quality` | Run all quality checks | `lint`, `format`, `type-check` |
| `lint` | Run Ruff linter | `ruff` |
| `format` | Check code formatting | `ruff format --check` |
| `format-fix` | Auto-fix formatting issues | `ruff format` |
| `type-check` | Run type checker | `ty` or `pyright` |

### Testing Targets

| Target | Description | Notes |
|--------|-------------|-------|
| `test` | Run all tests | Includes optional tests |
| `test-fast` | Run fast tests only | Excludes slow/optional tests |
| `test-unit` | Unit tests only | Core functionality tests |
| `test-integration` | Integration tests | Component interaction tests |
| `test-performance` | Performance tests | Speed and resource usage tests |
| `test-cov` | Tests with coverage | Generates coverage reports |

### Development Targets

| Target | Description | Use Case |
|--------|-------------|----------|
| `dev` | Development cycle | Quick iteration during development |
| `examples` | Run examples | Validate functionality with examples |
| `install` | Install dependencies | Initial setup |
| `setup` | Complete setup | First-time development setup |
| `clean` | Clean artifacts | Remove generated files |

### Documentation Targets

| Target | Description | Output |
|--------|-------------|--------|
| `docs-build` | Build documentation | `site/` directory |
| `docs-serve` | Serve docs locally | Local development server |
| `docs-check` | Validate documentation | Link checking, structure validation |
| `docs-deploy` | Deploy documentation | GitHub Pages or other hosting |

## Advanced Usage

### Custom Targets

The Makefile supports custom targets for specific workflows:

```makefile
# Example custom target
custom-workflow:
	@echo "Running custom workflow..."
	@make quality
	@make test-unit
	@python scripts/custom_script.py
```

### Parallel Execution

```bash
# Run tests in parallel (if supported)
make test-parallel

# Run quality checks in parallel
make quality-parallel
```

### Conditional Execution

```bash
# Run only if certain conditions are met
make test-conditional

# Skip certain steps based on environment
CI=true make test-ci
```

## Troubleshooting

### Common Issues

**Permission Errors:**
```bash
# Fix file permissions
chmod +x scripts/*.py
make clean
make install
```

**Dependency Conflicts:**
```bash
# Clear caches and reinstall
make clean-all
rm -rf .venv
make install-dev
```

**Test Failures:**
```bash
# Run specific failing test
python -m pytest tests/test_specific.py::TestClass::test_method -v

# Debug test environment
make test-debug
```

**Build Failures:**
```bash
# Check build logs
make build 2>&1 | tee build.log

# Validate configuration
make config-check
```

### Debug Mode

Enable verbose output for debugging:

```bash
# Verbose Makefile execution
make VERBOSE=1 target

# Debug test execution
make test-debug

# Show all available targets
make help
```

## Integration with CI/CD

The Makefile integrates seamlessly with CI/CD pipelines:

```yaml
# .github/workflows/ci.yml
- name: Run quality checks
  run: make quality

- name: Run tests
  run: make test-cov

- name: Build documentation
  run: make docs-build
```

## Best Practices

1. **Always run quality checks** before committing
2. **Use appropriate test targets** for different scenarios
3. **Keep the development environment clean** with regular `make clean`
4. **Document custom targets** in this guide
5. **Test Makefile changes** thoroughly before merging

## Contributing

When adding new Makefile targets:

1. Follow the existing naming conventions
2. Add documentation to this guide
3. Include proper error handling
4. Test on multiple platforms
5. Update CI/CD pipelines if necessary

## Related Documentation

- [Contributing Guide](contributing.md) - Development workflow
- [Testing Guide](testing.md) - Testing best practices
- [CI/CD Guide](ci-cd.md) - Continuous integration setup
- [Setup Guide](setup.md) - Development environment setup
