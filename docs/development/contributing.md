# Contributing Guide

We welcome contributions to DeepCritical! This guide explains how to contribute effectively to the project.

## Getting Started

### 1. Fork the Repository
```bash
# Fork on GitHub, then clone your fork
git clone https://github.com/DeepCritical/DeepCritical.git
cd DeepCritical

# Add upstream remote
git remote add upstream https://github.com/DeepCritical/DeepCritical.git
```

### 2. Set Up Development Environment
```bash
# Install dependencies
uv sync --dev

# Install pre-commit hooks
make pre-install

# Verify setup
make test-unit  # or make test-unit-win on Windows
make quality
```

### 3. Create Feature Branch
```bash
# Create and switch to feature branch
git checkout -b feature/amazing-new-feature

# Or for bug fixes
git checkout -b fix/issue-description
```

## Development Workflow

### 1. Make Changes
- Follow existing code style and patterns
- Add tests for new functionality
- Update documentation as needed
- Ensure all tests pass

### 2. Test Your Changes

#### Cross-Platform Testing

DeepCritical supports comprehensive testing across multiple platforms with Windows-specific PowerShell integration.

**For Windows Development:**
```bash
# Basic tests (always available)
make test-unit-win
make test-pydantic-ai-win
make test-performance-win

# Containerized tests (requires Docker)
$env:DOCKER_TESTS = "true"
make test-containerized-win
make test-docker-win
make test-bioinformatics-win
```

**For GitHub Contributors (Cross-Platform):**
```bash
# Basic tests (works on all platforms)
make test-unit
make test-pydantic-ai
make test-performance

# Containerized tests (works when Docker available)
DOCKER_TESTS=true make test-containerized
DOCKER_TESTS=true make test-docker
DOCKER_TESTS=true make test-bioinformatics
```

#### Test Categories

DeepCritical includes comprehensive test coverage:

- **Unit Tests**: Basic functionality testing
- **Pydantic AI Tests**: Agent workflows and tool integration
- **Performance Tests**: Response time and memory usage testing
- **LLM Framework Tests**: VLLM and LLaMACPP containerized testing
- **Bioinformatics Tests**: BWA, SAMtools, BEDTools, STAR, HISAT2, FreeBayes testing
- **Docker Sandbox Tests**: Container isolation and security testing

#### Test Commands

```bash
# Run all tests
make test

# Run specific test categories
make test-unit          # or make test-unit-win on Windows
make test-pydantic-ai   # or make test-pydantic-ai-win on Windows
make test-performance   # or make test-performance-win on Windows

# Run tests with coverage
make test-cov

# Test documentation
make docs-check
```

### 3. Code Quality Checks
```bash
# Format code
make format

# Lint code
make lint

# Type checking
make type-check

# Overall quality check (includes formatting, linting, and type checking)
make quality

# Windows-specific quality checks
make format  # Same commands work on Windows
make lint    # Same commands work on Windows
make type-check  # Same commands work on Windows
make quality     # Same commands work on Windows
```

### 4. Commit Changes
```bash
# Stage changes
git add .

# Write meaningful commit message
git commit -m "feat: add amazing new feature

- Add new functionality for X
- Update tests to cover new cases
- Update documentation with examples

Closes #123"

# Push to your fork
git push origin feature/amazing-new-feature
```

### 5. Create Pull Request
1. Go to the original repository on GitHub
2. Click "New Pull Request"
3. Select your feature branch
4. Fill out the PR template
5. Request review from maintainers

## Contribution Guidelines

### Code Style
- Follow PEP 8 for Python code
- Use type hints for all functions
- Write comprehensive docstrings (Google style)
- Keep functions focused and single-purpose
- Use meaningful variable and function names

### Testing Requirements

DeepCritical has comprehensive testing requirements for all new features:

#### Test Categories Required
- **Unit Tests**: Test individual functions and classes (`make test-unit` or `make test-unit-win`)
- **Integration Tests**: Test component interactions and workflows
- **Performance Tests**: Ensure no performance regressions (`make test-performance` or `make test-performance-win`)
- **Error Handling Tests**: Test failure scenarios and error conditions

#### Cross-Platform Testing
- Ensure tests pass on both Windows (using PowerShell targets) and Linux/macOS
- Test containerized functionality when Docker is available
- Verify Windows-specific PowerShell integration works correctly

