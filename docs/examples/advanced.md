# Advanced Workflow Examples

This section provides advanced usage examples showcasing DeepCritical's sophisticated workflow capabilities, multi-agent coordination, and complex research scenarios.

## Multi-Flow Integration

### Comprehensive Research Pipeline
```python
import asyncio
from deepresearch.app import main

async def comprehensive_research():
    """Execute comprehensive research combining multiple flows."""

    # Multi-flow research question
    result = await main(
        question="Design and validate a novel therapeutic approach for Alzheimer's disease using AI and bioinformatics",
        flows={
            "prime": {"enabled": True},
            "bioinformatics": {"enabled": True},
            "deepsearch": {"enabled": True}
        },
        config_overrides={
            "prime": {
                "params": {
                    "adaptive_replanning": True,
                    "nested_loops": 3
                }
            },
            "bioinformatics": {
                "data_sources": {
                    "go": {"max_annotations": 500},
                    "pubmed": {"max_results": 100}
                }
            }
        }
    )

    print(f"Comprehensive research completed: {result.success}")
    if result.success:
        print(f"Key findings: {result.data['summary']}")

asyncio.run(comprehensive_research())
```

### Cross-Domain Analysis
```python
import asyncio
from deepresearch.app import main

async def cross_domain_analysis():
    """Analyze relationships between different scientific domains."""

    result = await main(
        question="How do advances in machine learning impact drug discovery and protein engineering?",
        flows={
            "prime": {"enabled": True},
            "bioinformatics": {"enabled": True},
            "deepsearch": {"enabled": True}
        },
        execution_mode="multi_level_react",
        max_iterations=5
    )

    print(f"Cross-domain analysis completed: {result.success}")

asyncio.run(cross_domain_analysis())
```

## Custom Agent Workflows

### Multi-Agent Coordination
```python
import asyncio
from deepresearch.agents import MultiAgentOrchestrator, SearchAgent, RAGAgent
from deepresearch.datatypes import AgentDependencies

async def multi_agent_workflow():
    """Demonstrate multi-agent coordination."""

    # Create agent orchestrator
    orchestrator = MultiAgentOrchestrator()

    # Add specialized agents
    orchestrator.add_agent("search", SearchAgent())
    orchestrator.add_agent("rag", RAGAgent())

    # Define workflow
    workflow = [
        {"agent": "search", "task": "Find latest ML papers"},
        {"agent": "rag", "task": "Analyze research trends"},
        {"agent": "search", "task": "Find related applications"}
    ]

    # Execute workflow
    result = await orchestrator.execute_workflow(
        initial_query="Machine learning in drug discovery",
        workflow_sequence=workflow
    )

    print(f"Multi-agent workflow completed: {result.success}")

asyncio.run(multi_agent_workflow())
```

### Agent Specialization
```python
import asyncio
from deepresearch.agents import BaseAgent, AgentType, AgentDependencies

class SpecializedAgent(BaseAgent):
    """Custom agent for specific domain expertise."""

    def __init__(self, domain: str):
        super().__init__(AgentType.CUSTOM, "anthropic:claude-sonnet-4-0")
        self.domain = domain

    async def execute(self, input_data, deps=None):
        """Execute with domain specialization."""
        # Customize execution based on domain
        if self.domain == "drug_discovery":
            return await self._drug_discovery_analysis(input_data, deps)
        elif self.domain == "protein_engineering":
            return await self._protein_engineering_analysis(input_data, deps)
        else:
            return await super().execute(input_data, deps)

async def specialized_workflow():
    """Use specialized agents for domain-specific tasks."""

    # Create domain-specific agents
    drug_agent = SpecializedAgent("drug_discovery")
    protein_agent = SpecializedAgent("protein_engineering")

    # Execute specialized analysis
    drug_result = await drug_agent.execute(
        "Analyze ML applications in drug discovery",
        AgentDependencies()
    )

    protein_result = await protein_agent.execute(
        "Design proteins for therapeutic applications",
        AgentDependencies()
    )

    print(f"Drug discovery analysis: {drug_result.success}")
    print(f"Protein engineering analysis: {protein_result.success}")

asyncio.run(specialized_workflow())
```

