# Configuration API

This page provides detailed API documentation for DeepCritical's configuration management system.

## Hydra Configuration System

DeepCritical uses Hydra for flexible, composable configuration management that supports hierarchical overrides, environment variables, and dynamic composition.

## Core Configuration Classes

### ConfigStore
Central configuration registry and management.

```python
from hydra.core.config_store import ConfigStore
from deepresearch.config import register_configs

# Register all configurations
cs = ConfigStore.instance()
register_configs(cs)
```

### Configuration Validation

### ConfigValidator
Configuration validation and schema enforcement.

```python
from deepresearch.config.validation import ConfigValidator

validator = ConfigValidator()
result = validator.validate_config(config)

if not result.valid:
    for error in result.errors:
        print(f"Configuration error: {error}")
```

## Configuration Structure

### Main Configuration Schema

```python
@dataclass
class MainConfig:
    """Main configuration schema for DeepCritical."""

    # Research parameters
    question: str = ""
    plan: List[str] = field(default_factory=list)
    retries: int = 3
    manual_confirm: bool = False

    # Flow configuration
    flows: FlowConfig = field(default_factory=FlowConfig)

    # Agent configuration
    agents: AgentConfig = field(default_factory=AgentConfig)

    # Tool configuration
    tools: ToolConfig = field(default_factory=ToolConfig)

    # Output configuration
    output: OutputConfig = field(default_factory=OutputConfig)

    # Logging configuration
    logging: LoggingConfig = field(default_factory=LoggingConfig)
```

### Flow Configuration

```python
@dataclass
class FlowConfig:
    """Configuration for research flows."""

    # Enable/disable flows
    prime: FlowSettings = field(default_factory=lambda: FlowSettings(enabled=True))
    bioinformatics: FlowSettings = field(default_factory=lambda: FlowSettings(enabled=True))
    deepsearch: FlowSettings = field(default_factory=lambda: FlowSettings(enabled=True))
    challenge: FlowSettings = field(default_factory=lambda: FlowSettings(enabled=False))

    # Flow-specific parameters
    prime_params: PrimeFlowParams = field(default_factory=PrimeFlowParams)
    bioinformatics_params: BioinformaticsFlowParams = field(default_factory=BioinformaticsFlowParams)
    deepsearch_params: DeepSearchFlowParams = field(default_factory=DeepSearchFlowParams)
```

### Agent Configuration

```python
@dataclass
class AgentConfig:
    """Configuration for agent system."""

    # Default agent settings
    model_name: str = "anthropic:claude-sonnet-4-0"
    temperature: float = 0.7
    max_tokens: int = 2000
    timeout: float = 60.0

    # Agent-specific configurations
    parser: ParserAgentConfig = field(default_factory=ParserAgentConfig)
    planner: PlannerAgentConfig = field(default_factory=PlannerAgentConfig)
    executor: ExecutorAgentConfig = field(default_factory=ExecutorAgentConfig)
    evaluator: EvaluatorAgentConfig = field(default_factory=EvaluatorAgentConfig)

    # Multi-agent settings
    max_agents: int = 5
    communication_protocol: str = "message_passing"
    coordination_strategy: str = "hierarchical"
```

### Tool Configuration

```python
@dataclass
class ToolConfig:
    """Configuration for tool system."""

    # Registry settings
    auto_discover: bool = True
    registry_path: str = "deepresearch.tools"

    # Tool categories
    categories: Dict[str, ToolCategoryConfig] = field(default_factory=dict)

    # Execution settings
    max_concurrent_tools: int = 5
    tool_timeout: float = 30.0
    retry_failed_tools: bool = True

    # Resource limits
    memory_limit_mb: int = 1024
    cpu_limit: float = 1.0
```

## Configuration Composition

### Config Groups

DeepCritical organizes configuration into logical groups that can be composed together:

```yaml
# configs/config.yaml
defaults:
  - base_config
  - agent_configs
  - tool_configs
  - flow_configs
  - _self_

# Main configuration
question: "Research question"
flows:
  prime:
    enabled: true
  bioinformatics:
    enabled: true
```

### Dynamic Composition

```python
from hydra import compose, initialize_config_store
from hydra.core.global_hydra import GlobalHydra

# Initialize Hydra with config store
GlobalHydra.instance().initialize(config_path="configs")

# Compose configuration with overrides
cfg = compose(config_name="config", overrides=[
    "question=Analyze protein structures",
    "flows.prime.enabled=true",
    "agent.model_name=gpt-4"
])

# Use composed configuration
print(f"Question: {cfg.question}")
print(f"Model: {cfg.agent.model_name}")
```

## Environment Variable Integration

### Environment Variable Substitution

```python
@dataclass
class DatabaseConfig:
    """Database configuration with environment variable support."""

    host: str = "${oc.env:DATABASE_HOST,localhost}"
    port: int = "${oc.env:DATABASE_PORT,5432}"
    user: str = "${oc.env:DATABASE_USER,postgres}"
    password: str = "${oc.env:DATABASE_PASSWORD,secret}"
    database: str = "${oc.env:DATABASE_NAME,deepcritical}"
```

### Secure Configuration

```python
from deepresearch.config.security import SecretManager

# Initialize secret manager
secrets = SecretManager()

# Load secrets from environment or external store
api_key = secrets.get_secret("ANTHROPIC_API_KEY")
database_password = secrets.get_secret("DATABASE_PASSWORD")
```

## Configuration Validation

### Schema Validation

```python
from deepresearch.config.validation import ConfigValidator
from pydantic import ValidationError

validator = ConfigValidator()

try:
    # Validate configuration
    result = validator.validate_config(cfg)

    if result.valid:
        print("Configuration is valid")
    else:
        for error in result.errors:
            print(f"Validation error: {error}")

except ValidationError as e:
    print(f"Schema validation failed: {e}")
```

