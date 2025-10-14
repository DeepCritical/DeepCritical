"""
DeepAgent Graph - Pydantic AI graph patterns for DeepAgent operations.

This module implements graph-based agent orchestration using Pydantic AI patterns
that align with DeepCritical's architecture, providing agent builders and
orchestration capabilities.
"""

from __future__ import annotations

import asyncio
import time
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator
from pydantic_ai import Agent

# Import existing DeepCritical types
from DeepResearch.src.datatypes.deep_agent_state import DeepAgentState
from DeepResearch.src.datatypes.deep_agent_types import (
    AgentOrchestrationConfig,
    CustomSubAgent,
    SubAgent,
)
from DeepResearch.src.tools.deep_agent_middleware import (
    create_default_middleware_pipeline,
)
from DeepResearch.src.tools.deep_agent_tools import (
    edit_file_tool,
    list_files_tool,
    read_file_tool,
    task_tool,
    write_file_tool,
    write_todos_tool,
)


class AgentBuilderConfig(BaseModel):
    """Configuration for agent builder."""

    model_name: str = Field("anthropic:claude-sonnet-4-0", description="Model name")
    instructions: str = Field("", description="Additional instructions")
    tools: list[str] = Field(default_factory=list, description="Tool names to include")
    subagents: list[SubAgent | CustomSubAgent] = Field(
        default_factory=list, description="Subagents"
    )
    middleware_config: dict[str, Any] = Field(
        default_factory=dict, description="Middleware configuration"
    )
    enable_parallel_execution: bool = Field(
        True, description="Enable parallel execution"
    )
    max_concurrent_agents: int = Field(5, gt=0, description="Maximum concurrent agents")
    timeout: float = Field(300.0, gt=0, description="Default timeout")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {"max_agents": 10, "max_concurrent_agents": 5, "timeout": 300.0}
        }
    )


class AgentGraphNode(BaseModel):
    """Node in the agent graph."""

    name: str = Field(..., description="Node name")
    agent_type: str = Field(..., description="Type of agent")
    config: dict[str, Any] = Field(
        default_factory=dict, description="Node configuration"
    )
    dependencies: list[str] = Field(
        default_factory=list, description="Node dependencies"
    )
    timeout: float = Field(300.0, gt=0, description="Node timeout")

    @field_validator("name")
    @classmethod
    def validate_name(cls, v):
        if not v or not v.strip():
            msg = "Node name cannot be empty"
            raise ValueError(msg)
        return v.strip()

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "name": "search_node",
                "agent_type": "SearchAgent",
                "config": {"max_results": 10},
                "dependencies": ["plan_node"],
                "timeout": 300.0,
            }
        }
    )


class AgentGraphEdge(BaseModel):
    """Edge in the agent graph."""

    source: str = Field(..., description="Source node name")
    target: str = Field(..., description="Target node name")
    condition: str | None = Field(None, description="Condition for edge traversal")
    weight: float = Field(1.0, description="Edge weight")

    @field_validator("source", "target")
    @classmethod
    def validate_node_names(cls, v):
        if not v or not v.strip():
            msg = "Node name cannot be empty"
            raise ValueError(msg)
        return v.strip()

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "name": "search_node",
                "agent_type": "SearchAgent",
                "config": {"max_results": 10},
                "dependencies": ["plan_node"],
                "timeout": 300.0,
            }
        }
    )


