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
	@echo "  test-dev     Run tests excluding optional (for dev branch)"
	@echo "  test-dev-cov Run tests excluding optional with coverage (for dev branch)"
	@echo "  test-main    Run all tests including optional (for main branch)"
	@echo "  test-main-cov Run all tests including optional with coverage (for main branch)"
	@echo "  test-optional Run only optional tests"
	@echo "  test-optional-cov Run only optional tests with coverage"
	@echo "  test-*-pytest  Alternative pytest-only versions (for CI without uv)"
ifeq ($(OS),Windows_NT)
	@echo "  test-unit-win       Run unit tests (Windows)"
	@echo "  test-integration-win Run integration tests (Windows)"
	@echo "  test-docker-win     Run Docker tests (Windows, requires Docker)"
	@echo "  test-bioinformatics-win Run bioinformatics tests (Windows, requires Docker)"
	@echo "  test-llm-win        Run LLM framework tests (Windows)"
	@echo "  test-pydantic-ai-win Run Pydantic AI tests (Windows)"
	@echo "  test-containerized-win Run all containerized tests (Windows, requires Docker)"
	@echo "  test-performance-win Run performance tests (Windows)"
	@echo "  test-optional-win   Run all optional tests (Windows)"
endif
	@echo "  lint         Run linting (ruff)"
	@echo "  format       Run formatting (ruff)"
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
	@echo "  docs         Build documentation (full validation)"
	@echo ""
	@echo "🐳 Bioinformatics Docker:"
	@echo "  docker-build-bioinformatics    Build all bioinformatics Docker images"
	@echo "  docker-publish-bioinformatics  Publish images to Docker Hub"
	@echo "  docker-test-bioinformatics     Test built bioinformatics images"
	@echo "  docker-check-bioinformatics    Check Docker Hub image availability"
	@echo "  docker-pull-bioinformatics     Pull latest images from Docker Hub"
	@echo "  docker-clean-bioinformatics    Remove local bioinformatics images"
	@echo "  docker-status-bioinformatics   Show bioinformatics image status"
	@echo "  test-bioinformatics-containerized Run containerized bioinformatics tests"
	@echo "  test-bioinformatics-all        Run all bioinformatics tests"
	@echo "  validate-bioinformatics        Validate bioinformatics configurations"
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

# Branch-specific testing targets
test-dev:
	uv run pytest tests/ -m "not optional" -v

test-dev-cov:
	uv run pytest tests/ -m "not optional" --cov=DeepResearch --cov-report=html --cov-report=term

test-main:
	uv run pytest tests/ -v

test-main-cov:
	uv run pytest tests/ --cov=DeepResearch --cov-report=html --cov-report=term

test-optional:
	uv run pytest tests/ -m "optional" -v

test-optional-cov:
	uv run pytest tests/ -m "optional" --cov=DeepResearch --cov-report=html --cov-report=term

# Alternative pytest-only versions (for CI environments without uv)
test-dev-pytest:
	pytest tests/ -m "not optional" -v

test-dev-cov-pytest:
	pytest tests/ -m "not optional" --cov=DeepResearch --cov-report=xml --cov-report=term-missing

test-main-pytest:
	pytest tests/ -v

test-main-cov-pytest:
	pytest tests/ --cov=DeepResearch --cov-report=xml --cov-report=term-missing

test-optional-pytest:
	pytest tests/ -m "optional" -v

test-optional-cov-pytest:
	pytest tests/ -m "optional" --cov=DeepResearch --cov-report=xml --cov-report=term-missing

# Windows-specific testing targets (using PowerShell script)
ifeq ($(OS),Windows_NT)
test-unit-win:
	@powershell -ExecutionPolicy Bypass -File scripts/test/run_tests.ps1 -TestType unit

test-integration-win:
	@powershell -ExecutionPolicy Bypass -File scripts/test/run_tests.ps1 -TestType integration

