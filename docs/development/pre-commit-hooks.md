# Pre-commit Hooks Guide

This guide explains the pre-commit hook system used in DeepCritical for automated code quality assurance and consistency.

## Overview

Pre-commit hooks are automated scripts that run before each commit to ensure code quality, consistency, and adherence to project standards. DeepCritical uses a comprehensive set of hooks that catch issues early in the development process.

## Setup

### Installation

```bash
# Install pre-commit hooks (required for all contributors)
make pre-install

# Verify installation
pre-commit --version
```

### Manual Installation

```bash
# Alternative manual installation
pip install pre-commit
pre-commit install

# Install hooks in CI environment
pre-commit install --install-hooks
```

## Configuration

The pre-commit configuration is defined in `.pre-commit-config.yaml`:

```yaml
repos:
  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v4.4.0
    hooks:
      - id: trailing-whitespace
      - id: end-of-file-fixer
      - id: check-yaml
      - id: check-toml
      - id: check-merge-conflict
      - id: debug-statements

  - repo: https://github.com/psf/black
    rev: 23.7.0
    hooks:
      - id: black

  - repo: https://github.com/charliermarsh/ruff-pre-commit
    rev: v0.0.285
    hooks:
      - id: ruff
        args: [--fix]

  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v1.5.1
    hooks:
      - id: mypy
        additional_dependencies: [types-all]
```

## Available Hooks

### Core Quality Hooks

#### Ruff (Fast Python Linter and Formatter)
- **Purpose**: Code linting, formatting, and import sorting
- **Configuration**: `pyproject.toml`
- **Fixes automatically**: Import sorting, unused imports, formatting
- **Fails on**: Code style violations, syntax errors

```bash
# Manual usage
uv run ruff check .
uv run ruff check . --fix  # Auto-fix issues
uv run ruff format .        # Format code
```

#### Black (Code Formatter)
- **Purpose**: Opinionated code formatting
- **Configuration**: `pyproject.toml`
- **Fixes automatically**: Code formatting
- **Fails on**: Format violations

```bash
# Manual usage
uv run black .
uv run black --check .  # Check only
```

#### MyPy/Type Checking
- **Purpose**: Static type checking
- **Configuration**: `pyproject.toml`, `mypy.ini`
- **Fixes automatically**: None (informational only)
- **Fails on**: Type errors

```bash
# Manual usage
uv run mypy .
```

### Security Hooks

#### Bandit (Security Linter)
- **Purpose**: Security vulnerability detection
- **Configuration**: `.bandit` file
- **Fixes automatically**: None
- **Fails on**: Security issues

```bash
# Manual usage
uv run bandit -r DeepResearch/
```

### Standard Hooks

#### Trailing Whitespace
- **Purpose**: Remove trailing whitespace
- **Fixes automatically**: Trailing whitespace
- **Fails on**: Files with trailing whitespace

#### End of File Fixer
- **Purpose**: Ensure files end with newline
- **Fixes automatically**: Missing newlines
- **Fails on**: Files without final newline

#### YAML/TOML Validation
- **Purpose**: Validate configuration file syntax
- **Fixes automatically**: None
- **Fails on**: Invalid YAML/TOML syntax

#### Merge Conflict Detection
- **Purpose**: Detect unresolved merge conflicts
- **Fixes automatically**: None
- **Fails on**: Files with merge conflict markers

#### Debug Statement Detection
- **Purpose**: Prevent debug statements in production code
- **Fixes automatically**: None
- **Fails on**: Files with debug statements

## Usage

### Before Committing

Pre-commit hooks run automatically on `git commit`. If any hook fails, the commit is blocked until issues are resolved.

```bash
# Stage your changes
git add .

# Attempt to commit (hooks run automatically)
git commit -m "feat: add new feature"

# If hooks fail, fix issues and try again
# Hooks will auto-fix some issues
git add .
git commit -m "feat: add new feature"
```

### Manual Execution

```bash
# Run all hooks on all files
pre-commit run --all-files

# Run specific hook
pre-commit run ruff --all-files

# Run hooks on specific files
pre-commit run --files DeepResearch/src/agents.py

# Run hooks on staged files only
pre-commit run
```

### CI Integration

Pre-commit hooks are integrated into the CI pipeline:

```yaml
# .github/workflows/ci.yml
- name: Run pre-commit hooks
  run: |
    pre-commit run --all-files
```

## Hook Behavior

### Auto-fixing Hooks

