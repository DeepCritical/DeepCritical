# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Essential Commands

### Package Management
Use **uv** (recommended) for all package operations:
```bash
uv sync --dev              # Install all dependencies
uv run <command>           # Run commands in virtual environment
uvx <tool>                 # Run tools without installation
```

### Development Workflow
```bash
make dev                   # Quick cycle: format, lint, type-check, test-fast
make full                  # Full cycle: quality checks + coverage
make quality               # All quality checks (lint, format, type, security)
```

### Pre-commit Hooks (PRIMARY QUALITY ASSURANCE)
**Always use pre-commit hooks** - they are the primary quality gate:
```bash
make pre-install           # Install hooks (required first step)
make pre-commit            # Run all checks manually
```

### Code Quality
```bash
# Linting
uv run ruff check .        # Check code quality
uv run ruff check . --fix  # Auto-fix issues

# Formatting
uv run ruff format .       # Format all code

# Type Checking
uvx ty check               # Type validation (uses 'ty', not mypy)

# Security
uv run bandit -r DeepResearch/  # Security scanning
```

### Testing
```bash
# Quick testing
make test-fast             # Skip slow/containerized tests

# Comprehensive testing
uv run pytest              # All tests
uv run pytest --cov=DeepResearch --cov-report=html  # With coverage

# Specific test categories
pytest -m "not slow"       # Skip slow tests
pytest -m "containerized"  # Docker-based tests only
pytest -m "pydantic_ai"    # Pydantic AI agent tests
pytest -m "performance"    # Performance benchmarks
```

### Documentation
```bash
make docs                  # Build documentation
make docs-serve            # Serve docs locally at http://127.0.0.1:8000
```

### Running the Application
```bash
# CLI interface (primary)
uv run deepresearch --help
uv run deepresearch question="Your research question"

# With specific flow
uv run deepresearch flows.prime.enabled=true question="Design a protein..."

# Override configuration
uv run deepresearch --config-name=config_with_modes
```

## Architecture Overview

### Core Architecture Pattern
**Hydra + Pydantic Graph + Pydantic AI Multi-Agent System**

The system uses a **workflow-of-workflows** pattern where a primary orchestrator can dynamically spawn sub-workflows, each with specialized agent systems.

```
User Request
    ↓
Hydra Configuration Layer (composable configs)
    ↓
Pydantic Graph Workflow Engine (stateful execution)
    ↓
Flow Router (PRIME/Bioinformatics/DeepSearch/RAG/etc.)
    ↓
Pydantic AI Agent Orchestration (multi-agent coordination)
    ↓
Tool Ecosystem (65+ tools including 18 MCP bioinformatics servers)
    ↓
External Integrations (LLMs, Vector Stores, Bio APIs)
```

### Key Components

**1. Main Entry Point (`DeepResearch/app.py`)**
- Pydantic Graph workflow with node-based architecture
- Nodes: `Plan`, `Route`, `Execute`, `Analyze`, `Synthesize`
- Uses `ResearchState` dataclass for state management
- Flow selection based on Hydra configuration

**2. Agent Systems (`DeepResearch/src/agents/`)**
- Multi-level orchestration (primary → enhanced REACT → specialized agents)
- Three orchestration modes:
  - Single REACT: Basic reasoning loop
  - Multi-level REACT: Nested loops with break conditions
  - Nested Orchestration: Dynamic subgraph spawning
- Specialized agents: Parser, Planner, Executor, Bioinformatics, Code Generation

**3. State Machines (`DeepResearch/src/statemachines/`)**
- Workflow implementations for different domains
- Key workflows: PRIME, Bioinformatics, DeepSearch, RAG, Code Execution
- Each workflow is a Pydantic Graph with domain-specific nodes

**4. Tool Ecosystem (`DeepResearch/src/tools/`)**
- 65+ tools across multiple domains
- 18 MCP (Model Context Protocol) bioinformatics servers
- Docker sandbox for isolated code execution
- Tool registry with validation and adaptive re-planning

**5. Configuration (`configs/`)**
- Hierarchical Hydra configuration with composition
- Flow-based configs in `configs/statemachines/flows/`
- Override pattern: CLI > file > environment variables
- Key config: `configs/config.yaml` (main), `configs/statemachines/flows/*.yaml`