## Complex Configuration Scenarios

### Environment-Specific Workflows
```python
import asyncio
from deepresearch.app import main

async def environment_specific_workflow():
    """Execute workflows optimized for different environments."""

    # Development environment
    dev_result = await main(
        question="Test research workflow",
        config_name="development",
        debug=True,
        verbose_logging=True
    )

    # Production environment
    prod_result = await main(
        question="Production research analysis",
        config_name="production",
        optimization_level="high",
        caching_enabled=True
    )

    print(f"Development test: {dev_result.success}")
    print(f"Production run: {prod_result.success}")

asyncio.run(environment_specific_workflow())
```

### Batch Research Campaigns
```python
import asyncio
from deepresearch.app import main

async def batch_research_campaign():
    """Execute large-scale research campaigns."""

    # Define research campaign
    research_topics = [
        "AI in healthcare diagnostics",
        "Protein design for therapeutics",
        "Drug discovery optimization",
        "Bioinformatics data integration",
        "Machine learning interpretability"
    ]

    campaign_results = []

    for topic in research_topics:
        result = await main(
            question=topic,
            flows={
                "prime": {"enabled": True},
                "bioinformatics": {"enabled": True},
                "deepsearch": {"enabled": True}
            },
            batch_mode=True
        )
        campaign_results.append((topic, result))

    # Analyze campaign results
    success_count = sum(1 for _, result in campaign_results if result.success)
    print(f"Campaign completed: {success_count}/{len(research_topics)} successful")

asyncio.run(batch_research_campaign())
```

## Advanced Tool Integration

### Custom Tool Chains
```python
import asyncio
from deepresearch.tools import ToolRegistry

async def custom_tool_chain():
    """Create and execute custom tool chains."""

    registry = ToolRegistry.get_instance()

    # Define custom analysis chain
    tool_chain = [
        ("web_search", {
            "query": "machine learning applications",
            "num_results": 20
        }),
        ("content_extraction", {
            "urls": "web_search_results",
            "extract_metadata": True
        }),
        ("duplicate_removal", {
            "content": "content_extraction_results"
        }),
        ("quality_filtering", {
            "content": "duplicate_removal_results",
            "min_length": 500
        }),
        ("content_analysis", {
            "content": "quality_filtering_results",
            "analysis_types": ["sentiment", "topics", "entities"]
        })
    ]

    # Execute tool chain
    results = await registry.execute_tool_chain(tool_chain)

    print(f"Tool chain executed: {len(results)} steps")
    for i, result in enumerate(results):
        print(f"Step {i+1}: {'Success' if result.success else 'Failed'}")

asyncio.run(custom_tool_chain())
```

### Tool Result Processing
```python
import asyncio
from deepresearch.tools import ToolRegistry

async def tool_result_processing():
    """Process and analyze tool execution results."""

    registry = ToolRegistry.get_instance()

    # Execute multiple tools
    search_result = await registry.execute_tool("web_search", {
        "query": "AI applications",
        "num_results": 10
    })

    analysis_result = await registry.execute_tool("content_analysis", {
        "content": search_result.data,
        "analysis_types": ["topics", "sentiment"]
    })

    # Process combined results
    if search_result.success and analysis_result.success:
        combined_insights = {
            "search_summary": search_result.metadata,
            "content_analysis": analysis_result.data,
            "execution_metrics": {
                "search_time": search_result.execution_time,
                "analysis_time": analysis_result.execution_time
            }
        }

        print(f"Combined insights: {combined_insights}")

asyncio.run(tool_result_processing())
```

## Workflow State Management

### State Persistence
```python
import asyncio
from deepresearch.app import main
from deepresearch.datatypes import ResearchState

async def state_persistence_example():
    """Demonstrate workflow state persistence."""

    # Execute workflow with state tracking
    result = await main(
        question="Long-running research task",
        enable_state_persistence=True,
        state_save_interval=300,  # Save every 5 minutes
        state_file="research_state.json"
    )

    # Load and resume workflow
    if result.interrupted:
        # Resume from saved state
        resumed_result = await main(
            resume_from_state="research_state.json",
            question="Continue research task"
        )

        print(f"Workflow resumed: {resumed_result.success}")

asyncio.run(state_persistence_example())
```

