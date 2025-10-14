"""
Base classes and utilities for MCP server implementations in DeepCritical.

This module provides strongly-typed base classes for implementing MCP servers
using Pydantic AI patterns with testcontainers deployment support.

Pydantic AI integrates with MCP in two ways:
1. Agents can act as MCP clients to use tools from MCP servers
2. Pydantic AI agents can be embedded within MCP servers for enhanced tool execution

This module focuses on the second pattern - using Pydantic AI within MCP servers.
"""

from __future__ import annotations

import asyncio
import inspect
import logging
import time
import uuid
from abc import ABC, abstractmethod
from collections.abc import Callable
from pathlib import Path
from typing import (
    TYPE_CHECKING,
    Any,
    cast,
    get_type_hints,
)

from pydantic import BaseModel, Field
from pydantic_ai import Agent, RunContext
from pydantic_ai.tools import Tool

# Import DeepCritical types
from .agents import AgentDependencies
from .mcp import (
    MCPAgentIntegration,
    MCPAgentSession,
    MCPExecutionContext,
    MCPServerConfig,
    MCPServerDeployment,
    MCPServerType,
    MCPToolCall,
    MCPToolExecutionRequest,
    MCPToolExecutionResult,
    MCPToolResponse,
    MCPToolSpec,
)

if TYPE_CHECKING:
    from typing import Protocol

    class MCPToolFuncProtocol(Protocol):
        """Protocol for functions decorated with @mcp_tool."""

        _mcp_tool_spec: ToolSpec
        _is_mcp_tool: bool

        def __call__(self, *args: Any, **kwargs: Any) -> Any: ...


# Type alias for MCP tool functions
MCPToolFunc = Callable[..., Any]


class ToolSpec(BaseModel):
    """Specification for an MCP tool."""

    name: str = Field(..., description="Tool name")
    description: str = Field(..., description="Tool description")
    inputs: dict[str, str] = Field(
        default_factory=dict, description="Input parameter specifications"
    )
    outputs: dict[str, str] = Field(
        default_factory=dict, description="Output specifications"
    )
    version: str = Field("1.0.0", description="Tool version")
    server_type: MCPServerType = Field(
        MCPServerType.CUSTOM, description="Type of MCP server"
    )
    command_template: str | None = Field(
        None, description="Command template for tool execution"
    )
    validation_rules: dict[str, Any] = Field(
        default_factory=dict, description="Validation rules"
    )
    examples: list[dict[str, Any]] = Field(
        default_factory=list, description="Usage examples"
    )