#### Test Structure
```python
# Example test structure for new features
def test_new_feature_basic():
    """Test basic functionality."""
    # Test implementation
    assert feature_works()

def test_new_feature_edge_cases():
    """Test edge cases and error conditions."""
    # Test error handling
    with pytest.raises(ValueError):
        feature_with_invalid_input()

def test_new_feature_integration():
    """Test integration with existing components."""
    # Test component interactions
    result = feature_with_dependencies()
    assert result.successful
```

#### Running Tests
```bash
# Windows
make test-unit-win
make test-pydantic-ai-win

# Cross-platform
make test-unit
make test-pydantic-ai

# Performance testing
make test-performance-win  # Windows
make test-performance      # Cross-platform
```

### Documentation Updates
- Update docstrings for API changes
- Add examples for new features
- Update configuration documentation
- Keep README and guides current

### Commit Message Format
```bash
type(scope): description

[optional body]

[optional footer]
```

**Types:**
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code style changes
- `refactor`: Code refactoring
- `test`: Test additions/changes
- `chore`: Maintenance tasks

**Examples:**
```bash
feat(agents): add custom agent support

fix(bioinformatics): correct GO annotation parsing

docs(api): update tool registry documentation

test(tools): add comprehensive tool tests
```

## Development Areas

### Core Components
- **Agents**: Multi-agent orchestration and Pydantic AI integration
- **Tools**: Tool registry, execution framework, and domain tools
- **Workflows**: State machines, flow coordination, and execution
- **Configuration**: Hydra integration and configuration management

### Domain Areas
- **PRIME**: Protein engineering workflows and tools
- **Bioinformatics**: Data fusion and biological reasoning
- **DeepSearch**: Web research and content processing
- **RAG**: Retrieval-augmented generation systems

### Infrastructure
- **Testing**: Comprehensive test framework with Windows PowerShell integration
- **Documentation**: Documentation generation and maintenance
- **CI/CD**: Build, test, and deployment automation
- **Performance**: Monitoring, profiling, and optimization

#### Testing Framework

DeepCritical implements a comprehensive testing framework with multiple test categories:

- **Unit Tests**: Basic functionality testing (`make test-unit` or `make test-unit-win`)
- **Pydantic AI Tests**: Agent workflows and tool integration (`make test-pydantic-ai` or `make test-pydantic-ai-win`)
- **Performance Tests**: Response time and memory usage testing (`make test-performance` or `make test-performance-win`)
- **LLM Framework Tests**: VLLM and LLaMACPP containerized testing
- **Bioinformatics Tests**: BWA, SAMtools, BEDTools, STAR, HISAT2, FreeBayes testing
- **Docker Sandbox Tests**: Container isolation and security testing

**Windows Integration:**
- Windows-specific Makefile targets using PowerShell scripts
- Environment variable control for optional test execution
- Cross-platform compatibility maintained for GitHub contributors

## Adding New Features

### 1. Plan Your Feature
- Discuss with maintainers before starting large features
- Create issues for tracking and discussion
- Consider backward compatibility

### 2. Implement Feature
```python
# Example: Adding a new tool category
from deepresearch.tools import ToolCategory

class NewToolCategory(ToolCategory):
    """New category for specialized tools."""
    CUSTOM_ANALYSIS = "custom_analysis"
    ADVANCED_PROCESSING = "advanced_processing"

# Update existing enums and configurations
ToolCategory.CUSTOM_ANALYSIS = "custom_analysis"
```

### 3. Add Tests
```python
# Add comprehensive tests
def test_new_feature():
    """Test the new feature functionality."""
    # Test implementation
    assert feature_works_correctly()

def test_new_feature_edge_cases():
    """Test edge cases and error conditions."""
    # Test edge cases
    pass
```

### 4. Update Documentation
```python
# Update docstrings and examples
def new_function(param: str) -> Dict[str, Any]:
    """
    New function description.

    Args:
        param: Description of parameter

    Returns:
        Description of return value

    Examples:
        >>> result = new_function("test")
        {'result': 'success'}
    """
    pass
```

## Code Review Process

### What Reviewers Look For
- **Functionality**: Does it work as intended?
- **Code Quality**: Follows style guidelines and best practices?
- **Tests**: Adequate test coverage?
- **Documentation**: Updated documentation?
- **Performance**: No performance regressions?
- **Security**: No security issues?

### Responding to Reviews
- Address all reviewer comments
- Update code based on feedback
- Re-run tests after changes
- Update PR description if needed

## Release Process

