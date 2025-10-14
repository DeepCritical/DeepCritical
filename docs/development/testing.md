# Testing Guide

This guide explains the testing framework and practices used in DeepCritical, including unit tests, integration tests, and testing best practices.

## Testing Framework

DeepCritical uses a comprehensive testing framework with multiple test categories:

### Test Categories
```bash
# Run all tests
make test

# Run specific test categories
make test unit_tests          # Unit tests only
make test integration_tests   # Integration tests only
make test performance_tests   # Performance tests only
make test vllm_tests          # VLLM-specific tests only

# Run tests with coverage
make test-cov

# Run tests excluding slow tests
make test-fast
```

## Test Organization

### Directory Structure
```
tests/
├── __init__.py
├── test_agents.py              # Agent system tests
├── test_tools.py               # Tool framework tests
├── test_workflows.py           # Workflow execution tests
├── test_datatypes.py           # Data type validation tests
├── test_configuration.py       # Configuration tests
├── test_integration.py         # End-to-end integration tests
└── test_performance.py         # Performance and load tests
```

### Test Naming Conventions
```python
# Unit tests
def test_function_name():
    """Test specific function behavior."""

def test_function_name_edge_cases():
    """Test edge cases and error conditions."""

# Integration tests
def test_workflow_integration():
    """Test complete workflow execution."""

def test_cross_component_interaction():
    """Test interaction between components."""

# Performance tests
def test_performance_under_load():
    """Test performance with high load."""

def test_memory_usage():
    """Test memory usage patterns."""
```

## Writing Tests

### Unit Tests
```python
import pytest
from deepresearch.agents import SearchAgent
from deepresearch.datatypes import AgentDependencies

def test_search_agent_initialization():
    """Test SearchAgent initialization."""
    agent = SearchAgent()
    assert agent.agent_type == AgentType.SEARCH
    assert agent.status == AgentStatus.IDLE

def test_search_agent_execution():
    """Test SearchAgent execution."""
    agent = SearchAgent()
    deps = AgentDependencies()

    # Mock external dependencies
    with patch('deepresearch.tools.web_search') as mock_search:
        mock_search.return_value = "mock results"

        result = await agent.execute("test query", deps)

        assert result.success
        assert result.data == "mock results"
        mock_search.assert_called_once()

def test_search_agent_error_handling():
    """Test SearchAgent error handling."""
    agent = SearchAgent()
    deps = AgentDependencies()

    # Test with invalid input
    result = await agent.execute(None, deps)

    assert not result.success
    assert result.error is not None
```

### Integration Tests
```python
import pytest
from deepresearch.app import main

@pytest.mark.integration
async def test_full_workflow_execution():
    """Test complete workflow execution."""
    result = await main(
        question="What is machine learning?",
        flows={"prime": {"enabled": False}}
    )

    assert result.success
    assert result.data is not None
    assert len(result.execution_history.entries) > 0

@pytest.mark.integration
async def test_multi_flow_integration():
    """Test integration between multiple flows."""
    result = await main(
        question="Analyze protein function",
        flows={
            "prime": {"enabled": True},
            "bioinformatics": {"enabled": True}
        }
    )

    assert result.success
    # Verify results from both flows
    assert "prime_results" in result.data
    assert "bioinformatics_results" in result.data
```

### Performance Tests
```python
import pytest
import time
import psutil
import os

@pytest.mark.performance
async def test_execution_time():
    """Test execution time requirements."""
    start_time = time.time()

    result = await main(question="Performance test query")

    execution_time = time.time() - start_time

    # Should complete within reasonable time
    assert execution_time < 300  # 5 minutes
    assert result.success

@pytest.mark.performance
async def test_memory_usage():
    """Test memory usage during execution."""
    process = psutil.Process(os.getpid())
    initial_memory = process.memory_info().rss / 1024 / 1024  # MB

    result = await main(question="Memory usage test")

    final_memory = process.memory_info().rss / 1024 / 1024  # MB
    memory_increase = final_memory - initial_memory

    # Memory increase should be reasonable
    assert memory_increase < 500  # Less than 500MB increase
    assert result.success
```

## Test Configuration

### Test Configuration Files
```yaml
# tests/test_config.yaml
test_settings:
  mock_external_apis: true
  use_test_databases: true
  enable_performance_monitoring: true

  timeouts:
    unit_test: 30
    integration_test: 300
    performance_test: 600

  resources:
    max_memory_mb: 1000
    max_execution_time: 300
```