class MCPServerBase(ABC):
    """Enhanced base class for MCP server implementations with Pydantic AI integration.

    This class provides the foundation for MCP servers that use Pydantic AI agents
    for enhanced tool execution and reasoning capabilities.
    """

    def __init__(self, config: MCPServerConfig):
        self.config = config
        self.name = config.server_name
        self.server_type = config.server_type
        self.tools: dict[str, Tool] = {}
        self.pydantic_ai_tools: list[Tool] = []
        self.pydantic_ai_agent: Agent | None = None
        self.container_id: str | None = None
        self.container_name: str | None = None
        self.logger = logging.getLogger(f"MCP.{self.name}")
        self.session: MCPAgentSession | None = None

        # Register all methods decorated with @tool
        self._register_tools()

        # Initialize Pydantic AI agent
        self._initialize_pydantic_ai_agent()

    def _register_tools(self):
        """Register all methods decorated with @tool."""
        # Get all methods that have been decorated with @tool
        for name in dir(self):
            method = getattr(self, name)
            if hasattr(method, "_mcp_tool_spec") and callable(method):
                # Convert to Pydantic AI Tool
                tool = self._convert_to_pydantic_ai_tool(method)
                if tool:
                    # Store both the method and tool spec for later retrieval
                    self.tools[name] = {
                        "method": method,
                        "tool": tool,
                        "spec": method._mcp_tool_spec,
                    }
                    self.pydantic_ai_tools.append(tool)

    def _convert_to_pydantic_ai_tool(self, method: Callable) -> Tool | None:
        """Convert a method to a Pydantic AI Tool."""
        try:
            # Get tool specification
            tool_spec = getattr(method, "_mcp_tool_spec", None)
            if not tool_spec:
                self.logger.warning(
                    "No tool spec found for method %s",
                    getattr(method, "__name__", "unknown"),
                )
                return None

            # Create tool function
            async def tool_function(
                ctx: RunContext[AgentDependencies], **kwargs
            ) -> Any:
                """Execute the tool with Pydantic AI context."""
                return await self._execute_tool_with_context(method, ctx, **kwargs)

            # Create and return Tool with proper Pydantic AI Tool constructor
            return Tool(
                function=tool_function,
                name=tool_spec.name,
                description=tool_spec.description,
            )

        except Exception as e:
            method_name = getattr(method, "__name__", "unknown")
            self.logger.warning(
                "Failed to convert method %s to Pydantic AI tool: %s", method_name, e
            )
            return None

    def _create_tool_schema(self, tool_spec: ToolSpec) -> dict[str, Any]:
        """Create JSON schema for tool parameters."""
        properties = {}
        required = []

        for param_name, param_type in tool_spec.inputs.items():
            # Map string types to JSON schema types
            json_type = self._map_type_to_json_schema(param_type)
            properties[param_name] = {"type": json_type}

            # Add to required if not optional
            if not param_name.startswith("optional_"):
                required.append(param_name)

        return {
            "type": "object",
            "properties": properties,
            "required": required,
        }

    def _map_type_to_json_schema(self, type_str: str) -> str:
        """Map Python type string to JSON schema type."""
        type_mapping = {
            "str": "string",
            "int": "integer",
            "float": "number",
            "bool": "boolean",
            "list": "array",
            "dict": "object",
            "List[str]": "array",
            "List[int]": "array",
            "List[float]": "array",
            "Dict[str, Any]": "object",
            "Optional[str]": "string",
            "Optional[int]": "integer",
            "Optional[float]": "number",
            "Optional[bool]": "boolean",
        }
        return type_mapping.get(type_str, "string")

    async def _execute_tool_with_context(
        self, method: Callable, ctx: RunContext[AgentDependencies], **kwargs
    ) -> Any:
        """Execute a tool method with Pydantic AI context."""
        try:
            # Record tool call if session exists
            if self.session:
                method_name = getattr(method, "__name__", "unknown")
                tool_call = MCPToolCall(
                    tool_name=method_name,
                    server_name=self.name,
                    parameters=kwargs,
                    call_id=str(uuid.uuid4()),
                )
                self.session.record_tool_call(tool_call)

            # Execute the method
            if asyncio.iscoroutinefunction(method):
                result = await method(**kwargs)
            else:
                result = method(**kwargs)

            # Record tool response if session exists
            if self.session:
                tool_response = MCPToolResponse(
                    call_id=(
                        tool_call.call_id
                        if "tool_call" in locals()
                        else str(uuid.uuid4())
                    ),
                    success=True,
                    result=result,
                    execution_time=0.0,  # Would need timing logic
                )
                self.session.record_tool_response(tool_response)

            return result

        except Exception as e:
            # Record failed tool response
            if self.session:
                tool_response = MCPToolResponse(
                    call_id=str(uuid.uuid4()),
                    success=False,
                    error=str(e),
                    execution_time=0.0,
                )
                self.session.record_tool_response(tool_response)
            raise

    def _initialize_pydantic_ai_agent(self):
        """Initialize Pydantic AI agent for this server."""
        try:
            # Create agent with tools
            self.pydantic_ai_agent = Agent(
                model="anthropic:claude-sonnet-4-0",
                tools=self.pydantic_ai_tools,
                system_prompt=self._load_system_prompt(),
            )

            # Create session for tracking
            self.session = MCPAgentSession(
                session_id=str(uuid.uuid4()),
                agent_config=MCPAgentIntegration(
                    agent_model="anthropic:claude-sonnet-4-0",
                    system_prompt=self._load_system_prompt(),
                    execution_timeout=300,
                ),
            )

        except Exception as e:
            self.logger.warning("Failed to initialize Pydantic AI agent: %s", e)
            self.pydantic_ai_agent = None

    def _load_system_prompt(self) -> str:
        """Load system prompt from prompts directory."""
        try:
            prompt_path = Path(__file__).parent.parent / "prompts" / "system_prompt.txt"
            if prompt_path.exists():
                return prompt_path.read_text().strip()
            self.logger.warning("System prompt file not found: %s", prompt_path)
            return f"MCP Server: {self.name}"
        except Exception as e:
            self.logger.warning("Failed to load system prompt: %s", e)
            return f"MCP Server: {self.name}"

    def get_tool_spec(self, tool_name: str) -> ToolSpec | None:
        """Get the specification for a tool."""
        if tool_name in self.tools:
            tool_info = self.tools[tool_name]
            if isinstance(tool_info, dict) and "spec" in tool_info:
                return tool_info["spec"]
        return None

    def list_tools(self) -> list[str]:
        """List all available tools."""
        return list(self.tools.keys())

    def execute_tool(self, tool_name: str, **kwargs) -> Any:
        """Execute a tool with the given parameters."""
        if tool_name not in self.tools:
            msg = f"Tool '{tool_name}' not found"
            raise ValueError(msg)

        tool_info = self.tools[tool_name]
        if isinstance(tool_info, dict) and "method" in tool_info:
            method = tool_info["method"]
            return method(**kwargs)
        msg = f"Tool '{tool_name}' is not properly registered"
        raise ValueError(msg)

    async def execute_tool_async(
        self, request: MCPToolExecutionRequest, ctx: MCPExecutionContext | None = None
    ) -> MCPToolExecutionResult:
        """Execute a tool asynchronously with Pydantic AI integration."""
        execution_id = str(uuid.uuid4())
        start_time = time.time()

        if ctx is None:
            ctx = MCPExecutionContext(
                server_name=self.name,
                tool_name=request.tool_name,
                execution_id=execution_id,
                environment_variables=self.config.environment_variables,
                working_directory=self.config.working_directory,
                timeout=request.timeout,
                execution_mode=request.execution_mode,
            )

        try:
            # Validate parameters if requested
            if request.validation_required:
                tool_spec = self.get_tool_spec(request.tool_name)
                if tool_spec:
                    self._validate_tool_parameters(request.parameters, tool_spec)

            # Execute tool with retry logic
            result = None
            error = None

            for attempt in range(request.max_retries + 1):
                try:
                    result = self.execute_tool(request.tool_name, **request.parameters)
                    break
                except Exception as e:
                    error = str(e)
                    if not request.retry_on_failure or attempt == request.max_retries:
                        break
                    await asyncio.sleep(1 * (attempt + 1))  # Exponential backoff

            # Calculate execution time
            execution_time = time.time() - start_time

            # Determine success
            success = error is None

            # Format result
            if isinstance(result, dict):
                result_data = result
            else:
                result_data = {"result": str(result)}

            if not success:
                result_data = {"error": error, "success": False}

            return MCPToolExecutionResult(
                request=request,
                success=success,
                result=result_data,
                execution_time=execution_time,
                error_message=error,
                output_files=[
                    str(f)
                    for f in (
                        cast("list", result_data.get("output_files"))
                        if isinstance(result_data.get("output_files"), list)
                        else []
                    )
                ],
                stdout=str(result_data.get("stdout", "")),
                stderr=str(result_data.get("stderr", "")),
                exit_code=int(result_data.get("exit_code", 0 if success else 1)),
            )

        except Exception as e:
            execution_time = time.time() - start_time
            return MCPToolExecutionResult(
                request=request,
                success=False,
                result={"error": str(e)},
                execution_time=execution_time,
                error_message=str(e),
            )

    def _validate_tool_parameters(
        self, parameters: dict[str, Any], tool_spec: ToolSpec
    ):
        """Validate tool parameters against specification."""
        required_inputs = {
            name: type_info
            for name, type_info in tool_spec.inputs.items()
            if tool_spec.validation_rules.get(name, {}).get("required", True)
        }

        for param_name, expected_type in required_inputs.items():
            if param_name not in parameters:
                msg = f"Missing required parameter: {param_name}"
                raise ValueError(msg)

            # Basic type validation
            actual_value = parameters[param_name]
            if not self._validate_parameter_type(actual_value, expected_type):
                msg = f"Invalid type for parameter '{param_name}': expected {expected_type}, got {type(actual_value).__name__}"
                raise ValueError(msg)

    def _validate_parameter_type(self, value: Any, expected_type: str) -> bool:
        """Validate parameter type."""
        type_mapping = {
            "str": str,
            "int": int,
            "float": float,
            "bool": bool,
            "list": list,
            "dict": dict,
        }

        expected_python_type = type_mapping.get(expected_type.lower())
        if expected_python_type:
            return isinstance(value, expected_python_type)

        return True  # Allow unknown types

    @abstractmethod
    async def deploy_with_testcontainers(self) -> MCPServerDeployment:
        """Deploy the server using testcontainers."""

    @abstractmethod
    async def stop_with_testcontainers(self) -> bool:
        """Stop the server deployed with testcontainers."""

    async def health_check(self) -> bool:
        """Perform health check on the deployed server."""
        if not self.container_id:
            return False

        try:
            # Use testcontainers to check container health
            from testcontainers.core.container import DockerContainer

            container = DockerContainer(self.container_id)
            container.reload()

            return container.status == "running"
        except Exception:
            self.logger.exception("Health check failed")
            return False

    def get_pydantic_ai_agent(self) -> Agent | None:
        """Get the Pydantic AI agent for this server."""
        return self.pydantic_ai_agent

    def get_session_info(self) -> dict[str, Any] | None:
        """Get information about the current session."""
        if self.session:
            return {
                "session_id": self.session.session_id,
                "tool_calls_count": len(self.session.tool_calls),
                "tool_responses_count": len(self.session.tool_responses),
                "connected_servers": list(self.session.connected_servers.keys()),
                "last_activity": self.session.last_activity.isoformat(),
            }
        return None

    def get_server_info(self) -> dict[str, Any]:
        """Get information about this server."""
        return {
            "name": self.name,
            "type": self.server_type.value,
            "version": self.config.__dict__.get("version", "1.0.0"),
            "tools": self.list_tools(),
            "container_id": self.container_id,
            "container_name": self.container_name,
            "status": "running" if self.container_id else "stopped",
            "pydantic_ai_enabled": self.pydantic_ai_agent is not None,
            "session_active": self.session is not None,
        }