### Version Management
- Follow semantic versioning (MAJOR.MINOR.PATCH)
- Update version in `pyproject.toml`
- Update changelog for user-facing changes

### Release Checklist
- [ ] All tests pass
- [ ] Code quality checks pass
- [ ] Documentation updated
- [ ] Version bumped
- [ ] Changelog updated
- [ ] Release notes prepared

## Tools {#tools}

### Tool Development

DeepCritical supports extending the tool ecosystem with custom tools:

#### Tool Categories
- **Knowledge Query**: Information retrieval and search tools
- **Sequence Analysis**: Bioinformatics sequence analysis tools
- **Structure Prediction**: Protein structure prediction tools
- **Molecular Docking**: Drug-target interaction tools
- **De Novo Design**: Novel molecule design tools
- **Function Prediction**: Biological function annotation tools
- **RAG**: Retrieval-augmented generation tools
- **Search**: Web and document search tools
- **Analytics**: Data analysis and visualization tools
- **Code Execution**: Code execution and sandboxing tools

#### Creating Custom Tools
```python
from deepresearch.src.tools.base import ToolRunner, ToolSpec, ToolCategory

class CustomTool(ToolRunner):
    """Custom tool for specific analysis."""

    def __init__(self):
        super().__init__(ToolSpec(
            name="custom_analysis",
            description="Performs custom data analysis",
            category=ToolCategory.ANALYTICS,
            inputs={
                "data": "dict",
                "method": "str",
                "parameters": "dict"
            },
            outputs={
                "result": "dict",
                "statistics": "dict"
            }
        ))

    def run(self, parameters: Dict[str, Any]) -> ExecutionResult:
        """Execute the analysis."""
        # Implementation here
        return ExecutionResult(success=True, data={"result": "analysis_complete"})
```

#### Tool Registration
```python
from deepresearch.src.utils.tool_registry import ToolRegistry

# Register custom tool
registry = ToolRegistry.get_instance()
registry.register_tool(
    tool_spec=CustomTool().get_spec(),
    tool_runner=CustomTool()
)
```

#### Tool Testing
```python
def test_custom_tool():
    """Test custom tool functionality."""
    tool = CustomTool()
    result = tool.run({
        "data": {"key": "value"},
        "method": "analysis",
        "parameters": {"confidence": 0.95}
    })

    assert result.success
    assert "result" in result.data
```

### MCP Server Development

#### MCP Server Framework
DeepCritical includes an enhanced MCP (Model Context Protocol) server framework:

```python
from deepresearch.src.tools.mcp_server_base import MCPServerBase

class CustomMCPServer(MCPServerBase):
    """Custom MCP server with Pydantic AI integration."""

    def __init__(self, config):
        super().__init__(config)
        self.server_type = "custom"
        self.name = "custom-server"

    @mcp_tool
    async def custom_analysis(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Perform custom analysis."""
        # Tool implementation with Pydantic AI reasoning
        result = await self.pydantic_ai_agent.run(
            f"Analyze this data: {data}",
            message_history=[]
        )
        return {"analysis": result.data}
```

#### Containerized Deployment
```python
# Deploy MCP server with testcontainers
deployment = await server.deploy_with_testcontainers()
result = await server.execute_tool("custom_analysis", {"data": test_data})
```

## Community Guidelines

### Communication
- Be respectful and constructive
- Use clear, concise language
- Focus on technical merit
- Welcome diverse perspectives

### Issue Reporting
Use issue templates for:
- Bug reports
- Feature requests
- Documentation improvements
- Performance issues
- Questions

### Pull Request Guidelines
- Use PR templates
- Provide clear descriptions
- Reference related issues
- Update documentation
- Add appropriate labels

## Getting Help

### Resources
- **Documentation**: This documentation site
- **Issues**: GitHub issues for questions and bugs
- **Discussions**: GitHub discussions for broader topics
- **Examples**: Example code in the `example/` directory

### Asking Questions
1. Check existing documentation and issues
2. Search for similar questions
3. Create a clear, specific question
4. Provide context and background
5. Include error messages and logs

### Reporting Bugs
1. Use the bug report template
2. Include reproduction steps
3. Provide system information
4. Add relevant logs and error messages
5. Suggest potential fixes if possible

## Recognition

Contributors who make significant contributions may be:
- Added to the contributors list
- Invited to become maintainers
- Recognized in release notes
- Featured in community updates

Thank you for contributing to DeepCritical! Your contributions help advance research automation and scientific discovery.
