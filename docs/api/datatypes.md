# Data Types API

This page provides comprehensive documentation for DeepCritical's data type system, including Pydantic models, type definitions, and data validation schemas.

## Core Data Types

### Agent Framework Types

#### AgentRunResponse
Response structure from agent execution.

```python
@dataclass
class AgentRunResponse:
    """Response from agent execution."""

    messages: List[ChatMessage]
    """List of messages in the conversation."""

    data: Optional[Dict[str, Any]] = None
    """Optional structured data from agent execution."""

    metadata: Optional[Dict[str, Any]] = None
    """Optional metadata about the execution."""

    success: bool = True
    """Whether the agent execution was successful."""

    error: Optional[str] = None
    """Error message if execution failed."""

    execution_time: float = 0.0
    """Time taken for execution in seconds."""
```

#### ChatMessage
Message format for agent communication.

```python
@dataclass
class ChatMessage:
    """A message in an agent conversation."""

    role: Role
    """The role of the message sender."""

    contents: List[Content]
    """The content of the message."""

    metadata: Optional[Dict[str, Any]] = None
    """Optional metadata about the message."""
```

#### Role
Enumeration of message roles.

```python
class Role(Enum):
    """Message role enumeration."""

    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"
```

#### Content Types
Base classes for message content.

```python
@dataclass
class Content:
    """Base class for message content."""
    pass

@dataclass
class TextContent(Content):
    """Text content for messages."""

    text: str
    """The text content."""

@dataclass
class ImageContent(Content):
    """Image content for messages."""

    url: str
    """URL of the image."""

    alt_text: Optional[str] = None
    """Alternative text for the image."""
```

### Research Types

#### ResearchState
Main state object for research workflows.

```python
@dataclass
class ResearchState:
    """Main state for research workflow execution."""

    question: str
    """The research question being addressed."""

    plan: List[str] = field(default_factory=list)
    """List of planned research steps."""

    agent_results: Dict[str, Any] = field(default_factory=dict)
    """Results from agent executions."""

    tool_outputs: Dict[str, Any] = field(default_factory=dict)
    """Outputs from tool executions."""

    execution_history: ExecutionHistory = field(default_factory=lambda: ExecutionHistory())
    """History of workflow execution."""

    config: DictConfig = None
    """Hydra configuration object."""

    metadata: Dict[str, Any] = field(default_factory=dict)
    """Additional metadata."""

    status: ExecutionStatus = ExecutionStatus.PENDING
    """Current execution status."""
```

#### ResearchOutcome
Result structure for research execution.

```python
@dataclass
class ResearchOutcome:
    """Outcome of research execution."""

    success: bool
    """Whether the research was successful."""

    data: Optional[Dict[str, Any]] = None
    """Main research data and results."""

    metadata: Optional[Dict[str, Any]] = None
    """Metadata about the research execution."""

    error: Optional[str] = None
    """Error message if research failed."""

    execution_time: float = 0.0
    """Total execution time in seconds."""

    agent_results: Dict[str, AgentResult] = field(default_factory=dict)
    """Results from individual agents."""

    tool_outputs: Dict[str, Any] = field(default_factory=dict)
    """Outputs from tools used."""
```

#### ExecutionHistory
Tracking of workflow execution steps.

```python
@dataclass
class ExecutionHistory:
    """History of workflow execution steps."""

    entries: List[ExecutionHistoryEntry] = field(default_factory=list)
    """List of execution history entries."""

    total_time: float = 0.0
    """Total execution time."""

    start_time: Optional[datetime] = None
    """When execution started."""

    end_time: Optional[datetime] = None
    """When execution ended."""

    def add_entry(self, entry: ExecutionHistoryEntry) -> None:
        """Add an entry to the history."""
        self.entries.append(entry)
        if entry.execution_time:
            self.total_time += entry.execution_time

    def get_entries_by_type(self, entry_type: str) -> List[ExecutionHistoryEntry]:
        """Get entries filtered by type."""
        return [e for e in self.entries if e.entry_type == entry_type]

    def get_successful_entries(self) -> List[ExecutionHistoryEntry]:
        """Get entries that were successful."""
        return [e for e in self.entries if e.success]
```

### Agent Types

#### AgentResult
Result structure from agent execution.

```python
@dataclass
class AgentResult:
    """Result from agent execution."""

    success: bool
    """Whether the agent execution was successful."""

    data: Optional[Any] = None
    """Main result data."""

    metadata: Optional[Dict[str, Any]] = None
    """Metadata about the execution."""

    error: Optional[str] = None
    """Error message if execution failed."""

    execution_time: float = 0.0
    """Time taken for execution."""

    agent_type: AgentType = AgentType.UNKNOWN
    """Type of agent that produced this result."""
```

#### AgentDependencies
Configuration and dependencies for agent execution.