test-docker-win:
	@powershell -ExecutionPolicy Bypass -File scripts/test/run_tests.ps1 -TestType docker

test-bioinformatics-win:
	@powershell -ExecutionPolicy Bypass -File scripts/test/run_tests.ps1 -TestType bioinformatics

test-bioinformatics-unit-win:
	@echo "Running bioinformatics unit tests..."
	uv run pytest tests/test_bioinformatics_tools/ -m "not containerized" -v --tb=short

# General bioinformatics test target (works on all platforms)
test-bioinformatics:
	@echo "Running bioinformatics tests..."
	uv run pytest tests/test_bioinformatics_tools/ -v --tb=short

test-llm-win:
	@echo "Running LLM framework tests..."
	uv run pytest tests/test_llm_framework/ -v --tb=short

test-pydantic-ai-win:
	@echo "Running Pydantic AI tests..."
	uv run pytest tests/test_pydantic_ai/ -v --tb=short

test-containerized-win:
	@powershell -ExecutionPolicy Bypass -File scripts/test/run_tests.ps1 -TestType containerized

test-performance-win:
	@powershell -ExecutionPolicy Bypass -File scripts/test/run_tests.ps1 -TestType performance

test-optional-win: test-containerized-win test-performance-win
	@echo "Optional tests completed"
endif

# Code quality targets
lint:
	uv run ruff check .

lint-fix:
	uv run ruff check . --fix

format:
	uv run ruff format .

format-check:
	uv run ruff format --check .

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
	@echo "📚 Building DeepCritical Documentation"
	@echo "======================================"
	@echo "Building documentation (like pre-commit and CI)..."
	uv run mkdocs build --clean
	@echo ""
	@echo "✅ Documentation built successfully!"
	@echo "📁 Site files generated in: ./site/"
	@echo ""
	@echo "🔍 Running strict validation..."
	uv run mkdocs build --strict --quiet
	@echo ""
	@echo "✅ Documentation validation passed!"
	@echo ""
	@echo "🚀 Next steps:"
	@echo "  • Serve locally: make docs-serve"
	@echo "  • Deploy to GitHub Pages: make docs-deploy"
	@echo "  • Check links: make docs-check"

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
ifeq ($(OS),Windows_NT)
	@echo "  make test-unit-win       # Run unit tests (Windows)"
	@echo "  make test-integration-win # Run integration tests (Windows)"
	@echo "  make test-docker-win     # Run Docker tests (Windows, requires Docker)"
	@echo "  make test-bioinformatics-win # Run bioinformatics tests (Windows, requires Docker)"
	@echo "  make test-llm-win        # Run LLM framework tests (Windows)"
	@echo "  make test-pydantic-ai-win # Run Pydantic AI tests (Windows)"
	@echo "  make test-containerized-win # Run all containerized tests (Windows, requires Docker)"
	@echo "  make test-performance-win # Run performance tests (Windows)"
	@echo "  make test-optional-win   # Run all optional tests (Windows)"
endif
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
	@echo "🔍 Running strict documentation validation (warnings = errors)..."
	uv run mkdocs build --strict

# Docker targets
docker-build-bioinformatics:
	@echo "🐳 Building bioinformatics Docker images..."
	@for dockerfile in docker/bioinformatics/Dockerfile.*; do \
		tool=$$(basename "$$dockerfile" | cut -d'.' -f2); \
		echo "Building $$tool..."; \
		docker build -f "$$dockerfile" -t "deepcritical-$$tool:latest" . ; \
	done

docker-publish-bioinformatics:
	@echo "🚀 Publishing bioinformatics Docker images to Docker Hub..."
	python scripts/publish_docker_images.py

