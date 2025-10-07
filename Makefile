.PHONY: help install dev-install test test-cov lint format type-check quality clean build docs

# Default target
help:
	@echo "🚀 DeepCritical: Research Agent Ecosystem Development Commands"
	@echo "==========================================================="
	@echo ""
	@echo "📦 Installation & Setup:"
	@echo "  install      Install the package in development mode"
	@echo "  dev-install  Install with all development dependencies"
	@echo "  pre-install  Install pre-commit hooks"
	@echo ""
	@echo "🧪 Testing & Quality:"
	@echo "  test         Run all tests"
	@echo "  test-cov     Run tests with coverage report"
	@echo "  test-fast    Run tests quickly (skip slow tests)"
	@echo "  lint         Run linting (ruff)"
	@echo "  format       Run formatting (ruff + black)"
	@echo "  type-check   Run type checking (ty)"
	@echo "  quality      Run all quality checks"
	@echo "  pre-commit   Run pre-commit hooks on all files (includes docs build)"
	@echo ""
	@echo "🔬 Research Applications:"
	@echo "  research     Run basic research query"
	@echo "  single-react Run single REACT mode research"
	@echo "  multi-react  Run multi-level REACT research"
	@echo "  nested-orch  Run nested orchestration research"
	@echo "  loss-driven  Run loss-driven research"
	@echo ""
	@echo "🧬 Domain-Specific Flows:"
	@echo "  prime        Run PRIME protein engineering flow"
	@echo "  bioinfo      Run bioinformatics data fusion flow"
	@echo "  deepsearch   Run deep web search flow"
	@echo "  challenge    Run experimental challenge flow"
	@echo ""
	@echo "🛠️  Development & Tooling:"
	@echo "  scripts      Show available scripts"
	@echo "  prompt-test  Run prompt testing suite"
	@echo "  vllm-test    Run VLLM-based tests"
	@echo "  clean        Remove build artifacts and cache"
	@echo "  build        Build the package"
	@echo "  docs         Build documentation"
	@echo ""
	@echo "📊 Examples & Demos:"
	@echo "  examples     Show example usage patterns"
	@echo "  demo-antibody Design therapeutic antibody (PRIME demo)"
	@echo "  demo-protein  Analyze protein sequence (PRIME demo)"
	@echo "  demo-bioinfo  Gene function analysis (Bioinformatics demo)"

# Installation targets
install:
	uv pip install -e .

dev-install:
	uv sync --dev

# Testing targets
test:
	uv run pytest tests/ -v

test-cov:
	uv run pytest tests/ --cov=DeepResearch --cov-report=html --cov-report=term

test-fast:
	uv run pytest tests/ -m "not slow" -v

# Code quality targets
lint:
	uv run ruff check .

lint-fix:
	uv run ruff check . --fix

format:
	uv run ruff format .
	uv run black .

format-check:
	uv run ruff format --check .
	uv run black --check .

type-check:
	uvx ty check

security:
	uv run bandit -r DeepResearch/ -c pyproject.toml

quality: lint-fix format type-check security

# Development targets
clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type d -name "*.egg-info" -exec rm -rf {} +
	find . -type d -name ".pytest_cache" -exec rm -rf {} +
	find . -type d -name ".coverage" -exec rm -rf {} +
	rm -rf dist/
	rm -rf build/
	rm -rf .tox/

build:
	uv build

docs:
	@echo "Documentation build not configured yet"

# Pre-commit targets
pre-commit:
	@echo "🔍 Running pre-commit hooks (includes docs build check)..."
	pre-commit run --all-files

pre-install:
	pre-commit install
	pre-commit install --hook-type commit-msg

# Research Application Targets
research:
	@echo "🔬 Running DeepCritical Research Agent"
	@echo "Usage: make single-react question=\"Your research question\""
	@echo "       make multi-react question=\"Your complex question\""
	@echo "       make nested-orch question=\"Your orchestration question\""
	@echo "       make loss-driven question=\"Your optimization question\""

single-react:
	@echo "🔄 Running Single REACT Mode Research"
	uv run deepresearch question="$(question)" app_mode=single_react

multi-react:
	@echo "🔄 Running Multi-Level REACT Research"
	uv run deepresearch question="$(question)" app_mode=multi_level_react

nested-orch:
	@echo "🔄 Running Nested Orchestration Research"
	uv run deepresearch question="$(question)" app_mode=nested_orchestration

