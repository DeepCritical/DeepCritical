# Tool Development Guide

This guide provides comprehensive instructions for developing, testing, and integrating new tools into the DeepCritical ecosystem.

## Overview

DeepCritical's tool system is designed to be extensible, allowing researchers and developers to add new capabilities seamlessly. Tools can be written in any language and integrate with various external services and APIs.

## Tool Architecture

### Core Components

Every DeepCritical tool consists of three main components:

1. **Tool Specification**: Metadata describing the tool's interface
2. **Tool Runner**: The actual implementation that executes the tool
3. **Tool Registration**: Integration with the tool registry

### Tool Specification

The tool specification defines the tool's interface using the `ToolSpec` class:

```python
from deepresearch.src.datatypes.tools import ToolSpec, ToolCategory

tool_spec = ToolSpec(
    name="sequence_alignment",
    description="Performs pairwise or multiple sequence alignment",
    category=ToolCategory.SEQUENCE_ANALYSIS,
    inputs={
        "sequences": {
            "type": "list",
            "description": "List of DNA/RNA/protein sequences",
            "required": True,
            "schema": {
                "type": "array",
                "items": {"type": "string", "minLength": 1}
            }
        },
        "algorithm": {
            "type": "string",
            "description": "Alignment algorithm to use",
            "required": False,
            "default": "blast",
            "enum": ["blast", "clustal", "muscle", "mafft"]
        },
        "output_format": {
            "type": "string",
            "description": "Output format",
            "required": False,
            "default": "fasta",
            "enum": ["fasta", "clustal", "phylip", "nexus"]
        }
    },
    outputs={
        "alignment": {
            "type": "string",
            "description": "Aligned sequences in specified format"
        },
        "score": {
            "type": "number",
            "description": "Alignment quality score"
        },
        "metadata": {
            "type": "object",
            "description": "Additional alignment metadata",
            "properties": {
                "execution_time": {"type": "number"},
                "algorithm_version": {"type": "string"},
                "warnings": {"type": "array", "items": {"type": "string"}}
            }
        }
    },
    metadata={
        "version": "1.0.0",
        "author": "Bioinformatics Team",
        "license": "MIT",
        "tags": ["alignment", "bioinformatics", "sequence"],
        "dependencies": ["biopython", "numpy"],
        "timeout": 300,  # 5 minutes
        "memory_limit_mb": 1024,
        "gpu_required": False
    }
)
```

### Tool Runner Implementation

The tool runner implements the actual functionality:

```python
from deepresearch.src.tools.base import ToolRunner, ExecutionResult
from deepresearch.src.datatypes.tools import ToolSpec, ToolCategory
import time

class SequenceAlignmentTool(ToolRunner):
    """Tool for performing sequence alignments."""

    def __init__(self):
        super().__init__(ToolSpec(
            name="sequence_alignment",
            description="Performs pairwise or multiple sequence alignment",
            category=ToolCategory.SEQUENCE_ANALYSIS,
            # ... inputs, outputs, metadata as above
        ))

    def run(self, parameters: Dict[str, Any]) -> ExecutionResult:
        """Execute the sequence alignment."""
        start_time = time.time()

        try:
            # Extract parameters
            sequences = parameters["sequences"]
            algorithm = parameters.get("algorithm", "blast")
            output_format = parameters.get("output_format", "fasta")

            # Validate inputs
            if not sequences or len(sequences) < 2:
                return ExecutionResult(
                    success=False,
                    error="At least 2 sequences required for alignment",
                    error_type="ValidationError"
                )

            # Perform alignment
            alignment_result = self._perform_alignment(
                sequences, algorithm, output_format
            )

            execution_time = time.time() - start_time

            return ExecutionResult(
                success=True,
                data={
                    "alignment": alignment_result["alignment"],
                    "score": alignment_result["score"],
                    "metadata": {
                        "execution_time": execution_time,
                        "algorithm_version": "1.0.0",
                        "warnings": alignment_result.get("warnings", [])
                    }
                },
                execution_time=execution_time
            )

        except Exception as e:
            execution_time = time.time() - start_time
            return ExecutionResult(
                success=False,
                error=str(e),
                error_type=type(e).__name__,
                execution_time=execution_time
            )

    def _perform_alignment(self, sequences, algorithm, output_format):
        """Perform the actual alignment logic."""
        # Implementation here - would use BioPython or other alignment libraries
        # This is a simplified example

        if algorithm == "blast":
            # BLAST alignment logic
            pass
        elif algorithm == "clustal":
            # Clustal Omega alignment logic
            pass
        # ... other algorithms

        return {
            "alignment": ">seq1\nATCG...\n>seq2\nATCG...",
            "score": 85.5,
            "warnings": []
        }
```