docker-test-bioinformatics:
	@echo "🐳 Testing bioinformatics Docker images..."
	@for dockerfile in docker/bioinformatics/Dockerfile.*; do \
		tool=$$(basename "$$dockerfile" | cut -d'.' -f2); \
		echo "Testing $$tool container..."; \
		docker run --rm "deepcritical-$$tool:latest" --version || echo "⚠️  $$tool test failed"; \
	done

# Update the existing test targets to include containerized tests
test-bioinformatics-containerized:
	@echo "🐳 Running containerized bioinformatics tests..."
	uv run pytest tests/test_bioinformatics_tools/ -m "containerized" -v --tb=short

test-bioinformatics-all:
	@echo "🧬 Running all bioinformatics tests..."
	uv run pytest tests/test_bioinformatics_tools/ -v --tb=short

# Check Docker Hub images
docker-check-bioinformatics:
	@echo "🔍 Checking bioinformatics Docker Hub images..."
	python scripts/publish_docker_images.py --check-only

# Clean up local bioinformatics Docker images
docker-clean-bioinformatics:
	@echo "🧹 Cleaning up bioinformatics Docker images..."
	@for dockerfile in docker/bioinformatics/Dockerfile.*; do \
		tool=$$(basename "$$dockerfile" | cut -d'.' -f2); \
		echo "Removing deepcritical-$$tool:latest..."; \
		docker rmi "deepcritical-$$tool:latest" 2>/dev/null || echo "Image not found: deepcritical-$$tool:latest"; \
	done
	@echo "Removing dangling images..."
	docker image prune -f

# Pull latest bioinformatics images from Docker Hub
docker-pull-bioinformatics:
	@echo "📥 Pulling latest bioinformatics images from Docker Hub..."
	@for dockerfile in docker/bioinformatics/Dockerfile.*; do \
		tool=$$(basename "$$dockerfile" | cut -d'.' -f2); \
		image_name="tonic01/deepcritical-bioinformatics-$$tool:latest"; \
		echo "Pulling $$image_name..."; \
		docker pull "$$image_name" || echo "Failed to pull $$image_name"; \
	done

# Show bioinformatics Docker image status
docker-status-bioinformatics:
	@echo "📊 Bioinformatics Docker Images Status:"
	@echo "=========================================="
	@for dockerfile in docker/bioinformatics/Dockerfile.*; do \
		tool=$$(basename "$$dockerfile" | cut -d'.' -f2); \
		local_image="deepcritical-$$tool:latest"; \
		hub_image="tonic01/deepcritical-bioinformatics-$$tool:latest"; \
		echo "$$tool:"; \
		if docker images --format "table {{.Repository}}:{{.Tag}}" | grep -q "$$local_image"; then \
			echo "  ✅ Local: $$local_image"; \
		else \
			echo "  ❌ Local: $$local_image (not built)"; \
		fi; \
		if docker images --format "table {{.Repository}}:{{.Tag}}" | grep -q "$$hub_image"; then \
			echo "  ✅ Hub: $$hub_image"; \
		else \
			echo "  ❌ Hub: $$hub_image (not pulled)"; \
		fi; \
	done

# Validate bioinformatics configurations
validate-bioinformatics:
	@echo "🔍 Validating bioinformatics configurations..."
	@python3 -c "\
import yaml, os; \
from pathlib import Path; \
config_dir = Path('DeepResearch/src/tools/bioinformatics'); \
valid_configs = 0; \
invalid_configs = 0; \
for config_file in config_dir.glob('*_server.py'): \
    try: \
        module_name = config_file.stem; \
        exec(f'from DeepResearch.src.tools.bioinformatics.{module_name} import *'); \
        print(f'✅ {module_name}'); \
        valid_configs += 1; \
    except Exception as e: \
        print(f'❌ {module_name}: {e}'); \
        invalid_configs += 1; \
print(f'\\n📊 Validation Summary:'); \
print(f'✅ Valid configs: {valid_configs}'); \
print(f'❌ Invalid configs: {invalid_configs}'); \
if invalid_configs > 0: exit(1)"