### Runtime Validation

```python
from deepresearch.config.validation import RuntimeConfigValidator

runtime_validator = RuntimeConfigValidator()

# Validate configuration for specific runtime context
result = runtime_validator.validate_for_runtime(cfg, runtime_context="production")

if not result.compatible:
    for issue in result.compatibility_issues:
        print(f"Runtime compatibility issue: {issue}")
```

## Configuration Overrides

### Command Line Overrides

```bash
# Override configuration from command line
deepresearch \
  question="Custom research question" \
  flows.prime.enabled=true \
  agent.model_name="gpt-4" \
  tool.max_concurrent_tools=10
```

### Programmatic Overrides

```python
from deepresearch.config import override_config

# Override configuration programmatically
with override_config() as cfg:
    cfg.question = "New research question"
    cfg.flows.prime.enabled = True
    cfg.agent.model_name = "gpt-4"

    # Use modified configuration
    result = run_research(cfg)
```

### Configuration Profiles

```python
from deepresearch.config.profiles import ConfigProfile

# Load configuration profile
profile = ConfigProfile.load("production")

# Apply profile to configuration
cfg = profile.apply_to_config(base_config)

# Use profile-specific configuration
result = run_research(cfg)
```

## Configuration Management

### Configuration Persistence

```python
from deepresearch.config.persistence import ConfigPersistence

persistence = ConfigPersistence()

# Save configuration
persistence.save_config(cfg, "my_config.yaml")

# Load configuration
loaded_cfg = persistence.load_config("my_config.yaml")

# List saved configurations
configs = persistence.list_configs()
```

### Configuration History

```python
from deepresearch.config.history import ConfigHistory

history = ConfigHistory()

# Record configuration change
history.record_change(cfg, "Updated model settings")

# Get configuration history
changes = history.get_changes(limit=10)

# Revert to previous configuration
previous_cfg = history.revert_to_version("v1.2.3")
```

## Advanced Configuration Features

### Conditional Configuration

```yaml
# Conditional configuration based on environment
defaults:
  - _self_

question: "Research question"

# Conditional flow enabling
flows:
  prime:
    enabled: ${oc.env:ENABLE_PRIME,true}
  bioinformatics:
    enabled: ${oc.env:ENABLE_BIOINFORMATICS,false}

# Conditional agent settings
agent:
  model_name: ${oc.env:MODEL_NAME,anthropic:claude-sonnet-4-0}
  temperature: ${oc.env:TEMPERATURE,0.7}
```

### Configuration Templates

```python
from deepresearch.config.templates import ConfigTemplate

# Load configuration template
template = ConfigTemplate.load("bioinformatics_research")

# Fill template with parameters
config = template.fill({
    "organism": "Homo sapiens",
    "gene_id": "TP53",
    "analysis_type": "expression"
})

# Use templated configuration
result = run_bioinformatics_analysis(config)
```

### Configuration Plugins

```python
from deepresearch.config.plugins import ConfigPluginManager

# Load configuration plugins
plugin_manager = ConfigPluginManager()
plugin_manager.load_plugins()

# Apply plugins to configuration
enhanced_config = plugin_manager.apply_plugins(base_config)

# Use enhanced configuration with plugin features
result = run_research(enhanced_config)
```

## Configuration Debugging

### Configuration Inspection

```python
from deepresearch.config.debug import ConfigDebugger

debugger = ConfigDebugger()

# Print configuration structure
debugger.print_config_structure(cfg)

# Find configuration issues
issues = debugger.find_issues(cfg)
for issue in issues:
    print(f"Configuration issue: {issue}")

# Generate configuration report
report = debugger.generate_report(cfg)
print(report)
```

### Configuration Tracing

```python
from deepresearch.config.tracing import ConfigTracer

tracer = ConfigTracer()

# Trace configuration loading
with tracer.trace():
    cfg = load_configuration()

# Get trace information
trace_info = tracer.get_trace()
for event in trace_info.events:
    print(f"Config event: {event}")
```

## Best Practices

1. **Use Environment Variables**: Store sensitive data and environment-specific settings in environment variables
2. **Validate Configuration**: Always validate configuration before use
3. **Document Overrides**: Document configuration overrides and their purpose
4. **Version Control**: Keep configuration files in version control
5. **Test Configurations**: Test configurations in staging before production
6. **Monitor Changes**: Track configuration changes and their impact
7. **Use Profiles**: Leverage configuration profiles for different environments

## Error Handling

### Configuration Errors

```python
from deepresearch.config.errors import ConfigurationError

try:
    cfg = load_configuration()
except ConfigurationError as e:
    print(f"Configuration error: {e}")
    print(f"Error details: {e.details}")

    # Attempt automatic fix
    if e.can_fix_automatically:
        fixed_cfg = e.fix_configuration()
        print("Configuration automatically fixed")
```

### Validation Errors

```python
from deepresearch.config.validation import ValidationResult

result = validate_configuration(cfg)

if not result.valid:
    for error in result.errors:
        print(f"Validation error in {error.field}: {error.message}")

    # Get suggestions for fixes
    suggestions = result.get_suggestions()
    for suggestion in suggestions:
        print(f"Suggestion: {suggestion}")
```

## Related Documentation

- [Configuration Guide](../getting-started/configuration.md) - Basic configuration usage
- [Architecture Overview](../architecture/overview.md) - System design and configuration integration
- [Development Setup](../development/setup.md) - Development environment configuration
- [CI/CD Guide](../development/ci-cd.md) - Configuration in CI/CD pipelines