### State Analysis
```python
import asyncio
import json
from deepresearch.datatypes import ResearchState

async def state_analysis_example():
    """Analyze workflow execution state."""

    # Load execution state
    with open("research_state.json", "r") as f:
        state_data = json.load(f)

    state = ResearchState(**state_data)

    # Analyze state
    analysis = {
        "total_steps": len(state.execution_history.entries),
        "successful_steps": sum(1 for entry in state.execution_history.entries if entry.success),
        "failed_steps": sum(1 for entry in state.execution_history.entries if not entry.success),
        "total_execution_time": state.execution_history.total_time,
        "agent_results": len(state.agent_results),
        "tool_outputs": len(state.tool_outputs)
    }

    print(f"State analysis: {analysis}")

asyncio.run(state_analysis_example())
```

## Performance Optimization

### Parallel Execution
```python
import asyncio
from deepresearch.app import main

async def parallel_execution():
    """Execute multiple research tasks in parallel."""

    # Define parallel tasks
    tasks = [
        main(question="Machine learning in healthcare"),
        main(question="Protein engineering advances"),
        main(question="Bioinformatics data integration"),
        main(question="AI ethics in research")
    ]

    # Execute in parallel
    results = await asyncio.gather(*tasks, return_exceptions=True)

    # Process results
    for i, result in enumerate(results):
        if isinstance(result, Exception):
            print(f"Task {i+1} failed: {result}")
        else:
            print(f"Task {i+1} completed: {result.success}")

asyncio.run(parallel_execution())
```

### Memory-Efficient Processing
```python
import asyncio
from deepresearch.app import main

async def memory_efficient_processing():
    """Execute large workflows with memory optimization."""

    result = await main(
        question="Large-scale research analysis",
        memory_optimization=True,
        chunk_size=1000,
        max_concurrent_operations=5,
        cleanup_intermediate_results=True,
        compression_enabled=True
    )

    print(f"Memory-efficient execution: {result.success}")

asyncio.run(memory_efficient_processing())
```

## Error Recovery and Resilience

### Comprehensive Error Handling
```python
import asyncio
from deepresearch.app import main

async def error_recovery_example():
    """Demonstrate comprehensive error recovery."""

    try:
        result = await main(
            question="Research task that may fail",
            error_recovery_strategy="comprehensive",
            max_retries=5,
            retry_delay=2.0,
            fallback_enabled=True
        )

        if result.success:
            print(f"Task completed: {result.data}")
        else:
            print(f"Task failed after retries: {result.error}")
            print(f"Error history: {result.error_history}")

    except Exception as e:
        print(f"Unhandled exception: {e}")
        # Implement fallback logic

asyncio.run(error_recovery_example())
```

### Graceful Degradation
```python
import asyncio
from deepresearch.app import main

async def graceful_degradation():
    """Execute workflows with graceful degradation."""

    result = await main(
        question="Complex research requiring multiple tools",
        graceful_degradation=True,
        critical_path_only=False,
        partial_results_acceptable=True
    )

    if result.partial_success:
        print(f"Partial results available: {result.partial_data}")
        print(f"Failed components: {result.failed_components}")
    elif result.success:
        print(f"Full success: {result.data}")
    else:
        print(f"Complete failure: {result.error}")

asyncio.run(graceful_degradation())
```

## Monitoring and Observability

### Execution Monitoring
```python
import asyncio
from deepresearch.app import main

async def execution_monitoring():
    """Monitor workflow execution in real-time."""

    # Enable detailed monitoring
    result = await main(
        question="Research task with monitoring",
        monitoring_enabled=True,
        progress_reporting=True,
        metrics_collection=True,
        alert_thresholds={
            "execution_time": 300,  # 5 minutes
            "memory_usage": 0.8,    # 80%
            "error_rate": 0.1       # 10%
        }
    )

    # Access monitoring data
    if result.success:
        monitoring_data = result.monitoring_data
        print(f"Execution time: {monitoring_data.execution_time}")
        print(f"Memory usage: {monitoring_data.memory_usage}")
        print(f"Tool success rate: {monitoring_data.tool_success_rate}")

asyncio.run(execution_monitoring())
```

