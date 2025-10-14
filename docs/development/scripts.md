# Scripts Documentation

This section documents the various scripts and utilities available in the DeepCritical project for development, testing, and operational tasks.

## Overview

The `scripts/` directory contains utilities for testing, development, and operational tasks:

```
scripts/
├── prompt_testing/              # VLLM-based prompt testing system
│   ├── run_vllm_tests.py       # Main VLLM test runner
│   ├── testcontainers_vllm.py  # VLLM container management
│   ├── test_prompts_vllm_base.py  # Base test framework
│   ├── test_matrix_functionality.py  # Test matrix utilities
│   └── VLLM_TESTS_README.md     # Detailed VLLM testing documentation
└── README.md                   # This file
```

## VLLM Prompt Testing System

### Main Test Runner (`run_vllm_tests.py`)

The main script for running VLLM-based prompt tests with full Hydra configuration support.

**Usage:**
```bash
# Run all VLLM tests with Hydra configuration
python scripts/run_vllm_tests.py

# Run specific modules
python scripts/run_vllm_tests.py agents bioinformatics_agents

# Run with custom configuration
python scripts/run_vllm_tests.py --config-name vllm_tests --config-file custom.yaml

# Run without Hydra (fallback mode)
python scripts/run_vllm_tests.py --no-hydra

# Run with coverage
python scripts/run_vllm_tests.py --coverage

# List available modules
python scripts/run_vllm_tests.py --list-modules

# Verbose output
python scripts/run_vllm_tests.py --verbose
```

**Features:**
- **Hydra Integration**: Full configuration management through Hydra
- **Single Instance Optimization**: Optimized for single VLLM container usage
- **Module Selection**: Run tests for specific prompt modules
- **Artifact Collection**: Detailed test results and logs
- **Coverage Integration**: Optional coverage reporting
- **CI Integration**: Configurable for CI environments

**Configuration:**
The script uses Hydra configuration files in `configs/vllm_tests/` for comprehensive configuration management.

### Container Management (`testcontainers_vllm.py`)

Manages VLLM containers for isolated testing with configurable resource limits.

**Key Features:**
- **Container Lifecycle**: Automatic container startup, health checks, and cleanup
- **Resource Management**: Configurable CPU, memory, and timeout limits
- **Health Monitoring**: Automatic health checks with configurable intervals
- **Model Management**: Support for multiple VLLM models
- **Error Handling**: Comprehensive error handling and recovery

**Usage:**
```python
from scripts.prompt_testing.testcontainers_vllm import VLLMPromptTester

# Use with Hydra configuration
with VLLMPromptTester(config=hydra_config) as tester:
    result = tester.test_prompt("Hello", "test_prompt", {"greeting": "Hello"})

# Use with default configuration
with VLLMPromptTester() as tester:
    result = tester.test_prompt("Hello", "test_prompt", {"greeting": "Hello"})
```

### Base Test Framework (`test_prompts_vllm_base.py`)

Base class for VLLM prompt testing with common functionality.

**Key Features:**
- **Prompt Testing**: Standardized prompt testing interface
- **Response Parsing**: Automatic parsing of reasoning and tool calls
- **Result Validation**: Configurable result validation
- **Artifact Management**: Test result collection and storage
- **Error Handling**: Comprehensive error handling and reporting

**Usage:**
```python
from .test_prompts_vllm_base import VLLMPromptTestBase

class MyPromptTests(VLLMPromptTestBase):
    def test_my_prompt(self):
        """Test my custom prompt."""
        result = self.test_prompt(
            prompt="My custom prompt with {placeholder}",
            prompt_name="MY_CUSTOM_PROMPT",
            dummy_data={"placeholder": "test_value"}
        )

        self.assertTrue(result["success"])
        self.assertIn("reasoning", result)
```

## Test Matrix System

### Test Matrix Functionality (`test_matrix_functionality.py`)

Utilities for managing test matrices and configuration variations.

**Features:**
- **Matrix Generation**: Generate test configurations from parameter combinations
- **Configuration Management**: Handle complex test configuration matrices
- **Result Aggregation**: Aggregate results across matrix dimensions
- **Performance Tracking**: Track performance across configuration variations

**Usage:**
```python
from scripts.prompt_testing.test_matrix_functionality import TestMatrix

# Create test matrix
matrix = TestMatrix({
    "model": ["gpt-3.5-turbo", "gpt-4", "claude-3-sonnet"],
    "temperature": [0.3, 0.7, 0.9],
    "max_tokens": [256, 512, 1024]
})

# Generate configurations
configs = matrix.generate_configurations()

# Run tests across matrix
results = []
for config in configs:
    result = run_test_with_config(config)
    results.append(result)
```