### Critical Architectural Patterns

**Pydantic Graph Node Pattern:**
```python
@dataclass
class NodeName(BaseNode[ResearchState]):
    async def run(self, ctx: GraphRunContext[ResearchState]) -> NextNode:
        # Access state: ctx.state.question, ctx.state.config
        # Modify state: ctx.state.notes.append()
        return NextNode()
```

**Pydantic AI Agent Pattern:**
```python
from pydantic_ai import Agent

agent = Agent(
    model="anthropic:claude-sonnet-4-0",
    deps_type=AgentDeps,
    result_type=ResultType,
    system_prompt="..."
)

@agent.tool_plain  # or @defer for deferred execution
def tool_name(ctx: RunContext[AgentDeps], param: str) -> dict:
    return {"result": data}
```

**MCP Bioinformatics Server Pattern:**
```python
from fastmcp import FastMCP

server = FastMCP("tool_name")

@server.tool()
def operation(param1: str, param2: int) -> dict:
    """Structured input/output for bioinformatics operations"""
    return {"result": data}
```

## Important Implementation Details

### Package Name vs Repository Name
- **Repository**: `DeepCritical`
- **Package**: `DeepResearch` (import statements use `DeepResearch`)
- This is intentional - all imports are `from DeepResearch.src...`

### Type Checking
Uses **`ty`** type checker (not mypy or pyright):
```bash
uvx ty check  # Type validation
```

### Environment Variables
Copy `.env.example` to `.env` and configure:
- `ANTHROPIC_API_KEY`: Primary LLM provider
- `OPENAI_API_KEY`: Alternative LLM provider
- `SERPER_API_KEY`: Web search functionality
- `NEO4J_*`: Graph database (optional)
- `DOCKER_*`: Container execution (optional)

### Bioinformatics MCP Servers
18 containerized tools in `DeepResearch/src/tools/bioinformatics/`:
- Sequence alignment: BWA, Bowtie2, HISAT2, STAR
- Quality control: FastQC, MultiQC, Qualimap
- Variant calling: FreeBayes, BCFtools
- Quantification: Salmon, Kallisto, FeatureCounts
- And more...

Each server follows the FastMCP pattern with `@server.tool()` decorators.

### Workflow Flows
Enabled via Hydra config (`flows.*.enabled=true`):
- **PRIME**: Protein engineering and molecular biology
- **Bioinformatics**: Multi-source biological data fusion
- **DeepSearch**: Web search and research synthesis
- **RAG**: Retrieval-augmented generation with vector stores
- **Code Execution**: Sandboxed code generation and execution
- **Challenge**: Experimental validation workflows

### Multi-Agent Orchestration
Three levels of orchestration:
1. **Primary Orchestrator**: Workflow-of-workflows coordination
2. **Enhanced REACT Orchestrator**: Nested reasoning loops with break conditions
3. **Specialized Agents**: Task-specific execution (parsing, planning, execution)

Coordination strategies: Sequential, Collaborative, Competitive, Group Chat

### Adaptive Re-Planning
When tools fail:
- **Strategic**: Tool substitution (e.g., BLAST → ProTrek)
- **Tactical**: Parameter tuning (e.g., E-value relaxation)

### Break Conditions & Loss Functions
Configure execution termination:
- Iteration limits
- Time limits
- Quality thresholds
- Convergence detection
- Custom loss functions

Applied at: Global, Nested loop, or Subgraph level

## Testing Considerations

### Test Markers
```python
@pytest.mark.slow            # Skip in fast tests
@pytest.mark.containerized   # Requires Docker
@pytest.mark.pydantic_ai     # Pydantic AI framework tests
@pytest.mark.performance     # Performance benchmarks
@pytest.mark.optional        # Disabled by default
```

### Windows-Specific Tests
Use Windows-specific targets:
```bash
make test-unit-win
make test-integration-win
make test-bioinformatics-win
```

### Coverage Testing
Comprehensive coverage tracking with multiple categories:
- Unit tests: Core functionality
- Integration tests: Component interaction
- Performance tests: Benchmarking
- Containerized tests: Docker-based tools

## Configuration Deep Dive

