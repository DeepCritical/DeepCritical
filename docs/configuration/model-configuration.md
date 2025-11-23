# Model Configuration Guide

## Overview

All LLM and embedding model configurations are now centralized in `configs/models/default.yaml`. This eliminates hardcoded model strings and provides a single source of truth for model selection across the entire codebase.

## Configuration Structure

### LLM Models

```yaml
# configs/models/default.yaml
llm:
  # Default production model
  default: "anthropic:claude-sonnet-4-0"

  # Fallback model for rate limits or errors
  fallback: "anthropic:claude-sonnet-3-5"

  # Fast model for simple tasks
  fast: "anthropic:claude-haiku-3-5"

  # High-capability model for complex reasoning
  advanced: "anthropic:claude-opus-4"

  # Agent-specific overrides (optional)
  agents:
    bioinformatics: "anthropic:claude-sonnet-4-0"
    code_generation: "anthropic:claude-sonnet-4-0"
```

### Embedding Models

```yaml
embeddings:
  # Default embedding model
  default: "sentence-transformers/all-MiniLM-L6-v2"

  # Model parameters
  default_params:
    num_dimensions: 384
    batch_size: 32
    device: "cpu"
```

## Usage

### In Agent Code

Agents now automatically use the configured default model:

```python
from DeepResearch.agents import BaseAgent

# Old way (hardcoded)
class MyAgent(BaseAgent):
    def __init__(self):
        super().__init__(AgentType.CUSTOM, "anthropic:claude-sonnet-4-0")

# New way (uses config)
class MyAgent(BaseAgent):
    def __init__(self):
        super().__init__(AgentType.CUSTOM)  # Uses config default
```

### Programmatic Access

```python
from DeepResearch.src.utils.config_loader import ModelConfigLoader

config = ModelConfigLoader()

# Get default models
llm_model = config.get_default_llm_model()
embedding_model = config.get_default_embedding_model()

# Get specific model variants
fast_model = config.get_fast_llm_model()
advanced_model = config.get_advanced_llm_model()

# Get agent-specific models
bio_model = config.get_agent_llm_model("bioinformatics")
```

### Environment Variable Overrides

Override defaults via environment variables (highest priority):

```bash
# Override default LLM model
export DEFAULT_LLM_MODEL="anthropic:claude-haiku-3-5"

# Override default embedding model
export DEFAULT_EMBEDDING_MODEL="text-embedding-ada-002"

# Run application
python -m DeepResearch.app
```

### Hydra CLI Overrides

Override via command line:

```bash
# Override default LLM model
deepresearch models.llm.default=anthropic:claude-haiku-3-5

# Override agent-specific model
deepresearch models.llm.agents.bioinformatics=anthropic:claude-opus-4

# Override embedding model
deepresearch models.embeddings.default=mixedbread-ai/mxbai-embed-large-v1
```

## Configuration Priority

The system follows this priority order (highest to lowest):

1. **Environment Variables** - `DEFAULT_LLM_MODEL`, `DEFAULT_EMBEDDING_MODEL`
2. **Hydra CLI Overrides** - `models.llm.default=...`
3. **Agent-Specific Config** - `models.llm.agents.<agent_type>`
4. **Default Config** - `models.llm.default`
5. **Hardcoded Fallback** - Only as last resort in `config_loader.py`

## Testing Configuration

Override models for testing environments:

```yaml
# configs/models/testing.yaml
llm:
  default: "anthropic:claude-haiku-3-5"  # Faster/cheaper for tests

testing:
  llm:
    default: "anthropic:claude-haiku-3-5"
```

Load testing config:

```bash
deepresearch --config-name=testing
```

## Migration from Hardcoded Strings

### Before (Hardcoded)

```python
# ❌ Old: Hardcoded model string
search_agent = SearchAgent(model="anthropic:claude-sonnet-4-0")
```

### After (Config-Based)

```python
# ✅ New: Uses centralized config
search_agent = SearchAgent()  # Automatically uses config default
```

### Explicit Model Override

If you need to override for a specific use case:

```python
# Still supported - explicitly specify model
search_agent = SearchAgent(model="anthropic:claude-haiku-3-5")
```

## Benefits

1. **Single Source of Truth** - Change models in one place
2. **Environment Flexibility** - Different models for dev/staging/prod
3. **Cost Optimization** - Easy to switch to cheaper models for testing
4. **Agent-Specific Tuning** - Different models for different agent types
5. **No Code Changes** - Override via config or environment variables

## Examples

### Example 1: Development vs Production

```yaml
# configs/models/development.yaml
llm:
  default: "anthropic:claude-haiku-3-5"  # Fast, cheap for dev

# configs/models/production.yaml
llm:
  default: "anthropic:claude-sonnet-4-0"  # Full capability
```

### Example 2: Agent-Specific Models

```yaml
# configs/models/default.yaml
llm:
  default: "anthropic:claude-sonnet-4-0"
  agents:
    bioinformatics: "anthropic:claude-opus-4"  # Complex domain needs advanced model
    search: "anthropic:claude-haiku-3-5"        # Simple task uses fast model
```

### Example 3: Cost Optimization

```bash
# Use cheaper model globally
export DEFAULT_LLM_MODEL="anthropic:claude-haiku-3-5"
python -m DeepResearch.app
```

## Files Changed

The following files were updated to use centralized configuration:

- **Config**: `configs/models/default.yaml` (new)
- **Core**: `DeepResearch/src/utils/config_loader.py`
- **Agents**: `DeepResearch/agents.py`, all agent files in `src/agents/`
- **App**: `DeepResearch/app.py`
- **Statemachines**: All files in `src/statemachines/`
- **Examples**: `examples/mgrep_semantic_search/`, `examples/simple_genomics_discovery/`

## See Also

- [Configuration Overview](../getting-started/configuration.md)
- [Agent Development](../development/tool-development.md)
- [Testing Guide](../development/testing.md)