## Development Utilities

### Test Data Management (`test_data_matrix.json`)

Contains test data matrices for systematic testing across different scenarios.

**Structure:**
```json
{
  "research_questions": {
    "basic": ["What is machine learning?", "How does AI work?"],
    "complex": ["Design a protein for therapeutic use", "Analyze gene expression data"],
    "domain_specific": ["CRISPR applications in medicine", "Quantum computing algorithms"]
  },
  "test_scenarios": {
    "success_cases": [...],
    "edge_cases": [...],
    "error_cases": [...]
  }
}
```

## Operational Scripts

### VLLM Test Runner (`run_vllm_tests.py`)

**Command Line Interface:**
```bash
python scripts/run_vllm_tests.py [MODULES...] [OPTIONS]

Arguments:
  MODULES          Specific test modules to run (optional)

Options:
  --config-name    Hydra configuration name
  --config-file    Custom configuration file
  --no-hydra       Disable Hydra configuration
  --coverage       Enable coverage reporting
  --verbose        Enable verbose output
  --list-modules   List available test modules
  --parallel       Enable parallel execution (not recommended for VLLM)
```

**Environment Variables:**
- `HYDRA_FULL_ERROR=1`: Enable detailed Hydra error reporting
- `PYTHONPATH`: Should include project root for imports

### Test Container Management

**Container Configuration:**
```python
# Container configuration through Hydra
container:
  image: "vllm/vllm-openai:latest"
  resources:
    cpu_limit: 2
    memory_limit: "4g"
    network_mode: "bridge"

  health_check:
    interval: 30
    timeout: 10
    retries: 3
```

## Testing Best Practices

### 1. Test Organization
- **Module-Specific Tests**: Organize tests by prompt module
- **Configuration Matrices**: Use test matrices for systematic testing
- **Artifact Management**: Collect and organize test results

### 2. Performance Optimization
- **Single Instance**: Use single VLLM container for efficiency
- **Resource Limits**: Configure appropriate resource limits
- **Batch Processing**: Process tests in small batches

### 3. Error Handling
- **Graceful Degradation**: Handle container failures gracefully
- **Retry Logic**: Implement retry for transient failures
- **Resource Cleanup**: Ensure proper container cleanup

### 4. CI/CD Integration
- **Optional Tests**: Keep VLLM tests optional in CI
- **Resource Allocation**: Allocate sufficient resources for containers
- **Timeout Management**: Set appropriate timeouts for container operations

## Troubleshooting

### Common Issues

**Container Startup Failures:**
```bash
# Check Docker status
docker info

# Check VLLM image availability
docker pull vllm/vllm-openai:latest

# Check system resources
docker system df
```

**Hydra Configuration Issues:**
```bash
# Enable full error reporting
export HYDRA_FULL_ERROR=1
python scripts/run_vllm_tests.py

# Check configuration files
python scripts/run_vllm_tests.py --cfg job
```

**Memory Issues:**
```bash
# Use smaller models
model:
  name: "TinyLlama/TinyLlama-1.1B-Chat-v1.0"

# Reduce resource limits
container:
  resources:
    memory_limit: "2g"
```

**Network Issues:**
```bash
# Check container networking
docker network ls

# Test container connectivity
docker run --rm curlimages/curl curl -f https://httpbin.org/get
```

### Debug Mode

**Enable Debug Logging:**
```bash
# With Hydra
export HYDRA_FULL_ERROR=1
python scripts/run_vllm_tests.py --verbose

# Without Hydra
python scripts/run_vllm_tests.py --no-hydra --verbose
```

**Manual Container Testing:**
```python
from scripts.prompt_testing.testcontainers_vllm import VLLMPromptTester

# Test container manually
with VLLMPromptTester() as tester:
    # Test basic functionality
    result = tester.test_prompt("Hello", "test", {"greeting": "Hello"})
    print(f"Test result: {result}")
```

## Maintenance

### Dependency Updates
```bash
# Update testcontainers
pip install --upgrade testcontainers

# Update VLLM-related packages
pip install --upgrade vllm openai

# Update Hydra and OmegaConf
pip install --upgrade hydra-core omegaconf
```

### Artifact Cleanup
```bash
# Clean old test artifacts
find test_artifacts/ -type f -name "*.json" -mtime +30 -delete
find test_artifacts/ -type f -name "*.log" -mtime +7 -delete

# Clean Docker resources
docker system prune -f
docker volume prune -f
```

### Performance Monitoring
```bash
# Monitor container resource usage
docker stats

# Monitor system resources during testing
htop
```

For more detailed information about VLLM testing, see the [Testing Guide](../development/testing.md).
