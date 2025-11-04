#!/bin/bash
set -e

echo "🚀 Running CI checks locally..."
echo ""

echo "=== 1/4: LINT CHECK ==="
uv run ruff check DeepResearch/ tests/ --extend-ignore=EXE001,PLR0913,PLR0912,PLR0915,PLR0911
echo "✅ LINT PASSED"
echo ""

echo "=== 2/4: FORMAT CHECK ==="
uv run ruff format --check DeepResearch/ tests/
echo "✅ FORMAT PASSED"
echo ""

echo "=== 3/4: TYPE CHECK (our files) ==="
uvx ty check DeepResearch/app.py tests/imports/test_app_imports.py
echo "✅ TYPE CHECK PASSED (our changes)"
echo ""

echo "=== 4/4: RUNNING TESTS ==="
uv run pytest tests/ -m "not optional and not containerized" -x
echo "✅ TESTS PASSED"
echo ""

echo "🎉 All CI checks passed locally!"
