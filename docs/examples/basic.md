# Basic Usage Examples

This section provides basic usage examples to help you get started with DeepCritical quickly.

## Simple Research Query

The most basic way to use DeepCritical is with a simple research question:

```python
import asyncio
from deepresearch.app import main

async def basic_example():
    # Simple research query
    result = await main(question="What is machine learning?")

    print(f"Research completed: {result.success}")
    print(f"Answer: {result.data}")

# Run the example
asyncio.run(basic_example())
```

Command line equivalent:
```bash
uv run deepresearch question="What is machine learning?"
```

## Flow-Specific Examples

### PRIME Flow Example
```python
import asyncio
from deepresearch.app import main

async def prime_example():
    # Enable PRIME flow for protein engineering
    result = await main(
        question="Design a therapeutic antibody for SARS-CoV-2 spike protein",
        flows_prime_enabled=True
    )

    print(f"Design completed: {result.success}")
    if result.success:
        print(f"Antibody design: {result.data}")

asyncio.run(prime_example())
```

### Bioinformatics Flow Example
```python
import asyncio
from deepresearch.app import main

async def bioinformatics_example():
    # Enable bioinformatics flow for gene analysis
    result = await main(
        question="What is the function of TP53 gene based on GO annotations and recent literature?",
        flows_bioinformatics_enabled=True
    )

    print(f"Analysis completed: {result.success}")
    if result.success:
        print(f"Gene function: {result.data}")

asyncio.run(bioinformatics_example())
```

### DeepSearch Flow Example
```python
import asyncio
from deepresearch.app import main

async def deepsearch_example():
    # Enable DeepSearch for web research
    result = await main(
        question="Latest advances in quantum computing 2024",
        flows_deepsearch_enabled=True
    )

    print(f"Research completed: {result.success}")
    if result.success:
        print(f"Advances summary: {result.data}")

asyncio.run(deepsearch_example())
```

## Configuration-Based Examples

### Using Configuration Files
```python
import asyncio
from deepresearch.app import main

async def config_example():
    # Use specific configuration
    result = await main(
        question="Machine learning in drug discovery",
        config_name="config_with_modes"
    )

    print(f"Analysis completed: {result.success}")

asyncio.run(config_example())
```

Command line equivalent:
```bash
uv run deepresearch --config-name=config_with_modes question="Machine learning in drug discovery"
```

### Custom Configuration
```python
import asyncio
from deepresearch.app import main

async def custom_config_example():
    # Custom configuration overrides
    result = await main(
        question="Protein structure analysis",
        flows_prime_enabled=True,
        flows_prime_params_adaptive_replanning=True,
        flows_prime_params_manual_confirmation=False
    )

    print(f"Analysis completed: {result.success}")

asyncio.run(custom_config_example())
```

## Batch Processing

### Multiple Questions
```python
import asyncio
from deepresearch.app import main

async def batch_example():
    # Process multiple questions
    questions = [
        "What is machine learning?",
        "How does deep learning work?",
        "What are the applications of AI?"
    ]

    results = []
    for question in questions:
        result = await main(question=question)
        results.append((question, result))

    # Display results
    for question, result in results:
        print(f"Q: {question}")
        print(f"A: {result.data if result.success else 'Failed'}")
        print("---")

asyncio.run(batch_example())
```

### Batch Configuration
```python
import asyncio
from deepresearch.app import main

async def batch_config_example():
    # Use batch configuration for multiple runs
    result = await main(
        question="Batch research questions",
        config_name="batch_config",
        app_mode="multi_level_react"
    )

    print(f"Batch completed: {result.success}")

asyncio.run(batch_config_example())
```

## Error Handling

### Basic Error Handling
```python
import asyncio
from deepresearch.app import main

async def error_handling_example():
    try:
        result = await main(question="Invalid research question")

        if result.success:
            print(f"Success: {result.data}")
        else:
            print(f"Error: {result.error}")
            print(f"Error type: {result.error_type}")

    except Exception as e:
        print(f"Exception occurred: {e}")
        # Handle unexpected errors

asyncio.run(error_handling_example())
```

### Retry Logic
```python
import asyncio
from deepresearch.app import main

async def retry_example():
    # Configure retry behavior
    result = await main(
        question="Research question",
        retries=3,
        retry_delay=1.0
    )

    print(f"Final result: {'Success' if result.success else 'Failed'}")

asyncio.run(retry_example())
```

## Output Processing

### Accessing Results
```python
import asyncio
from deepresearch.app import main

async def results_example():
    result = await main(question="Machine learning applications")

    if result.success:
        # Access different result components
        answer = result.data
        metadata = result.metadata
        execution_time = result.execution_time

        print(f"Answer: {answer}")
        print(f"Metadata: {metadata}")
        print(f"Execution time: {execution_time}s")

asyncio.run(results_example())
```

### Saving Results
```python
import asyncio
import json
from deepresearch.app import main

async def save_results_example():
    result = await main(question="Research topic")

    if result.success:
        # Save results to file
        output = {
            "question": "Research topic",
            "answer": result.data,
            "metadata": result.metadata,
            "timestamp": result.timestamp
        }

        with open("research_results.json", "w") as f:
            json.dump(output, f, indent=2)

        print("Results saved to research_results.json")

asyncio.run(save_results_example())
```

## Integration Examples

### With External APIs
```python
import asyncio
from deepresearch.app import main

async def api_integration_example():
    # Use external API results in research
    result = await main(
        question="Analyze recent API developments",
        external_data={
            "api_docs": "https://api.example.com/docs",
            "github_repo": "https://github.com/example/api"
        }
    )

    print(f"Analysis completed: {result.success}")

asyncio.run(api_integration_example())
```

### Custom Data Sources
```python
import asyncio
from deepresearch.app import main

async def custom_data_example():
    # Use custom data sources
    custom_data = {
        "datasets": ["dataset1.csv", "dataset2.csv"],
        "metadata": {"domain": "healthcare", "size": "large"}
    }

    result = await main(
        question="Analyze healthcare datasets",
        custom_data_sources=custom_data
    )

    print(f"Analysis completed: {result.success}")

asyncio.run(custom_data_example())
```

## Performance Optimization

### Fast Execution
```python
import asyncio
from deepresearch.app import main

async def fast_example():
    # Optimize for speed
    result = await main(
        question="Quick research query",
        flows_prime_params_use_fast_variants=True,
        flows_prime_params_max_iterations=3
    )

    print(f"Fast execution completed: {result.success}")

asyncio.run(fast_example())
```

### Memory Optimization
```python
import asyncio
from deepresearch.app import main

async def memory_optimized_example():
    # Optimize memory usage
    result = await main(
        question="Memory-intensive research",
        batch_size=10,
        max_concurrent_tools=3,
        cleanup_intermediate=True
    )

    print(f"Memory-optimized execution: {result.success}")

asyncio.run(memory_optimized_example())
```

## Next Steps

After trying these basic examples:

1. **Explore Flows**: Try different combinations of flows for your use case
2. **Customize Configuration**: Modify configuration files for your specific needs
3. **Advanced Examples**: Check out the [Advanced Workflows](advanced.md) section
4. **Integration Examples**: See [Advanced Examples](advanced.md) for more complex scenarios

For more detailed examples and tutorials, visit the [Examples Repository](https://github.com/DeepCritical/DeepCritical/tree/main/example) and the [Advanced Workflows](advanced.md) section.