class AgentGraph(BaseModel):
    """Graph structure for agent orchestration."""

    nodes: list[AgentGraphNode] = Field(..., description="Graph nodes")
    edges: list[AgentGraphEdge] = Field(default_factory=list, description="Graph edges")
    entry_point: str = Field(..., description="Entry point node")
    exit_points: list[str] = Field(default_factory=list, description="Exit point nodes")

    @field_validator("entry_point")
    @classmethod
    def validate_entry_point(cls, v, info):
        if info.data and "nodes" in info.data:
            node_names = [node.name for node in info.data["nodes"]]
            if v not in node_names:
                msg = f"Entry point '{v}' not found in nodes"
                raise ValueError(msg)
        return v

    @field_validator("exit_points")
    @classmethod
    def validate_exit_points(cls, v, info):
        if info.data and "nodes" in info.data:
            node_names = [node.name for node in info.data["nodes"]]
            for exit_point in v:
                if exit_point not in node_names:
                    msg = f"Exit point '{exit_point}' not found in nodes"
                    raise ValueError(msg)
        return v

    def get_node(self, name: str) -> AgentGraphNode | None:
        """Get a node by name."""
        for node in self.nodes:
            if node.name == name:
                return node
        return None

    def get_adjacent_nodes(self, node_name: str) -> list[str]:
        """Get nodes adjacent to the given node."""
        adjacent = []
        for edge in self.edges:
            if edge.source == node_name:
                adjacent.append(edge.target)
        return adjacent

    def get_dependencies(self, node_name: str) -> list[str]:
        """Get dependencies for a node."""
        node = self.get_node(node_name)
        if node:
            return node.dependencies
        return []

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "name": "search_node",
                "agent_type": "SearchAgent",
                "config": {"max_results": 10},
                "dependencies": ["plan_node"],
                "timeout": 300.0,
            }
        }
    )


class AgentGraphExecutor:
    """Executor for agent graphs."""

    def __init__(
        self,
        graph: AgentGraph,
        agent_registry: dict[str, Agent],
        config: AgentOrchestrationConfig | None = None,
    ):
        self.graph = graph
        self.agent_registry = agent_registry
        self.config = config or AgentOrchestrationConfig()
        self.execution_history: list[dict[str, Any]] = []

    async def execute(
        self, initial_state: DeepAgentState, start_node: str | None = None
    ) -> dict[str, Any]:
        """Execute the agent graph."""
        start_node = start_node or self.graph.entry_point
        execution_start = time.time()

        try:
            # Initialize execution state
            execution_state = {
                "current_node": start_node,
                "completed_nodes": [],
                "failed_nodes": [],
                "state": initial_state,
                "results": {},
            }

            # Execute graph traversal
            result = await self._execute_graph_traversal(execution_state)

            execution_time = time.time() - execution_start
            result["execution_time"] = execution_time
            result["execution_history"] = self.execution_history

            return result

        except Exception as e:
            execution_time = time.time() - execution_start
            return {
                "success": False,
                "error": str(e),
                "execution_time": execution_time,
                "execution_history": self.execution_history,
            }

    async def _execute_graph_traversal(
        self, execution_state: dict[str, Any]
    ) -> dict[str, Any]:
        """Execute graph traversal logic."""
        current_node = execution_state["current_node"]

        while current_node:
            # Check if node is already completed
            if current_node in execution_state["completed_nodes"]:
                # Move to next node
                current_node = self._get_next_node(current_node, execution_state)
                continue

            # Check dependencies
            dependencies = self.graph.get_dependencies(current_node)
            if not self._dependencies_satisfied(dependencies, execution_state):
                # Wait for dependencies or fail
                current_node = self._handle_dependency_wait(
                    current_node, execution_state
                )
                continue

            # Execute current node
            node_result = await self._execute_node(current_node, execution_state)

            if node_result["success"]:
                execution_state["completed_nodes"].append(current_node)
                execution_state["results"][current_node] = node_result
                current_node = self._get_next_node(current_node, execution_state)
            else:
                execution_state["failed_nodes"].append(current_node)
                if self.config.enable_failure_recovery:
                    current_node = self._handle_failure(current_node, execution_state)
                else:
                    break

        return {
            "success": len(execution_state["failed_nodes"]) == 0,
            "completed_nodes": execution_state["completed_nodes"],
            "failed_nodes": execution_state["failed_nodes"],
            "results": execution_state["results"],
            "final_state": execution_state["state"],
        }

    async def _execute_node(
        self, node_name: str, execution_state: dict[str, Any]
    ) -> dict[str, Any]:
        """Execute a single node."""
        node = self.graph.get_node(node_name)
        if not node:
            return {"success": False, "error": f"Node {node_name} not found"}

        agent = self.agent_registry.get(node_name)
        if not agent:
            return {"success": False, "error": f"Agent for node {node_name} not found"}

        start_time = time.time()
        try:
            # Execute agent with timeout
            result = await asyncio.wait_for(
                self._run_agent(agent, execution_state["state"], node.config),
                timeout=node.timeout,
            )

            execution_time = time.time() - start_time

            # Record execution
            self.execution_history.append(
                {
                    "node": node_name,
                    "success": True,
                    "execution_time": execution_time,
                    "timestamp": time.time(),
                }
            )

            return {
                "success": True,
                "result": result,
                "execution_time": execution_time,
                "node": node_name,
            }

        except asyncio.TimeoutError:
            execution_time = time.time() - start_time
            self.execution_history.append(
                {
                    "node": node_name,
                    "success": False,
                    "error": "timeout",
                    "execution_time": execution_time,
                    "timestamp": time.time(),
                }
            )
            return {
                "success": False,
                "error": "timeout",
                "execution_time": execution_time,
            }

        except Exception as e:
            execution_time = time.time() - start_time
            self.execution_history.append(
                {
                    "node": node_name,
                    "success": False,
                    "error": str(e),
                    "execution_time": execution_time,
                    "timestamp": time.time(),
                }
            )
            return {"success": False, "error": str(e), "execution_time": execution_time}

    async def _run_agent(
        self, agent: Agent, state: DeepAgentState, config: dict[str, Any]
    ) -> Any:
        """Run an agent with the given state and configuration."""
        # This is a simplified implementation
        # In practice, you would implement proper agent execution
        # with Pydantic AI patterns

        # For now, return a mock result
        return {"agent_result": "mock_result", "config": config, "state_updated": True}

    def _dependencies_satisfied(
        self, dependencies: list[str], execution_state: dict[str, Any]
    ) -> bool:
        """Check if all dependencies are satisfied."""
        completed_nodes = execution_state["completed_nodes"]
        return all(dep in completed_nodes for dep in dependencies)

    def _get_next_node(
        self, current_node: str, execution_state: dict[str, Any]
    ) -> str | None:
        """Get the next node to execute."""
        adjacent_nodes = self.graph.get_adjacent_nodes(current_node)

        # Find the first adjacent node that hasn't been completed or failed
        for node in adjacent_nodes:
            if (
                node not in execution_state["completed_nodes"]
                and node not in execution_state["failed_nodes"]
            ):
                return node

        # If no adjacent nodes available, check if we're at an exit point
        if current_node in self.graph.exit_points:
            return None

        return None

    def _handle_dependency_wait(
        self, current_node: str, execution_state: dict[str, Any]
    ) -> str | None:
        """Handle waiting for dependencies."""
        # In a real implementation, you might implement retry logic
        # or parallel execution of independent nodes
        return None

    def _handle_failure(
        self, failed_node: str, execution_state: dict[str, Any]
    ) -> str | None:
        """Handle node failure."""
        # In a real implementation, you might implement retry logic
        # or alternative execution paths
        return None