## Development Workflow

### 1. Planning Your Tool

Before implementing a tool, consider:

- **Purpose**: What problem does this tool solve?
- **Inputs/Outputs**: What data does it need and produce?
- **Dependencies**: What external libraries or services are required?
- **Performance**: What's the expected execution time and resource usage?
- **Error Cases**: What can go wrong and how should it be handled?

### 2. Creating the Tool Specification

Start by defining a clear, comprehensive specification:

```python
def create_tool_spec() -> ToolSpec:
    """Create tool specification for a BLAST search tool."""
    return ToolSpec(
        name="blast_search",
        description="Perform BLAST sequence similarity searches",
        category=ToolCategory.SEQUENCE_ANALYSIS,
        inputs={
            "sequence": {
                "type": "string",
                "description": "Query sequence in FASTA format",
                "required": True,
                "minLength": 10,
                "maxLength": 10000
            },
            "database": {
                "type": "string",
                "description": "Target database to search",
                "required": False,
                "default": "nr",
                "enum": ["nr", "refseq", "swissprot", "pdb"]
            },
            "e_value_threshold": {
                "type": "number",
                "description": "E-value threshold for results",
                "required": False,
                "default": 1e-5,
                "minimum": 0,
                "maximum": 1
            },
            "max_results": {
                "type": "integer",
                "description": "Maximum number of results to return",
                "required": False,
                "default": 100,
                "minimum": 1,
                "maximum": 1000
            }
        },
        outputs={
            "results": {
                "type": "array",
                "description": "List of BLAST hit results",
                "items": {
                    "type": "object",
                    "properties": {
                        "accession": {"type": "string"},
                        "description": {"type": "string"},
                        "e_value": {"type": "number"},
                        "identity": {"type": "number"},
                        "alignment_length": {"type": "integer"}
                    }
                }
            },
            "search_info": {
                "type": "object",
                "description": "Search metadata and statistics",
                "properties": {
                    "database_size": {"type": "integer"},
                    "search_time": {"type": "number"},
                    "total_hits": {"type": "integer"}
                }
            }
        },
        metadata={
            "version": "2.0.0",
            "author": "NCBI Tools Team",
            "license": "Public Domain",
            "tags": ["blast", "similarity", "search", "sequence"],
            "dependencies": ["biopython", "requests"],
            "timeout": 600,  # 10 minutes
            "memory_limit_mb": 2048,
            "network_required": True
        }
    )
```

### 3. Implementing the Tool Runner

Implement the core logic with proper error handling:

```python
import requests
from Bio.Blast import NCBIWWW
from Bio.Blast import NCBIXML

class BlastSearchTool(ToolRunner):
    """NCBI BLAST search tool."""

    def __init__(self):
        super().__init__(create_tool_spec())

    def run(self, parameters: Dict[str, Any]) -> ExecutionResult:
        """Execute BLAST search."""
        start_time = time.time()

        try:
            # Extract and validate parameters
            sequence = self._validate_sequence(parameters["sequence"])
            database = parameters.get("database", "nr")
            e_threshold = parameters.get("e_value_threshold", 1e-5)
            max_results = parameters.get("max_results", 100)

            # Perform BLAST search
            result_handle = NCBIWWW.qblast(
                program="blastp" if self._is_protein(sequence) else "blastn",
                database=database,
                sequence=sequence,
                expect=e_threshold,
                hitlist_size=max_results
            )

            # Parse results
            blast_records = NCBIXML.parse(result_handle)
            results = self._parse_blast_results(blast_records, max_results)

            execution_time = time.time() - start_time

            return ExecutionResult(
                success=True,
                data={
                    "results": results,
                    "search_info": {
                        "database_size": self._get_database_size(database),
                        "search_time": execution_time,
                        "total_hits": len(results)
                    }
                },
                execution_time=execution_time
            )

        except requests.exceptions.RequestException as e:
            return ExecutionResult(
                success=False,
                error=f"Network error during BLAST search: {e}",
                error_type="NetworkError",
                execution_time=time.time() - start_time
            )
        except Exception as e:
            return ExecutionResult(
                success=False,
                error=f"BLAST search failed: {e}",
                error_type=type(e).__name__,
                execution_time=time.time() - start_time
            )

    def _validate_sequence(self, sequence: str) -> str:
        """Validate and clean input sequence."""
        # Remove FASTA header if present
        lines = sequence.strip().split('\n')
        if lines[0].startswith('>'):
            sequence = '\n'.join(lines[1:])

        # Remove whitespace and validate
        sequence = ''.join(sequence.split()).upper()

        if len(sequence) < 10:
            raise ValueError("Sequence too short (minimum 10 characters)")

        if len(sequence) > 10000:
            raise ValueError("Sequence too long (maximum 10000 characters)")

        # Validate sequence characters
        valid_chars = set('ATCGNUWSMKRYBDHVZ-')
        if not all(c in valid_chars for c in sequence):
            raise ValueError("Invalid characters in sequence")

        return sequence

    def _is_protein(self, sequence: str) -> bool:
        """Determine if sequence is protein or nucleotide."""
        # Simple heuristic: check for amino acid characters
        protein_chars = set('EFILPQXZ')
        return any(c in protein_chars for c in sequence.upper())

    def _parse_blast_results(self, blast_records, max_results):
        """Parse BLAST XML results into structured format."""
        results = []

        for blast_record in blast_records:
            for alignment in blast_record.alignments[:max_results]:
                for hsp in alignment.hsps:
                    results.append({
                        "accession": alignment.accession,
                        "description": alignment.title,
                        "e_value": hsp.expect,
                        "identity": (hsp.identities / hsp.align_length) * 100,
                        "alignment_length": hsp.align_length,
                        "query_start": hsp.query_start,
                        "query_end": hsp.query_end,
                        "subject_start": hsp.sbjct_start,
                        "subject_end": hsp.sbjct_end
                    })

                    if len(results) >= max_results:
                        break
                if len(results) >= max_results:
                    break

        return results

    def _get_database_size(self, database: str) -> int:
        """Get approximate database size."""
        # This would typically query NCBI for actual database statistics
        db_sizes = {
            "nr": 500000000,  # 500M sequences
            "refseq": 100000000,  # 100M sequences
            "swissprot": 500000,  # 500K sequences
            "pdb": 100000  # 100K sequences
        }
        return db_sizes.get(database, 0)
```

### 4. Testing Your Tool

Create comprehensive tests for your tool:

```python
import pytest
from unittest.mock import patch, MagicMock

class TestBlastSearchTool:

    @pytest.fixture
    def tool(self):
        """Create tool instance for testing."""
        return BlastSearchTool()

    def test_tool_specification(self, tool):
        """Test tool specification is correctly defined."""
        spec = tool.get_spec()

        assert spec.name == "blast_search"
        assert spec.category == ToolCategory.SEQUENCE_ANALYSIS
        assert "sequence" in spec.inputs
        assert "results" in spec.outputs

    def test_sequence_validation(self, tool):
        """Test sequence input validation."""
        # Valid sequence
        valid_seq = tool._validate_sequence("ATCGATCGATCGATCGATCG")
        assert valid_seq == "ATCGATCGATCGATCGATCG"

        # Sequence with FASTA header
        fasta_seq = ">test\nATCGATCG\nATCGATCG"
        cleaned = tool._validate_sequence(fasta_seq)
        assert cleaned == "ATCGATCGATCGATCG"

        # Invalid sequences
        with pytest.raises(ValueError, match="too short"):
            tool._validate_sequence("ATCG")

        with pytest.raises(ValueError, match="Invalid characters"):
            tool._validate_sequence("ATCGXATCG")  # X is invalid

    @patch('Bio.Blast.NCBIWWW.qblast')
    def test_successful_search(self, mock_qblast, tool):
        """Test successful BLAST search."""
        # Mock BLAST response
        mock_result = MagicMock()
        mock_qblast.return_value = mock_result

        # Mock parsing
        with patch.object(tool, '_parse_blast_results', return_value=[
            {
                "accession": "XP_001234",
                "description": "Test protein",
                "e_value": 1e-10,
                "identity": 95.5,
                "alignment_length": 100
            }
        ]):
            result = tool.run({
                "sequence": "ATCGATCGATCGATCGATCGATCGATCGATCGATCG"
            })

            assert result.success
            assert "results" in result.data
            assert len(result.data["results"]) == 1
            assert result.data["results"][0]["accession"] == "XP_001234"

    @patch('Bio.Blast.NCBIWWW.qblast')
    def test_network_error_handling(self, mock_qblast, tool):
        """Test network error handling."""
        from requests.exceptions import ConnectionError
        mock_qblast.side_effect = ConnectionError("Network timeout")

        result = tool.run({
            "sequence": "ATCGATCGATCGATCGATCGATCGATCGATCGATCG"
        })

        assert not result.success
        assert "Network error" in result.error
        assert result.error_type == "NetworkError"

    def test_protein_detection(self, tool):
        """Test protein vs nucleotide sequence detection."""
        # Nucleotide sequence
        assert not tool._is_protein("ATCGATCGATCG")

        # Protein sequence
        assert tool._is_protein("MEEPQSDPSVEPPLSQETFSDLWK")

        # Mixed/ambiguous
        assert tool._is_protein("ATCGLEUF")  # Contains E, F

    @pytest.mark.parametrize("database,expected_size", [
        ("nr", 500000000),
        ("swissprot", 500000),
        ("unknown", 0)
    ])
    def test_database_size_lookup(self, tool, database, expected_size):
        """Test database size lookup."""
        assert tool._get_database_size(database) == expected_size
```

### 5. Registering Your Tool

Register the tool with the system:

```python
from deepresearch.src.utils.tool_registry import ToolRegistry

def register_blast_tool():
    """Register the BLAST search tool."""
    registry = ToolRegistry.get_instance()

    tool = BlastSearchTool()
    registry.register_tool(tool.get_spec(), tool)

    print(f"Registered tool: {tool.get_spec().name}")

# Register during module import or application startup
register_blast_tool()
```

## Advanced Tool Features

### Asynchronous Execution

For tools that perform long-running operations:

```python
import asyncio
from deepresearch.src.tools.base import AsyncToolRunner

class AsyncBlastTool(AsyncToolRunner):
    """Asynchronous BLAST search tool."""

    async def run_async(self, parameters: Dict[str, Any]) -> ExecutionResult:
        """Execute BLAST search asynchronously."""
        # Implementation using async HTTP requests
        # This allows better concurrency and resource utilization
        pass
```

### Streaming Results

For tools that produce large amounts of data:

