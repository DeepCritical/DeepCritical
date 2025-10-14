"""
Workflow Pattern Integration - Main integration module for agent interaction design patterns.

This module provides the main entry points and factory functions for using
agent interaction design patterns with minimal external dependencies.
"""

from __future__ import annotations

import asyncio
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from .agents.workflow_pattern_agents import (
    AdaptivePatternAgent,
    CollaborativePatternAgent,
    HierarchicalPatternAgent,
    PatternOrchestratorAgent,
    SequentialPatternAgent,
    create_adaptive_pattern_agent,
    create_collaborative_agent,
    create_hierarchical_agent,
    create_pattern_orchestrator,
    create_sequential_agent,
)
from .datatypes.agents import AgentDependencies, AgentType

# Import all the core components
from .datatypes.workflow_patterns import (
    AgentInteractionRequest,
    AgentInteractionResponse,
    AgentInteractionState,
    InteractionConfig,
    InteractionMessage,
    InteractionPattern,
    MessageType,
    WorkflowOrchestrator,
)
from .statemachines.workflow_pattern_statemachines import (
    run_collaborative_pattern_workflow,
    run_hierarchical_pattern_workflow,
    run_pattern_workflow,
    run_sequential_pattern_workflow,
)
from .utils.workflow_patterns import (
    ConsensusAlgorithm,
    InteractionMetrics,
    MessageRoutingStrategy,
    WorkflowPatternUtils,
)


class WorkflowPatternConfig(BaseModel):
    """Configuration for workflow pattern execution."""

    pattern: InteractionPattern = Field(..., description="Interaction pattern to use")
    max_rounds: int = Field(10, description="Maximum number of interaction rounds")
    consensus_threshold: float = Field(
        0.8, description="Consensus threshold for collaborative patterns"
    )
    timeout: float = Field(300.0, description="Timeout in seconds")
    enable_monitoring: bool = Field(True, description="Enable execution monitoring")
    enable_caching: bool = Field(True, description="Enable result caching")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "enable_caching": True,
                "cache_ttl": 3600,
                "max_parallel_tasks": 5,
            }
        }
    )


class AgentExecutorRegistry:
    """Registry for agent executors."""

    def __init__(self):
        self._executors: dict[str, Any] = {}

    def register(self, agent_id: str, executor: Any) -> None:
        """Register an agent executor."""
        self._executors[agent_id] = executor

    def get(self, agent_id: str) -> Any | None:
        """Get an agent executor."""
        return self._executors.get(agent_id)

    def list(self) -> list[str]:
        """List all registered agent IDs."""
        return list(self._executors.keys())

    def clear(self) -> None:
        """Clear all registered executors."""
        self._executors.clear()


# Global registry instance
agent_registry = AgentExecutorRegistry()


class WorkflowPatternFactory:
    """Factory for creating workflow pattern components."""

    @staticmethod
    def create_interaction_state(
        pattern: InteractionPattern = InteractionPattern.COLLABORATIVE,
        agents: list[str] | None = None,
        agent_types: dict[str, AgentType] | None = None,
        config: dict[str, Any] | None = None,
    ) -> AgentInteractionState:
        """Create a new interaction state."""
        state = AgentInteractionState(pattern=pattern)

        if agents and agent_types:
            for agent_id in agents:
                agent_type = agent_types.get(agent_id, AgentType.EXECUTOR)
                state.add_agent(agent_id, agent_type)

        if config:
            if "max_rounds" in config:
                state.max_rounds = config["max_rounds"]
            if "consensus_threshold" in config:
                state.consensus_threshold = config["consensus_threshold"]

        return state

    @staticmethod
    def create_orchestrator(
        interaction_state: AgentInteractionState,
        agent_executors: dict[str, Any] | None = None,
    ) -> WorkflowOrchestrator:
        """Create a workflow orchestrator."""
        orchestrator = WorkflowOrchestrator(interaction_state)

        if agent_executors:
            for agent_id, executor in agent_executors.items():
                orchestrator.register_agent_executor(agent_id, executor)

        return orchestrator

    @staticmethod
    def create_collaborative_agent(
        model_name: str = "anthropic:claude-sonnet-4-0",
        dependencies: AgentDependencies | None = None,
    ) -> CollaborativePatternAgent:
        """Create a collaborative pattern agent."""
        return create_collaborative_agent(model_name, dependencies)

    @staticmethod
    def create_sequential_agent(
        model_name: str = "anthropic:claude-sonnet-4-0",
        dependencies: AgentDependencies | None = None,
    ) -> SequentialPatternAgent:
        """Create a sequential pattern agent."""
        return create_sequential_agent(model_name, dependencies)

    @staticmethod
    def create_hierarchical_agent(
        model_name: str = "anthropic:claude-sonnet-4-0",
        dependencies: AgentDependencies | None = None,
    ) -> HierarchicalPatternAgent:
        """Create a hierarchical pattern agent."""
        return create_hierarchical_agent(model_name, dependencies)

    @staticmethod
    def create_pattern_orchestrator(
        model_name: str = "anthropic:claude-sonnet-4-0",
        dependencies: AgentDependencies | None = None,
    ) -> PatternOrchestratorAgent:
        """Create a pattern orchestrator agent."""
        return create_pattern_orchestrator(model_name, dependencies)

    @staticmethod
    def create_adaptive_pattern_agent(
        model_name: str = "anthropic:claude-sonnet-4-0",
        dependencies: AgentDependencies | None = None,
    ) -> AdaptivePatternAgent:
        """Create an adaptive pattern agent."""
        return create_adaptive_pattern_agent(model_name, dependencies)


