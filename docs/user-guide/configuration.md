# Configuration Guide

DeepCritical uses a comprehensive configuration system based on Hydra that allows flexible composition of different configuration components. This guide explains the configuration structure and how to customize DeepCritical for your needs.

## Configuration Structure

The configuration system is organized into several key areas:

```
configs/
├── config.yaml                 # Main configuration file
├── app_modes/                  # Application execution modes
├── bioinformatics/             # Bioinformatics-specific configurations
├── challenge/                  # Challenge and experimental configurations
├── db/                         # Database connection configurations
├── deep_agent/                 # Deep agent configurations
├── deepsearch/                 # Deep search configurations
├── prompts/                    # Prompt templates for all agents
├── rag/                        # RAG system configurations
├── statemachines/              # Workflow state machine configurations
├── vllm/                       # VLLM model configurations
└── workflow_orchestration/     # Advanced workflow configurations
```

## Main Configuration (`config.yaml`)

The main configuration file defines the core parameters for DeepCritical:

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

# Output management
hydra:
  run:
    dir: outputs/${now:%Y-%m-%d}/${now:%H-%M-%S}
  sweep:
    dir: multirun/${now:%Y-%m-%d}/${now:%H-%M-%S}
```

## Application Modes (`app_modes/`)

Different execution modes for various research scenarios:

### Single REACT Mode
```yaml
# configs/app_modes/single_react.yaml
question: "What is machine learning?"
flows:
  prime:
    enabled: false
  bioinformatics:
    enabled: false
  deepsearch:
    enabled: false
```

### Multi-Level REACT Mode
```yaml
# configs/app_modes/multi_level_react.yaml
question: "Analyze machine learning in drug discovery"
flows:
  prime:
    enabled: true
    params:
      nested_loops: 3
  bioinformatics:
    enabled: true
  deepsearch:
    enabled: true
```

### Nested Orchestration Mode
```yaml
# configs/app_modes/nested_orchestration.yaml
question: "Design comprehensive research framework"
flows:
  prime:
    enabled: true
    params:
      nested_loops: 5
      subgraphs_enabled: true
  bioinformatics:
    enabled: true
  deepsearch:
    enabled: true
```

### Loss-Driven Mode
```yaml
# configs/app_modes/loss_driven.yaml
question: "Optimize research quality"
flows:
  prime:
    enabled: true
    params:
      loss_functions: ["quality", "efficiency", "comprehensiveness"]
  bioinformatics:
    enabled: true
```

## Bioinformatics Configuration (`bioinformatics/`)

### Agent Configuration
```yaml
# configs/bioinformatics/agents.yaml
agents:
  data_fusion:
    model: "anthropic:claude-sonnet-4-0"
    temperature: 0.7
    max_tokens: 2000
  go_annotation:
    model: "anthropic:claude-sonnet-4-0"
    temperature: 0.5
    max_tokens: 1500
  reasoning:
    model: "anthropic:claude-sonnet-4-0"
    temperature: 0.3
    max_tokens: 3000
```

### Data Sources Configuration
```yaml
# configs/bioinformatics/data_sources.yaml
data_sources:
  go:
    enabled: true
    api_base_url: "https://api.geneontology.org"
    evidence_codes: ["IDA", "EXP", "TAS", "IMP"]
    year_min: 2020
    quality_threshold: 0.85
    max_annotations: 1000

  pubmed:
    enabled: true
    api_base_url: "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
    max_results: 100
    include_abstracts: true
    year_min: 2020
    relevance_threshold: 0.7

  geo:
    enabled: false
    max_datasets: 10
    sample_threshold: 50

  cmap:
    enabled: false
    max_profiles: 100
    correlation_threshold: 0.8
```

### Workflow Configuration
```yaml
# configs/bioinformatics/workflow.yaml
workflow:
  steps:
    - name: "parse_query"
      agent: "query_parser"
      timeout: 30

    - name: "fuse_data"
      agent: "data_fusion"
      timeout: 120
      retry_on_failure: true

    - name: "assess_quality"
      agent: "data_quality"
      timeout: 60

    - name: "reason_integrate"
      agent: "reasoning"
      timeout: 180

  quality_thresholds:
    data_fusion: 0.8
    cross_reference: 0.75
    evidence_integration: 0.85
