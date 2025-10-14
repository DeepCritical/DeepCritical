# LLM Model Configuration

DeepCritical supports multiple LLM backends through a unified OpenAI-compatible interface. This guide covers configuration and usage of different LLM providers.

## Supported Providers

DeepCritical supports any OpenAI-compatible API server:

- **vLLM**: High-performance inference server for local models
- **llama.cpp**: Efficient C++ inference for GGUF models
- **Text Generation Inference (TGI)**: Hugging Face's optimized inference server
- **Custom OpenAI-compatible servers**: Any server implementing the OpenAI Chat Completions API

## Configuration Files

LLM configurations are stored in `configs/llm/` directory:

```
configs/llm/
├── vllm_pydantic.yaml      # vLLM server configuration
├── llamacpp_local.yaml     # llama.cpp server configuration
└── tgi_local.yaml          # TGI server configuration
```

## Configuration Schema

All LLM configurations follow this Pydantic-validated schema:

### Basic Configuration

```yaml
# Provider identifier
provider: "vllm"  # or "llamacpp", "tgi", "custom"

# Model identifier
model_name: "meta-llama/Llama-3-8B"

# Server endpoint
base_url: "http://localhost:8000/v1"

# Optional API key (set to null for local servers)
api_key: null

# Connection settings
timeout: 60.0        # Request timeout in seconds (1-600)
max_retries: 3       # Maximum retry attempts (0-10)
retry_delay: 1.0     # Delay between retries in seconds
```

### Generation Parameters

```yaml
generation:
  temperature: 0.7           # Sampling temperature (0.0-2.0)
  max_tokens: 512           # Maximum tokens to generate (1-32000)
  top_p: 0.9                # Nucleus sampling threshold (0.0-1.0)
  frequency_penalty: 0.0    # Penalize token frequency (-2.0-2.0)
  presence_penalty: 0.0     # Penalize token presence (-2.0-2.0)
```

## Provider-Specific Configurations

### vLLM Configuration

```yaml
# configs/llm/vllm_pydantic.yaml
provider: "vllm"
model_name: "meta-llama/Llama-3-8B"
base_url: "http://localhost:8000/v1"
api_key: null  # vLLM uses "EMPTY" by default if auth is disabled

generation:
  temperature: 0.7
  max_tokens: 512
  top_p: 0.9
  frequency_penalty: 0.0
  presence_penalty: 0.0

timeout: 60.0
max_retries: 3
retry_delay: 1.0
```

**Starting vLLM server:**

```bash
python -m vllm.entrypoints.openai.api_server \
  --model meta-llama/Llama-3-8B \
  --port 8000
```

### llama.cpp Configuration

```yaml
# configs/llm/llamacpp_local.yaml
provider: "llamacpp"
model_name: "llama"  # Default name used by llama.cpp server
base_url: "http://localhost:8080/v1"
api_key: null

generation:
  temperature: 0.7
  max_tokens: 512
  top_p: 0.9
  frequency_penalty: 0.0
  presence_penalty: 0.0

timeout: 60.0
max_retries: 3
retry_delay: 1.0
```

**Starting llama.cpp server:**

```bash
./llama-server \
  --model models/llama-3-8b.gguf \
  --port 8080 \
  --ctx-size 4096
```

### TGI Configuration

```yaml
# configs/llm/tgi_local.yaml
provider: "tgi"
model_name: "bigscience/bloom-560m"
base_url: "http://localhost:3000/v1"
api_key: null

generation:
  temperature: 0.7
  max_tokens: 512
  top_p: 0.9
  frequency_penalty: 0.0
  presence_penalty: 0.0

timeout: 60.0
max_retries: 3
retry_delay: 1.0
```

**Starting TGI server:**

```bash
docker run -p 3000:80 \
  -v $PWD/data:/data \
  ghcr.io/huggingface/text-generation-inference:latest \
  --model-id bigscience/bloom-560m
```

## Python API Usage

### Loading Models from Configuration

```python
from omegaconf import DictConfig, OmegaConf
from DeepResearch.src.models import OpenAICompatibleModel

# Load configuration
config = OmegaConf.load("configs/llm/vllm_pydantic.yaml")

# Type guard: ensure config is a DictConfig (not ListConfig)
assert OmegaConf.is_dict(config), "Config must be a dict"
dict_config: DictConfig = config  # type: ignore

# Create model from configuration
model = OpenAICompatibleModel.from_config(dict_config)

# Or use provider-specific methods
model = OpenAICompatibleModel.from_vllm(dict_config)
model = OpenAICompatibleModel.from_llamacpp(dict_config)
model = OpenAICompatibleModel.from_tgi(dict_config)
```

### Direct Instantiation

```python
from omegaconf import DictConfig, OmegaConf
from DeepResearch.src.models import OpenAICompatibleModel

# Create model with direct parameters (no config file needed)
model = OpenAICompatibleModel.from_vllm(
    base_url="http://localhost:8000/v1",
    model_name="meta-llama/Llama-3-8B"
)

# Override config parameters from file
config = OmegaConf.load("configs/llm/vllm_pydantic.yaml")

# Type guard before using config
assert OmegaConf.is_dict(config), "Config must be a dict"
dict_config: DictConfig = config  # type: ignore

model = OpenAICompatibleModel.from_config(
    dict_config,
    model_name="override-model",  # Override model name
    timeout=120.0                 # Override timeout
)
```

