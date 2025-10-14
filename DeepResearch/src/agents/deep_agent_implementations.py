"""
DeepAgent Implementations - Pydantic AI agent implementations for DeepAgent operations.

This module implements specific agent types and orchestration patterns using
Pydantic AI that align with DeepCritical's architecture.
"""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator
from pydantic_ai import Agent, ModelRetry

# Import existing DeepCritical types
from DeepResearch.src.datatypes.deep_agent_state import DeepAgentState
from DeepResearch.src.datatypes.deep_agent_types import AgentCapability, AgentMetrics
from DeepResearch.src.prompts.deep_agent_prompts import get_system_prompt
from DeepResearch.src.tools.deep_agent_middleware import (
    MiddlewarePipeline,
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


class AgentConfig(BaseModel):
    """Configuration for agent instances."""

    name: str = Field(..., description="Agent name")
    model_name: str = Field("anthropic:claude-sonnet-4-0", description="Model name")
    system_prompt: str = Field("", description="System prompt")
    tools: list[str] = Field(default_factory=list, description="Tool names")
    capabilities: list[AgentCapability] = Field(
        default_factory=list, description="Agent capabilities"
    )
    max_iterations: int = Field(10, gt=0, description="Maximum iterations")
    timeout: float = Field(300.0, gt=0, description="Timeout in seconds")
    enable_retry: bool = Field(True, description="Enable retry on failure")
    retry_attempts: int = Field(3, ge=0, description="Number of retry attempts")

    @field_validator("name")
    @classmethod
    def validate_name(cls, v):
        if not v or not v.strip():
            msg = "Agent name cannot be empty"
            raise ValueError(msg)
        return v.strip()

    model_config = ConfigDict(json_schema_extra={})


class AgentExecutionResult(BaseModel):
    """Result from agent execution."""

    success: bool = Field(..., description="Whether execution succeeded")
    result: dict[str, Any] | None = Field(None, description="Execution result")
    error: str | None = Field(None, description="Error message if failed")
    execution_time: float = Field(..., description="Execution time in seconds")
    iterations_used: int = Field(0, description="Number of iterations used")
    tools_used: list[str] = Field(
        default_factory=list, description="Tools used during execution"
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict, description="Additional metadata"
    )

    model_config = ConfigDict(json_schema_extra={})


class BaseDeepAgent:
    """Base class for DeepAgent implementations."""

    def __init__(self, config: AgentConfig):
        self.config = config
        self.agent: Agent | None = None
        self.middleware_pipeline: MiddlewarePipeline | None = None
        self.metrics = AgentMetrics(agent_name=config.name)
        self._initialize_agent()

    def _initialize_agent(self) -> None:
        """Initialize the Pydantic AI agent."""
        # Build system prompt
        system_prompt = self._build_system_prompt()

        # Create agent
        self.agent = Agent(
            model=self.config.model_name,
            system_prompt=system_prompt,
            deps_type=DeepAgentState,
        )

        # Add tools
        self._add_tools()

        # Initialize middleware
        self._initialize_middleware()

    def _build_system_prompt(self) -> str:
        """Build the system prompt for the agent."""
        if self.config.system_prompt:
            return self.config.system_prompt

        # Build default system prompt based on capabilities
        prompt_components = ["base_agent"]

        if AgentCapability.PLANNING in self.config.capabilities:
            prompt_components.append("write_todos_system")

        if AgentCapability.FILESYSTEM in self.config.capabilities:
            prompt_components.append("filesystem_system")

        if AgentCapability.TASK_ORCHESTRATION in self.config.capabilities:
            prompt_components.append("task_system")

        return get_system_prompt(prompt_components)

    def _add_tools(self) -> None:
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
                self.agent.add_tool(tool_map[tool_name])

    def _initialize_middleware(self) -> None:
        """Initialize middleware pipeline."""
        self.middleware_pipeline = create_default_middleware_pipeline()

    async def execute(
        self,
        input_data: str | dict[str, Any],
        context: DeepAgentState | None = None,
    ) -> AgentExecutionResult:
        """Execute the agent with given input and context."""
        if not self.agent:
            return AgentExecutionResult(
                success=False, error="Agent not initialized", execution_time=0.0
            )

        start_time = time.time()
        iterations_used = 0
        tools_used = []

        try:
            # Prepare context
            if context is None:
                context = DeepAgentState(session_id=f"session_{int(time.time())}")

            # Process middleware
            if self.middleware_pipeline:
                middleware_results = await self.middleware_pipeline.process(
                    self.agent, context
                )
                # Check for middleware failures
                for result in middleware_results:
                    if not result.success:
                        return AgentExecutionResult(
                            success=False,
                            error=f"Middleware failed: {result.error}",
                            execution_time=time.time() - start_time,
                        )

            # Execute agent with retry logic
            result = await self._execute_with_retry(input_data, context)

            execution_time = time.time() - start_time

            # Update metrics
            self._update_metrics(execution_time, True, tools_used)

            return AgentExecutionResult(
                success=True,
                result=result,
                execution_time=execution_time,
                iterations_used=iterations_used,
                tools_used=tools_used,
                metadata={"agent_name": self.config.name},
            )

        except Exception as e:
            execution_time = time.time() - start_time
            self._update_metrics(execution_time, False, tools_used)

            return AgentExecutionResult(
                success=False,
                error=str(e),
                execution_time=execution_time,
                iterations_used=iterations_used,
                tools_used=tools_used,
                metadata={"agent_name": self.config.name},
            )

    async def _execute_with_retry(
        self, input_data: str | dict[str, Any], context: DeepAgentState
    ) -> Any:
        """Execute agent with retry logic."""
        last_error = None

        for attempt in range(self.config.retry_attempts + 1):
            try:
                if isinstance(input_data, str):
                    result = await self.agent.run(input_data, deps=context)
                else:
                    result = await self.agent.run(input_data, deps=context)

                return result

            except ModelRetry as e:
                last_error = e
                if attempt < self.config.retry_attempts:
                    await asyncio.sleep(1.0 * (attempt + 1))  # Exponential backoff
                    continue
                raise

            except Exception as e:
                last_error = e
                if attempt < self.config.retry_attempts and self.config.enable_retry:
                    await asyncio.sleep(1.0 * (attempt + 1))
                    continue
                raise

        if last_error:
            raise last_error
        msg = "No agents available for execution"
        raise RuntimeError(msg)

    def _update_metrics(
        self, execution_time: float, success: bool, tools_used: list[str]
    ) -> None:
        """Update agent metrics."""
        self.metrics.total_tasks += 1
        if success:
            self.metrics.successful_tasks += 1
        else:
            self.metrics.failed_tasks += 1

        # Update average execution time
        total_time = self.metrics.average_execution_time * (
            self.metrics.total_tasks - 1
        )
        self.metrics.average_execution_time = (
            total_time + execution_time
        ) / self.metrics.total_tasks

        self.metrics.last_activity = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

    def get_metrics(self) -> AgentMetrics:
        """Get agent performance metrics."""
        return self.metrics


class PlanningAgent(BaseDeepAgent):
    """Agent specialized for planning and task management."""

    def __init__(self, config: AgentConfig | None = None):
        if config is None:
            config = AgentConfig(
                name="planning-agent",
                system_prompt="You are a planning specialist focused on breaking down complex tasks into manageable steps.",
                tools=["write_todos"],
                capabilities=[AgentCapability.PLANNING],
            )
        super().__init__(config)

    async def create_plan(
        self, task_description: str, context: DeepAgentState | None = None
    ) -> AgentExecutionResult:
        """Create a plan for the given task."""
        prompt = f"Create a detailed plan for the following task: {task_description}"
        return await self.execute(prompt, context)


class FilesystemAgent(BaseDeepAgent):
    """Agent specialized for filesystem operations."""

    def __init__(self, config: AgentConfig | None = None):
        if config is None:
            config = AgentConfig(
                name="filesystem-agent",
                system_prompt="You are a filesystem specialist focused on file operations and management.",
                tools=["list_files", "read_file", "write_file", "edit_file"],
                capabilities=[AgentCapability.FILESYSTEM],
            )
        super().__init__(config)

    async def manage_files(
        self, operation: str, context: DeepAgentState | None = None
    ) -> AgentExecutionResult:
        """Perform filesystem operations."""
        prompt = f"Perform the following filesystem operation: {operation}"
        return await self.execute(prompt, context)


class ResearchAgent(BaseDeepAgent):
    """Agent specialized for research tasks."""

    def __init__(self, config: AgentConfig | None = None):
        if config is None:
            config = AgentConfig(
                name="research-agent",
                system_prompt="You are a research specialist focused on gathering and analyzing information.",
                tools=["write_todos", "read_file", "web_search"],
                capabilities=[AgentCapability.SEARCH, AgentCapability.ANALYSIS],
            )
        super().__init__(config)

    async def conduct_research(
        self, research_query: str, context: DeepAgentState | None = None
    ) -> AgentExecutionResult:
        """Conduct research on the given query."""
        prompt = f"Conduct comprehensive research on: {research_query}"
        return await self.execute(prompt, context)


class TaskOrchestrationAgent(BaseDeepAgent):
    """Agent specialized for task orchestration and subagent management."""

    def __init__(self, config: AgentConfig | None = None):
        if config is None:
            config = AgentConfig(
                name="orchestration-agent",
                system_prompt="You are a task orchestration specialist focused on coordinating multiple agents and tasks.",
                tools=["write_todos", "task"],
                capabilities=[
                    AgentCapability.TASK_ORCHESTRATION,
                    AgentCapability.PLANNING,
                ],
            )
        super().__init__(config)

    async def orchestrate_tasks(
        self, task_description: str, context: DeepAgentState | None = None
    ) -> AgentExecutionResult:
        """Orchestrate tasks using subagents."""
        prompt = f"Orchestrate the following complex task using appropriate subagents: {task_description}"
        return await self.execute(prompt, context)


class GeneralPurposeAgent(BaseDeepAgent):
    """General-purpose agent with all capabilities."""

    def __init__(self, config: AgentConfig | None = None):
        if config is None:
            config = AgentConfig(
                name="general-purpose-agent",
                system_prompt="You are a general-purpose AI assistant with access to various tools and capabilities.",
                tools=[
                    "write_todos",
                    "list_files",
                    "read_file",
                    "write_file",
                    "edit_file",
                    "task",
                ],
                capabilities=[
                    AgentCapability.PLANNING,
                    AgentCapability.FILESYSTEM,
                    AgentCapability.SEARCH,
                    AgentCapability.ANALYSIS,
                    AgentCapability.TASK_ORCHESTRATION,
                ],
            )
        super().__init__(config)


class AgentOrchestrator:
    """Orchestrator for managing multiple agents."""

    def __init__(self, agents: list[BaseDeepAgent] | None = None):
        self.agents: dict[str, BaseDeepAgent] = {}
        self.agent_registry: dict[str, Agent] = {}

        if agents:
            for agent in agents:
                self.register_agent(agent)

    def register_agent(self, agent: BaseDeepAgent) -> None:
        """Register an agent with the orchestrator."""
        self.agents[agent.config.name] = agent
        if agent.agent:
            self.agent_registry[agent.config.name] = agent.agent

    def get_agent(self, name: str) -> BaseDeepAgent | None:
        """Get an agent by name."""
        return self.agents.get(name)

    async def execute_with_agent(
        self,
        agent_name: str,
        input_data: str | dict[str, Any],
        context: DeepAgentState | None = None,
    ) -> AgentExecutionResult:
        """Execute a specific agent."""
        agent = self.get_agent(agent_name)
        if not agent:
            return AgentExecutionResult(
                success=False,
                error=f"Agent '{agent_name}' not found",
                execution_time=0.0,
            )

        return await agent.execute(input_data, context)

    async def execute_parallel(
        self, tasks: list[dict[str, Any]], context: DeepAgentState | None = None
    ) -> list[AgentExecutionResult]:
        """Execute multiple tasks in parallel."""

        async def execute_task(task):
            agent_name = task.get("agent_name")
            input_data = task.get("input_data")
            return await self.execute_with_agent(agent_name, input_data, context)

        tasks_coroutines = [execute_task(task) for task in tasks]
        results = await asyncio.gather(*tasks_coroutines, return_exceptions=True)
        # Filter out exceptions and return only successful results
        return [r for r in results if isinstance(r, AgentExecutionResult)]

    def get_all_metrics(self) -> dict[str, AgentMetrics]:
        """Get metrics for all registered agents."""
        return {name: agent.get_metrics() for name, agent in self.agents.items()}


# Factory functions
def create_planning_agent(config: AgentConfig | None = None) -> PlanningAgent:
    """Create a planning agent."""
    return PlanningAgent(config)


def create_filesystem_agent(config: AgentConfig | None = None) -> FilesystemAgent:
    """Create a filesystem agent."""
    return FilesystemAgent(config)


def create_research_agent(config: AgentConfig | None = None) -> ResearchAgent:
    """Create a research agent."""
    return ResearchAgent(config)


def create_task_orchestration_agent(
    config: AgentConfig | None = None,
) -> TaskOrchestrationAgent:
    """Create a task orchestration agent."""
    return TaskOrchestrationAgent(config)


def create_general_purpose_agent(
    config: AgentConfig | None = None,
) -> GeneralPurposeAgent:
    """Create a general-purpose agent."""
    return GeneralPurposeAgent(config)


def create_agent_orchestrator(
    agent_types: list[str] | None = None,
) -> AgentOrchestrator:
    """Create an agent orchestrator with default agents."""
    if agent_types is None:
        agent_types = ["planning", "filesystem", "research", "orchestration", "general"]

    agents = []
    for agent_type in agent_types:
        if agent_type == "planning":
            agents.append(create_planning_agent())
        elif agent_type == "filesystem":
            agents.append(create_filesystem_agent())
        elif agent_type == "research":
            agents.append(create_research_agent())
        elif agent_type == "orchestration":
            agents.append(create_task_orchestration_agent())
        elif agent_type == "general":
            agents.append(create_general_purpose_agent())

    return AgentOrchestrator(agents)


# Export all components
__all__ = [
    # Configuration and results
    "AgentConfig",
    "AgentExecutionResult",
    # Orchestrator
    "AgentOrchestrator",
    # Base class
    "BaseDeepAgent",
    # Main implementation class
    "DeepAgentImplementation",
    "FilesystemAgent",
    "GeneralPurposeAgent",
    # Specialized agents
    "PlanningAgent",
    "ResearchAgent",
    "TaskOrchestrationAgent",
    "create_agent_orchestrator",
    "create_filesystem_agent",
    "create_general_purpose_agent",
    # Factory functions
    "create_planning_agent",
    "create_research_agent",
    "create_task_orchestration_agent",
]


@dataclass
class DeepAgentImplementation:
    """Main DeepAgent implementation that coordinates multiple specialized agents."""

    config: AgentConfig
    agents: dict[str, BaseDeepAgent] = field(default_factory=dict)
    orchestrator: AgentOrchestrator | None = None

    def __post_init__(self):
        """Initialize the DeepAgent implementation."""
        self._initialize_agents()
        self._initialize_orchestrator()

    def _initialize_agents(self):
        """Initialize all specialized agents."""
        self.agents = {
            "planning": create_planning_agent(self.config),
            "filesystem": create_filesystem_agent(self.config),
            "research": create_research_agent(self.config),
            "task_orchestration": create_task_orchestration_agent(self.config),
            "general_purpose": create_general_purpose_agent(self.config),
        }

    def _initialize_orchestrator(self):
        """Initialize the agent orchestrator."""
        self.orchestrator = create_agent_orchestrator()

    async def execute_task(self, task: str) -> AgentExecutionResult:
        """Execute a task using the appropriate agent."""
        return (
            await self.orchestrator.execute_task(task)
            if self.orchestrator
            else AgentExecutionResult(
                success=False, error="Orchestrator not initialized"
            )
        )

    def get_agent(self, agent_type: str) -> BaseDeepAgent | None:
        """Get a specific agent by type."""
        return self.agents.get(agent_type)