class WorkflowPatternExecutor:
    """Main executor for workflow patterns."""

    def __init__(self, config: WorkflowPatternConfig | None = None):
        self.config = config or WorkflowPatternConfig()
        self.factory = WorkflowPatternFactory()
        self.registry = agent_registry

    async def execute_collaborative_pattern(
        self,
        question: str,
        agents: list[str],
        agent_types: dict[str, AgentType],
        agent_executors: dict[str, Any] | None = None,
    ) -> str:
        """Execute collaborative pattern workflow."""
        return await run_collaborative_pattern_workflow(
            question=question,
            agents=agents,
            agent_types=agent_types,
            agent_executors=agent_executors or {},
            config=self.config.dict(),
        )

    async def execute_sequential_pattern(
        self,
        question: str,
        agents: list[str],
        agent_types: dict[str, AgentType],
        agent_executors: dict[str, Any] | None = None,
    ) -> str:
        """Execute sequential pattern workflow."""
        return await run_sequential_pattern_workflow(
            question=question,
            agents=agents,
            agent_types=agent_types,
            agent_executors=agent_executors or {},
            config=self.config.dict(),
        )

    async def execute_hierarchical_pattern(
        self,
        question: str,
        coordinator_id: str,
        subordinate_ids: list[str],
        agent_types: dict[str, AgentType],
        agent_executors: dict[str, Any] | None = None,
    ) -> str:
        """Execute hierarchical pattern workflow."""
        return await run_hierarchical_pattern_workflow(
            question=question,
            coordinator_id=coordinator_id,
            subordinate_ids=subordinate_ids,
            agent_types=agent_types,
            agent_executors=agent_executors or {},
            config=self.config.dict(),
        )

    async def execute_pattern(
        self,
        question: str,
        pattern: InteractionPattern,
        agents: list[str],
        agent_types: dict[str, AgentType],
        agent_executors: dict[str, Any] | None = None,
    ) -> str:
        """Execute workflow with specified pattern."""
        return await run_pattern_workflow(
            question=question,
            pattern=pattern,
            agents=agents,
            agent_types=agent_types,
            agent_executors=agent_executors or {},
            config=self.config.dict(),
        )


# Global executor instance
workflow_executor = WorkflowPatternExecutor()


# Main API functions
async def execute_workflow_pattern(
    question: str,
    pattern: InteractionPattern,
    agents: list[str],
    agent_types: dict[str, AgentType],
    agent_executors: dict[str, Any] | None = None,
    config: dict[str, Any] | None = None,
) -> str:
    """
    Execute a workflow pattern with the given agents and configuration.

    Args:
        question: The question to answer
        pattern: The interaction pattern to use
        agents: List of agent IDs
        agent_types: Mapping of agent IDs to agent types
        agent_executors: Optional mapping of agent IDs to executor functions
        config: Optional configuration overrides

    Returns:
        The workflow execution result
    """
    executor = WorkflowPatternExecutor(
        WorkflowPatternConfig(**config) if config else None
    )

    return await executor.execute_pattern(
        question=question,
        pattern=pattern,
        agents=agents,
        agent_types=agent_types,
        agent_executors=agent_executors,
    )