class AgentBuilder:
    """Builder for creating agents with middleware and tools."""

    def __init__(self, config: AgentBuilderConfig | None = None):
        self.config = config or AgentBuilderConfig()
        self.middleware_pipeline = create_default_middleware_pipeline(
            subagents=self.config.subagents
        )

    def build_agent(self) -> Agent:
        """Build an agent with the configured middleware and tools."""
        # Create base agent
        agent = Agent(
            model=self.config.model_name,
            system_prompt=self._build_system_prompt(),
            deps_type=DeepAgentState,
        )

        # Add tools
        self._add_tools(agent)

        # Add middleware
        self._add_middleware(agent)

        return agent

    def _build_system_prompt(self) -> str:
        """Build the system prompt for the agent."""
        base_prompt = "You are a helpful AI assistant with access to various tools and capabilities."

        if self.config.instructions:
            base_prompt += f"\n\nAdditional instructions: {self.config.instructions}"

        # Add subagent information
        if self.config.subagents:
            subagent_descriptions = [
                f"- {sa.name}: {sa.description}" for sa in self.config.subagents
            ]
            base_prompt += "\n\nAvailable subagents:\n" + "\n".join(
                subagent_descriptions
            )

        return base_prompt

    def _add_tools(self, agent: Agent) -> None:
        """Add tools to the agent."""
        tool_map = {
            "write_todos": write_todos_tool,
            "list_files": list_files_tool,
            "read_file": read_file_tool,
            "write_file": write_file_tool,
            "edit_file": edit_file_tool,
            "task": task_tool,
        }

        for tool_name in self.config.tools:
            if tool_name in tool_map:
                # Add tool if method exists
                if hasattr(agent, "add_tool") and callable(agent.add_tool):
                    add_tool_method = agent.add_tool
                    add_tool_method(tool_map[tool_name])  # type: ignore
                elif hasattr(agent, "tools") and hasattr(agent.tools, "append"):
                    tools_attr = agent.tools
                    if hasattr(tools_attr, "append") and callable(tools_attr.append):
                        tools_attr.append(tool_map[tool_name])  # type: ignore

    def _add_middleware(self, agent: Agent) -> None:
        """Add middleware to the agent."""
        # In a real implementation, you would integrate middleware
        # with the Pydantic AI agent system

    def build_graph(
        self, nodes: list[AgentGraphNode], edges: list[AgentGraphEdge]
    ) -> AgentGraph:
        """Build an agent graph."""
        return AgentGraph(
            nodes=nodes,
            edges=edges,
            entry_point=nodes[0].name if nodes else "",
            exit_points=[
                node.name
                for node in nodes
                if not self._has_outgoing_edges(node.name, edges)
            ],
        )

    def _has_outgoing_edges(self, node_name: str, edges: list[AgentGraphEdge]) -> bool:
        """Check if a node has outgoing edges."""
        return any(edge.source == node_name for edge in edges)


