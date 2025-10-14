# AG2 Code Execution Integration for DeepCritical

This document describes the comprehensive integration of AG2 (AutoGen 2) code execution capabilities into the DeepCritical research agent system.

## Overview

DeepCritical now includes a fully vendored and adapted version of AG2's code execution framework, providing:

- **Multi-environment code execution** (Docker, local, Jupyter)
- **Configurable retry/error handling** for robust agent workflows
- **Pydantic AI integration** for seamless agent tool usage
- **Jupyter notebook integration** for interactive code execution
- **Python environment management** with virtual environment support
- **Type-safe interfaces** using Pydantic models

## Architecture

### Core Components

```
DeepResearch/src/
├── datatypes/
│   ├── ag_types.py              # AG2-compatible message types
│   └── coding_base.py          # Base classes and protocols for code execution
├── utils/
│   ├── code_utils.py            # Code execution utilities (execute_code, infer_lang, extract_code)
│   ├── python_code_execution.py # Python code execution tool
│   ├── coding/                  # Code execution framework
│   │   ├── base.py             # Import from datatypes.coding_base
│   │   ├── docker_commandline_code_executor.py
│   │   ├── local_commandline_code_executor.py
│   │   ├── markdown_code_extractor.py
│   │   ├── utils.py
│   │   └── __init__.py
│   ├── jupyter/                # Jupyter integration
│   │   ├── base.py
│   │   ├── jupyter_client.py
│   │   ├── jupyter_code_executor.py
│   │   └── __init__.py
│   └── environments/           # Python environment management
│       ├── python_environment.py
│       ├── system_python_environment.py
│       ├── working_directory.py
│       └── __init__.py
```

### Enhanced Deployers

The existing deployers have been enhanced with AG2 integration:

- **TestcontainersDeployer**: Now includes code execution tools for deployed servers
- **DockerComposeDeployer**: Integrated with AG2 code execution capabilities
- **DockerSandbox**: Enhanced with Pydantic AI compatibility and configurable retry logic

## Key Features

### 1. Multi-Backend Code Execution

```python
from DeepResearch.src.utils.coding import DockerCommandLineCodeExecutor, LocalCommandLineCodeExecutor
from DeepResearch.src.utils.python_code_execution import PythonCodeExecutionTool

# Docker-based execution
docker_executor = DockerCommandLineCodeExecutor()
result = docker_executor.execute_code_blocks([code_block])

# Local execution
local_executor = LocalCommandLineCodeExecutor()
result = local_executor.execute_code_blocks([code_block])

# Python-specific tool
python_tool = PythonCodeExecutionTool(use_docker=True)
result = python_tool.run({"code": "print('Hello World!')"})
```

### 2. Jupyter Integration

```python
from DeepResearch.src.utils.jupyter import JupyterConnectionInfo, JupyterCodeExecutor

# Connect to Jupyter server
conn_info = JupyterConnectionInfo(
    host="localhost",
    use_https=False,
    port=8888,
    token="your-token"
)

# Create executor
executor = JupyterCodeExecutor(conn_info)
result = executor.execute_code_blocks([code_block])
```

### 3. Python Environment Management

```python
from DeepResearch.src.utils.environments import SystemPythonEnvironment, WorkingDirectory

# System Python environment
with SystemPythonEnvironment() as env:
    result = env.execute_code("print('Hello!')", "/tmp/test.py", timeout=30)

# Working directory management
with WorkingDirectory.create_tmp() as work_dir:
    # Code runs in temporary directory
    pass
```

### 4. Pydantic AI Integration

```python
from DeepResearch.src.tools.docker_sandbox import PydanticAICodeExecutionTool

# Create tool with configurable retry logic
tool = PydanticAICodeExecutionTool(max_retries=3, timeout=60, use_docker=True)

# Execute code asynchronously
result = await tool.execute_python_code(
    code="print('Hello from Pydantic AI!')",
    max_retries=2,
    timeout=30
)
```

## Agent Integration

### Configurable Retry/Error Handling

Agents can now configure code execution behavior at the agent level:

```python
from DeepResearch.src.agents import ExecutorAgent

# Create agent with code execution capabilities
agent = ExecutorAgent(
    code_execution_config={
        "max_retries": 3,
        "timeout": 60,
        "use_docker": True,
        "retry_on_error": True
    }
)

# Agent will automatically retry failed executions
result = await agent.execute_task(task)
```

### Tool Registration

Code execution tools are automatically registered with the tool registry:

```python
from DeepResearch.src.tools.base import registry

# Register code execution tools
registry.register("python_executor", PythonCodeExecutionTool)
registry.register("docker_sandbox", DockerSandboxRunner)
registry.register("jupyter_executor", JupyterCodeExecutor)
```

## Usage Examples

### Basic Code Execution

```python
from DeepResearch.src.utils.code_utils import execute_code
from DeepResearch.src.datatypes.coding_base import CodeBlock

# Simple code execution
result = execute_code("print('Hello World!')", lang="python", use_docker=True)

# Structured code block execution
code_block = CodeBlock(
    code="def factorial(n):\n    return 1 if n <= 1 else n * factorial(n-1)\nprint(factorial(5))",
    language="python"
)

executor = LocalCommandLineCodeExecutor()
result = executor.execute_code_blocks([code_block])
```

### Agent Workflow Integration

```python
from DeepResearch.src.datatypes.agent_framework_agent import AgentRunResponse
from DeepResearch.src.utils.python_code_execution import PythonCodeExecutionTool

# In an agent workflow
async def execute_code_task(code: str, agent_context) -> AgentRunResponse:
    tool = PythonCodeExecutionTool(
        timeout=agent_context.get("timeout", 60),
        use_docker=agent_context.get("use_docker", True)
    )

    # Execute with retry logic
    max_retries = agent_context.get("max_retries", 3)
    for attempt in range(max_retries):
        try:
            result = tool.run({"code": code})
            if result.success:
                return AgentRunResponse(
                    messages=[{"role": "assistant", "content": result.data["output"]}]
                )
            elif attempt < max_retries - 1:
                # Retry logic - could improve code based on error
                improved_code = improve_code_based_on_error(code, result.error)
                code = improved_code
        except Exception as e:
            if attempt == max_retries - 1:
                return AgentRunResponse(
                    messages=[{"role": "assistant", "content": f"Execution failed: {str(e)}"}]
                )

    return AgentRunResponse(
        messages=[{"role": "assistant", "content": "Max retries exceeded"}]
    )
```

## Configuration

### Hydra Configuration

Add to your `configs/config.yaml`:

```yaml
code_execution:
  default_timeout: 60
  max_retries: 3
  use_docker: true
  jupyter:
    host: localhost
    port: 8888
    token: ${oc.env:JUPYTER_TOKEN}
  environments:
    default: system
    venv_path: ./venvs

agent:
  code_execution:
    max_retries: ${code_execution.max_retries}
    timeout: ${code_execution.default_timeout}
    use_docker: ${code_execution.use_docker}
```

## Testing

Run the integration tests:

```bash
# Basic functionality tests
python example/simple_test.py

# Comprehensive integration tests
python example/test_vendored_ag_integration.py
```

## Security Considerations

1. **Docker Execution**: All code execution can be forced to run in Docker containers for isolation
2. **Resource Limits**: Configurable timeouts and resource limits prevent runaway execution
3. **Code Validation**: Input validation prevents malicious code execution
4. **Network Isolation**: Docker containers can be run without network access

## Performance Optimization

1. **Container Reuse**: Docker containers are reused when possible
2. **Connection Pooling**: Jupyter connections are pooled for efficiency
3. **Async Execution**: All execution methods support async/await patterns
4. **Caching**: Environment setup is cached to reduce startup time

## Migration from Previous Versions

If upgrading from a previous version:

1. Update imports to use the new module structure
2. Review agent configurations for code execution settings
3. Test workflows with the new retry/error handling logic

### Import Changes

```python
# Old imports
from DeepResearch.src.utils.code_execution import CodeExecutor

# New imports
from DeepResearch.src.utils.coding import CodeExecutor
from DeepResearch.src.datatypes.coding_base import CodeBlock, CodeResult
```

## Contributing

When adding new code execution backends:

1. Extend the `CodeExecutor` protocol
2. Implement proper error handling and timeouts
3. Add comprehensive tests
4. Update documentation

## Troubleshooting

### Common Issues

1. **Docker not available**: Ensure Docker is installed and running
2. **Jupyter connection failed**: Check server URL, token, and network connectivity
3. **Import errors**: Ensure all vendored modules are properly imported
4. **Timeout errors**: Increase timeout values in configuration

### Debug Mode

Enable debug logging:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## Related Documentation

- [Pydantic AI Tools Integration](../../docs/tools/pydantic_ai_tools.md)
- [Docker Sandbox Usage](../../docs/tools/docker_sandbox.md)
- [Agent Configuration](../../docs/core/agent_configuration.md)
- [Workflow Orchestration](../../docs/flows/workflow_orchestration.md)