### Hydra Composition
Hierarchical configuration with defaults:
```yaml
# configs/config.yaml
defaults:
  - challenge: default
  - workflow_orchestration: default
  - db: neo4j
  - statemachines/flows: prime
  - _self_
```

### Override Patterns
```bash
# CLI override
deepresearch flows.prime.enabled=true db.neo4j.uri="bolt://localhost:7687"

# Config file override
deepresearch --config-name=config_with_modes

# Environment variable interpolation
# In YAML: ${oc.env:ANTHROPIC_API_KEY}
```

### Flow Configuration Structure
Each flow has a config in `configs/statemachines/flows/`:
- `prime.yaml`: Protein engineering
- `bioinformatics.yaml`: Data fusion
- `deepsearch.yaml`: Web search
- `rag.yaml`: RAG pipeline
- And 16+ more...

## Key Dependencies

### Core Framework
- `hydra-core >=1.3.2`: Configuration management
- `pydantic >=2.7`: Data validation
- `pydantic-ai >=0.0.16`: Agent framework
- `pydantic-graph >=0.2.0`: Workflow engine
- `python-dotenv >=1.0.0`: Environment variable loading

### LLM & Embeddings
- Anthropic Claude (primary): via `pydantic-ai`
- OpenAI (alternative): via `pydantic-ai`
- `sentence-transformers >=5.1.1`: Local embeddings

### Vector Stores
- `neo4j >=6.0.2`: Graph database with vector indexing
- ChromaDB: In-memory vector store
- Qdrant: Production vector database

### Bioinformatics
- `fastmcp >=2.12.4`: MCP server framework
- `testcontainers`: Dynamic Docker management (custom fork)

### Development
- `ruff >=0.6.0`: Linting and formatting
- `ty`: Type checking
- `bandit >=1.7.0`: Security scanning
- `pytest >=7.0.0`: Testing framework

## Common Development Patterns

### Adding a New Flow
1. Create config: `configs/statemachines/flows/newflow.yaml`
2. Implement workflow: `DeepResearch/src/statemachines/newflow_workflow.py`
3. Add nodes to `DeepResearch/app.py` or use separate graph
4. Update routing in `Plan` node
5. Add tests in `tests/`

### Adding a New MCP Server
1. Create server: `DeepResearch/src/tools/bioinformatics/newtool_server.py`
2. Follow FastMCP pattern with `@server.tool()` decorators
3. Create Dockerfile: `docker/bioinformatics/newtool/Dockerfile`
4. Add to tool registry
5. Add tests in `tests/test_bioinformatics_tools/`

### Adding a New Agent
1. Define dependencies and result types (Pydantic models)
2. Create agent: `DeepResearch/src/agents/newagent.py`
3. Use `Agent(model=..., deps_type=..., result_type=...)`
4. Register tools with `@agent.tool_plain` or `@defer`
5. Integrate into workflow or orchestrator
6. Add tests in `tests/test_pydantic_ai/`

### Modifying State
Always modify `ResearchState` through graph context:
```python
async def run(self, ctx: GraphRunContext[ResearchState]) -> NextNode:
    ctx.state.notes.append("New note")
    ctx.state.results["key"] = value
    return NextNode()
```

## Documentation Structure

- `README.md`: Comprehensive overview (912 lines)
- `CONTRIBUTING.md`: Development guidelines (554 lines)
- `docs/`: MkDocs site with user guide, API reference, architecture docs
- `.env.example`: Environment variable documentation (128 lines)
- `Makefile`: Development commands (480 lines with extensive comments)

Access docs locally:
```bash
make docs-serve  # http://127.0.0.1:8000
```

## Important Notes

1. **Pre-commit hooks are mandatory** - they enforce code quality standards
2. **Use `ty` for type checking** - not mypy or pyright
3. **Package is `DeepResearch`** - despite repo being `DeepCritical`
4. **uv is preferred** over pip for package management
5. **All flows are optional** - enable via config or CLI
6. **MCP servers require Docker** - ensure Docker is running for bioinformatics tools
7. **State is immutable in nodes** - modifications only through context
8. **Agent tools use @defer** for deferred execution of heavy operations
9. **Configuration is hierarchical** - override at CLI, file, or environment level
10. **Testing requires markers** - use appropriate pytest markers for test categories
