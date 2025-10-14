# AG2 Code Execution Integration for DeepCritical

This directory contains the vendored and adapted AG2 (AutoGen 2) code execution framework integrated into DeepCritical's agent system.

## Overview

The integration provides:

- **AG2-compatible code execution** with Docker and local execution modes
- **Configurable retry/error handling** for robust agent workflows
- **Pydantic AI integration** for seamless agent tool usage
- **Multiple execution backends** (Docker containers, local execution, deployment integration)
- **Code extraction from markdown** and structured text
- **Type-safe interfaces** using Pydantic models

## Key Components

### Core Classes

- `CodeBlock`: Represents executable code with language metadata
- `CodeResult`: Contains execution results (output, exit code, errors)
- `CodeExtractor`: Protocol for extracting code from various text formats
- `CodeExecutor`: Protocol for executing code blocks

### Executors

- `DockerCommandLineCodeExecutor`: Executes code in isolated Docker containers
- `LocalCommandLineCodeExecutor`: Executes code locally on the host system
- `PythonCodeExecutionTool`: Specialized tool for Python code with retry logic

### Extractors

- `MarkdownCodeExtractor`: Extracts code blocks from markdown-formatted text

## Usage Examples

### Basic Python Code Execution

```python
from DeepResearch.src.utils.python_code_execution import PythonCodeExecutionTool

tool = PythonCodeExecutionTool(timeout=30, use_docker=True)

result = tool.run({
    "code": "print('Hello, World!')",
    "max_retries": 3,
    "timeout": 60
})

if result.success:
    print(f"Output: {result.data['output']}")
else:
    print(f"Error: {result.data['error']}")
```

### Code Blocks Execution

```python
from DeepResearch.src.utils.coding import CodeBlock, DockerCommandLineCodeExecutor

code_blocks = [
    CodeBlock(code="x = 42", language="python"),
    CodeBlock(code="print(f'x = {x}')", language="python"),
]

with DockerCommandLineCodeExecutor() as executor:
    result = executor.execute_code_blocks(code_blocks)
    print(f"Success: {result.exit_code == 0}")
    print(f"Output: {result.output}")
```

### Pydantic AI Integration

```python
from DeepResearch.src.tools.docker_sandbox import PydanticAICodeExecutionTool

tool = PydanticAICodeExecutionTool(max_retries=3, timeout=60)

# Use in agent workflows
result = await tool.execute_python_code(
    code="print('Agent-generated code')",
    max_retries=5,
    working_directory="/tmp/agent_workspace"
)
```

### Markdown Code Extraction

```python
from DeepResearch.src.utils.coding.markdown_code_extractor import MarkdownCodeExtractor

extractor = MarkdownCodeExtractor()
code_blocks = extractor.extract_code_blocks("""
Here's some code:

```python
def hello():
    return "Hello, World!"
```

And some bash:
```bash
echo "Hello from shell"
```
""")

for block in code_blocks:
    print(f"Language: {block.language}")
    print(f"Code: {block.code}")
```

## Integration with Deployment Systems

The code execution system integrates with DeepCritical's deployment infrastructure:

### Testcontainers Deployer

```python
from DeepResearch.src.utils.testcontainers_deployer import testcontainers_deployer

# Execute code in a deployed server's environment
result = await testcontainers_deployer.execute_code(
    server_name="my_server",
    code="print('Running in server environment')",
    language="python",
    max_retries=3
)
```

### Docker Compose Deployer

```python
from DeepResearch.src.utils.docker_compose_deployer import docker_compose_deployer

# Execute code blocks in compose-managed containers
result = await docker_compose_deployer.execute_code_blocks(
    server_name="my_service",
    code_blocks=[CodeBlock(code="print('Hello')", language="python")]
)
```

## Agent Workflow Integration

The system is designed for agent workflows where:

1. **Agents generate code** based on tasks or user requests
2. **Code execution happens** with configurable retry logic
3. **Errors are analyzed** and code is improved iteratively
4. **Success/failure metrics** inform agent learning

### Configurable Parameters

- `max_retries`: Maximum number of execution attempts (default: 3)
- `timeout`: Execution timeout in seconds (default: 60)
- `use_docker`: Whether to use Docker isolation (default: True)
- `working_directory`: Execution working directory
- `execution_policies`: Language-specific execution permissions

### Error Handling

The system provides comprehensive error handling:

- **Timeout detection** with configurable limits
- **Retry logic** with exponential backoff
- **Error categorization** for intelligent retry decisions
- **Resource cleanup** after execution
- **Detailed error reporting** for agent analysis

## Security Considerations

- **Docker isolation** by default for untrusted code
- **Execution policies** to restrict dangerous languages
- **Resource limits** (CPU, memory, timeout)
- **Working directory isolation**
- **Safe builtins** in Python execution

## Testing

Run the integration tests:

```bash
python example/test_ag2_integration.py
```

This will test:
- Python code execution with retry logic
- Multi-block code execution
- Markdown code extraction
- Direct executor usage
- Deployment system integration
- Agent workflow simulation

## Architecture Notes

The integration maintains compatibility with AG2 while adapting to DeepCritical's architecture:

- **Pydantic models** for type safety
- **Async/await patterns** for agent workflows
- **Registry-based tool system**
- **Hydra configuration** integration
- **Logging and monitoring** hooks

## Future Enhancements

- **Jupyter notebook execution** support
- **Multi-language REPL** environments
- **Code improvement agents** using execution feedback
- **Performance profiling** and optimization
- **Distributed execution** across multiple containers