loss-driven:
	@echo "🎯 Running Loss-Driven Research"
	uv run deepresearch question="$(question)" app_mode=loss_driven

# Domain-Specific Flow Targets
prime:
	@echo "🧬 Running PRIME Protein Engineering Flow"
	uv run deepresearch flows.prime.enabled=true question="$(question)"

bioinfo:
	@echo "🧬 Running Bioinformatics Data Fusion Flow"
	uv run deepresearch flows.bioinformatics.enabled=true question="$(question)"

deepsearch:
	@echo "🔍 Running Deep Web Search Flow"
	uv run deepresearch flows.deepsearch.enabled=true question="$(question)"

challenge:
	@echo "🏆 Running Experimental Challenge Flow"
	uv run deepresearch challenge.enabled=true question="$(question)"

# Development & Tooling Targets
scripts:
	@echo "🛠️  Available Scripts in scripts/ directory:"
	@find scripts/ -type f -name "*.py" -o -name "*.sh" | sort
	@echo ""
	@echo "📋 Prompt Testing Scripts:"
	@find scripts/prompt_testing/ -type f \( -name "*.py" -o -name "*.sh" \) | sort
	@echo ""
	@echo "Usage examples:"
	@echo "  python scripts/prompt_testing/run_vllm_tests.py"
	@echo "  python scripts/prompt_testing/test_matrix_functionality.py"

prompt-test:
	@echo "🧪 Running Prompt Testing Suite"
	python scripts/prompt_testing/test_matrix_functionality.py

vllm-test:
	@echo "🤖 Running VLLM-based Tests"
	python scripts/prompt_testing/run_vllm_tests.py

# Example & Demo Targets
examples:
	@echo "📊 DeepCritical Usage Examples"
	@echo "=============================="
	@echo ""
	@echo "🔬 Research Applications:"
	@echo "  make single-react question=\"What is machine learning?\""
	@echo "  make multi-react question=\"Analyze machine learning in drug discovery\""
	@echo "  make nested-orch question=\"Design a comprehensive research framework\""
	@echo "  make loss-driven question=\"Optimize research quality\""
	@echo ""
	@echo "🧬 Domain Flows:"
	@echo "  make prime question=\"Design a therapeutic antibody for SARS-CoV-2\""
	@echo "  make bioinfo question=\"What is the function of TP53 gene?\""
	@echo "  make deepsearch question=\"Latest advances in quantum computing\""
	@echo "  make challenge question=\"Solve this research challenge\""
	@echo ""
	@echo "🛠️  Development:"
	@echo "  make quality    # Run all quality checks"
	@echo "  make test       # Run all tests"
	@echo "  make prompt-test # Test prompt functionality"
	@echo "  make vllm-test  # Test with VLLM containers"

demo-antibody:
	@echo "💉 PRIME Demo: Therapeutic Antibody Design"
	uv run deepresearch flows.prime.enabled=true question="Design a therapeutic antibody for SARS-CoV-2 spike protein targeting the receptor-binding domain with high affinity and neutralization potency"

demo-protein:
	@echo "🧬 PRIME Demo: Protein Sequence Analysis"
	uv run deepresearch flows.prime.enabled=true question="Analyze protein sequence MKTVRQERLKSIVRILERSKEPVSGAQLAEELSVSRQVIVQDIAYLRSLGYNIVATPRGYVLAGG and predict its structure, function, and potential binding partners"

demo-bioinfo:
	@echo "🧬 Bioinformatics Demo: Gene Function Analysis"
	uv run deepresearch flows.bioinformatics.enabled=true question="What is the function of TP53 gene based on GO annotations and recent literature? Include evidence from experimental studies and cross-reference with protein interaction data"

# CI targets (for GitHub Actions)
ci-test:
	uv run pytest tests/ --cov=DeepResearch --cov-report=xml

ci-quality: quality
	uv run ruff check . --output-format=github
	uvx ty check --output github

# Quick development cycle
dev: format lint type-check test-fast

# Full development cycle
full: quality test-cov

# Environment targets
venv:
	python -m venv .venv
	.venv/bin/activate && pip install uv && uv sync --dev

# Documentation commands
docs-serve:
	@echo "🚀 Starting MkDocs development server..."
	uv run mkdocs serve

docs-build:
	@echo "📚 Building documentation..."
	uv run mkdocs build

docs-deploy:
	@echo "🚀 Deploying documentation..."
	uv run mkdocs gh-deploy

docs-check:
	@echo "🔍 Checking documentation links..."
	uv run mkdocs build --strict
