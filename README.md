# 🚀 DeepCritical: Building a Highly Configurable Deep Research Agent Ecosystem

[![Documentation](https://img.shields.io/badge/docs-latest-blue.svg)](https://deepcritical.github.io/DeepCritical)
[![codecov](https://codecov.io/gh/DeepCritical/DeepCritical/branch/dev/graph/badge.svg)](https://codecov.io/gh/DeepCritical/DeepCritical)

## Vision: From Single Questions to Research Field Generation

**DeepCritical** isn't just another research assistant—it's a framework for building entire research ecosystems. While a typical user asks one question, DeepCritical generates datasets of hypotheses, tests them systematically, runs simulations, and produces comprehensive reports—all through configurable Hydra-based workflows.

### The Big Picture

```yaml
# Hydra makes this possible - single config generates entire research workflows
flows:
  hypothesis_generation: {enabled: true, batch_size: 100}
  hypothesis_testing: {enabled: true, validation_environments: ["simulation", "real_world"]}
  validation: {enabled: true, methods: ["statistical", "experimental"]}
  simulation: {enabled: true, frameworks: ["python", "docker"]}
  reporting: {enabled: true, formats: ["academic_paper", "dpo_dataset"]}
```

## 🏗️ Current Architecture Overview

### Hydra + Pydantic AI Integration
- **Hydra Configuration**: `configs/` directory with flow-based composition
- **Pydantic Graph**: Stateful workflow execution with `ResearchState`
- **Pydantic AI Agents**: Multi-agent orchestration with `@defer` tools
- **Flow Routing**: Dynamic composition based on `flows.*.enabled` flags

### Existing Flow Infrastructure
The project already has the foundation for your vision:

```yaml
# Current flow configurations (configs/statemachines/flows/)
- hypothesis_generation.yaml    # Generate hypothesis datasets
- hypothesis_testing.yaml       # Test hypothesis environments
- execution.yaml               # Run experiments/simulations
- reporting.yaml              # Generate research outputs
- bioinformatics.yaml         # Multi-source data fusion
- rag.yaml                   # Retrieval-augmented workflows
- deepsearch.yaml            # Web research automation
```

### Agent Orchestration System
```python
@dataclass
class AgentOrchestrator:
    """Spawns nested REACT loops, manages subgraphs, coordinates multi-agent workflows"""
    config: AgentOrchestratorConfig
    nested_loops: Dict[str, NestedReactConfig]
    subgraphs: Dict[str, SubgraphConfig]
    break_conditions: List[BreakCondition]  # Loss functions for smart termination
```

## 🎯 Core Capabilities Already Built

### 1. **Hypothesis Dataset Generation**
```python
class HypothesisDataset(BaseModel):
    dataset_id: str
    hypotheses: List[Dict[str, Any]]  # Generated hypothesis batches
    source_workflows: List[str]
    metadata: Dict[str, Any]
```

### 2. **Testing Environment Management**
```python
class HypothesisTestingEnvironment(BaseModel):
    environment_id: str
    hypothesis: Dict[str, Any]
    test_configuration: Dict[str, Any]
    expected_outcomes: List[str]
    success_criteria: Dict[str, Any]
```

### 3. **Workflow-of-Workflows Architecture**
- **Primary REACT**: Main orchestration workflow
- **Sub-workflows**: Specialized execution paths (RAG, bioinformatics, search)
- **Nested Loops**: Multi-level reasoning with configurable break conditions
- **Subgraphs**: Modular workflow components

### 4. **Tool Ecosystem**
- **Bioinformatics**: Neo4j RAG, GO annotations, PubMed integration
- **Search**: Web search, deep search, integrated retrieval
- **Code Execution**: Docker sandbox, Python execution environments
- **RAG**: Vector stores, document processing, embeddings
- **Analytics**: Quality assessment, loss function evaluation

## 🚧 Development Roadmap

### Immediate Next Steps (1-2 weeks)

#### 1. **Coding Agent Loop**
```yaml
# New flow configuration needed
flows:
  coding_agent:
    enabled: true
    languages: ["python", "r", "julia"]
    frameworks: ["pytorch", "tensorflow", "scikit-learn"]
    execution_environments: ["docker", "local", "cloud"]
```

#### 2. **Writing/Report Agent System**
```yaml
# Extend reporting.yaml
reporting:
  formats: ["academic_paper", "blog_post", "technical_report", "dpo_dataset"]
  agents:
    - role: "structure_organizer"
    - role: "content_writer"
    - role: "editor_reviewer"
    - role: "formatter_publisher"
```

#### 3. **Database & Data Source Integration**
- **Persistent State**: Non-agentics datasets for workflow state
- **Trace Logging**: Execution traces → formatted datasets
- **Ana's Neo4j RAG**: Agent-based knowledge base management

#### 4. **"Final" Agent System**
```python
class MetaAgent(BaseModel):
    """Agent that uses DeepCritical to build and answer with custom agents"""
    def create_custom_agent(self, specification: AgentSpecification) -> Agent:
        # Generate agent configuration
        # Build agent with tools, prompts, capabilities
        # Deploy and execute
        pass
```

### Configuration-Driven Development

The beauty of Hydra integration means we can build this incrementally:

```bash
# Start with hypothesis generation
deepresearch flows.hypothesis_generation.enabled=true question="machine learning"

# Add hypothesis testing
deepresearch flows.hypothesis_testing.enabled=true question="test ML hypothesis"

# Enable full research pipeline
deepresearch flows="{hypothesis_generation,testing,validation,simulation,reporting}"
```

## 🔧 Technical Implementation Strategy

### 1. **Hydra Flow Composition**
```yaml
# configs/config.yaml - Main composition point
defaults:
  - hypothesis_generation: default
  - hypothesis_testing: default
  - execution: default
  - reporting: default

flows:
  hypothesis_generation: {enabled: true, batch_size: 50}
  hypothesis_testing: {enabled: true, validation_frameworks: ["simulation"]}
  execution: {enabled: true, compute_backends: ["docker", "local"]}
  reporting: {enabled: true, output_formats: ["markdown", "json"]}
```

### 2. **Pydantic Graph Integration**
```python
@dataclass
class ResearchPipeline(BaseNode[ResearchState]):
    async def run(self, ctx: GraphRunContext[ResearchState]) -> NextNode:
        # Check enabled flows and compose dynamically
        if ctx.state.config.flows.hypothesis_generation.enabled:
            return HypothesisGenerationNode()
        elif ctx.state.config.flows.hypothesis_testing.enabled:
            return HypothesisTestingNode()
        # ... etc
```

### 3. **Agent-Tool Integration**
```python
@defer
def generate_hypothesis_dataset(
    ctx: RunContext[AgentDependencies],
    research_question: str,
    batch_size: int
) -> HypothesisDataset:
    """Generate a dataset of testable hypotheses"""
    # Implementation using existing tools and agents
    return dataset
```

## 🎨 Use Cases Enabled

### 1. **Literature Review Automation**
```bash
deepresearch question="CRISPR applications in cancer therapy" \
  flows.hypothesis_generation.enabled=true \
  flows.reporting.format="literature_review"
```

### 2. **Experiment Design & Simulation**
```bash
deepresearch question="protein folding prediction improvements" \
  flows.hypothesis_generation.enabled=true \
  flows.hypothesis_testing.enabled=true \
  flows.simulation.enabled=true
```

### 3. **Research Field Development**
```bash
# Generate entire research program from minimal input
deepresearch question="novel therapeutic approaches for Alzheimer's" \
  flows="{hypothesis_generation,testing,validation,reporting}" \
  outputs.enable_dpo_datasets=true
```

## 🤝 Collaboration Opportunities

This project provides a foundation for:

1. **Domain-Specific Research Agents**: Biology, chemistry, physics, social sciences
2. **Publication Pipeline Automation**: From hypothesis → experiment → paper
3. **Collaborative Research Platforms**: Multi-researcher workflow coordination
4. **AI Research on AI**: Using the system to improve itself

## 🚀 Getting Started

The framework is ready for extension:

```bash
# Current capabilities
uv run deepresearch --help

# Enable specific flows
uv run deepresearch question="your question" flows.hypothesis_generation.enabled=true

# Configure for batch processing
uv run deepresearch --config-name=config_with_modes \
  question="batch research questions" \
  app_mode=multi_level_react
```

## 💡 Questions for Discussion

1. **How should we structure the "final" meta-agent system?** (Self-improving, agent factories, etc.)
2. **What database backends for persistent state?** (SQLite, PostgreSQL, vector stores?)
3. **How to handle multi-researcher collaboration?** (Access control, workflow sharing, etc.)
4. **What loss functions and judges for research quality?** (Novelty, rigor, impact, etc.)

This is a sketchpad for building the future of autonomous research—let's collaborate on making it a reality! 🔬✨

# DeepCritical - Hydra + Pydantic Graph Deep Research with Critical Review Tools

A comprehensive research automation platform architecture for autonomous scientific discovery workflows.

## 🚀 Quickstart

### Using uv (Recommended)

```bash
# Install uv and dependencies
uv sync

# Single REACT mode
uv run deepresearch question="What is machine learning?" app_mode=single_react

# Multi-level REACT with nested loops
uv run deepresearch question="Analyze machine learning in drug discovery" app_mode=multi_level_react

# Complex nested orchestration
uv run deepresearch question="Design a comprehensive research framework" app_mode=nested_orchestration

# Loss-driven execution
uv run deepresearch question="Optimize research quality" app_mode=loss_driven

# Using configuration files
uv run deepresearch --config-name=config_with_modes question="Your question" app_mode=multi_level_react
```

### Using pip (Legacy)

```bash
# Single REACT mode
deepresearch question="What is machine learning?" app_mode=single_react

# Multi-level REACT with nested loops
deepresearch question="Analyze machine learning in drug discovery" app_mode=multi_level_react

# Complex nested orchestration
deepresearch question="Design a comprehensive research framework" app_mode=nested_orchestration

# Loss-driven execution
deepresearch question="Optimize research quality" app_mode=loss_driven

# Using configuration files
deepresearch --config-name=config_with_modes question="Your question" app_mode=multi_level_react
```

### 1) Installation

#### Using uv (Recommended)

```bash
# Install uv if not already installed
# Windows:
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"

# macOS/Linux:
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install dependencies and create virtual environment
uv sync

# Run the application
uv run deepresearch --help
```

#### Using pip (Alternative)

```bash
# Create virtual environment
python -m venv .venv && .venv\Scripts\activate

# Install package
pip install -e .
```

### 2) Basic Usage

#### Using uv (Recommended)

```bash
# Run default workflow
uv run deepresearch

# Run with custom question
uv run deepresearch question="What are PRIME's core contributions?"

# Run with specific configuration
uv run deepresearch --config-name=config_with_modes question="Your question" app_mode=multi_level_react
```

#### Using pip (Alternative)

```bash
# Run default workflow
python -m deepresearch.app

# Run with custom question
python -m deepresearch.app question="What are PRIME's core contributions?"
```

### 3) PRIME Flow (Protein Engineering)

#### Using uv (Recommended)

```bash
# Design therapeutic antibody
uv run deepresearch flows.prime.enabled=true question="Design a therapeutic antibody for SARS-CoV-2"

# Analyze protein sequence
uv run deepresearch flows.prime.enabled=true question="Analyze protein sequence MKTVRQERLKSIVRILERSKEPVSGAQLAEELSVSRQVIVQDIAYLRSLGYNIVATPRGYVLAGG"

# Predict protein structure
uv run deepresearch flows.prime.enabled=true question="Predict 3D structure of protein P12345"
```

#### Using pip (Alternative)

```bash
# Design therapeutic antibody
python -m deepresearch.app flows.prime.enabled=true question="Design a therapeutic antibody for SARS-CoV-2"

# Analyze protein sequence
python -m deepresearch.app flows.prime.enabled=true question="Analyze protein sequence MKTVRQERLKSIVRILERSKEPVSGAQLAEELSVSRQVIVQDIAYLRSLGYNIVATPRGYVLAGG"

# Predict protein structure
python -m deepresearch.app flows.prime.enabled=true question="Predict 3D structure of protein P12345"
```

### 4) Bioinformatics Flow (Data Fusion & Reasoning)

```bash
# GO + PubMed reasoning for gene function
python -m deepresearch.app flows.bioinformatics.enabled=true question="What is the function of TP53 gene based on GO annotations and recent literature?"

# Multi-source drug-target analysis
python -m deepresearch.app flows.bioinformatics.enabled=true question="Analyze the relationship between drug X and protein Y using expression profiles and interactions"

# Protein structure-function analysis
python -m deepresearch.app flows.bioinformatics.enabled=true question="What is the likely function of protein P12345 based on its structure and GO annotations?"
```

### 5) Flow Selection

```bash
# PRIME flow (protein engineering)
python -m deepresearch.app flows.prime.enabled=true

# Bioinformatics flow (data fusion & reasoning)
python -m deepresearch.app flows.bioinformatics.enabled=true

# DeepSearch flow (web research)
python -m deepresearch.app flows.deepsearch.enabled=true

# Challenge flow (experimental)
python -m deepresearch.app challenge.enabled=true
```

### 6) Advanced Configuration

```bash
# Custom plan steps
python -m deepresearch.app plan='["clarify scope","collect sources","synthesize"]'

# Manual confirmation mode
python -m deepresearch.app flows.prime.params.manual_confirmation=true

# Disable adaptive re-planning
python -m deepresearch.app flows.prime.params.adaptive_replanning=false
```

## 🏗️ Architecture

### Core Components

- **Hydra Configuration**: Uses Hydra composition for configuration (`configs/`) per [Hydra docs](https://hydra.cc/docs/intro/)
- **Pydantic Graph**: Stateful workflow execution (`deepresearch/app.py`) per [Pydantic Graph docs](https://ai.pydantic.dev/graph/#stateful-graphs)
- **PRIME Integration**: Replicates the PRIME paper's three-stage architecture

### PRIME Three-Stage Architecture

```
┌─────────┐    ┌─────────┐    ┌─────────┐
│  Parse  │───▶│  Plan   │───▶│ Execute │
│         │    │         │    │         │
│ Query   │    │ DAG     │    │ Tool    │
│ Parser  │    │ Gen.    │    │ Exec.   │
└─────────┘    └─────────┘    └─────────┘
```

1. **Parse** → `QueryParser` - Semantic/syntactic analysis of research queries
2. **Plan** → `PlanGenerator` - DAG workflow construction with 65+ tools
3. **Execute** → `ToolExecutor` - Adaptive re-planning with strategic/tactical recovery

## 🧬 PRIME Features

### Protein Engineering Tool Ecosystem
- **65+ Tools** across 6 categories: Knowledge Query, Sequence Analysis, Structure Prediction, Molecular Docking, De Novo Design, Function Prediction
- **Scientific Intent Detection**: Automatically categorizes queries (protein_design, binding_analysis, structure_prediction, etc.)
- **Domain-Specific Heuristics**: Immunology, enzymology, cell biology, general protein domains

### Adaptive Re-planning System
- **Strategic Re-planning**: Tool substitution (BLAST → ProTrek, AlphaFold2 → ESMFold)
- **Tactical Re-planning**: Parameter adjustment (E-value relaxation, exhaustiveness tuning)
- **Execution History**: Comprehensive tracking with failure pattern analysis
- **Success Criteria Validation**: Quantitative metrics (pLDDT, E-values) and binary outcomes

### Scientific Grounding
- **Verifiable Results**: All conclusions come from validated tools, never from LLM generation
- **Tool Validation**: Strict input/output schema compliance and type checking
- **Mock Implementations**: Complete development environment with realistic outputs
- **Error Recovery**: Graceful handling with actionable recommendations

## 🧬 Bioinformatics Integration

### Multi-Source Data Fusion
- **GO + PubMed**: Gene Ontology annotations with paper context for reasoning tasks
- **GEO + CMAP**: Gene expression data with perturbation profiles
- **DrugBank + TTD + CMAP**: Drug-target-perturbation relationship graphs
- **PDB + IntAct**: Protein structure-interaction datasets

### Agent-to-Agent Communication
- **Specialized Agents**: DataFusionAgent, GOAnnotationAgent, ReasoningAgent, DataQualityAgent
- **Pydantic AI Integration**: Multi-model reasoning with evidence integration
- **Deferred Tools**: Efficient data processing with registry integration
- **Quality Assessment**: Cross-database consistency and evidence validation

### Integrative Reasoning
- **Non-Reductionist Approach**: Multi-source evidence integration beyond structural similarity
- **Evidence Code Prioritization**: IDA (gold standard) > EXP > computational predictions

### MCP Server Ecosystem
- **18 Vendored Bioinformatics Tools**: FastQC, Samtools, Bowtie2, MACS3, HOMER, HISAT2, BEDTools, STAR, BWA, MultiQC, Salmon, StringTie, FeatureCounts, TrimGalore, Kallisto, HTSeq, TopHat, Picard
- **Pydantic AI Integration**: Strongly-typed tool decorators with automatic agent registration
- **Testcontainers Deployment**: Isolated execution environments for reproducible research
- **Bioinformatics Pipeline Support**: Complete RNA-seq, ChIP-seq, and genomics analysis workflows
- **Cross-Database Validation**: Consistency checks and temporal relevance
- **Human Curation Integration**: Leverages existing curation expertise

q### Example Data Fusion
```json
{
  "pmid": "12345678",
  "title": "p53 mediates the DNA damage response in mammalian cells",
  "abstract": "DNA damage induces p53 stabilization, leading to cell cycle arrest and apoptosis.",
  "gene_id": "P04637",
  "gene_symbol": "TP53",
  "go_term_id": "GO:0006977",
  "go_term_name": "DNA damage response",
  "evidence_code": "IDA",
  "annotation_note": "Curated based on experimental results in Figure 3."
}
```

## 🔄 Flow Architecture

### Available Flows
- **PRIME Flow**: Protein engineering with 65+ specialized tools
- **Bioinformatics Flow**: Multi-source data fusion and integrative reasoning
- **DeepSearch Flow**: Web research and information gathering
- **Challenge Flow**: Experimental workflows for research challenges
- **Default Flow**: General-purpose research automation

### Flow Orchestration
```
Plan → Route to Flow → Execute Subflow → Synthesize Results
  │
  ├─ PRIME: Parse → Plan → Execute → Evaluate
  ├─ Bioinformatics: Parse → Fuse → Assess → Reason → Synthesize
  ├─ DeepSearch: DSPlan → DSExecute → DSAnalyze → DSSynthesize
  └─ Challenge: PrepareChallenge → RunChallenge → EvaluateChallenge
```

## ⚙️ Configuration

### Main Configuration

Key parameters in `configs/config.yaml`:

```yaml
# Research parameters
question: "Your research question here"
plan: ["step1", "step2", "step3"]
retries: 3
manual_confirm: false

# Flow control
flows:
  prime:
    enabled: true
    params:
      adaptive_replanning: true
      manual_confirmation: false
      tool_validation: true
  bioinformatics:
    enabled: true
    data_sources:
      go:
        enabled: true
        evidence_codes: ["IDA", "EXP"]
        year_min: 2022
        quality_threshold: 0.9
      pubmed:
        enabled: true
        max_results: 50
        include_full_text: true
    fusion:
      quality_threshold: 0.85
      max_entities: 500
      cross_reference_enabled: true
    reasoning:
      model: "anthropic:claude-sonnet-4-0"
      confidence_threshold: 0.8
      integrative_approach: true

# Output management
hydra:
  run:
    dir: outputs/${now:%Y-%m-%d}/${now:%H-%M-%S}
  sweep:
    dir: multirun/${now:%Y-%m-%d}/${now:%H-%M-%S}
```

### Flow-Specific Configuration

Each flow has its own configuration file:

- `configs/statemachines/flows/prime.yaml` - PRIME flow parameters
- `configs/statemachines/flows/bioinformatics.yaml` - Bioinformatics flow parameters
- `configs/statemachines/flows/deepsearch.yaml` - DeepSearch parameters
- `configs/statemachines/flows/hypothesis_generation.yaml` - Hypothesis flow
- `configs/statemachines/flows/execution.yaml` - Execution flow
- `configs/statemachines/flows/reporting.yaml` - Reporting flow

### LLM Model Configuration

DeepCritical supports multiple LLM providers through OpenAI-compatible APIs:

```yaml
# configs/llm/vllm_pydantic.yaml
provider: "vllm"
model_name: "meta-llama/Llama-3-8B"
base_url: "http://localhost:8000/v1"
api_key: null

generation:
  temperature: 0.7
  max_tokens: 512
  top_p: 0.9
```

**Supported providers:**
- **vLLM**: High-performance local inference
- **llama.cpp**: Efficient GGUF model serving
- **TGI**: Hugging Face Text Generation Inference
- **Custom**: Any OpenAI-compatible server

See [LLM Models Documentation](docs/user-guide/llm-models.md) for detailed configuration and usage examples.

### Prompt Configuration

Prompt templates in `configs/prompts/`:

- `configs/prompts/prime_parser.yaml` - Query parsing prompts
- `configs/prompts/prime_planner.yaml` - Workflow planning prompts
- `configs/prompts/prime_executor.yaml` - Tool execution prompts
- `configs/prompts/prime_evaluator.yaml` - Result evaluation prompts

## 🔧 Development

### Development

### Codecov Setup

To enable coverage reporting with Codecov:

1. **Set up the repository in Codecov:**
   - Visit [https://app.codecov.io/gh/DeepCritical/DeepCritical](https://app.codecov.io/gh/DeepCritical/DeepCritical)
   - Click "Add new repository" or "Setup repo" if prompted
   - Follow the setup wizard to connect your GitHub repository

2. **Generate a Codecov token:**
   - In Codecov, go to your repository settings
   - Navigate to "Repository Settings" > "Tokens"
   - Generate a new token with "upload" permissions

3. **Add the token as a GitHub secret:**
   - In your GitHub repository, go to Settings > Secrets and variables > Actions
   - Click "New repository secret"
   - Name: `CODECOV_TOKEN`
   - Value: Your Codecov token from step 2

4. **Verify setup:**
   - Push a commit to trigger the CI pipeline
   - Check that coverage reports appear in Codecov

The CI workflow will automatically upload coverage reports once the repository is configured in Codecov and the token is added as a secret.

### Development with uv

```bash
# Install development dependencies
uv sync --dev

# Run tests
uv run pytest

# Run linting
uv run ruff check .

# Add new dependencies
uv add package_name

# Add development dependencies
uv add --dev package_name

# Update dependencies
uv lock --upgrade

# Run scripts in the project environment
uv run python script.py
```

### Project Structure

```
DeepCritical/
├── deepresearch/           # Main package
│   ├── app.py             # Pydantic Graph workflow
│   ├── src/               # PRIME implementation
│   │   ├── agents/        # PRIME agents (Parser, Planner, Executor)
│   │   ├── datatypes/     # Bioinformatics data types
│   │   ├── statemachines/ # Bioinformatics workflows
│   │   └── utils/         # Utilities (Tool Registry, Execution History)
│   └── tools/             # Tool implementations
├── configs/               # Hydra configuration
│   ├── config.yaml        # Main configuration
│   ├── prompts/           # Prompt templates
│   └── statemachines/     # Flow configurations
├── docs/                  # Documentation
│   └── bioinformatics_integration.md
└── .cursor/rules/         # Cursor rules for development
```

### Extending Flows

1. **Create Flow Configuration**:
   ```yaml
   # configs/statemachines/flows/my_flow.yaml
   enabled: true
   params:
     custom_param: "value"
   ```

2. **Implement Nodes**:
   ```python
   @dataclass
   class MyFlowNode(BaseNode[ResearchState]):
       async def run(self, ctx: GraphRunContext[ResearchState]) -> NextNode:
           # Implementation
           return NextNode()
   ```

3. **Register in Graph**:
   ```python
   # In run_graph function
   nodes = (..., MyFlowNode())
   ```

4. **Add Flow Routing**:
   ```python
   # In Plan node
   if getattr(cfg.flows, "my_flow", {}).get("enabled"):
       return MyFlowNode()
   ```

### Tool Development

1. **Define Tool Specification**:
   ```python
   tool_spec = ToolSpec(
       name="my_tool",
       category=ToolCategory.SEQUENCE_ANALYSIS,
       input_schema={"sequence": "string"},
       output_schema={"result": "dict"},
       success_criteria={"min_confidence": 0.8}
   )
   ```

2. **Implement Tool Runner**:
   ```python
   class MyToolRunner(ToolRunner):
       def run(self, parameters: Dict[str, Any]) -> ExecutionResult:
           # Tool implementation
           return ExecutionResult(success=True, data=result)
   ```

3. **Register Tool**:
   ```python
   registry.register_tool(tool_spec, MyToolRunner)
   ```

### Bioinformatics Development

1. **Create Data Types**:
   ```python
   from pydantic import BaseModel, Field

   class GOAnnotation(BaseModel):
       pmid: str = Field(..., description="PubMed ID")
       gene_id: str = Field(..., description="Gene identifier")
       go_term: GOTerm = Field(..., description="GO term")
       evidence_code: EvidenceCode = Field(..., description="Evidence code")
   ```

2. **Implement Agents**:
   ```python
   from pydantic_ai import Agent

   class DataFusionAgent:
       def __init__(self, model_name: str):
           self.agent = Agent(
               model=AnthropicModel(model_name),
               deps_type=BioinformaticsAgentDeps,
               result_type=DataFusionResult
           )
   ```

3. **Create Workflow Nodes**:
   ```python
   @dataclass
   class FuseDataSources(BaseNode[BioinformaticsState]):
       async def run(self, ctx: GraphRunContext[BioinformaticsState]) -> NextNode:
           # Data fusion logic
           return AssessDataQuality()
   ```

## 🚀 Advanced Usage

### Batch Processing

```bash
# Run multiple experiments
python -m deepresearch.app --multirun \
  question="Design antibody for SARS-CoV-2",question="Analyze protein P12345" \
  flows.prime.enabled=true
```

### Custom Tool Integration

```python
from deepresearch.src.utils.tool_registry import ToolRegistry, ToolSpec, ToolCategory

# Create custom tool
registry = ToolRegistry()
tool_spec = ToolSpec(
    name="custom_analyzer",
    category=ToolCategory.SEQUENCE_ANALYSIS,
    input_schema={"sequence": "string"},
    output_schema={"analysis": "dict"}
)
registry.register_tool(tool_spec)
```

### Execution History Analysis

```python
from deepresearch.src.utils.execution_history import ExecutionHistory

# Load execution history
history = ExecutionHistory.load_from_file("outputs/2024-01-01/12-00-00/execution_history.json")

# Analyze performance
summary = history.get_execution_summary()
print(f"Success rate: {summary['success_rate']:.2%}")
print(f"Tools used: {summary['tools_used']}")
```

## 📚 References

- [Hydra Documentation](https://hydra.cc/docs/intro/) - Configuration management
- [Pydantic Graph](https://ai.pydantic.dev/graph/#stateful-graphs) - Stateful workflow execution
- [Pydantic AI](https://ai.pydantic.dev/) - Agent-to-agent communication
- [PRIME Paper](https://doi.org/10.1101/2025.09.22.677756) - Original research paper
- [Bioinformatics Integration](docs/bioinformatics_integration.md) - Multi-source data fusion guide
- [Protein Engineering Tools](https://github.com/facebookresearch/hydra) - Tool ecosystem reference

## License

DeepCritical uses dual licensing to maximize open, non-commercial use while reserving rights for commercial applications:

- **Source Code**: Licensed under [GNU General Public License v3 (GPLv3)](LICENSE.md), allowing broad non-commercial use including copying, modification, distribution, and collaboration for personal, educational, research, or non-profit purposes.

- **AI Models and Application**: Licensed under [DeepCritical RAIL-AMS License](RAIL.md), permitting non-commercial use subject to use restrictions (no discrimination, military applications, disinformation, or privacy violations), but prohibiting distribution and derivative creation for sharing.

For commercial use or permissions beyond these licenses, contact us to discuss alternative commercial licensing options.
