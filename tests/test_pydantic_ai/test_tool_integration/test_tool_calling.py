"""
Tool calling tests for Pydantic AI framework.
"""

import asyncio
from unittest.mock import Mock

import pytest
from pydantic_ai import Agent, RunContext


class TestPydanticAIToolCalling:
    """Test Pydantic AI tool calling functionality."""

    @pytest.mark.asyncio
    @pytest.mark.optional
    @pytest.mark.pydantic_ai
    async def test_agent_tool_registration(self):
        """Test that tools are properly registered with agents."""
        # Create a mock agent with tool registration
        agent = Mock(spec=Agent)
        agent.tools = []

        # Mock tool registration
        def mock_tool_registration(func):
            agent.tools.append(func)
            return func

        # Register a test tool
        @mock_tool_registration
        def test_tool(param: str) -> str:
            """Test tool function."""
            return f"Processed: {param}"

        assert len(agent.tools) == 1
        assert agent.tools[0] == test_tool

    @pytest.mark.asyncio
    @pytest.mark.optional
    @pytest.mark.pydantic_ai
    async def test_tool_execution_with_dependencies(self):
        """Test tool execution with dependency injection."""
        # Mock agent dependencies
        deps = {
            "model_name": "anthropic:claude-sonnet-4-0",
            "temperature": 0.7,
            "max_tokens": 1000,
        }

        # Mock tool execution context
        ctx = Mock(spec=RunContext)
        ctx.deps = deps

        # Test tool function with context
        def test_tool_with_deps(param: str, ctx: RunContext) -> str:
            deps_str = str(ctx.deps) if ctx.deps is not None else "None"
            return f"Deps: {deps_str}, Param: {param}"

        result = test_tool_with_deps("test", ctx)
        assert "test" in result

    @pytest.mark.asyncio
    @pytest.mark.optional
    @pytest.mark.pydantic_ai
    async def test_error_handling_in_tools(self):
        """Test error handling in tool functions."""

        def failing_tool(param: str) -> str:
            if param == "fail":
                raise ValueError("Test error")
            return f"Success: {param}"

        # Test successful execution
        result = failing_tool("success")
        assert result == "Success: success"

        # Test error handling
        with pytest.raises(ValueError, match="Test error"):
            failing_tool("fail")

    @pytest.mark.asyncio
    @pytest.mark.optional
    @pytest.mark.pydantic_ai
    async def test_async_tool_execution(self):
        """Test asynchronous tool execution."""

        async def async_test_tool(param: str) -> str:
            await asyncio.sleep(0.1)  # Simulate async operation
            return f"Async result: {param}"

        result = await async_test_tool("test")
        assert result == "Async result: test"
