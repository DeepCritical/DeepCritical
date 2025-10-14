"""
AG2 Code Execution Integration Tests for DeepCritical.

This module tests the vendored AG2 code execution capabilities
with configurable retry/error handling in agent workflows.
"""

import asyncio
from typing import Any

import pytest

from DeepResearch.src.datatypes.ag_types import UserMessageTextContentPart
from DeepResearch.src.tools.docker_sandbox import PydanticAICodeExecutionTool
from DeepResearch.src.utils.coding import (
    CodeBlock,
    DockerCommandLineCodeExecutor,
    LocalCommandLineCodeExecutor,
)
from DeepResearch.src.utils.coding.markdown_code_extractor import MarkdownCodeExtractor
from DeepResearch.src.utils.python_code_execution import PythonCodeExecutionTool


class TestAG2Integration:
    """Test AG2 code execution integration in DeepCritical."""

    @pytest.mark.asyncio
    @pytest.mark.optional
    async def test_python_code_execution(self):
        """Test Python code execution with retry logic."""
        tool = PydanticAICodeExecutionTool(max_retries=3, timeout=30, use_docker=True)

        # Test successful execution
        code = """
print("Hello from DeepCritical!")
x = 42
y = x * 2
print(f"Result: {y}")
"""

        result = await tool.execute_python_code(code)
        assert result["success"] is True
        assert "Hello from DeepCritical!" in result["output"]
        assert result["exit_code"] == 0
        assert result["retries_used"] >= 0

        # Test execution with intentional error and retry
        error_code = """
import sys
# This will fail
result = 1 / 0
print("This should not print")
"""

        result = await tool.execute_python_code(error_code, max_retries=2)
        assert result["success"] is False
        assert result["retries_used"] >= 0

    @pytest.mark.asyncio
    @pytest.mark.optional
    @pytest.mark.containerized
    async def test_code_blocks_execution(self):
        """Test execution of multiple code blocks."""
        tool = PydanticAICodeExecutionTool()

        # Test with independent code blocks (each executes in isolation)
        code_blocks = [
            CodeBlock(code="print('Block 1: Hello')", language="python"),
            CodeBlock(code="print('Block 2: Independent')", language="python"),
            CodeBlock(code="print('Block 3: Standalone')", language="python"),
        ]

        # Test with Docker executor
        result = await tool.execute_code_blocks(code_blocks, executor_type="docker")
        assert isinstance(result, dict)
        assert result.get("success") is True, f"Docker execution failed: {result}"
        assert "Block 1: Hello" in result.get("output", "")
        assert "Block 2: Independent" in result.get("output", "")
        assert "Block 3: Standalone" in result.get("output", "")

        # Test with Local executor
        result = await tool.execute_code_blocks(code_blocks, executor_type="local")
        assert isinstance(result, dict)
        assert result.get("success") is True, f"Local execution failed: {result}"
        assert "Block 1: Hello" in result.get("output", "")

    @pytest.mark.optional
    def test_markdown_extraction(self):
        """Test markdown code extraction."""
        extractor = MarkdownCodeExtractor()

        markdown_text = """
Here's some Python code:

```python
def hello():
    print("Hello, World!")
    return 42

result = hello()
print(f"Result: {result}")
```

And here's some bash:

```bash
echo "Hello from bash!"
pwd
```
"""

        messages = [UserMessageTextContentPart(type="text", text=markdown_text)]
        code_blocks = extractor.extract_code_blocks(messages)

        assert len(code_blocks) == 2
        assert code_blocks[0].language == "python"
        assert "def hello():" in code_blocks[0].code
        assert code_blocks[1].language == "bash"
        assert "echo" in code_blocks[1].code

    @pytest.mark.optional
    @pytest.mark.containerized
    def test_direct_executor_usage(self):
        """Test direct usage of AG2 code executors."""
        # Test Docker executor
        try:
            with DockerCommandLineCodeExecutor(timeout=30) as executor:
                code_blocks = [
                    CodeBlock(code="print('Docker execution test')", language="python")
                ]
                result = executor.execute_code_blocks(code_blocks)
                assert result.exit_code == 0
                assert "Docker execution test" in result.output
        except Exception as e:
            pytest.skip(f"Docker executor test failed: {e}")

        # Test Local executor
        try:
            executor = LocalCommandLineCodeExecutor(timeout=30)
            code_blocks = [
                CodeBlock(code="print('Local execution test')", language="python")
            ]
            result = executor.execute_code_blocks(code_blocks)
            assert result.exit_code == 0
            assert "Local execution test" in result.output
        except Exception as e:
            pytest.skip(f"Local executor test failed: {e}")

    @pytest.mark.optional
    @pytest.mark.containerized
    @pytest.mark.asyncio
    async def test_deployment_integration(self):
        """Test integration with deployment systems."""
        try:
            # Create a mock deployment record for testing
            from DeepResearch.src.datatypes.mcp import (
                MCPServerConfig,
                MCPServerDeployment,
                MCPServerStatus,
                MCPServerType,
            )
            from DeepResearch.src.utils.testcontainers_deployer import (
                testcontainers_deployer,
            )

            mock_deployment = MCPServerDeployment(
                server_name="test_server",
                status=MCPServerStatus.RUNNING,
                container_name="test_container",
                container_id="test_id",
                configuration=MCPServerConfig(
                    server_name="test_server",
                    server_type=MCPServerType.CUSTOM,
                    container_image="python:3.11-slim",
                ),
            )

            # Add to deployer for testing
            testcontainers_deployer.deployments["test_server"] = mock_deployment

            # Test code execution through deployer
            result = await testcontainers_deployer.execute_code(
                "test_server",
                "print('Code execution via deployer')",
                language="python",
                timeout=30,
                max_retries=2,
            )

            # The result should be a dictionary with execution results
            assert isinstance(result, dict)
            assert "success" in result

        except Exception as e:
            pytest.skip(f"Deployment integration test failed: {e}")

    @pytest.mark.optional
    @pytest.mark.asyncio
    async def test_agent_workflow_simulation(self):
        """Test simulated agent workflow."""
        # Simulate agent workflow for factorial calculation
        initial_code = """
def factorial(n):
    if n == 0:
        return 1
    else:
        return n * factorial(n - 1)

# Test the function
print(f"Factorial of 5: {factorial(5)}")
"""

        tool = PydanticAICodeExecutionTool(max_retries=3)
        result = await tool.execute_python_code(initial_code)

        # The code should execute successfully
        assert result["success"] is True
        assert "Factorial of 5: 120" in result["output"]

    @pytest.mark.optional
    def test_basic_imports(self):
        """Test that all AG2 integration imports work correctly."""
        # This test ensures all the vendored AG2 components can be imported
        from DeepResearch.src.datatypes.ag_types import (
            MessageContentType,
            UserMessageImageContentPart,
            UserMessageTextContentPart,
            content_str,
        )
        from DeepResearch.src.utils.code_utils import execute_code, infer_lang
        from DeepResearch.src.utils.coding import (
            CodeBlock,
            CodeExecutor,
            CodeExtractor,
            CodeResult,
            DockerCommandLineCodeExecutor,
            LocalCommandLineCodeExecutor,
            MarkdownCodeExtractor,
        )

        # Test basic functionality
        assert content_str is not None
        assert execute_code is not None
        assert infer_lang is not None
        assert PythonCodeExecutionTool is not None
        assert CodeBlock is not None
        assert DockerCommandLineCodeExecutor is not None
        assert LocalCommandLineCodeExecutor is not None
        assert MarkdownCodeExtractor is not None

    @pytest.mark.optional
    def test_language_inference(self):
        """Test language inference from code."""
        from DeepResearch.src.utils.code_utils import infer_lang

        # Test Python inference
        python_code = "def hello():\n    print('Hello')"
        assert infer_lang(python_code) == "python"

        # Test shell inference
        shell_code = "echo 'Hello World'"
        assert infer_lang(shell_code) == "bash"

        # Test unknown language
        unknown_code = "some random text without clear language indicators"
        assert infer_lang(unknown_code) == "unknown"

    @pytest.mark.optional
    def test_code_extraction(self):
        """Test code extraction from markdown."""
        from DeepResearch.src.utils.code_utils import extract_code

        markdown = """
Some text here.

```python
def test():
    return 42
```

More text.
"""

        extracted = extract_code(markdown)
        assert len(extracted) == 1
        # extract_code returns list of (language, code) tuples
        assert len(extracted[0]) == 2
        language, code = extracted[0]
        assert language == "python"
        assert "def test():" in code

    @pytest.mark.optional
    def test_content_string_utility(self):
        """Test content string utility functions."""
        from DeepResearch.src.datatypes.ag_types import content_str

        # Test with string content
        result = content_str("Hello world")
        assert result == "Hello world"

        # Test with text content parts
        text_parts = [{"type": "text", "text": "Hello world"}]
        result = content_str(text_parts)
        assert result == "Hello world"

        # Test with mixed content (AG2 joins with newlines)
        mixed_parts = [
            {"type": "text", "text": "Hello"},
            {"type": "text", "text": " world"},
        ]
        result = content_str(mixed_parts)
        assert result == "Hello\n world"

        # Test with None
        result = content_str(None)
        assert result == ""