```python
from deepresearch.src.tools.base import StreamingToolRunner

class StreamingAlignmentTool(StreamingToolRunner):
    """Tool that streams alignment results."""

    def run_streaming(self, parameters: Dict[str, Any]):
        """Execute alignment and stream results."""
        # Yield results as they become available
        for partial_result in self._perform_incremental_alignment(parameters):
            yield partial_result
```

### Tool Dependencies

Handle tools that depend on other tools:

```python
class DependentAnalysisTool(ToolRunner):
    """Tool that depends on other tools."""

    def __init__(self, registry: ToolRegistry):
        super().__init__(tool_spec)
        self.registry = registry

    def run(self, parameters: Dict[str, Any]) -> ExecutionResult:
        # First, use a BLAST search tool
        blast_result = self.registry.execute_tool("blast_search", {
            "sequence": parameters["sequence"]
        })

        if not blast_result.success:
            return ExecutionResult(
                success=False,
                error=f"BLAST search failed: {blast_result.error}"
            )

        # Then perform analysis on the results
        analysis = self._analyze_blast_results(blast_result.data["results"])

        return ExecutionResult(success=True, data={"analysis": analysis})
```

### Tool Configuration

Support configurable tool behavior:

```python
class ConfigurableBlastTool(ToolRunner):
    """BLAST tool with runtime configuration."""

    def __init__(self, config: Dict[str, Any]):
        self.max_retries = config.get("max_retries", 3)
        self.timeout = config.get("timeout", 600)
        self.api_key = config.get("api_key")

        super().__init__(create_tool_spec())

    def run(self, parameters: Dict[str, Any]) -> ExecutionResult:
        # Use configuration in execution
        # Implementation here
        pass
```

## Tool Packaging and Distribution

### Tool Modules

Organize tools into modules:

```
deepresearch/src/tools/
├── bioinformatics/
│   ├── blast_search.py
│   ├── sequence_alignment.py
│   └── __init__.py
├── chemistry/
│   ├── molecular_docking.py
│   └── property_prediction.py
└── search/
    ├── web_search.py
    └── document_search.py
```

### Tool Discovery

Enable automatic tool discovery:

```python
# In __init__.py
from deepresearch.src.utils.tool_registry import ToolRegistry

def discover_and_register_tools():
    """Automatically discover and register tools."""
    registry = ToolRegistry.get_instance()

    # Import tool modules
    from . import bioinformatics, chemistry, search

    # Register all tools in modules
    tool_modules = [bioinformatics, chemistry, search]

    for module in tool_modules:
        for attr_name in dir(module):
            attr = getattr(module, attr_name)
            if (isinstance(attr, type) and
                issubclass(attr, ToolRunner) and
                attr != ToolRunner):
                # Create instance and register
                tool_instance = attr()
                registry.register_tool(
                    tool_instance.get_spec(),
                    tool_instance
                )

# Auto-discover tools on import
discover_and_register_tools()
```

## Performance Optimization

### Caching

Implement result caching for expensive operations:

```python
from deepresearch.src.utils.cache import ToolCache

class CachedBlastTool(ToolRunner):
    """BLAST tool with result caching."""

    def __init__(self):
        super().__init__(tool_spec)
        self.cache = ToolCache(ttl_seconds=3600)  # 1 hour cache

    def run(self, parameters: Dict[str, Any]) -> ExecutionResult:
        # Create cache key from parameters
        cache_key = self.cache.create_key(parameters)

        # Check cache first
        cached_result = self.cache.get(cache_key)
        if cached_result:
            return cached_result

        # Execute tool
        result = self._execute_blast(parameters)

        # Cache successful results
        if result.success:
            self.cache.set(cache_key, result)

        return result
```

### Resource Management

Handle resource-intensive operations properly:

```python
import psutil
import os

class ResourceAwareBlastTool(ToolRunner):
    """BLAST tool with resource monitoring."""

    def run(self, parameters: Dict[str, Any]) -> ExecutionResult:
        # Check available memory
        available_memory = psutil.virtual_memory().available / (1024 * 1024)  # MB

        if available_memory < self.get_spec().metadata.get("memory_limit_mb", 1024):
            return ExecutionResult(
                success=False,
                error="Insufficient memory for BLAST search",
                error_type="ResourceError"
            )

        # Monitor memory usage during execution
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss

        result = self._execute_blast(parameters)

        final_memory = process.memory_info().rss
        memory_used = (final_memory - initial_memory) / (1024 * 1024)  # MB

        # Add memory usage to result metadata
        if result.success and "metadata" in result.data:
            result.data["metadata"]["memory_used_mb"] = memory_used

        return result
```

## Error Handling and Recovery

### Comprehensive Error Handling

```python
class RobustBlastTool(ToolRunner):
    """BLAST tool with comprehensive error handling."""

    def run(self, parameters: Dict[str, Any]) -> ExecutionResult:
        try:
            # Input validation
            validated_params = self._validate_parameters(parameters)

            # Pre-flight checks
            self._check_prerequisites(validated_params)

            # Execute with retries
            result = self._execute_with_retries(validated_params)

            # Post-processing validation
            self._validate_results(result)

            return result

        except ValidationError as e:
            return ExecutionResult(
                success=False,
                error=f"Input validation failed: {e}",
                error_type="ValidationError"
            )
        except NetworkError as e:
            return ExecutionResult(
                success=False,
                error=f"Network error: {e}",
                error_type="NetworkError"
            )
        except TimeoutError as e:
            return ExecutionResult(
                success=False,
                error=f"Operation timed out: {e}",
                error_type="TimeoutError"
            )
        except Exception as e:
            # Log unexpected errors
            self._log_error(e, parameters)
            return ExecutionResult(
                success=False,
                error=f"Unexpected error: {e}",
                error_type="InternalError"
            )

    def _validate_parameters(self, parameters):
        """Validate input parameters."""
        # Implementation here
        pass

    def _check_prerequisites(self, parameters):
        """Check system prerequisites."""
        # Check network connectivity, API availability, etc.
        pass

    def _execute_with_retries(self, parameters, max_retries=3):
        """Execute with automatic retries."""
        for attempt in range(max_retries):
            try:
                return self._execute_blast(parameters)
            except TemporaryError:
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)  # Exponential backoff
                else:
                    raise

    def _validate_results(self, result):
        """Validate execution results."""
        # Check result structure, data integrity, etc.
        pass

    def _log_error(self, error, parameters):
        """Log errors for debugging."""
        # Implementation here
        pass
```

## Testing Best Practices

### Test Categories

1. **Unit Tests**: Test individual methods and functions
2. **Integration Tests**: Test tool interaction with external services
3. **Performance Tests**: Test execution time and resource usage
4. **Error Handling Tests**: Test various error conditions
5. **Edge Case Tests**: Test boundary conditions and unusual inputs

### Test Fixtures

```python
@pytest.fixture
def sample_blast_parameters():
    """Provide sample BLAST search parameters."""
    return {
        "sequence": "MEEPQSDPSVEPPLSQETFSDLWKLLPENNVLSPLPSQAMDDLMLSPDDIEQWFTEDPGP",
        "database": "swissprot",
        "e_value_threshold": 1e-5,
        "max_results": 50
    }

@pytest.fixture
def mock_blast_response():
    """Mock BLAST search response."""
    return {
        "results": [
            {
                "accession": "P04637",
                "description": "Cellular tumor antigen p53",
                "e_value": 1e-150,
                "identity": 100.0,
                "alignment_length": 393
            }
        ],
        "search_info": {
            "database_size": 500000,
            "search_time": 2.5,
            "total_hits": 1
        }
    }
```

### Mocking External Dependencies

