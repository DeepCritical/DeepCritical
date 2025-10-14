# Agents API

This page provides comprehensive documentation for the DeepCritical agent system, including specialized agents for different research tasks.

## Agent Framework

### Agent Types

The `AgentType` enum defines the different types of agents available in the system:

- `SEARCH`: Web search and information retrieval
- `RAG`: Retrieval-augmented generation
- `BIOINFORMATICS`: Biological data analysis
- `EXECUTOR`: Tool execution and workflow management
- `EVALUATOR`: Result evaluation and quality assessment

### Agent Dependencies

`AgentDependencies` provides the configuration and context needed for agent execution, including model settings, API keys, and tool configurations.

## Specialized Agents

### Code Execution Agents

#### CodeGenerationAgent
The `CodeGenerationAgent` uses AI models to generate code from natural language descriptions, supporting multiple programming languages including Python and Bash.

#### CodeExecutionAgent
The `CodeExecutionAgent` safely executes generated code in isolated environments with comprehensive error handling and resource management.

#### CodeExecutionAgentSystem
The `CodeExecutionAgentSystem` coordinates code generation and execution workflows with integrated error recovery and improvement capabilities.

### Code Improvement Agent

The Code Improvement Agent provides intelligent error analysis and code enhancement capabilities for automatic error correction and code optimization.

#### CodeImprovementAgent

::: DeepResearch.src.agents.code_improvement_agent.CodeImprovementAgent
        handler: python
        options:
          docstring_style: google
          show_category_heading: true

The `CodeImprovementAgent` analyzes execution errors and provides intelligent code corrections and optimizations with multi-step improvement tracking.

**Key Capabilities:**
- **Intelligent Error Analysis**: Analyzes execution errors and identifies root causes
- **Automatic Code Correction**: Generates corrected code based on error analysis
- **Iterative Improvement**: Multi-step improvement process with configurable retry logic
- **Multi-Language Support**: Support for Python, Bash, and other programming languages
- **Performance Optimization**: Code efficiency and resource usage improvements
- **Robustness Enhancement**: Error handling and input validation improvements

**Usage:**
```python
from DeepResearch.src.agents.code_improvement_agent import CodeImprovementAgent

# Initialize agent
agent = CodeImprovementAgent(
    model_name="anthropic:claude-sonnet-4-0",
    max_improvement_attempts=3
)

# Analyze error
analysis = await agent.analyze_error(
    code="print(undefined_var)",
    error_message="NameError: name 'undefined_var' is not defined",
    language="python"
)
print(f"Error type: {analysis['error_type']}")
print(f"Root cause: {analysis['root_cause']}")

# Improve code
improvement = await agent.improve_code(
    original_code="print(undefined_var)",
    error_message="NameError: name 'undefined_var' is not defined",
    language="python",
    improvement_focus="fix_errors"
)
print(f"Improved code: {improvement['improved_code']}")

# Iterative improvement
result = await agent.iterative_improve(
    code="def divide(a, b): return a / b\nresult = divide(10, 0)",
    language="python",
    test_function=my_execution_test,
    max_iterations=3
)
if result["success"]:
    print(f"Final working code: {result['final_code']}")
```

#### Error Analysis Methods

**analyze_error()**
- Analyzes execution errors and provides detailed insights
- Returns error type, root cause, impact assessment, and recommendations

**improve_code()**
- Generates improved code based on error analysis
- Supports different improvement focuses (error fixing, optimization, robustness)

**iterative_improve()**
- Performs multi-step improvement until code works or max attempts reached
- Includes comprehensive improvement history tracking

### Multi-Agent Orchestrator

#### AgentOrchestrator
The AgentOrchestrator provides coordination for multiple specialized agents in complex workflows.

### Code Execution Orchestrator

The Code Execution Orchestrator provides high-level coordination for code generation, execution, and improvement workflows.

#### CodeExecutionOrchestrator

::: DeepResearch.src.agents.code_execution_orchestrator.CodeExecutionOrchestrator
        handler: python
        options:
          docstring_style: google
          show_category_heading: true

The `CodeExecutionOrchestrator` provides high-level coordination for complete code generation, execution, and improvement workflows with automatic error recovery and intelligent retry logic.

**Key Methods:**

**analyze_and_improve_code()**
- Single-step error analysis and code improvement
- Returns analysis results and improved code with detailed explanations
- Supports contextual error information and language-specific fixes

**iterative_improve_and_execute()**
- Full iterative improvement workflow with automatic error correction
- Generates → Tests → Improves → Retries cycle with configurable limits
- Includes comprehensive improvement history and performance tracking
- Supports multiple programming languages (Python, Bash, etc.)

**process_message_to_command_log()**
- End-to-end natural language to executable code conversion
- Automatic error detection and correction during execution
- Returns detailed execution logs and improvement summaries

### PRIME Agents

#### ParserAgent
The ParserAgent analyzes research questions and extracts key scientific intent and requirements for optimal tool selection and workflow planning.

#### PlannerAgent
The PlannerAgent creates detailed execution plans based on parsed research queries and available tools.

#### ExecutorAgent
The ExecutorAgent executes planned research workflows and coordinates tool interactions.

### Research Agents

#### SearchAgent
The SearchAgent provides web search and information retrieval capabilities for research tasks.

#### RAGAgent
The RAGAgent implements Retrieval-Augmented Generation for knowledge-intensive tasks.