### Test Fixtures
```python
# tests/conftest.py
import pytest
from deepresearch.datatypes import AgentDependencies, ResearchState

@pytest.fixture
def sample_dependencies():
    """Provide sample agent dependencies for tests."""
    return AgentDependencies(
        model_name="anthropic:claude-sonnet-4-0",
        api_keys={"anthropic": "test-key"},
        config={"temperature": 0.7}
    )

@pytest.fixture
def sample_research_state():
    """Provide sample research state for tests."""
    return ResearchState(
        question="Test question",
        plan=["step1", "step2"],
        agent_results={},
        tool_outputs={}
    )

@pytest.fixture
def mock_tool_registry():
    """Mock tool registry for isolated testing."""
    with patch('deepresearch.tools.base.registry') as mock_registry:
        yield mock_registry
```

## Testing Best Practices

### 1. Test Isolation
```python
# Use fixtures for test isolation
def test_isolated_functionality(sample_dependencies):
    """Test with isolated dependencies."""
    # Test implementation using fixture
    pass

# Avoid global state in tests
def test_without_global_state():
    """Test without relying on global state."""
    # Create fresh instances for each test
    pass
```

### 2. Mocking External Dependencies
```python
from unittest.mock import patch, MagicMock

def test_with_mocked_external_api():
    """Test with mocked external API calls."""
    with patch('requests.get') as mock_get:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"data": "test"}
        mock_get.return_value = mock_response

        # Test implementation
        result = call_external_api()
        assert result == {"data": "test"}
```

### 3. Async Testing
```python
import pytest

@pytest.mark.asyncio
async def test_async_functionality():
    """Test async functions properly."""
    result = await async_function()
    assert result.success

# For testing async context managers
@pytest.mark.asyncio
async def test_async_context_manager():
    """Test async context managers."""
    async with async_context_manager() as manager:
        result = await manager.do_something()
        assert result is not None
```

### 4. Parameterized Tests
```python
import pytest

@pytest.mark.parametrize("input_data,expected", [
    ("test1", "result1"),
    ("test2", "result2"),
    ("test3", "result3"),
])
def test_parameterized_functionality(input_data, expected):
    """Test function with multiple parameter sets."""
    result = process_data(input_data)
    assert result == expected

@pytest.mark.parametrize("flow_enabled", [True, False])
@pytest.mark.parametrize("config_override", ["config1", "config2"])
async def test_flow_combinations(flow_enabled, config_override):
    """Test different flow and configuration combinations."""
    result = await main(
        question="Test query",
        flows={"test_flow": {"enabled": flow_enabled}},
        config_name=config_override
    )
    assert result.success
```

## Specialized Testing

### Tool Testing
```python
from deepresearch.tools import ToolRunner, ToolSpec

def test_custom_tool():
    """Test custom tool implementation."""
    tool = CustomTool()

    # Test tool specification
    spec = tool.get_spec()
    assert spec.name == "custom_tool"
    assert spec.category == ToolCategory.ANALYTICS

    # Test tool execution
    result = tool.run({"input": "test_data"})
    assert result.success
    assert "output" in result.data

def test_tool_error_handling():
    """Test tool error conditions."""
    tool = CustomTool()

    # Test with invalid input
    result = tool.run({"invalid": "input"})
    assert not result.success
    assert result.error is not None
```

### Agent Testing
```python
from deepresearch.agents import SearchAgent

def test_agent_lifecycle():
    """Test complete agent lifecycle."""
    agent = SearchAgent()

    # Test initialization
    assert agent.status == AgentStatus.IDLE

    # Test execution
    result = await agent.execute("test query", AgentDependencies())
    assert result.success

    # Test cleanup
    agent.cleanup()
    assert agent.status == AgentStatus.IDLE
```

### Workflow Testing
```python
from deepresearch.app import main

@pytest.mark.integration
async def test_workflow_error_recovery():
    """Test workflow error recovery mechanisms."""
    # Test with failing components
    result = await main(
        question="Test error recovery",
        enable_error_recovery=True,
        max_retries=3
    )

    # Should either succeed or provide meaningful error information
    assert result is not None
    if not result.success:
        assert result.error is not None
        assert len(result.error_history) > 0
```

## Tool Testing {#tools}

### Testing Custom Tools

DeepCritical provides comprehensive testing support for custom tools:

#### Tool Unit Testing
```python
import pytest
from deepresearch.src.tools.base import ToolRunner, ExecutionResult

class TestCustomTool:
    """Test cases for custom tool implementation."""

    @pytest.fixture
    def tool(self):
        """Create tool instance for testing."""
        return CustomTool()

    def test_tool_specification(self, tool):
        """Test tool specification is correctly defined."""
        spec = tool.get_spec()

        assert spec.name == "custom_tool"
        assert spec.category.value == "custom"
        assert "input_param" in spec.inputs
        assert "output_result" in spec.outputs

    def test_tool_execution_success(self, tool):
        """Test successful tool execution."""
        result = tool.run({
            "input_param": "test_value",
            "options": {"verbose": True}
        })

        assert isinstance(result, ExecutionResult)
        assert result.success
        assert "output_result" in result.data
        assert result.execution_time > 0
```

#### Tool Integration Testing
```python
import pytest
from deepresearch.src.utils.tool_registry import ToolRegistry

class TestToolIntegration:
    """Integration tests for tool registry and execution."""

    @pytest.fixture
    def registry(self):
        """Get tool registry instance."""
        return ToolRegistry.get_instance()

    def test_tool_registration(self, registry):
        """Test tool registration in registry."""
        tool = CustomTool()
        registry.register_tool(tool.get_spec(), tool)

        # Verify tool is registered
        assert "custom_tool" in registry.list_tools()
        spec = registry.get_tool_spec("custom_tool")
        assert spec.name == "custom_tool"

    def test_tool_execution_through_registry(self, registry):
        """Test tool execution through registry."""
        tool = CustomTool()
        registry.register_tool(tool.get_spec(), tool)

        result = registry.execute_tool("custom_tool", {
            "input_param": "registry_test"
        })

        assert result.success
        assert result.data["output_result"] == "processed: registry_test"
```

### Testing Best Practices for Tools

#### Tool Test Organization
```python
# tests/tools/test_custom_tool.py
import pytest
from deepresearch.src.tools.custom_tool import CustomTool

class TestCustomTool:
    """Comprehensive test suite for CustomTool."""

    # Unit tests
    def test_initialization(self): ...
    def test_input_validation(self): ...
    def test_output_formatting(self): ...

    # Integration tests
    def test_registry_integration(self): ...
    def test_workflow_integration(self): ...

    # Performance tests
    def test_execution_performance(self): ...
    def test_memory_usage(self): ...
```

## Continuous Integration Testing

### CI Test Configuration
```yaml
# .github/workflows/test.yml
test:
  runs-on: ubuntu-latest
  strategy:
    matrix:
      python-version: ['3.10', '3.11']

  steps:
    - uses: actions/checkout@v4
    - uses: actions/setup-python@v4
      with:
        python-version: ${{ matrix.python-version }}

    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install -e .
        pip install -e ".[dev]"

    - name: Run tests
      run: make test

    - name: Run tests with coverage
      run: make test-cov

    - name: Upload coverage
      uses: codecov/codecov-action@v3
      with:
        file: ./coverage.xml
```

### Test Markers
```python
# Use pytest markers for test categorization
@pytest.mark.unit
def test_unit_functionality():
    """Unit test marker."""
    pass

@pytest.mark.integration
@pytest.mark.slow
async def test_integration_functionality():
    """Integration test that may be slow."""
    pass

@pytest.mark.performance
@pytest.mark.skip(reason="Requires significant resources")
async def test_performance_benchmark():
    """Performance test that may be skipped in CI."""
    pass

# Run specific marker categories
# pytest -m "unit"                    # Unit tests only
# pytest -m "integration and not slow"  # Fast integration tests
# pytest -m "not performance"         # Exclude performance tests
```

## Test Data Management

### Test Data Fixtures
```python
# tests/fixtures/test_data.py
@pytest.fixture
def sample_protein_data():
    """Sample protein data for testing."""
    return {
        "accession": "P04637",
        "name": "Cellular tumor antigen p53",
        "sequence": "MEEPQSDPSVEPPLSQETFSDLWKLLPENNVLSPLPSQAMDDLMLSPDDIEQWFTEDPGP",
        "organism": "Homo sapiens"
    }

@pytest.fixture
def sample_go_annotations():
    """Sample GO annotations for testing."""
    return [
        {
            "gene_id": "TP53",
            "go_id": "GO:0003677",
            "go_term": "DNA binding",
            "evidence_code": "IDA"
        }
    ]
```

