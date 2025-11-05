# Ray's Pre-Commit Workflow

## ALWAYS Run These Before Pushing

### 1. Format Everything
```bash
# Format all code (auto-fixes)
uv run ruff format DeepResearch/ tests/

# Check formatting (dry run)
uv run ruff format --check DeepResearch/ tests/
```

### 2. Lint Everything
```bash
# Lint all code (shows issues)
uv run ruff check DeepResearch/ tests/

# Auto-fix linting issues
uv run ruff check --fix DeepResearch/ tests/
```

### 3. Type Check Everything
```bash
# This project uses 'ty' (not mypy/pyright!)
uvx ty check
```

### 4. Run Tests
```bash
# Fast tests
make test-fast

# All tests (if needed)
uv run pytest
```

## Full Pre-Commit Command

Copy-paste this before every commit:

```bash
uv run ruff format DeepResearch/ tests/ && \
uv run ruff check --fix DeepResearch/ tests/ && \
uvx ty check && \
make test-fast
```

## What CI Actually Runs

The GitHub Actions CI runs:
- `ruff check DeepResearch/ tests/ --extend-ignore=EXE001,PLR0913,PLR0912,PLR0915,PLR0911`
- `uvx ty check`
- `pytest` (all tests)

## Common Mistakes

### ❌ WRONG - Only checking one file
```bash
uv run ruff check DeepResearch/app.py
```

### ✅ RIGHT - Check all directories
```bash
uv run ruff check DeepResearch/ tests/
```

### ❌ WRONG - Forgetting type checker
```bash
# Just running ruff isn't enough!
```

### ✅ RIGHT - Always run type checker
```bash
uvx ty check
```

## Fixing Specific Issues

### Import Sorting (I001)
```bash
# Auto-fix import sorting
uv run ruff check --fix --select I DeepResearch/ tests/
```

### Type Errors
```bash
# Check types
uvx ty check

# Some type errors may be pre-existing - check git blame to see if you introduced them
```

## Branch Workflow

### Working in ray-sandbox
```bash
# 1. Make changes
# 2. Run pre-commit checks
uv run ruff format DeepResearch/ tests/
uv run ruff check --fix DeepResearch/ tests/
uvx ty check
make test-fast

# 3. Commit if all pass
git add .
git commit -m "fix: description"
git push origin ray-sandbox
```

### Creating PRs
```bash
# 1. Create feature branch from upstream
git fetch upstream
git checkout -b feat/my-feature upstream/dev

# 2. Make changes
# 3. Run pre-commit checks (same as above)
# 4. Push and create PR
git push origin feat/my-feature
gh pr create --repo DeepCritical/DeepCritical --base dev
```

### Cherry-picking fixes from ray-sandbox to PR branches
```bash
# 1. Fix issues in ray-sandbox
git checkout ray-sandbox
# make fixes, commit

# 2. Find the commit hash
git log --oneline -5

# 3. Switch to feature branch
git checkout feat/my-feature

# 4. Cherry-pick the fix
git cherry-pick <commit-hash>

# 5. Push to update PR
git push origin feat/my-feature
```

## Notes

- This project uses `ty` for type checking (not mypy/pyright)
- Always check BOTH `DeepResearch/` and `tests/` directories
- Some type errors in the codebase are pre-existing (not your fault)
- CI is strict - all checks must pass before merge
