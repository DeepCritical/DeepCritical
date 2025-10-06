# VLLM-Based Prompt Testing with Hydra Configuration

This document describes the VLLM-based testing system for DeepCritical prompts, which allows testing prompts with actual LLM inference using Testcontainers and full Hydra configuration support.

## Overview

The VLLM testing system provides:
- **Real LLM Testing**: Tests prompts using actual VLLM containers with real language models
- **Hydra Configuration**: Fully configurable through Hydra configuration system
- **Single Instance Optimization**: Optimized for single VLLM container usage for faster execution
- **Reasoning Parsing**: Automatically parses reasoning outputs and tool calls from responses
- **Artifact Collection**: Saves detailed test results and artifacts for analysis
- **CI Integration**: Optional tests that don't run in CI by default

## Architecture

### Core Components

1. **VLLMPromptTester**: Main class for managing VLLM containers and testing prompts (Hydra-configurable)
2. **VLLMPromptTestBase**: Base test class for prompt testing (Hydra-configurable)
3. **Individual Test Modules**: Test files for each prompt module with Hydra support
4. **Testcontainers Integration**: Uses VLLM containers for isolated testing
5. **Hydra Configuration**: Full configuration management through Hydra configs

### Configuration Structure

```
configs/
└── vllm_tests/
    ├── default.yaml              # Main VLLM test configuration
    ├── model/
    │   ├── local_model.yaml      # Local model configuration
    │   └── ...
    ├── performance/
    │   ├── balanced.yaml         # Balanced performance settings
    │   └── ...
    ├── testing/
    │   ├── comprehensive.yaml    # Comprehensive testing settings
    │   └── ...
    └── output/
        ├── structured.yaml       # Structured output settings
        └── ...
```

### Test Structure

```
tests/
├── testcontainers_vllm.py          # VLLM container management (Hydra-configurable)
├── test_prompts_vllm_base.py       # Base test class (Hydra-configurable)
├── test_prompts_agents_vllm.py     # Tests for agents.py prompts
├── test_prompts_bioinformatics_agents_vllm.py  # Tests for bioinformatics prompts
├── test_prompts_broken_ch_fixer_vllm.py       # Tests for broken character fixer
├── test_prompts_code_exec_vllm.py             # Tests for code execution prompts
├── test_prompts_code_sandbox_vllm.py          # Tests for code sandbox prompts
├── test_prompts_deep_agent_prompts_vllm.py    # Tests for deep agent prompts
├── test_prompts_error_analyzer_vllm.py        # Tests for error analyzer prompts
├── test_prompts_evaluator_vllm.py             # Tests for evaluator prompts
├── test_prompts_finalizer_vllm.py              # Tests for finalizer prompts
└── ... (more test files for each prompt module)
```

## Usage

### Running All VLLM Tests

```bash
# Using the script with Hydra configuration (recommended)
python scripts/run_vllm_tests.py

# Using the script without Hydra (fallback)
python scripts/run_vllm_tests.py --no-hydra

# Using pytest directly
pytest tests/test_prompts_*_vllm.py -m vllm

# Using tox with Hydra configuration
tox -e vllm-tests-config

# Using tox without Hydra (fallback)
tox -e vllm-tests
```

### Running Tests for Specific Modules

```bash
# Test specific modules with Hydra configuration
python scripts/run_vllm_tests.py agents bioinformatics_agents

# Test specific modules without Hydra
python scripts/run_vllm_tests.py --no-hydra agents bioinformatics_agents

# Using pytest for specific modules
pytest tests/test_prompts_agents_vllm.py tests/test_prompts_bioinformatics_agents_vllm.py -m vllm
```

### Running with Coverage

```bash
# With Hydra configuration
python scripts/run_vllm_tests.py --coverage

# Without Hydra configuration
python scripts/run_vllm_tests.py --no-hydra --coverage

# Or using pytest
pytest tests/test_prompts_*_vllm.py -m vllm --cov=DeepResearch --cov-report=html
```

### Advanced Usage Options

```bash
# List available modules
python scripts/run_vllm_tests.py --list-modules

# Verbose output
python scripts/run_vllm_tests.py --verbose

# Custom Hydra configuration
python scripts/run_vllm_tests.py --config-name vllm_tests --config-file custom.yaml

# Disable parallel execution (single instance optimization)
python scripts/run_vllm_tests.py --parallel  # Note: This is automatically disabled for single instance

# Combine options
python scripts/run_vllm_tests.py agents --verbose --coverage
```

## CI Integration

VLLM tests are **disabled by default in CI** to avoid resource requirements and are optimized for single instance usage. They can be enabled:

### GitHub Actions

Tests run automatically but skip VLLM tests. To run VLLM tests:

1. **Manual Trigger**: Use workflow dispatch in GitHub Actions UI
2. **Commit Message**: Include `[vllm-tests]` in commit message
3. **Pull Request**: Add `[vllm-tests]` label or comment