### Environment Variables

Use environment variables for sensitive data:

```yaml
# In your config file
base_url: ${oc.env:LLM_BASE_URL,http://localhost:8000/v1}
api_key: ${oc.env:LLM_API_KEY}
```

```bash
# Set environment variables
export LLM_BASE_URL="http://my-server:8000/v1"
export LLM_API_KEY="your-api-key"
```

## Configuration Validation

All configurations are validated using Pydantic models at runtime:

### LLMModelConfig

```python
from DeepResearch.src.datatypes.llm_models import LLMModelConfig, LLMProvider

config = LLMModelConfig(
    provider=LLMProvider.VLLM,
    model_name="meta-llama/Llama-3-8B",
    base_url="http://localhost:8000/v1",
    timeout=60.0,
    max_retries=3
)
```

**Validation rules:**
- `model_name`: Non-empty string (whitespace stripped)
- `base_url`: Non-empty string (whitespace stripped)
- `timeout`: Positive float (1-600 seconds)
- `max_retries`: Integer (0-10)
- `retry_delay`: Positive float

### GenerationConfig

```python
from DeepResearch.src.datatypes.llm_models import GenerationConfig

gen_config = GenerationConfig(
    temperature=0.7,
    max_tokens=512,
    top_p=0.9,
    frequency_penalty=0.0,
    presence_penalty=0.0
)
```

**Validation rules:**
- `temperature`: Float (0.0-2.0)
- `max_tokens`: Positive integer (1-32000)
- `top_p`: Float (0.0-1.0)
- `frequency_penalty`: Float (-2.0-2.0)
- `presence_penalty`: Float (-2.0-2.0)

## Command Line Overrides

Override LLM configuration from the command line:

```bash
# Override model name
uv run deepresearch \
  llm.model_name="different-model" \
  question="Your question"

# Override server URL
uv run deepresearch \
  llm.base_url="http://different-server:8000/v1" \
  question="Your question"

# Override generation parameters
uv run deepresearch \
  llm.generation.temperature=0.9 \
  llm.generation.max_tokens=1024 \
  question="Your question"
```

## Testing LLM Configurations

Test your LLM configuration before use:

```python
# tests/test_models.py
from omegaconf import DictConfig, OmegaConf
from DeepResearch.src.models import OpenAICompatibleModel

def test_vllm_config():
    """Test vLLM model configuration."""
    config = OmegaConf.load("configs/llm/vllm_pydantic.yaml")

    # Type guard: ensure config is a DictConfig
    assert OmegaConf.is_dict(config), "Config must be a dict"
    dict_config: DictConfig = config  # type: ignore

    model = OpenAICompatibleModel.from_vllm(dict_config)

    assert model.model_name == "meta-llama/Llama-3-8B"
    assert "localhost:8000" in model.base_url
```

Run tests:

```bash
# Run all model tests
uv run pytest tests/test_models.py -v

# Test specific provider
uv run pytest tests/test_models.py::TestOpenAICompatibleModelWithConfigs::test_from_vllm_with_actual_config_file -v
```

## Troubleshooting

### Connection Errors

**Problem:** `ConnectionError: Failed to connect to server`

**Solutions:**
1. Verify server is running: `curl http://localhost:8000/v1/models`
2. Check `base_url` in configuration
3. Increase `timeout` value
4. Check firewall settings

### Type Validation Errors

**Problem:** `ValidationError: Invalid type for model_name`

**Solutions:**
1. Ensure `model_name` is a non-empty string
2. Check for trailing whitespace (automatically stripped)
3. Verify configuration file syntax

### Model Not Found

**Problem:** `Model 'xyz' not found`

**Solutions:**
1. Verify model is loaded on the server
2. Check `model_name` matches server's model identifier
3. For llama.cpp, use default name `"llama"`

## Best Practices

1. **Configuration Management**
   - Keep separate configs for development, staging, production
   - Use environment variables for sensitive data
   - Version control your configuration files

2. **Performance Tuning**
   - Adjust `max_tokens` based on use case
   - Use appropriate `temperature` for creativity vs. consistency
   - Set reasonable `timeout` values for your network

3. **Error Handling**
   - Configure `max_retries` based on server reliability
   - Set appropriate `retry_delay` to avoid overwhelming servers
   - Implement proper error logging

4. **Testing**
   - Test configurations in development environment first
   - Validate generation parameters produce expected output
   - Monitor server response times

## Related Documentation

- [Configuration Guide](../getting-started/configuration.md): General Hydra configuration
- [Core Modules](../core/index.md): Implementation details
- [Data Types API](../api/datatypes.md): Pydantic schemas and validation

## References

- [vLLM Documentation](https://docs.vllm.ai/)
- [llama.cpp Server](https://github.com/ggerganov/llama.cpp/tree/master/)
- [Text Generation Inference](https://huggingface.co/docs/text-generation-inference)
- [OpenAI API Reference](https://platform.openai.com/docs/api-reference)
