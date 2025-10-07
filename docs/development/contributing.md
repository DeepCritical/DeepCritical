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
make test
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
```bash
# Run all tests
make test

# Run specific test categories
make test unit_tests
make test integration_tests

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

# Overall quality check
make quality
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
- Add unit tests for new functionality
- Include integration tests for complex workflows
- Ensure test coverage meets project standards
- Test error conditions and edge cases

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
- **Testing**: Test framework and quality assurance
- **Documentation**: Documentation generation and maintenance
- **CI/CD**: Build, test, and deployment automation
- **Performance**: Monitoring, profiling, and optimization

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