### Performance Profiling
```python
import asyncio
from deepresearch.app import main

async def performance_profiling():
    """Profile workflow performance."""

    result = await main(
        question="Performance-intensive research task",
        profiling_enabled=True,
        detailed_metrics=True,
        bottleneck_detection=True
    )

    if result.success and result.profiling_data:
        profile = result.profiling_data
        print(f"Performance bottlenecks: {profile.bottlenecks}")
        print(f"Optimization suggestions: {profile.suggestions}")
        print(f"Resource usage patterns: {profile.resource_usage}")

asyncio.run(performance_profiling())
```

## Integration Patterns

### API Integration
```python
import asyncio
from deepresearch.app import main

async def api_integration():
    """Integrate with external APIs."""

    # Use external API data
    external_data = {
        "protein_database": "https://api.uniprot.org",
        "literature_api": "https://api.pubmed.org",
        "structure_api": "https://api.pdb.org"
    }

    result = await main(
        question="Integrate external biological data sources",
        external_apis=external_data,
        api_timeout=30,
        api_retry_attempts=3
    )

    print(f"API integration completed: {result.success}")

asyncio.run(api_integration())
```

### Database Integration
```python
import asyncio
from deepresearch.app import main

async def database_integration():
    """Integrate with research databases."""

    # Configure database connections
    db_config = {
        "neo4j": {
            "uri": "bolt://localhost:7687",
            "auth": {"user": "neo4j", "password": "password"}
        },
        "postgres": {
            "host": "localhost",
            "database": "research_db",
            "user": "researcher"
        }
    }

    result = await main(
        question="Query research database for related studies",
        database_connections=db_config,
        query_optimization=True
    )

    print(f"Database integration completed: {result.success}")

asyncio.run(database_integration())
```

## Best Practices for Advanced Usage

1. **Workflow Composition**: Combine flows strategically for complex research
2. **Resource Management**: Monitor and optimize resource usage for large workflows
3. **Error Recovery**: Implement comprehensive error handling and recovery strategies
4. **State Management**: Use state persistence for long-running workflows
5. **Performance Monitoring**: Track execution metrics and identify bottlenecks
6. **Integration Testing**: Test integrations thoroughly before production use

## Next Steps

After exploring these advanced examples:

1. **Custom Development**: Create custom agents and tools for specific domains
2. **Workflow Optimization**: Fine-tune configurations for your use cases
3. **Production Deployment**: Set up production-ready workflows
4. **Monitoring Setup**: Implement comprehensive monitoring and alerting
5. **Integration Expansion**: Connect with additional external systems

## Code Improvement Workflow Examples

### Automatic Error Correction
```python
import asyncio
from DeepResearch.src.agents.code_execution_orchestrator import CodeExecutionOrchestrator

async def automatic_error_correction():
    """Demonstrate automatic code improvement and error correction."""

    orchestrator = CodeExecutionOrchestrator()

    # This intentionally problematic request will trigger error correction
    result = await orchestrator.iterative_improve_and_execute(
        user_message="Write a Python script that reads a CSV file and calculates statistics, but make sure it handles all possible errors",
        max_iterations=3
    )

    print(f"Success: {result.success}")
    print(f"Final code has {len(result.data['final_code'])} characters")
    print(f"Improvement attempts: {result.data['iterations_used']}")

asyncio.run(automatic_error_correction())
```