# Factory functions
def create_agent_builder(
    model_name: str = "anthropic:claude-sonnet-4-0",
    instructions: str = "",
    tools: list[str] | None = None,
    subagents: list[SubAgent | CustomSubAgent] | None = None,
    **kwargs,
) -> AgentBuilder:
    """Create an agent builder with default configuration."""
    config = AgentBuilderConfig(
        model_name=model_name,
        instructions=instructions,
        tools=tools or [],
        subagents=subagents or [],
        **kwargs,
    )
    return AgentBuilder(config)


def create_simple_agent(
    model_name: str = "anthropic:claude-sonnet-4-0",
    instructions: str = "",
    tools: list[str] | None = None,
) -> Agent:
    """Create a simple agent with basic configuration."""
    builder = create_agent_builder(model_name, instructions, tools)
    return builder.build_agent()


def create_deep_agent(
    tools: list[str] | None = None,
    instructions: str = "",
    subagents: list[SubAgent | CustomSubAgent] | None = None,
    model_name: str = "anthropic:claude-sonnet-4-0",
    **kwargs,
) -> Agent:
    """Create a deep agent with full capabilities."""
    default_tools = [
        "write_todos",
        "list_files",
        "read_file",
        "write_file",
        "edit_file",
        "task",
    ]
    tools = tools or default_tools

    builder = create_agent_builder(
        model_name=model_name,
        instructions=instructions,
        tools=tools,
        subagents=subagents,
        **kwargs,
    )
    return builder.build_agent()


def create_async_deep_agent(
    tools: list[str] | None = None,
    instructions: str = "",
    subagents: list[SubAgent | CustomSubAgent] | None = None,
    model_name: str = "anthropic:claude-sonnet-4-0",
    **kwargs,
) -> Agent:
    """Create an async deep agent with full capabilities."""
    # For now, this is the same as create_deep_agent
    # In a real implementation, you would configure async-specific settings
    return create_deep_agent(tools, instructions, subagents, model_name, **kwargs)


# Export all components
__all__ = [
    # Prompt constants and classes
    "DEEP_AGENT_GRAPH_PROMPTS",
    "AgentBuilder",
    # Configuration and models
    "AgentBuilderConfig",
    "AgentGraph",
    "AgentGraphEdge",
    # Executors and builders
    "AgentGraphExecutor",
    "AgentGraphNode",
    "DeepAgentGraphPrompts",
    # Factory functions
    "create_agent_builder",
    "create_async_deep_agent",
    "create_deep_agent",
    "create_simple_agent",
]


# Prompt constants for DeepAgent Graph operations
DEEP_AGENT_GRAPH_PROMPTS = {
    "system": "You are a DeepAgent Graph orchestrator for complex multi-agent workflows.",
    "build_graph": "Build a graph for the following agent workflow: {workflow_description}",
    "execute_graph": "Execute the graph with the following state: {state}",
}


class DeepAgentGraphPrompts:
    """Prompt templates for DeepAgent Graph operations."""

    PROMPTS = DEEP_AGENT_GRAPH_PROMPTS