async def execute_collaborative_workflow(
    question: str,
    agents: list[str],
    agent_types: dict[str, AgentType],
    agent_executors: dict[str, Any] | None = None,
    config: dict[str, Any] | None = None,
) -> str:
    """
    Execute a collaborative workflow pattern.

    Args:
        question: The question to answer
        agents: List of agent IDs
        agent_types: Mapping of agent IDs to agent types
        agent_executors: Optional mapping of agent IDs to executor functions
        config: Optional configuration overrides

    Returns:
        The collaborative workflow result
    """
    return await execute_workflow_pattern(
        question=question,
        pattern=InteractionPattern.COLLABORATIVE,
        agents=agents,
        agent_types=agent_types,
        agent_executors=agent_executors,
        config=config,
    )


async def execute_sequential_workflow(
    question: str,
    agents: list[str],
    agent_types: dict[str, AgentType],
    agent_executors: dict[str, Any] | None = None,
    config: dict[str, Any] | None = None,
) -> str:
    """
    Execute a sequential workflow pattern.

    Args:
        question: The question to answer
        agents: List of agent IDs in execution order
        agent_types: Mapping of agent IDs to agent types
        agent_executors: Optional mapping of agent IDs to executor functions
        config: Optional configuration overrides

    Returns:
        The sequential workflow result
    """
    return await execute_workflow_pattern(
        question=question,
        pattern=InteractionPattern.SEQUENTIAL,
        agents=agents,
        agent_types=agent_types,
        agent_executors=agent_executors,
        config=config,
    )


async def execute_hierarchical_workflow(
    question: str,
    coordinator_id: str,
    subordinate_ids: list[str],
    agent_types: dict[str, AgentType],
    agent_executors: dict[str, Any] | None = None,
    config: dict[str, Any] | None = None,
) -> str:
    """
    Execute a hierarchical workflow pattern.

    Args:
        question: The question to answer
        coordinator_id: ID of the coordinator agent
        subordinate_ids: List of subordinate agent IDs
        agent_types: Mapping of agent IDs to agent types
        agent_executors: Optional mapping of agent IDs to executor functions
        config: Optional configuration overrides

    Returns:
        The hierarchical workflow result
    """
    all_agents = [coordinator_id, *subordinate_ids]

    return await execute_workflow_pattern(
        question=question,
        pattern=InteractionPattern.HIERARCHICAL,
        agents=all_agents,
        agent_types=agent_types,
        agent_executors=agent_executors,
        config=config,
    )


# Example usage functions
async def example_collaborative_workflow():
    """Example of using collaborative workflow pattern."""

    # Define agents
    agents = ["parser", "planner", "executor"]
    agent_types = {
        "parser": AgentType.PARSER,
        "planner": AgentType.PLANNER,
        "executor": AgentType.EXECUTOR,
    }

    # Define mock agent executors
    agent_executors = {
        "parser": lambda messages: {
            "result": "Parsed question successfully",
            "confidence": 0.9,
        },
        "planner": lambda messages: {
            "result": "Created execution plan",
            "confidence": 0.85,
        },
        "executor": lambda messages: {
            "result": "Executed plan successfully",
            "confidence": 0.8,
        },
    }

    # Execute workflow
    return await execute_collaborative_workflow(
        question="What is machine learning?",
        agents=agents,
        agent_types=agent_types,
        agent_executors=agent_executors,
    )


async def example_sequential_workflow():
    """Example of using sequential workflow pattern."""

    # Define agents in execution order
    agents = ["analyzer", "researcher", "synthesizer"]
    agent_types = {
        "analyzer": AgentType.PARSER,
        "researcher": AgentType.SEARCH,
        "synthesizer": AgentType.EXECUTOR,
    }

    # Define mock agent executors
    agent_executors = {
        "analyzer": lambda messages: {
            "result": "Analyzed requirements",
            "confidence": 0.9,
        },
        "researcher": lambda messages: {
            "result": "Gathered research data",
            "confidence": 0.85,
        },
        "synthesizer": lambda messages: {
            "result": "Synthesized final answer",
            "confidence": 0.8,
        },
    }

    # Execute workflow
    return await execute_sequential_workflow(
        question="Explain quantum computing",
        agents=agents,
        agent_types=agent_types,
        agent_executors=agent_executors,
    )