#### EvaluatorAgent
The EvaluatorAgent provides result evaluation and quality assessment capabilities.

### Bioinformatics Agents

#### BioinformaticsAgent
The BioinformaticsAgent specializes in biological data analysis and multi-source data fusion.

### DeepSearch Agents

#### DeepSearchAgent
The DeepSearchAgent provides advanced web research with reflection and iterative search strategies.

## Agent Configuration

### Agent Dependencies Configuration

```python
from DeepResearch.src.datatypes.agents import AgentDependencies

# Configure agent dependencies
deps = AgentDependencies(
    model_name="anthropic:claude-sonnet-4-0",
    api_keys={
        "anthropic": "your-api-key",
        "openai": "your-openai-key"
    },
    config={
        "temperature": 0.7,
        "max_tokens": 2000
    }
)
```

### Code Execution Configuration

```python
from DeepResearch.src.agents.code_execution_orchestrator import CodeExecutionConfig

# Configure code execution orchestrator
config = CodeExecutionConfig(
    generation_model="anthropic:claude-sonnet-4-0",
    use_docker=True,
    max_retries=3,
    max_improvement_attempts=3,
    enable_improvement=True,
    execution_timeout=60.0
)
```

## Agent Execution Patterns

### Basic Agent Execution
```python
# Execute agent directly
result = await agent.execute(
    input_data="Analyze this research question",
    deps=agent_dependencies
)

if result.success:
    print(f"Result: {result.data}")
else:
    print(f"Error: {result.error}")
```

### Multi-Agent Workflow
```python
from DeepResearch.agents import AgentOrchestrator

# Create orchestrator
orchestrator = AgentOrchestrator()

# Add agents to workflow
orchestrator.add_agent("parser", ParserAgent())
orchestrator.add_agent("planner", PlannerAgent())
orchestrator.add_agent("executor", ExecutorAgent())

# Execute workflow
result = await orchestrator.execute_workflow(
    initial_query="Complex research task",
    workflow_sequence=[
        {"agent": "parser", "task": "Parse query"},
        {"agent": "planner", "task": "Create plan"},
        {"agent": "executor", "task": "Execute plan"}
    ]
)
```

### Code Improvement Workflow
```python
from DeepResearch.src.agents.code_execution_orchestrator import CodeExecutionOrchestrator

# Initialize orchestrator
orchestrator = CodeExecutionOrchestrator()

# Execute with automatic error correction
result = await orchestrator.iterative_improve_and_execute(
    user_message="Write a Python function that calculates factorial",
    max_iterations=3
)

print(f"Final successful code: {result.data['final_code']}")
print(f"Improvement attempts: {result.data['iterations_used']}")
```

## Error Handling

### Agent Error Types

- **ExecutionError**: Agent execution failed
- **DependencyError**: Required dependencies not available
- **TimeoutError**: Agent execution timed out
- **ValidationError**: Input validation failed
- **ModelError**: AI model API errors

### Error Recovery

```python
# Configure error recovery
agent_config = {
    "max_retries": 3,
    "retry_delay": 1.0,
    "fallback_agents": ["backup_agent"],
    "error_logging": True
}

# Execute with error recovery
result = await agent.execute_with_recovery(
    input_data="Task that might fail",
    deps=deps,
    recovery_config=agent_config
)
```

## Performance Optimization

### Agent Pooling
```python
# Create agent pool for high-throughput tasks
agent_pool = AgentPool(
    agent_class=SearchAgent,
    pool_size=10,
    preload_models=True
)

# Execute multiple tasks concurrently
results = await agent_pool.execute_batch([
    "Query 1", "Query 2", "Query 3"
])
```

### Caching and Memoization
```python
# Enable result caching
agent.enable_caching(
    cache_backend="redis",
    ttl_seconds=3600
)

# Execute with caching
result = await agent.execute_cached(
    input_data="Frequently asked question",
    cache_key="faq_1"
)
```

## Testing Agents

### Unit Testing Agents
```python
import pytest
from unittest.mock import AsyncMock

def test_agent_execution():
    agent = SearchAgent()
    mock_deps = AgentDependencies()

    # Mock external dependencies
    with patch('agent.external_api_call') as mock_api:
        mock_api.return_value = {"results": "mock data"}

        result = await agent.execute("test query", mock_deps)

        assert result.success
        assert result.data == {"results": "mock data"}
```

### Integration Testing
```python
@pytest.mark.integration
async def test_agent_integration():
    agent = BioinformaticsAgent()

    # Test with real dependencies
    result = await agent.execute(
        "Analyze TP53 gene function",
        deps=real_dependencies
    )

    assert result.success
    assert "gene_function" in result.data
```

## Best Practices

1. **Type Safety**: Use proper type annotations for all agent methods
2. **Error Handling**: Implement comprehensive error handling and recovery
3. **Configuration**: Use configuration files for agent parameters
4. **Testing**: Write both unit and integration tests for agents
5. **Documentation**: Document agent capabilities and usage patterns
6. **Performance**: Monitor and optimize agent execution performance
7. **Security**: Validate inputs and handle sensitive data appropriately

## Related Documentation

- [Tool Registry](../user-guide/tools/registry.md) - Tool management and execution
- [Workflow Documentation](../flows/index.md) - State machine workflows
- [Configuration Guide](../getting-started/configuration.md) - Agent configuration
- [Testing Guide](../development/testing.md) - Agent testing patterns