```python
@patch('Bio.Blast.NCBIWWW.qblast')
def test_blast_search_with_mock(mock_qblast, tool, sample_blast_parameters, mock_blast_response):
    """Test BLAST search with mocked NCBI API."""
    # Setup mock
    mock_result = MagicMock()
    mock_qblast.return_value = mock_result

    # Mock result parsing
    with patch.object(tool, '_parse_blast_results', return_value=mock_blast_response["results"]):
        result = tool.run(sample_blast_parameters)

        assert result.success
        assert result.data["results"] == mock_blast_response["results"]
        mock_qblast.assert_called_once()
```

## Documentation

### Tool Documentation

Provide comprehensive documentation for your tool:

```python
def get_tool_documentation():
    """Get detailed documentation for the BLAST search tool."""
    return {
        "name": "NCBI BLAST Search",
        "description": "Perform sequence similarity searches using NCBI BLAST",
        "version": "2.0.0",
        "author": "NCBI Tools Team",
        "license": "Public Domain",
        "usage_examples": [
            {
                "description": "Basic protein BLAST search",
                "parameters": {
                    "sequence": "MEEPQSDPSVEPPLSQETFSDLWKLLPENNVLSPLPSQAMDDLMLSPDDIEQWFTEDPGP",
                    "database": "swissprot"
                }
            },
            {
                "description": "Nucleotide BLAST with custom parameters",
                "parameters": {
                    "sequence": "ATCGATCGATCGATCGATCGATCG",
                    "database": "nr",
                    "e_value_threshold": 1e-10,
                    "max_results": 100
                }
            }
        ],
        "limitations": [
            "Requires internet connection for NCBI API access",
            "Subject to NCBI usage policies and rate limits",
            "Large searches may take significant time"
        ],
        "troubleshooting": {
            "NetworkError": "Check internet connection and NCBI service status",
            "TimeoutError": "Reduce sequence length or increase timeout limit",
            "ValidationError": "Ensure sequence format is correct"
        }
    }
```

## Deployment and Distribution

### Tool Packaging

Package tools for distribution:

```python
# setup.py or pyproject.toml
setup(
    name="deepcritical-blast-tool",
    version="2.0.0",
    packages=["deepresearch.tools.bioinformatics"],
    install_requires=[
        "deepresearch>=1.0.0",
        "biopython>=1.80",
        "requests>=2.28.0"
    ],
    entry_points={
        "deepresearch.tools": [
            "blast_search = deepresearch.tools.bioinformatics.blast_search:BlastSearchTool"
        ]
    }
)
```

### CI/CD Integration

Integrate tool testing into CI/CD:

```yaml
# .github/workflows/test-tools.yml
name: Test Tools
on: [push, pull_request]

jobs:
  test-bioinformatics-tools:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Setup Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      - name: Install dependencies
        run: pip install -e .[dev]
      - name: Run bioinformatics tool tests
        run: pytest tests/tools/test_bioinformatics/ -v
      - name: Test tool registration
        run: python -c "from deepresearch.tools.bioinformatics import register_tools; register_tools()"
```

## Best Practices Summary

1. **Clear Specifications**: Define comprehensive input/output specifications
2. **Robust Error Handling**: Handle all error conditions gracefully
3. **Comprehensive Testing**: Test all code paths and edge cases
4. **Performance Awareness**: Monitor and optimize resource usage
5. **Good Documentation**: Provide clear usage examples and limitations
6. **Version Compatibility**: Maintain backward compatibility
7. **Security Conscious**: Validate inputs and handle sensitive data properly
8. **Modular Design**: Keep tools focused on single responsibilities

## Related Documentation

- [Tool Registry Guide](../user-guide/tools/registry.md) - Tool registration and management
- [Testing Guide](../development/testing.md) - Testing best practices
- [Contributing Guide](../development/contributing.md) - Contribution guidelines
- [API Reference](../api/tools.md) - Complete tool API documentation