async def example_hierarchical_workflow():
    """Example of using hierarchical workflow pattern."""

    # Define coordinator and subordinates
    coordinator_id = "orchestrator"
    subordinate_ids = ["specialist1", "specialist2", "validator"]
    # agents = [coordinator_id] + subordinate_ids

    agent_types = {
        coordinator_id: AgentType.ORCHESTRATOR,
        subordinate_ids[0]: AgentType.SEARCH,
        subordinate_ids[1]: AgentType.RAG,
        subordinate_ids[2]: AgentType.EVALUATOR,
    }

    # Define mock agent executors
    agent_executors = {
        coordinator_id: lambda messages: {
            "result": "Coordinated workflow",
            "confidence": 0.95,
        },
        subordinate_ids[0]: lambda messages: {
            "result": "Specialized search",
            "confidence": 0.85,
        },
        subordinate_ids[1]: lambda messages: {
            "result": "RAG processing",
            "confidence": 0.9,
        },
        subordinate_ids[2]: lambda messages: {
            "result": "Validated results",
            "confidence": 0.8,
        },
    }

    # Execute workflow
    return await execute_hierarchical_workflow(
        question="Analyze the impact of AI on healthcare",
        coordinator_id=coordinator_id,
        subordinate_ids=subordinate_ids,
        agent_types=agent_types,
        agent_executors=agent_executors,
    )


# Main demonstration function
async def demonstrate_workflow_patterns():
    """Demonstrate all workflow pattern types."""

    # Run examples
    await example_collaborative_workflow()

    await example_sequential_workflow()

    await example_hierarchical_workflow()


# CLI interface for testing
def main():
    """Main CLI entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="DeepCritical Workflow Patterns Demo")
    parser.add_argument(
        "--pattern",
        choices=["collaborative", "sequential", "hierarchical", "all"],
        default="all",
        help="Pattern to demonstrate",
    )
    parser.add_argument(
        "--question", default="What is machine learning?", help="Question to process"
    )

    args = parser.parse_args()

    async def run_demo():
        if args.pattern == "all":
            await demonstrate_workflow_patterns()
        elif args.pattern == "collaborative":
            await example_collaborative_workflow()
        elif args.pattern == "sequential":
            await example_sequential_workflow()
        elif args.pattern == "hierarchical":
            await example_hierarchical_workflow()

    asyncio.run(run_demo())


if __name__ == "__main__":
    main()


# Export all public APIs
__all__ = [
    "AdaptivePatternAgent",
    "AgentExecutorRegistry",
    "AgentInteractionRequest",
    "AgentInteractionResponse",
    "AgentInteractionState",
    # Agent classes
    "CollaborativePatternAgent",
    "ConsensusAlgorithm",
    "HierarchicalPatternAgent",
    "InteractionConfig",
    "InteractionMessage",
    "InteractionMetrics",
    # Core types
    "InteractionPattern",
    "MessageRoutingStrategy",
    "MessageType",
    "PatternOrchestratorAgent",
    "SequentialPatternAgent",
    "WorkflowOrchestrator",
    # Configuration
    "WorkflowPatternConfig",
    "WorkflowPatternExecutor",
    # Factory classes
    "WorkflowPatternFactory",
    # Utilities
    "WorkflowPatternUtils",
    "agent_registry",
    "create_adaptive_pattern_agent",
    # Factory functions for agents
    "create_collaborative_agent",
    "create_hierarchical_agent",
    "create_pattern_orchestrator",
    "create_sequential_agent",
    # Demo functions
    "demonstrate_workflow_patterns",
    "example_collaborative_workflow",
    "example_hierarchical_workflow",
    "example_sequential_workflow",
    "execute_collaborative_workflow",
    "execute_hierarchical_workflow",
    "execute_sequential_workflow",
    # Execution functions
    "execute_workflow_pattern",
    # CLI
    "main",
    # Global instances
    "workflow_executor",
]