```python
@dataclass
class AgentDependencies:
    """Dependencies and configuration for agent execution."""

    model_name: str = "anthropic:claude-sonnet-4-0"
    """Name of the LLM model to use."""

    api_keys: Dict[str, str] = field(default_factory=dict)
    """API keys for external services."""

    config: Dict[str, Any] = field(default_factory=dict)
    """Additional configuration parameters."""

    tools: List[str] = field(default_factory=list)
    """List of tool names to make available."""

    context: Optional[Dict[str, Any]] = None
    """Additional context for agent execution."""

    timeout: float = 60.0
    """Timeout for agent execution in seconds."""
```

### Tool Types

#### ToolSpec
Specification for tool metadata and interface.

```python
@dataclass
class ToolSpec:
    """Specification for a tool's interface and metadata."""

    name: str
    """Unique name of the tool."""

    description: str
    """Human-readable description of the tool."""

    category: str = "general"
    """Category this tool belongs to."""

    inputs: Dict[str, str] = field(default_factory=dict)
    """Input parameter specifications."""

    outputs: Dict[str, str] = field(default_factory=dict)
    """Output specifications."""

    metadata: Dict[str, Any] = field(default_factory=dict)
    """Additional metadata."""

    version: str = "1.0.0"
    """Version of the tool specification."""

    author: Optional[str] = None
    """Author of the tool."""

    license: Optional[str] = None
    """License for the tool."""
```

#### ExecutionResult
Result structure from tool execution.

```python
@dataclass
class ExecutionResult:
    """Result from tool execution."""

    success: bool
    """Whether the tool execution was successful."""

    data: Optional[Any] = None
    """Main result data."""

    metadata: Optional[Dict[str, Any]] = None
    """Metadata about the execution."""

    execution_time: float = 0.0
    """Time taken for execution."""

    error: Optional[str] = None
    """Error message if execution failed."""

    error_type: Optional[str] = None
    """Type of error that occurred."""

    citations: List[Dict[str, Any]] = field(default_factory=list)
    """Source citations for the result."""
```

#### ToolRequest
Request structure for tool execution.

```python
@dataclass
class ToolRequest:
    """Request to execute a tool."""

    tool_name: str
    """Name of the tool to execute."""

    parameters: Dict[str, Any] = field(default_factory=dict)
    """Parameters to pass to the tool."""

    metadata: Dict[str, Any] = field(default_factory=dict)
    """Additional metadata for the request."""

    timeout: Optional[float] = None
    """Timeout for tool execution."""

    priority: int = 0
    """Priority of the request (higher numbers = higher priority)."""
```

#### ToolResponse
Response structure from tool execution.

```python
@dataclass
class ToolResponse:
    """Response from tool execution."""

    success: bool
    """Whether the tool execution was successful."""

    data: Optional[Any] = None
    """Result data from the tool."""

    metadata: Dict[str, Any] = field(default_factory=dict)
    """Metadata about the execution."""

    citations: List[Dict[str, Any]] = field(default_factory=list)
    """Source citations."""

    execution_time: float = 0.0
    """Time taken for execution."""

    error: Optional[str] = None
    """Error message if execution failed."""
```

### Bioinformatics Types

#### GOAnnotation
Gene Ontology annotation data structure.

```python
@dataclass
class GOAnnotation:
    """Gene Ontology annotation."""

    gene_id: str
    """Gene identifier."""

    go_id: str
    """GO term identifier."""

    go_term: str
    """GO term description."""

    evidence_code: str
    """Evidence code for the annotation."""

    aspect: str
    """GO aspect (P, F, or C)."""

    source: str = "GO"
    """Source of the annotation."""

    confidence_score: Optional[float] = None
    """Confidence score for the annotation."""
```

#### PubMedPaper
PubMed paper data structure.

```python
@dataclass
class PubMedPaper:
    """PubMed paper information."""

    pmid: str
    """PubMed ID."""

    title: str
    """Paper title."""

    abstract: Optional[str] = None
    """Paper abstract."""

    authors: List[str] = field(default_factory=list)
    """List of authors."""

    journal: Optional[str] = None
    """Journal name."""

    publication_date: Optional[str] = None
    """Publication date."""

    doi: Optional[str] = None
    """Digital Object Identifier."""

    keywords: List[str] = field(default_factory=list)
    """Paper keywords."""

    relevance_score: Optional[float] = None
    """Relevance score for the query."""
```

#### FusedDataset
Fused dataset from multiple bioinformatics sources.

```python
@dataclass
class FusedDataset:
    """Fused dataset from multiple bioinformatics sources."""

    gene_id: str
    """Primary gene identifier."""

    annotations: List[GOAnnotation] = field(default_factory=list)
    """GO annotations."""

    publications: List[PubMedPaper] = field(default_factory=list)
    """Related publications."""

    expression_data: Dict[str, Any] = field(default_factory=dict)
    """Expression data from various sources."""

    quality_score: float = 0.0
    """Overall quality score for the fused data."""

    sources_used: List[str] = field(default_factory=list)
    """List of data sources used."""

    fusion_metadata: Dict[str, Any] = field(default_factory=dict)
    """Metadata about the fusion process."""
```

### Code Execution Types

#### CodeExecutionWorkflowState

::: DeepResearch.src.statemachines.code_execution_workflow.CodeExecutionWorkflowState
        handler: python
        options:
          docstring_style: google
          show_category_heading: true