### Code Analysis and Improvement
```python
import asyncio
from DeepResearch.src.agents.code_improvement_agent import CodeImprovementAgent

async def code_analysis_improvement():
    """Analyze and improve existing code."""

    agent = CodeImprovementAgent()

    # Code with intentional issues
    problematic_code = '''
def process_list(items):
    total = 0
    for item in items:
        total += item  # No error handling for non-numeric items
    return total / len(items)  # Division by zero if empty list

result = process_list([])
'''

    # Analyze the error
    analysis = await agent.analyze_error(
        code=problematic_code,
        error_message="ZeroDivisionError: division by zero",
        language="python"
    )

    print(f"Error Type: {analysis['error_type']}")
    print(f"Root Cause: {analysis['root_cause']}")

    # Improve the code
    improvement = await agent.improve_code(
        original_code=problematic_code,
        error_message="ZeroDivisionError: division by zero",
        language="python",
        improvement_focus="robustness"
    )

    print(f"Improved Code:\n{improvement['improved_code']}")

asyncio.run(code_analysis_improvement())
```

### Multi-Language Code Generation with Error Handling
```python
import asyncio
from DeepResearch.src.agents.code_execution_orchestrator import CodeExecutionOrchestrator

async def multi_language_generation():
    """Generate and improve code in multiple languages."""

    orchestrator = CodeExecutionOrchestrator()

    # Python script with error correction
    python_result = await orchestrator.iterative_improve_and_execute(
        "Create a Python function that safely parses JSON data from a file",
        code_type="python",
        max_iterations=3
    )

    # Bash script with error correction
    bash_result = await orchestrator.iterative_improve_and_execute(
        "Write a bash script that checks if a directory exists and creates it if not",
        code_type="bash",
        max_iterations=2
    )

    print("Python script result:", python_result.success)
    print("Bash script result:", bash_result.success)

asyncio.run(multi_language_generation())
```

### Performance Optimization and Code Enhancement
```python
import asyncio
from DeepResearch.src.agents.code_improvement_agent import CodeImprovementAgent

async def performance_optimization():
    """Optimize code for better performance."""

    agent = CodeImprovementAgent()

    # Inefficient code
    slow_code = '''
def fibonacci_recursive(n):
    if n <= 1:
        return n
    return fibonacci_recursive(n-1) + fibonacci_recursive(n-2)

# Calculate multiple values (very inefficient)
results = [fibonacci_recursive(i) for i in range(35)]
'''

    # Optimize for performance
    optimization = await agent.improve_code(
        original_code=slow_code,
        error_message="",  # No error, just optimization
        language="python",
        improvement_focus="optimize"
    )

    print("Optimization completed")
    print(f"Optimized code:\n{optimization['improved_code']}")

asyncio.run(performance_optimization())
```

### Integration with Code Execution Workflow
```bash
# Complete workflow with automatic error correction
uv run deepresearch \
  flows.code_execution.enabled=true \
  question="Create a data analysis script that reads CSV, performs statistical analysis, and generates plots" \
  flows.code_execution.improvement.enabled=true \
  flows.code_execution.improvement.max_attempts=5 \
  flows.code_execution.execution.use_docker=true
```

### Advanced Error Recovery Scenarios
```python
import asyncio
from DeepResearch.src.agents.code_execution_orchestrator import CodeExecutionOrchestrator

async def advanced_error_recovery():
    """Handle complex error scenarios with multiple improvement attempts."""

    orchestrator = CodeExecutionOrchestrator()

    # Complex request that may require multiple iterations
    result = await orchestrator.iterative_improve_and_execute(
        user_message="""
        Write a Python script that:
        1. Downloads data from a REST API
        2. Parses and validates the JSON response
        3. Performs statistical analysis on numeric fields
        4. Saves results to both CSV and JSON formats
        5. Includes comprehensive error handling for all operations
        """,
        max_iterations=5,  # Allow more attempts for complex tasks
        enable_improvement=True
    )

    print(f"Complex task completed: {result.success}")
    if result.success:
        print(f"Final code quality: {len(result.data['improvement_history'])} improvements made")
        print("Improvement history:")
        for i, improvement in enumerate(result.data['improvement_history'], 1):
            print(f"  {i}. {improvement['explanation'][:100]}...")

asyncio.run(advanced_error_recovery())
```

For more specialized examples, see [Bioinformatics Tools](../user-guide/tools/bioinformatics.md) and [Integration Examples](../examples/basic.md).