```

## Database Configurations (`db/`)

### Neo4j Configuration
```yaml
# configs/db/neo4j.yaml
neo4j:
  uri: "bolt://localhost:7687"
  user: "neo4j"
  password: "${oc.env:NEO4J_PASSWORD}"
  database: "neo4j"

  connection:
    max_connection_lifetime: 3600
    max_connection_pool_size: 50
    connection_acquisition_timeout: 60

  queries:
    default_timeout: 30
    max_query_complexity: 1000
```

### PostgreSQL Configuration
```yaml
# configs/db/postgres.yaml
postgres:
  host: "localhost"
  port: 5432
  database: "deepcritical"
  user: "${oc.env:POSTGRES_USER}"
  password: "${oc.env:POSTGRES_PASSWORD}"

  connection:
    pool_size: 20
    max_overflow: 30
    pool_timeout: 30

  tables:
    research_state: "research_states"
    execution_history: "execution_history"
    tool_results: "tool_results"
```

## Deep Agent Configurations (`deep_agent/`)

### Basic Configuration
```yaml
# configs/deep_agent/basic.yaml
deep_agent:
  enabled: true
  model: "anthropic:claude-sonnet-4-0"
  temperature: 0.7

  capabilities:
    - "file_system"
    - "web_search"
    - "code_execution"

  tools:
    - "read_file"
    - "search_web"
    - "run_terminal_cmd"
```

### Comprehensive Configuration
```yaml
# configs/deep_agent/comprehensive.yaml
deep_agent:
  enabled: true
  model: "anthropic:claude-sonnet-4-0"
  temperature: 0.5
  max_tokens: 4000

  capabilities:
    - "file_system"
    - "web_search"
    - "code_execution"
    - "data_analysis"
    - "document_processing"

  tools:
    - "read_file"
    - "write_file"
    - "search_web"
    - "run_terminal_cmd"
    - "analyze_data"
    - "process_document"

  context_window: 8000
  memory_enabled: true
  memory_size: 100
```

## Prompt Templates (`prompts/`)

### PRIME Parser Prompt
```yaml
# configs/prompts/prime_parser.yaml
system_prompt: |
  You are an expert research query parser for the PRIME protein engineering system.
  Your task is to analyze research questions and extract key scientific intent,
  identify relevant protein engineering domains, and structure the query for
  optimal tool selection and workflow planning.

  Focus on:
  1. Scientific domain identification (immunology, enzymology, etc.)
  2. Query intent classification (design, analysis, prediction, etc.)
  3. Key entities and relationships
  4. Required computational methods

instructions: |
  Parse the research question and return structured output with:
  - scientific_domain: Primary domain of research
  - query_intent: Main objective (design, analyze, predict, etc.)
  - key_entities: Important proteins, genes, or molecules mentioned
  - required_methods: Computational approaches needed
  - complexity_level: low, medium, high
```

## RAG Configuration (`rag/`)

### Vector Store Configuration
```yaml
# configs/rag/vector_store/chroma.yaml
vector_store:
  type: "chroma"
  collection_name: "deepcritical_docs"
  persist_directory: "./chroma_db"

  embedding:
    model: "all-MiniLM-L6-v2"
    dimension: 384
    batch_size: 32

  search:
    k: 5
    score_threshold: 0.7
    include_metadata: true
```

### LLM Configuration
```yaml
# configs/rag/llm/openai.yaml
llm:
  provider: "openai"
  model: "gpt-4"
  temperature: 0.1
  max_tokens: 1000
  api_key: "${oc.env:OPENAI_API_KEY}"

  parameters:
    top_p: 0.9
    frequency_penalty: 0.0
    presence_penalty: 0.0