Some hooks can automatically fix issues:

- **Ruff**: Fixes import sorting, unused imports, some formatting
- **Black**: Fixes code formatting
- **Trailing Whitespace**: Removes trailing whitespace
- **End of File Fixer**: Adds missing newlines

### Informational Hooks

Other hooks provide information but don't auto-fix:

- **MyPy**: Reports type issues (can be configured to fail)
- **Bandit**: Reports security issues
- **YAML/TOML validation**: Reports syntax errors

## Configuration

### Hook Configuration

Configure hook behavior in `.pre-commit-config.yaml`:

```yaml
repos:
  - repo: https://github.com/charliermarsh/ruff-pre-commit
    rev: v0.0.285
    hooks:
      - id: ruff
        args: [--fix, --show-fixes]
        exclude: ^(docs/|examples/)
```

### Skipping Hooks

```bash
# Skip all hooks for a commit
git commit --no-verify -m "urgent fix"

# Skip specific hooks
SKIP=ruff git commit -m "temporary workaround"
```

### Local Configuration

Override configuration locally with `.pre-commit-config-local.yaml`:

```yaml
repos:
  - repo: local
    hooks:
      - id: custom-check
        name: Custom check
        entry: python scripts/custom_check.py
        language: system
        files: \.py$
```

## Troubleshooting

### Common Issues

**Hooks not running:**
```bash
# Check if hooks are installed
pre-commit --version

# Reinstall hooks
pre-commit install --install-hooks
```

**Slow hooks:**
```bash
# Use file filtering
pre-commit run --files changed_files.txt

# Skip slow hooks temporarily
SKIP=mypy pre-commit run
```

**Hook failures:**
```bash
# Get detailed output
pre-commit run ruff --verbose

# Run hooks individually for debugging
pre-commit run ruff --all-files
pre-commit run black --all-files
```

### Performance Optimization

**Caching:**
Pre-commit automatically caches hook environments for faster subsequent runs.

**Parallel Execution:**
```bash
# Run hooks in parallel (if supported)
pre-commit run --all-files --parallel
```

**Selective Execution:**
```bash
# Only run on changed files
pre-commit run --from-ref HEAD~1 --to-ref HEAD
```

## Best Practices

### For Contributors

1. **Always run hooks** before pushing changes
2. **Fix hook failures** immediately when they occur
3. **Don't skip hooks** without good reason
4. **Keep hooks updated** with the latest versions
5. **Review auto-fixes** to understand code standards

### For Maintainers

1. **Keep hook versions current** to benefit from latest improvements
2. **Configure hooks appropriately** for project needs
3. **Document custom hooks** and their purpose
4. **Monitor hook performance** and optimize slow hooks
5. **Review hook failures** in CI and address issues

### Development Workflow

```bash
# Development workflow with hooks
1. Make changes
2. Stage changes: git add .
3. Run hooks manually: pre-commit run
4. Fix any issues
5. Commit: git commit -m "message"
6. Push: git push
```

## Advanced Usage

### Custom Hooks

Create custom hooks for project-specific checks:

```yaml
repos:
  - repo: local
    hooks:
      - id: check-license
        name: Check license headers
        entry: python scripts/check_license.py
        language: system
        files: \.py$
```

### Hook Dependencies

Specify dependencies for hooks:

```yaml
repos:
  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v1.5.1
    hooks:
      - id: mypy
        additional_dependencies:
          - types-requests
          - types-pytz
```

### Conditional Hooks

Run hooks only in certain conditions:

```yaml
repos:
  - repo: local
    hooks:
      - id: expensive-check
        name: Expensive check
        entry: python scripts/expensive_check.py
        language: system
        files: \.py$
        pass_filenames: false
        stages: [commit]
        # Only run if EXPENSIVE_CHECKS=true
        args: [--enable-only-if-env=EXPENSIVE_CHECKS]
```

## Integration

### IDE Integration

Many IDEs support pre-commit hooks:

**VS Code:**
- Install "Pre-commit" extension
- Configure to run on save

**PyCharm:**
- Configure pre-commit as external tool
- Set up file watchers

### CI/CD Integration

Pre-commit is integrated into the CI pipeline to ensure all code meets quality standards before merging.

## Related Documentation

- [Contributing Guide](contributing.md) - Development workflow
- [Testing Guide](testing.md) - Testing practices
- [Makefile Usage](makefile-usage.md) - Build system
- [CI/CD Guide](ci-cd.md) - Continuous integration