#### CodeBlock

::: DeepResearch.src.datatypes.coding_base.CodeBlock
        handler: python
        options:
          docstring_style: google
          show_category_heading: true

#### CodeResult

::: DeepResearch.src.datatypes.coding_base.CodeResult
        handler: python
        options:
          docstring_style: google
          show_category_heading: true

#### CodeExecutionConfig

::: DeepResearch.src.datatypes.coding_base.CodeExecutionConfig
        handler: python
        options:
          docstring_style: google
          show_category_heading: true

#### CodeExecutor

::: DeepResearch.src.datatypes.coding_base.CodeExecutor
        handler: python
        options:
          docstring_style: google
          show_category_heading: true

#### CodeExtractor

::: DeepResearch.src.datatypes.coding_base.CodeExtractor
        handler: python
        options:
          docstring_style: google
          show_category_heading: true

### Validation and Error Types

#### ValidationResult
Result from data validation.

```python
@dataclass
class ValidationResult:
    """Result from data validation."""

    valid: bool
    """Whether the data is valid."""

    errors: List[str] = field(default_factory=list)
    """List of validation errors."""

    warnings: List[str] = field(default_factory=list)
    """List of validation warnings."""

    metadata: Dict[str, Any] = field(default_factory=dict)
    """Additional validation metadata."""
```

#### ErrorInfo
Structured error information.

```python
@dataclass
class ErrorInfo:
    """Structured error information."""

    error_type: str
    """Type of error."""

    message: str
    """Error message."""

    details: Optional[Dict[str, Any]] = None
    """Additional error details."""

    stack_trace: Optional[str] = None
    """Stack trace if available."""

    timestamp: datetime = field(default_factory=datetime.now)
    """When the error occurred."""

    context: Optional[Dict[str, Any]] = None
    """Context information about the error."""
```

## Type Validation

### Pydantic Models

All data types use Pydantic for validation:

```python
from pydantic import BaseModel, Field, validator

class ValidatedResearchState(BaseModel):
    """Validated research state using Pydantic."""

    question: str = Field(..., min_length=1, max_length=1000)
    plan: List[str] = Field(default_factory=list)
    status: ExecutionStatus = ExecutionStatus.PENDING

    @validator('question')
    def validate_question(cls, v):
        if not v.strip():
            raise ValueError('Question cannot be empty')
        return v.strip()
```

### Type Guards

Type guards for runtime type checking:

```python
from typing import TypeGuard

def is_agent_result(obj: Any) -> TypeGuard[AgentResult]:
    """Type guard for AgentResult."""
    return (
        isinstance(obj, dict) and
        'success' in obj and
        isinstance(obj['success'], bool)
    )

def is_tool_response(obj: Any) -> TypeGuard[ToolResponse]:
    """Type guard for ToolResponse."""
    return (
        isinstance(obj, dict) and
        'success' in obj and
        isinstance(obj['success'], bool) and
        'data' in obj
    )
```

## Serialization

### JSON Serialization

All data types support JSON serialization:

```python
import json
from deepresearch.datatypes import AgentResult

# Create and serialize
result = AgentResult(
    success=True,
    data={"answer": "42"},
    execution_time=1.5
)

# Serialize to JSON
json_str = result.json()
print(json_str)

# Deserialize from JSON
result_dict = json.loads(json_str)
restored_result = AgentResult(**result_dict)
```

### YAML Serialization

Support for YAML serialization:

```python
import yaml
from deepresearch.datatypes import ResearchState

# Serialize to YAML
state = ResearchState(question="Test question")
yaml_str = yaml.dump(state.dict())

# Deserialize from YAML
state_dict = yaml.safe_load(yaml_str)
restored_state = ResearchState(**state_dict)
```

## Data Validation

### Schema Validation

```python
from deepresearch.datatypes.validation import DataValidator

validator = DataValidator()

# Validate agent result
result = AgentResult(success=True, data="test")
validation = validator.validate(result, AgentResult)

if validation.valid:
    print("Data is valid")
else:
    for error in validation.errors:
        print(f"Validation error: {error}")
```

### Cross-Field Validation

```python
from pydantic import root_validator

class ValidatedToolSpec(ToolSpec):
    """Tool specification with cross-field validation."""

    @root_validator
    def validate_inputs_outputs(cls, values):
        inputs = values.get('inputs', {})
        outputs = values.get('outputs', {})

        if not inputs and not outputs:
            raise ValueError("Tool must have either inputs or outputs")

        return values
```

## Best Practices

1. **Use Type Hints**: Always use proper type hints for better IDE support and validation
2. **Validate Input**: Validate all input data using Pydantic models
3. **Handle Errors**: Use structured error types for better error handling
4. **Document Types**: Provide comprehensive docstrings for all data types
5. **Test Serialization**: Ensure all types can be properly serialized/deserialized
6. **Version Compatibility**: Consider backward compatibility when changing data types

## Related Documentation

- [Agents API](agents.md) - Agent system data types
- [Tools API](tools.md) - Tool system data types
- [Configuration API](configuration.md) - Configuration data types
- [Research Types](#research-types) - Research workflow data types