### Test Database Setup
```python
# tests/conftest.py
@pytest.fixture(scope="session")
def test_database():
    """Set up test database."""
    # Create test database
    db_config = {
        "type": "sqlite",
        "database": ":memory:",
        "echo": False
    }

    # Initialize database
    engine = create_engine(**db_config)
    Base.metadata.create_all(engine)

    yield engine

    # Cleanup
    engine.dispose()
```

## Performance Testing

### Benchmark Tests
```python
import pytest
import time

def test_function_performance(benchmark):
    """Benchmark function performance."""
    result = benchmark(process_large_dataset, large_dataset)
    assert result is not None

def test_memory_usage():
    """Test memory usage patterns."""
    import tracemalloc

    tracemalloc.start()

    # Execute function
    result = process_data(large_input)

    current, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    # Check memory usage
    assert current < 100 * 1024 * 1024  # Less than 100MB
    assert peak < 200 * 1024 * 1024     # Peak less than 200MB
```

### Load Testing
```python
@pytest.mark.load
async def test_concurrent_execution():
    """Test concurrent execution performance."""
    # Test with multiple concurrent requests
    tasks = [
        main(question=f"Query {i}") for i in range(10)
    ]

    start_time = time.time()
    results = await asyncio.gather(*tasks)
    execution_time = time.time() - start_time

    # Check performance requirements
    assert execution_time < 60  # Complete within 60 seconds
    assert all(result.success for result in results)
```

## Debugging Tests

### Test Debugging Techniques
```python
def test_with_debugging():
    """Test with detailed debugging information."""
    # Enable debug logging
    import logging
    logging.basicConfig(level=logging.DEBUG)

    # Execute with debug information
    result = function_under_test()

    # Log intermediate results
    logger.debug(f"Intermediate result: {intermediate_value}")

    assert result.success
```

### Test Failure Analysis
```python
def test_failure_analysis():
    """Analyze test failures systematically."""
    try:
        result = await main(question="Test query")
        assert result.success
    except AssertionError as e:
        # Log failure details for debugging
        logger.error(f"Test failed: {e}")
        logger.error(f"Result data: {result.data if 'result' in locals() else 'N/A'}")
        logger.error(f"Error details: {result.error if 'result' in locals() else 'N/A'}")

        # Re-raise for test framework
        raise
```

## Test Coverage

### Coverage Requirements
```python
# Run tests with coverage
def test_coverage_requirements():
    """Ensure adequate test coverage."""
    # Aim for >80% overall coverage
    # >90% coverage for critical paths
    # 100% coverage for error conditions

    coverage = pytest.main([
        "--cov=deepresearch",
        "--cov-report=html",
        "--cov-report=term-missing",
        "--cov-fail-under=80"
    ])

    assert coverage == 0  # No test failures
```

### Coverage Exclusions
```python
# pytest.ini
[tool:pytest]
addopts = --cov=deepresearch --cov-report=html --cov-report=term-missing
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*

# Exclude certain files from coverage
[coverage:run]
omit =
    */tests/*
    */test_*.py
    */conftest.py
    deepresearch/__init__.py
    deepresearch/scripts/*
```

## Best Practices

1. **Test Early and Often**: Write tests as you develop features
2. **Keep Tests Fast**: Unit tests should run quickly (<1 second each)
3. **Test in Isolation**: Each test should be independent
4. **Use Descriptive Names**: Test names should explain what they test
5. **Test Error Conditions**: Include tests for failure cases
6. **Mock External Dependencies**: Avoid relying on external services in tests
7. **Use Fixtures**: Create reusable test data and setup
8. **Document Test Intent**: Explain why each test exists

## Troubleshooting

### Common Test Issues

**Flaky Tests:**
```python
# Use retry for flaky tests
@pytest.mark.flaky(reruns=3)
async def test_flaky_functionality():
    """Test that may occasionally fail."""
    pass
```

**Slow Tests:**
```python
# Mark slow tests to skip in fast mode
@pytest.mark.slow
async def test_slow_operation():
    """Test that takes significant time."""
    pass

# Run fast tests only
pytest -m "not slow"
```

**Resource-Intensive Tests:**
```python
# Mark tests that require significant resources
@pytest.mark.resource_intensive
async def test_large_dataset_processing():
    """Test with large datasets."""
    pass

# Run on CI with resource allocation
# pytest -m "resource_intensive" --maxfail=1
```

For more information about testing patterns and examples, see the [Contributing Guide](../development/contributing.md) and [CI/CD Guide](../development/ci-cd.md).