# Enhanced MCP tool decorator with Pydantic AI integration
def mcp_tool(spec: ToolSpec | MCPToolSpec | None = None):
    """
    Decorator for marking methods as MCP tools with Pydantic AI integration.

    This decorator creates tools that can be used both as MCP server tools and
    as Pydantic AI agent tools, enabling seamless integration between the two systems.

    Args:
        spec: Tool specification (optional, will be auto-generated from method)
    """

    def decorator(func: Callable[..., Any]) -> MCPToolFunc:
        # Store the tool spec on the function
        if spec:
            func._mcp_tool_spec = spec  # type: ignore
        else:
            # Auto-generate spec from method signature and docstring
            sig = inspect.signature(func)
            type_hints = get_type_hints(func)

            # Extract inputs from parameters
            inputs = {}
            for param_name in sig.parameters:
                if param_name != "self":  # Skip self parameter
                    param_type = type_hints.get(param_name, str)
                    inputs[param_name] = _get_type_name(param_type)

            # Extract outputs (this is simplified - would need more sophisticated parsing)
            outputs = {
                "result": "dict",
                "command_executed": "str",
                "stdout": "str",
                "stderr": "str",
                "output_files": "List[str]",
                "success": "bool",
                "error": "Optional[str]",
            }

            # Extract description from docstring
            description = (
                getattr(func, "__doc__", None)
                or f"Tool: {getattr(func, '__name__', 'unknown')}"
            )

            tool_spec = ToolSpec(
                name=getattr(func, "__name__", "unknown"),
                description=description,
                inputs=inputs,
                outputs=outputs,
                server_type=MCPServerType.CUSTOM,
            )
            func._mcp_tool_spec = tool_spec  # type: ignore

        # Mark function as MCP tool for later Pydantic AI integration
        func._is_mcp_tool = True  # type: ignore
        return cast("MCPToolFunc", func)

    return decorator


def _get_type_name(type_hint: Any) -> str:
    """Convert a type hint to a string name."""
    if hasattr(type_hint, "__name__"):
        return type_hint.__name__
    if hasattr(type_hint, "_name"):
        return type_hint._name
    if str(type_hint).startswith("typing."):
        return str(type_hint).split(".")[-1]
    return str(type_hint)


# Use the enhanced types from datatypes module
# MCPServerConfig and MCPServerDeployment are now imported from datatypes.mcp
# These provide enhanced functionality with Pydantic AI integration
