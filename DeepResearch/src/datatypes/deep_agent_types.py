"""
DeepAgent Types - Pydantic models for DeepAgent system components.

This module defines Pydantic models for subagents, custom agents, and related
types that align with DeepCritical's Pydantic AI architecture.
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional, Protocol

from pydantic import BaseModel, Field, field_validator

# Import existing DeepCritical types


class DeepAgentType(str, Enum):
    """Types of DeepAgent implementations."""

    BASIC = "basic"
    ADVANCED = "advanced"
    SPECIALIZED = "specialized"
    CUSTOM = "custom"


class AgentCapability(str, Enum):
    """Capabilities that agents can have."""

    PLANNING = "planning"
    FILESYSTEM = "filesystem"
    SEARCH = "search"
    ANALYSIS = "analysis"
    CODE_GENERATION = "code_generation"
    DATA_PROCESSING = "data_processing"
    BIOINFORMATICS = "bioinformatics"
    RAG = "rag"
    WEB_SEARCH = "web_search"
    TASK_ORCHESTRATION = "task_orchestration"


class ModelProvider(str, Enum):
    """Supported model providers."""

    ANTHROPIC = "anthropic"
    OPENAI = "openai"
    HUGGINGFACE = "huggingface"
    VLLM = "vllm"
    CUSTOM = "custom"


class ModelConfig(BaseModel):
    """Configuration for model instances."""

    provider: ModelProvider = Field(..., description="Model provider")
    model_name: str = Field(..., description="Model name or identifier")
    api_key: str | None = Field(None, description="API key if required")
    base_url: str | None = Field(None, description="Base URL for API")
    temperature: float = Field(0.7, ge=0.0, le=2.0, description="Sampling temperature")
    max_tokens: int = Field(2048, gt=0, description="Maximum tokens to generate")
    timeout: float = Field(30.0, gt=0, description="Request timeout in seconds")

    class Config:
        json_schema_extra = {
            "example": {
                "provider": "anthropic",
                "model_name": "claude-sonnet-4-0",
                "temperature": 0.7,
                "max_tokens": 2048,
            }
        }


class ToolConfig(BaseModel):
    """Configuration for tools."""

    name: str = Field(..., description="Tool name")
    description: str = Field(..., description="Tool description")
    parameters: dict[str, Any] = Field(
        default_factory=dict, description="Tool parameters"
    )
    enabled: bool = Field(True, description="Whether tool is enabled")

    class Config:
        json_schema_extra = {
            "example": {
                "name": "web_search",
                "description": "Search the web for information",
                "parameters": {"max_results": 10},
                "enabled": True,
            }
        }


class SubAgent(BaseModel):
    """Configuration for a subagent."""

    name: str = Field(..., description="Subagent name")
    description: str = Field(..., description="Subagent description")
    prompt: str = Field(..., description="System prompt for the subagent")
    capabilities: list[AgentCapability] = Field(
        default_factory=list, description="Agent capabilities"
    )
    tools: list[ToolConfig] = Field(default_factory=list, description="Available tools")
    model: ModelConfig | None = Field(None, description="Model configuration")
    middleware: list[str] = Field(
        default_factory=list, description="Middleware components"
    )
    max_iterations: int = Field(10, gt=0, description="Maximum iterations")
    timeout: float = Field(300.0, gt=0, description="Execution timeout in seconds")

    @field_validator("name", mode="before")
    @classmethod
    def validate_name(cls, v):
        if not v or not v.strip():
            raise ValueError("Subagent name cannot be empty")
        return v.strip()

    @field_validator("description", mode="before")
    @classmethod
    def validate_description(cls, v):
        if not v or not v.strip():
            raise ValueError("Subagent description cannot be empty")
        return v.strip()

    class Config:
        json_schema_extra = {
            "example": {
                "name": "research-analyst",
                "description": "Conducts thorough research on complex topics",
                "prompt": "You are a research analyst...",
                "capabilities": ["search", "analysis", "rag"],
                "tools": [
                    {
                        "name": "web_search",
                        "description": "Search the web",
                        "enabled": True,
                    }
                ],
                "max_iterations": 10,
                "timeout": 300.0,
            }
        }


class CustomSubAgent(BaseModel):
    """Configuration for a custom subagent with graph-based execution."""

    name: str = Field(..., description="Custom subagent name")
    description: str = Field(..., description="Custom subagent description")
    graph_config: dict[str, Any] = Field(..., description="Graph configuration")
    entry_point: str = Field(..., description="Graph entry point")
    capabilities: list[AgentCapability] = Field(
        default_factory=list, description="Agent capabilities"
    )
    timeout: float = Field(300.0, gt=0, description="Execution timeout in seconds")

    @field_validator("name", mode="before")
    @classmethod
    def validate_name(cls, v):
        if not v or not v.strip():
            raise ValueError("Custom subagent name cannot be empty")
        return v.strip()

    @field_validator("description", mode="before")
    @classmethod
    def validate_description(cls, v):
        if not v or not v.strip():
            raise ValueError("Custom subagent description cannot be empty")
        return v.strip()

    class Config:
        json_schema_extra = {
            "example": {
                "name": "bioinformatics-pipeline",
                "description": "Executes bioinformatics analysis pipeline",
                "graph_config": {
                    "nodes": ["parse", "analyze", "report"],
                    "edges": [["parse", "analyze"], ["analyze", "report"]],
                },
                "entry_point": "parse",
                "capabilities": ["bioinformatics", "data_processing"],
                "timeout": 600.0,
            }
        }


class AgentOrchestrationConfig(BaseModel):
    """Configuration for agent orchestration."""

    max_concurrent_agents: int = Field(5, gt=0, description="Maximum concurrent agents")
    default_timeout: float = Field(
        300.0, gt=0, description="Default timeout for agents"
    )
    retry_attempts: int = Field(3, ge=0, description="Number of retry attempts")
    retry_delay: float = Field(1.0, gt=0, description="Delay between retries")
    enable_parallel_execution: bool = Field(
        True, description="Enable parallel execution"
    )
    enable_failure_recovery: bool = Field(True, description="Enable failure recovery")

    class Config:
        json_schema_extra = {
            "example": {
                "max_concurrent_agents": 5,
                "default_timeout": 300.0,
                "retry_attempts": 3,
                "retry_delay": 1.0,
                "enable_parallel_execution": True,
                "enable_failure_recovery": True,
            }
        }


class TaskRequest(BaseModel):
    """Request for task execution."""

    task_id: str = Field(..., description="Unique task identifier")
    description: str = Field(..., description="Task description")
    subagent_type: str = Field(..., description="Type of subagent to use")
    parameters: dict[str, Any] = Field(
        default_factory=dict, description="Task parameters"
    )
    priority: int = Field(0, description="Task priority (higher = more important)")
    dependencies: list[str] = Field(
        default_factory=list, description="Task dependencies"
    )
    timeout: float | None = Field(None, description="Task timeout override")

    @field_validator("description", mode="before")
    @classmethod
    def validate_description(cls, v):
        if not v or not v.strip():
            raise ValueError("Task description cannot be empty")
        return v.strip()

    class Config:
        json_schema_extra = {
            "example": {
                "task_id": "task_001",
                "description": "Research the latest developments in CRISPR technology",
                "subagent_type": "research-analyst",
                "parameters": {
                    "depth": "comprehensive",
                    "sources": ["pubmed", "arxiv"],
                },
                "priority": 1,
                "dependencies": [],
                "timeout": 600.0,
            }
        }


class TaskResult(BaseModel):
    """Result from task execution."""

    task_id: str = Field(..., description="Task identifier")
    success: bool = Field(..., description="Whether task succeeded")
    result: dict[str, Any] | None = Field(None, description="Task result data")
    error: str | None = Field(None, description="Error message if failed")
    execution_time: float = Field(..., description="Execution time in seconds")
    subagent_used: str = Field(..., description="Subagent that executed the task")
    metadata: dict[str, Any] = Field(
        default_factory=dict, description="Additional metadata"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "task_id": "task_001",
                "success": True,
                "result": {
                    "summary": "CRISPR technology has advanced significantly...",
                    "sources": ["pubmed:123456", "arxiv:2023.12345"],
                },
                "execution_time": 45.2,
                "subagent_used": "research-analyst",
                "metadata": {"tokens_used": 1500, "sources_found": 12},
            }
        }


class AgentContext(BaseModel):
    """Context for agent execution."""

    session_id: str = Field(..., description="Session identifier")
    user_id: str | None = Field(None, description="User identifier")
    conversation_history: list[dict[str, Any]] = Field(
        default_factory=list, description="Conversation history"
    )
    shared_state: dict[str, Any] = Field(
        default_factory=dict, description="Shared state between agents"
    )
    active_tasks: list[str] = Field(
        default_factory=list, description="Currently active task IDs"
    )
    completed_tasks: list[str] = Field(
        default_factory=list, description="Completed task IDs"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "session_id": "session_123",
                "user_id": "user_456",
                "conversation_history": [
                    {"role": "user", "content": "Research CRISPR technology"},
                    {
                        "role": "assistant",
                        "content": "I'll help you research CRISPR...",
                    },
                ],
                "shared_state": {"research_focus": "CRISPR applications"},
                "active_tasks": ["task_001"],
                "completed_tasks": [],
            }
        }


class AgentMetrics(BaseModel):
    """Metrics for agent performance."""

    agent_name: str = Field(..., description="Agent name")
    total_tasks: int = Field(0, description="Total tasks executed")
    successful_tasks: int = Field(0, description="Successfully completed tasks")
    failed_tasks: int = Field(0, description="Failed tasks")
    average_execution_time: float = Field(0.0, description="Average execution time")
    total_tokens_used: int = Field(0, description="Total tokens used")
    last_activity: str | None = Field(None, description="Last activity timestamp")

    @property
    def success_rate(self) -> float:
        """Calculate success rate."""
        if self.total_tasks == 0:
            return 0.0
        return self.successful_tasks / self.total_tasks

    class Config:
        json_schema_extra = {
            "example": {
                "agent_name": "research-analyst",
                "total_tasks": 100,
                "successful_tasks": 95,
                "failed_tasks": 5,
                "average_execution_time": 45.2,
                "total_tokens_used": 150000,
                "last_activity": "2024-01-15T10:30:00Z",
            }
        }


# Protocol for agent execution
class AgentExecutor(Protocol):
    """Protocol for agent execution."""

    async def execute_task(
        self, task: TaskRequest, context: AgentContext
    ) -> TaskResult:
        """Execute a task with the given context."""
        ...

    async def get_metrics(self) -> AgentMetrics:
        """Get agent performance metrics."""
        ...


# Factory functions
def create_subagent(
    name: str,
    description: str,
    prompt: str,
    capabilities: list[AgentCapability] | None = None,
    tools: list[ToolConfig] | None = None,
    model: ModelConfig | None = None,
    **kwargs,
) -> SubAgent:
    """Create a SubAgent with default values."""
    return SubAgent(
        name=name,
        description=description,
        prompt=prompt,
        capabilities=capabilities or [],
        tools=tools or [],
        model=model,
        **kwargs,
    )


def create_custom_subagent(
    name: str,
    description: str,
    graph_config: dict[str, Any],
    entry_point: str,
    capabilities: list[AgentCapability] | None = None,
    **kwargs,
) -> CustomSubAgent:
    """Create a CustomSubAgent with default values."""
    return CustomSubAgent(
        name=name,
        description=description,
        graph_config=graph_config,
        entry_point=entry_point,
        capabilities=capabilities or [],
        **kwargs,
    )


def create_model_config(
    provider: ModelProvider, model_name: str, **kwargs
) -> ModelConfig:
    """Create a ModelConfig with default values."""
    return ModelConfig(provider=provider, model_name=model_name, **kwargs)