The CI workflow uses Hydra configuration and installs required dependencies:
```yaml
- name: Run VLLM tests (optional, manual trigger only)
  run: |
    pip install testcontainers omegaconf hydra-core
    python scripts/run_vllm_tests.py --no-hydra
```

### Local Development

```bash
# Run only basic tests (default)
pytest tests/

# Run VLLM tests with Hydra configuration (recommended)
python scripts/run_vllm_tests.py

# Run VLLM tests without Hydra (fallback)
python scripts/run_vllm_tests.py --no-hydra

# Run specific modules with Hydra
python scripts/run_vllm_tests.py agents bioinformatics_agents

# Run VLLM tests explicitly with pytest
pytest tests/test_prompts_*_vllm.py -m vllm

# Run all tests including VLLM (not recommended for CI)
pytest tests/ -m "vllm or not optional"
```

### Tox Integration

```bash
# Run VLLM tests with Hydra configuration
tox -e vllm-tests-config

# Run VLLM tests without Hydra configuration
tox -e vllm-tests

# Run all tests including VLLM
tox -e all-tests
```

## Test Output and Artifacts

### Artifacts Directory

```
test_artifacts/
└── vllm_prompts/
    ├── test_summary.md              # Summary report
    ├── agents_parser_1234567890.json # Individual test results
    ├── bioinformatics_fusion_1234567891.json
    └── vllm_prompt_tests.log        # Detailed logs
```

### Test Results

Each test generates:
- **JSON Artifacts**: Detailed results with reasoning parsing
- **Log Files**: Execution logs and error details
- **Summary Reports**: Overview of test outcomes

### Example Test Result

```json
{
  "prompt_name": "PARSER_AGENT_SYSTEM_PROMPT",
  "original_prompt": "You are a research question parser...",
  "formatted_prompt": "You are a research question parser...",
  "dummy_data": {"question": "What is AI?", "context": "..."},
  "generated_response": "I need to analyze this question...",
  "reasoning": {
    "has_reasoning": true,
    "reasoning_steps": ["Step 1: Analyze question...", "Step 2: Identify entities..."],
    "tool_calls": [],
    "final_answer": "The question is about artificial intelligence...",
    "reasoning_format": "structured"
  },
  "success": true,
  "timestamp": 1234567890.123
}
```

## Configuration

### Hydra Configuration

VLLM tests are fully configurable through Hydra configuration files in `configs/vllm_tests/`. The main configuration files are:

#### Main Configuration (`configs/vllm_tests/default.yaml`)
```yaml
vllm_tests:
  enabled: true
  run_in_ci: false
  execution_strategy: sequential
  max_concurrent_tests: 1  # Single instance optimization

  artifacts:
    enabled: true
    base_directory: "test_artifacts/vllm_tests"

  monitoring:
    enabled: true
    max_execution_time_per_module: 300

  error_handling:
    graceful_degradation: true
    retry_failed_prompts: true
```

#### Model Configuration (`configs/vllm_tests/model/local_model.yaml`)
```yaml
model:
  name: "microsoft/DialoGPT-medium"
  generation:
    max_tokens: 256
    temperature: 0.7

container:
  image: "vllm/vllm-openai:latest"
  resources:
    cpu_limit: 2
    memory_limit: "4g"
```

#### Performance Configuration (`configs/vllm_tests/performance/balanced.yaml`)
```yaml
targets:
  max_execution_time_per_module: 300
  max_memory_usage_mb: 2048

execution:
  enable_batching: true
  max_batch_size: 4

monitoring:
  track_execution_times: true
  track_memory_usage: true
```

#### Testing Configuration (`configs/vllm_tests/testing/comprehensive.yaml`)
```yaml
scope:
  test_all_modules: true
  max_prompts_per_module: 50

validation:
  validate_prompt_structure: true
  validate_response_structure: true

assertions:
  min_success_rate: 0.8
  min_response_length: 10
```

### Custom Configuration

Create custom configurations by overriding defaults:

```bash
# Use custom configuration
python scripts/run_vllm_tests.py --config-name vllm_tests --config-file custom.yaml

# Override specific values
python scripts/run_vllm_tests.py model.name=microsoft/DialoGPT-large performance.max_container_startup_time=300
```

### Environment Variables

- `HYDRA_FULL_ERROR=1`: Enable full Hydra error reporting
- `PYTHONPATH`: Include project root for imports

### Pytest Configuration

Tests use markers to control execution:
- `@pytest.mark.vllm`: Marks tests requiring VLLM containers
- `@pytest.mark.optional`: Marks tests as optional

### Container Configuration

VLLM containers are configured through Hydra:
- **Model**: Configurable through `model.name`
- **Resources**: Configurable through `container.resources`
- **Generation Parameters**: Configurable through `model.generation`
- **Health Checks**: Configurable through `model.server.health_check`

## Troubleshooting

### Common Issues

1. **Container Startup Failures**
   - Check Docker is running and accessible
   - Verify VLLM image availability (`vllm/vllm-openai:latest`)
   - Check network connectivity and firewall settings
   - Ensure sufficient disk space for container images