```

## State Machine Configurations (`statemachines/`)

### Flow Configurations
```yaml
# configs/statemachines/flows/prime.yaml
enabled: true
params:
  adaptive_replanning: true
  manual_confirmation: false
  tool_validation: true
  scientific_intent_detection: true

  domain_heuristics:
    - immunology
    - enzymology
    - cell_biology

  tool_categories:
    - knowledge_query
    - sequence_analysis
    - structure_prediction
    - molecular_docking
    - de_novo_design
    - function_prediction
```

### Orchestrator Configuration
```yaml
# configs/statemachines/orchestrators/config.yaml
orchestrators:
  primary:
    type: "react"
    max_iterations: 10
    convergence_threshold: 0.95

  sub_orchestrators:
    - name: "search"
      type: "linear"
      max_steps: 5

    - name: "analysis"
      type: "tree"
      branching_factor: 3
```

## VLLM Configurations (`vllm/`)

### Default Configuration
```yaml
# configs/vllm/default.yaml
vllm:
  model: "microsoft/DialoGPT-medium"
  tensor_parallel_size: 1
  dtype: "auto"

  generation:
    temperature: 0.7
    top_p: 0.9
    max_tokens: 512
    repetition_penalty: 1.1

  performance:
    max_model_len: 2048
    max_num_seqs: 16
    max_paddings: 256
```

## Workflow Orchestration (`workflow_orchestration/`)

### Primary Workflow
```yaml
# configs/workflow_orchestration/primary_workflow/react_primary.yaml
workflow:
  type: "react"
  max_iterations: 10
  convergence_threshold: 0.95

  steps:
    - name: "thought"
      type: "reasoning"
      required: true

    - name: "action"
      type: "tool_execution"
      required: true

    - name: "observation"
      type: "result_processing"
      required: true
```

### Multi-Agent Systems
```yaml
# configs/workflow_orchestration/multi_agent_systems/default_multi_agent.yaml
multi_agent:
  enabled: true
  max_agents: 5
  communication_protocol: "message_passing"

  agents:
    - role: "coordinator"
      model: "anthropic:claude-sonnet-4-0"
      capabilities: ["planning", "monitoring"]

    - role: "specialist"
      model: "anthropic:claude-sonnet-4-0"
      capabilities: ["analysis", "execution"]
```

## Configuration Composition

DeepCritical supports flexible configuration composition:

```bash
# Use specific configuration components
uv run deepresearch \
  --config-name=config_with_modes \
  --config-path=configs/bioinformatics \
  --config-path=configs/rag \
  question="Bioinformatics research query"

# Override specific parameters
uv run deepresearch \
  question="Custom question" \
  flows.prime.enabled=true \
  flows.bioinformatics.data_sources.go.year_min=2023 \
  model.temperature=0.8
```

## Environment Variables

Many configurations support environment variable substitution:

```yaml
# In any config file
api_keys:
  anthropic: "${oc.env:ANTHROPIC_API_KEY}"
  openai: "${oc.env:OPENAI_API_KEY}"

database:
  password: "${oc.env:DATABASE_PASSWORD}"
  host: "${oc.env:DATABASE_HOST,localhost}"
```

## Best Practices

1. **Start Simple**: Begin with basic configurations and add complexity as needed
2. **Use Composition**: Leverage Hydra's composition features for reusable components
3. **Environment Variables**: Use environment variables for sensitive data
4. **Documentation**: Document custom configurations for team use
5. **Validation**: Test configurations before production deployment
6. **Version Control**: Keep configuration files in version control
7. **Backups**: Maintain backups of critical configurations

## Troubleshooting

### Common Configuration Issues

**Missing Required Parameters:**
```bash
# Check configuration structure
uv run deepresearch --cfg job

# Validate against schemas
uv run deepresearch --config-name=my_config --cfg job
```

**Environment Variable Issues:**
```bash
# Check environment variable resolution
export MY_VAR="test_value"
uv run deepresearch hydra.verbose=true question="test"
```

**Configuration Conflicts:**
```bash
# Check configuration precedence
uv run deepresearch --cfg path

# Use specific config files
uv run deepresearch --config-path=configs/bioinformatics question="test"
```

For more detailed information about specific configuration areas, see the [API Reference](../api/configuration.md) and individual flow documentation.
