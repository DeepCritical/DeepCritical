# Configuration Guide

DeepCritical uses Hydra for configuration management, providing flexible and composable configuration options.

## Main Configuration File

The main configuration is in `configs/config.yaml`:

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

## Flow-Specific Configuration

Each flow has its own configuration file in `configs/statemachines/flows/`:

### PRIME Flow Configuration (`prime.yaml`)

```yaml
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

### Bioinformatics Flow Configuration (`bioinformatics.yaml`)

```yaml
enabled: true
data_sources:
  go:
    enabled: true
    evidence_codes: ["IDA", "EXP", "TAS"]
    year_min: 2020
    quality_threshold: 0.85
  pubmed:
    enabled: true
    max_results: 100
    include_abstracts: true
    year_min: 2020
  geo:
    enabled: false
    max_datasets: 10
  cmap:
    enabled: false
    max_profiles: 100
fusion:
  quality_threshold: 0.8
  max_entities: 1000
  cross_reference_enabled: true
reasoning:
  model: "anthropic:claude-sonnet-4-0"
  confidence_threshold: 0.75
  integrative_approach: true
```

### DeepSearch Flow Configuration (`deepsearch.yaml`)

```yaml
enabled: true
search_engines:
  - name: "google"
    enabled: true
    max_results: 20
  - name: "duckduckgo"
    enabled: true
    max_results: 15
  - name: "bing"
    enabled: false
    max_results: 20
processing:
  extract_content: true
  remove_duplicates: true
  quality_filtering: true
  min_content_length: 500
```

## Command Line Overrides

You can override any configuration parameter from the command line:

```bash
# Override question
uv run deepresearch question="New research question"

# Override flow settings
uv run deepresearch flows.prime.enabled=false flows.bioinformatics.enabled=true

# Override nested parameters
uv run deepresearch flows.prime.params.adaptive_replanning=false

# Multiple overrides
uv run deepresearch \
  question="Advanced question" \
  flows.prime.params.manual_confirmation=true \
  flows.bioinformatics.data_sources.pubmed.max_results=200
```

## Configuration Composition

Hydra supports configuration composition using multiple config files:

```bash
# Use base config with overrides
uv run deepresearch --config-name=config_with_modes question="Your question"

# Compose multiple config groups
uv run deepresearch \
  --config-path=configs \
  --config-name=prime_config,bioinformatics_config \
  question="Multi-flow research"
```

## Environment Variables

You can use environment variables in configuration:

```yaml
# In your config file
model:
  api_key: ${oc.env:OPENAI_API_KEY}
  base_url: ${oc.env:OPENAI_BASE_URL,https://api.openai.com/v1}
```

## Logging Configuration

Configure logging in your config:

```yaml
# Logging configuration
logging:
  level: INFO
  formatters:
    simple:
      format: '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
  handlers:
    console:
      class: logging.StreamHandler
      formatter: simple
      stream: ext://sys.stdout
```

## Custom Configuration Files

Create custom configuration files in the `configs/` directory:

```yaml
# configs/my_custom_config.yaml
defaults:
  - base_config
  - _self_

# Custom parameters
question: "My specific research question"
flows:
  prime:
    enabled: true
    params:
      custom_parameter: "my_value"

# Run with custom config
uv run deepresearch --config-name=my_custom_config
```

## Tool Configuration {#tools}

### Tool Registry Configuration

Configure the tool registry and execution settings:

```yaml
# Tool registry configuration
tool_registry:
  auto_discovery: true
  cache_enabled: true
  cache_ttl: 3600
  max_concurrent_executions: 10
  retry_failed_tools: true
  retry_attempts: 3
  validation_enabled: true

  performance_monitoring:
    enabled: true
    metrics_retention_days: 30
    alert_thresholds:
      avg_execution_time: 60  # seconds
      error_rate: 0.1         # 10%
      success_rate: 0.9       # 90%
```

### Tool-Specific Configuration

Configure individual tools:

```yaml
# Tool-specific configurations
tool_configs:
  web_search:
    max_results: 20
    timeout: 30
    retry_on_failure: true

  bioinformatics_tools:
    blast:
      e_value_threshold: 1e-5
      max_target_seqs: 100

    structure_prediction:
      alphafold:
        max_model_len: 2000
        use_gpu: true
```

## Configuration Best Practices

1. **Start Simple**: Begin with basic configurations and add complexity as needed
2. **Use Composition**: Leverage Hydra's composition features for reusable config components
3. **Override Carefully**: Use command-line overrides for experimentation
4. **Document Changes**: Keep notes about why specific configurations were chosen
5. **Test Configurations**: Validate configurations in development before production use

## Debugging Configuration

Debug configuration issues:

```bash
# Show resolved configuration
uv run deepresearch --cfg job

# Show configuration tree
uv run deepresearch --cfg path

# Show hydra configuration
uv run deepresearch --cfg hydra

# Verbose output
uv run deepresearch hydra.verbose=true question="Test"
```

## Configuration Files Reference

- `configs/config.yaml` - Main configuration
- `configs/statemachines/flows/` - Individual flow configurations
- `configs/prompts/` - Prompt templates for agents
- `configs/app_modes/` - Application mode configurations
- `configs/llm/` - LLM model configurations (see [LLM Models Guide](../user-guide/llm-models.md))
- `configs/db/` - Database connection configurations

For more advanced configuration options, see the [Hydra Documentation](https://hydra.cc/docs/intro/).
