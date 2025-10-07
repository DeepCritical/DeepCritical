# Tools API

This page provides comprehensive documentation for the DeepCritical tool system.

## Tool Framework

### ToolRunner
Abstract base class for all DeepCritical tools.

**Key Methods:**
- `run(parameters)`: Execute tool with given parameters
- `get_spec()`: Get tool specification
- `validate_inputs(parameters)`: Validate input parameters

**Attributes:**
- `spec`: Tool specification with metadata
- `category`: Tool category for organization

### ToolSpec
Defines tool metadata and interface specification.

**Attributes:**
- `name`: Unique tool identifier
- `description`: Human-readable description
- `category`: Tool category (search, bioinformatics, etc.)
- `inputs`: Input parameter specifications
- `outputs`: Output specifications
- `metadata`: Additional tool metadata

### ToolRegistry
Central registry for tool management and execution.

**Key Methods:**
- `register_tool(spec, runner)`: Register a new tool
- `execute_tool(name, parameters)`: Execute tool by name
- `list_tools()`: List all registered tools
- `get_tools_by_category(category)`: Get tools by category

## Tool Categories

DeepCritical organizes tools into logical categories:

- **KNOWLEDGE_QUERY**: Information retrieval tools
- **SEQUENCE_ANALYSIS**: Bioinformatics sequence tools
- **STRUCTURE_PREDICTION**: Protein structure tools
- **MOLECULAR_DOCKING**: Drug-target interaction tools
- **DE_NOVO_DESIGN**: Novel molecule design tools
- **FUNCTION_PREDICTION**: Function annotation tools
- **RAG**: Retrieval-augmented generation tools
- **SEARCH**: Web and document search tools
- **ANALYTICS**: Data analysis and visualization tools

## Execution Framework

### ExecutionResult
Results from tool execution.

**Attributes:**
- `success`: Whether execution was successful
- `data`: Main result data
- `metadata`: Additional result metadata
- `execution_time`: Time taken for execution
- `error`: Error message if execution failed

### ToolRequest
Request structure for tool execution.

**Attributes:**
- `tool_name`: Name of tool to execute
- `parameters`: Input parameters for the tool
- `metadata`: Additional request metadata

### ToolResponse
Response structure from tool execution.

**Attributes:**
- `success`: Whether execution was successful
- `data`: Tool output data
- `metadata`: Response metadata
- `citations`: Source citations if applicable

## Domain Tools

### Web Search Tools

::: DeepResearch.src.tools.websearch_tools.WebSearchTool
    handler: python
    options:
      docstring_style: google
      show_category_heading: true

::: DeepResearch.src.tools.websearch_tools.ChunkedSearchTool
    handler: python
    options:
      docstring_style: google
      show_category_heading: true

### Bioinformatics Tools

::: DeepResearch.src.tools.bioinformatics_tools.GOAnnotationTool
    handler: python
    options:
      docstring_style: google
      show_category_heading: true

::: DeepResearch.src.tools.bioinformatics_tools.PubMedRetrievalTool
    handler: python
    options:
      docstring_style: google
      show_category_heading: true

### Deep Search Tools

::: DeepResearch.src.tools.deepsearch_tools.DeepSearchTool
    handler: python
    options:
      docstring_style: google
      show_category_heading: true

### RAG Tools

::: DeepResearch.src.tools.integrated_search_tools.RAGSearchTool
    handler: python
    options:
      docstring_style: google
      show_category_heading: true

## Usage Examples

### Creating a Custom Tool

```python
from deepresearch.tools import ToolRunner, ToolSpec, ToolCategory
from deepresearch.datatypes import ExecutionResult

class CustomAnalysisTool(ToolRunner):
    """Custom tool for data analysis."""

    def __init__(self):
        super().__init__(ToolSpec(
            name="custom_analysis",
            description="Performs custom data analysis",
            category=ToolCategory.ANALYTICS,
            inputs={
                "data": "dict",
                "analysis_type": "str",
                "parameters": "dict"
            },
            outputs={
                "result": "dict",
                "statistics": "dict"
            }
        ))

    def run(self, parameters: Dict[str, Any]) -> ExecutionResult:
        """Execute the analysis.

        Args:
            parameters: Tool parameters including data, analysis_type, and parameters

        Returns:
            ExecutionResult with analysis results
        """
        try:
            data = parameters["data"]
            analysis_type = parameters["analysis_type"]

            # Perform analysis
            result = self._perform_analysis(data, analysis_type, parameters)

            return ExecutionResult(
                success=True,
                data={
                    "result": result,
                    "statistics": self._calculate_statistics(result)
                }
            )
        except Exception as e:
            return ExecutionResult(
                success=False,
                error=str(e),
                error_type=type(e).__name__
            )

    def _perform_analysis(self, data: Dict, analysis_type: str, params: Dict) -> Dict:
        """Perform the actual analysis logic."""
        # Implementation here
        return {"analysis": "completed"}

    def _calculate_statistics(self, result: Dict) -> Dict:
        """Calculate statistics for the result."""
        # Implementation here
        return {"stats": "calculated"}
```

### Registering and Using Tools

```python
from deepresearch.tools import ToolRegistry

# Get global registry
registry = ToolRegistry.get_instance()

# Register custom tool
registry.register_tool(
    tool_spec=CustomAnalysisTool().get_spec(),
    tool_runner=CustomAnalysisTool()
)

# Use the tool
result = registry.execute_tool("custom_analysis", {
    "data": {"key": "value"},
    "analysis_type": "statistical",
    "parameters": {"confidence": 0.95}
})

if result.success:
    print(f"Analysis result: {result.data}")
else:
    print(f"Analysis failed: {result.error}")
```

### Tool Categories and Organization

```python
from deepresearch.tools import ToolCategory

# Available categories
categories = [
    ToolCategory.KNOWLEDGE_QUERY,    # Information retrieval
    ToolCategory.SEQUENCE_ANALYSIS,  # Bioinformatics sequence tools
    ToolCategory.STRUCTURE_PREDICTION, # Protein structure tools
    ToolCategory.MOLECULAR_DOCKING,  # Drug-target interaction
    ToolCategory.DE_NOVO_DESIGN,     # Novel molecule design
    ToolCategory.FUNCTION_PREDICTION, # Function annotation
    ToolCategory.RAG,               # Retrieval-augmented generation
    ToolCategory.SEARCH,            # Web and document search
    ToolCategory.ANALYTICS,         # Data analysis and visualization
    ToolCategory.CODE_EXECUTION,    # Code execution environments
]
```