2. **Hydra Configuration Issues**
   - Verify `configs/` directory exists and contains `vllm_tests/` subdirectory
   - Check Hydra configuration syntax in YAML files
   - Ensure OmegaConf and Hydra-Core are installed
   - Use `--no-hydra` flag for fallback mode

3. **Test Timeouts**
   - Increase `max_container_startup_time` in performance configuration
   - Use smaller models for faster testing (configure in `model.name`)
   - Run tests sequentially (single instance optimization)
   - Check system resource availability

4. **Memory Issues**
   - Use smaller models (e.g., `DialoGPT-medium` vs. `DialoGPT-large`)
   - Reduce `max_tokens` in model configuration
   - Limit concurrent test execution (already optimized to 1)
   - Monitor system resources during testing

5. **Import Errors**
   - Ensure `testcontainers`, `omegaconf`, and `hydra-core` are installed
   - Check PYTHONPATH includes project root
   - Verify module imports in test files

### Debug Mode

```bash
# Enable debug logging with Hydra configuration
export PYTHONPATH="$PWD:$PYTHONPATH"
export HYDRA_FULL_ERROR=1
python scripts/run_vllm_tests.py --verbose

# Enable debug logging without Hydra
python scripts/run_vllm_tests.py --no-hydra --verbose
```

### Manual Container Testing

```python
from tests.testcontainers_vllm import VLLMPromptTester
from omegaconf import OmegaConf

# Test container manually with Hydra configuration
config = OmegaConf.create({
    "model": {"name": "microsoft/DialoGPT-medium"},
    "performance": {"max_container_startup_time": 120},
    "vllm_tests": {"enabled": True}
})

with VLLMPromptTester(config=config) as tester:
    result = tester.test_prompt(
        "Hello, how are you?",
        "test_prompt",
        {"greeting": "Hello"}
    )
    print(result)

# Test with default configuration
with VLLMPromptTester() as tester:
    result = tester.test_prompt(
        "Hello, how are you?",
        "test_prompt",
        {"greeting": "Hello"}
    )
    print(result)
```

## Single Instance Optimization

The VLLM testing system is optimized for single container usage to improve performance and reduce resource requirements:

### Key Optimizations

1. **Single Container**: Uses one VLLM container for all tests
2. **Sequential Execution**: Tests run sequentially to avoid container conflicts
3. **Reduced Delays**: Minimal delays between tests (0.1s default)
4. **Resource Limits**: Configurable CPU and memory limits
5. **Health Monitoring**: Efficient health checks with configurable intervals

### Configuration Benefits

```yaml
# Single instance optimization in config
vllm_tests:
  execution_strategy: sequential  # No parallel execution
  max_concurrent_tests: 1        # Single container
  module_batch_size: 3           # Process modules in small batches

performance:
  max_container_startup_time: 120  # Faster container startup
  enable_batching: true           # Efficient request handling

model:
  generation:
    max_tokens: 256               # Reasonable token limit
    temperature: 0.7              # Balanced creativity/consistency
```

### Performance Improvements

- **Faster Startup**: Single container reduces initialization overhead
- **Lower Memory Usage**: One container vs. multiple containers
- **Better Stability**: Fewer container management issues
- **Predictable Performance**: Consistent resource allocation

## Best Practices

1. **Test Prompt Structure**: Ensure prompts have proper placeholders and formatting
2. **Use Realistic Data**: Provide meaningful dummy data for testing
3. **Monitor Resources**: VLLM containers use significant resources
4. **Artifact Management**: Regularly clean old test artifacts
5. **CI Optimization**: Keep VLLM tests optional and resource-efficient

## Extending the System

### Adding New Test Modules

1. Create `test_prompts_{module_name}_vllm.py`
2. Inherit from `VLLMPromptTestBase`
3. Implement module-specific test methods
4. Add to `scripts/run_vllm_tests.py` if needed

### Custom Reasoning Parsing

Extend `VLLMPromptTester._parse_reasoning()` to support new reasoning formats:

```python
def _parse_reasoning(self, response: str) -> Dict[str, Any]:
    # Add custom parsing logic
    if "CUSTOM_FORMAT" in response:
        # Custom parsing
        pass
    return super()._parse_reasoning(response)
```

### New Container Types

Add support for new container types in `testcontainers_vllm.py`:

```python
class CustomContainer(VLLMContainer):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Custom configuration
```

## Performance Considerations

- **Test Duration**: VLLM tests take longer than unit tests
- **Resource Usage**: Containers require CPU, memory, and disk space
- **Parallel Execution**: Limited by system resources
- **Model Size**: Smaller models = faster tests but less capability

## Security

- **Container Isolation**: Tests run in isolated containers
- **Resource Limits**: Containers have resource constraints
- **Network Security**: Containers use internal networking
- **Data Privacy**: Test data stays within containers

## Maintenance

- **Dependencies**: Keep testcontainers and VLLM dependencies updated
- **Model Updates**: Monitor model availability and performance
- **Artifact Cleanup**: Implement regular cleanup of old artifacts
- **CI Monitoring**: Monitor CI performance and resource usage
