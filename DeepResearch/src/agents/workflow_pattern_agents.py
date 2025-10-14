"""
Workflow Pattern Agents - Pydantic AI agents for workflow pattern execution.

This module provides specialized agents for executing workflow interaction patterns,
integrating with the existing DeepCritical agent system and workflow patterns.
"""

from __future__ import annotations

import time
from typing import Any

from DeepResearch.agents import BaseAgent  # Use top-level BaseAgent to satisfy linters
from DeepResearch.src.datatypes.agents import AgentDependencies, AgentResult, AgentType
from DeepResearch.src.datatypes.workflow_patterns import InteractionPattern
from DeepResearch.src.prompts.workflow_pattern_agents import WorkflowPatternAgentPrompts
from DeepResearch.src.statemachines.workflow_pattern_statemachines import (
    run_collaborative_pattern_workflow,
    run_hierarchical_pattern_workflow,
    run_sequential_pattern_workflow,
)
from DeepResearch.src.utils.workflow_patterns import ConsensusAlgorithm


class WorkflowPatternAgent(BaseAgent):
    """Base agent for workflow pattern execution."""

    def __init__(
        self,
        pattern: InteractionPattern,
        model_name: str = "anthropic:claude-sonnet-4-0",
        dependencies: AgentDependencies | None = None,
    ):
        super().__init__(
            agent_type=AgentType.ORCHESTRATOR,
            model_name=model_name,
            dependencies=dependencies,
        )
        self.pattern = pattern

    def _get_default_system_prompt(self) -> str:
        """Get default system prompt for workflow pattern agents."""
        prompts = WorkflowPatternAgentPrompts()
        return prompts.get_system_prompt(self.pattern.value)

    def _get_default_instructions(self) -> str:
        """Get default instructions for workflow pattern agents."""
        prompts = WorkflowPatternAgentPrompts()
        instructions = prompts.get_instructions(self.pattern.value)
        return "\n".join(instructions)

    def _register_tools(self):
        """Register tools for workflow pattern execution."""
        # Register pattern-specific tools

        # Add tools to agent
        if self._agent:
            # Note: In a real implementation, these would be added as tool functions
            # For now, we're registering them conceptually
            pass

    async def execute_pattern(
        self,
        agents: list[str],
        agent_types: dict[str, AgentType],
        agent_executors: dict[str, Any],
        input_data: dict[str, Any],
        config: dict[str, Any] | None = None,
    ) -> AgentResult:
        """Execute the workflow pattern."""
        try:
            start_time = time.time()

            # Use the appropriate workflow execution function
            if self.pattern == InteractionPattern.COLLABORATIVE:
                result = await run_collaborative_pattern_workflow(
                    question=input_data.get("question", ""),
                    agents=agents,
                    agent_types=agent_types,
                    agent_executors=agent_executors,
                    config=self.dependencies.config,
                )
            elif self.pattern == InteractionPattern.SEQUENTIAL:
                result = await run_sequential_pattern_workflow(
                    question=input_data.get("question", ""),
                    agents=agents,
                    agent_types=agent_types,
                    agent_executors=agent_executors,
                    config=self.dependencies.config,
                )
            elif self.pattern == InteractionPattern.HIERARCHICAL:
                coordinator_id = input_data.get(
                    "coordinator_id", agents[0] if agents else ""
                )
                subordinate_ids = input_data.get(
                    "subordinate_ids", agents[1:] if len(agents) > 1 else []
                )

                result = await run_hierarchical_pattern_workflow(
                    question=input_data.get("question", ""),
                    coordinator_id=coordinator_id,
                    subordinate_ids=subordinate_ids,
                    agent_types=agent_types,
                    agent_executors=agent_executors,
                    config=self.dependencies.config,
                )
            else:
                return AgentResult(
                    success=False,
                    error=f"Unsupported pattern: {self.pattern}",
                    agent_type=self.agent_type,
                )

            execution_time = time.time() - start_time

            return AgentResult(
                success=True,
                data={
                    "result": result,
                    "pattern": self.pattern.value,
                    "execution_time": execution_time,
                    "agents_involved": len(agents),
                },
                metadata={
                    "pattern": self.pattern.value,
                    "agents": agents,
                    "execution_time": execution_time,
                },
                agent_type=self.agent_type,
                execution_time=execution_time,
            )

        except Exception as e:
            return AgentResult(
                success=False,
                error=str(e),
                agent_type=self.agent_type,
            )


class CollaborativePatternAgent(WorkflowPatternAgent):
    """Agent for collaborative interaction patterns."""

    def __init__(
        self,
        model_name: str = "anthropic:claude-sonnet-4-0",
        dependencies: AgentDependencies | None = None,
    ):
        super().__init__(
            pattern=InteractionPattern.COLLABORATIVE,
            model_name=model_name,
            dependencies=dependencies,
        )

    def _get_default_system_prompt(self) -> str:
        """Get default system prompt for collaborative pattern agent."""
        prompts = WorkflowPatternAgentPrompts()
        return prompts.get_collaborative_prompt()

    async def execute_collaborative_workflow(
        self,
        agents: list[str],
        agent_types: dict[str, AgentType],
        agent_executors: dict[str, Any],
        input_data: dict[str, Any],
        consensus_algorithm: ConsensusAlgorithm = ConsensusAlgorithm.SIMPLE_AGREEMENT,
        config: dict[str, Any] | None = None,
    ) -> AgentResult:
        """Execute collaborative workflow with consensus."""
        try:
            # Execute the base pattern
            base_result = await self.execute_pattern(
                agents=agents,
                agent_types=agent_types,
                agent_executors=agent_executors,
                input_data=input_data,
                config=config,
            )

            if not base_result.success:
                return base_result

            # Add consensus information
            base_result.data["consensus_algorithm"] = consensus_algorithm.value
            base_result.data["collaboration_summary"] = {
                "agents_involved": len(agents),
                "consensus_algorithm": consensus_algorithm.value,
                "coordination_strategy": "parallel_execution",
            }

            return base_result

        except Exception as e:
            return AgentResult(
                success=False,
                error=f"Collaborative workflow failed: {e!s}",
                agent_type=self.agent_type,
            )


class SequentialPatternAgent(WorkflowPatternAgent):
    """Agent for sequential interaction patterns."""

    def __init__(
        self,
        model_name: str = "anthropic:claude-sonnet-4-0",
        dependencies: AgentDependencies | None = None,
    ):
        super().__init__(
            pattern=InteractionPattern.SEQUENTIAL,
            model_name=model_name,
            dependencies=dependencies,
        )

    def _get_default_system_prompt(self) -> str:
        """Get default system prompt for sequential pattern agent."""
        prompts = WorkflowPatternAgentPrompts()
        return prompts.get_sequential_prompt()

    async def execute_sequential_workflow(
        self,
        agent_order: list[str],
        agent_types: dict[str, AgentType],
        agent_executors: dict[str, Any],
        input_data: dict[str, Any],
        config: dict[str, Any] | None = None,
    ) -> AgentResult:
        """Execute sequential workflow."""
        try:
            # Execute the base pattern
            base_result = await self.execute_pattern(
                agents=agent_order,
                agent_types=agent_types,
                agent_executors=agent_executors,
                input_data=input_data,
                config=config,
            )

            if not base_result.success:
                return base_result

            # Add sequential-specific information
            base_result.data["execution_order"] = agent_order
            base_result.data["sequential_summary"] = {
                "total_steps": len(agent_order),
                "execution_order": agent_order,
                "coordination_strategy": "sequential_execution",
            }

            return base_result

        except Exception as e:
            return AgentResult(
                success=False,
                error=f"Sequential workflow failed: {e!s}",
                agent_type=self.agent_type,
            )


class HierarchicalPatternAgent(WorkflowPatternAgent):
    """Agent for hierarchical interaction patterns."""

    def __init__(
        self,
        model_name: str = "anthropic:claude-sonnet-4-0",
        dependencies: AgentDependencies | None = None,
    ):
        super().__init__(
            pattern=InteractionPattern.HIERARCHICAL,
            model_name=model_name,
            dependencies=dependencies,
        )

    def _get_default_system_prompt(self) -> str:
        """Get default system prompt for hierarchical pattern agent."""
        prompts = WorkflowPatternAgentPrompts()
        return prompts.get_hierarchical_prompt()

    async def execute_hierarchical_workflow(
        self,
        coordinator_id: str,
        subordinate_ids: list[str],
        agent_types: dict[str, AgentType],
        agent_executors: dict[str, Any],
        input_data: dict[str, Any],
        config: dict[str, Any] | None = None,
    ) -> AgentResult:
        """Execute hierarchical workflow."""
        try:
            all_agents = [coordinator_id, *subordinate_ids]

            # Execute the base pattern
            base_result = await self.execute_pattern(
                agents=all_agents,
                agent_types=agent_types,
                agent_executors=agent_executors,
                input_data=input_data,
                config=config,
            )

            if not base_result.success:
                return base_result

            # Add hierarchical-specific information
            base_result.data["hierarchy"] = {
                "coordinator": coordinator_id,
                "subordinates": subordinate_ids,
                "total_agents": len(all_agents),
            }
            base_result.data["hierarchical_summary"] = {
                "coordination_strategy": "hierarchical_execution",
                "coordinator_executed": True,
                "subordinates_executed": len(subordinate_ids),
            }

            return base_result

        except Exception as e:
            return AgentResult(
                success=False,
                error=f"Hierarchical workflow failed: {e!s}",
                agent_type=self.agent_type,
            )


class PatternOrchestratorAgent(BaseAgent):
    """Agent for orchestrating multiple workflow patterns."""

    def __init__(
        self,
        model_name: str = "anthropic:claude-sonnet-4-0",
        dependencies: AgentDependencies | None = None,
    ):
        super().__init__(
            agent_type=AgentType.ORCHESTRATOR,
            model_name=model_name,
            dependencies=dependencies,
        )

        # Initialize pattern agents
        self.collaborative_agent = CollaborativePatternAgent(model_name, dependencies)
        self.sequential_agent = SequentialPatternAgent(model_name, dependencies)
        self.hierarchical_agent = HierarchicalPatternAgent(model_name, dependencies)

    def _get_default_system_prompt(self) -> str:
        """Get default system prompt for pattern orchestrator."""
        prompts = WorkflowPatternAgentPrompts()
        return prompts.get_pattern_orchestrator_prompt()

    def _get_default_instructions(self) -> str:
        """Get default instructions for pattern orchestrator."""
        prompts = WorkflowPatternAgentPrompts()
        instructions = prompts.get_instructions("pattern_orchestrator")
        return "\n".join(instructions)

    def _register_tools(self):
        """Register orchestration tools."""
        # Register pattern selection and orchestration tools
        if self._agent:
            # Note: In a real implementation, these would be added as tool functions
            pass

    def _select_optimal_pattern(
        self,
        problem_complexity: str,
        agent_count: int,
        agent_capabilities: list[str],
        coordination_requirements: dict[str, Any] | None = None,
    ) -> InteractionPattern:
        """Select the optimal interaction pattern based on requirements."""

        # Analyze requirements
        needs_consensus = (
            coordination_requirements.get("consensus", False)
            if coordination_requirements
            else False
        )
        needs_sequential_flow = (
            coordination_requirements.get("sequential_flow", False)
            if coordination_requirements
            else False
        )
        needs_hierarchy = (
            coordination_requirements.get("hierarchy", False)
            if coordination_requirements
            else False
        )

        # Pattern selection logic
        if needs_hierarchy or agent_count > 5:
            return InteractionPattern.HIERARCHICAL
        if needs_sequential_flow or agent_count <= 3:
            return InteractionPattern.SEQUENTIAL
        if needs_consensus or (
            agent_count > 3 and "diverse_perspectives" in str(agent_capabilities)
        ):
            return InteractionPattern.COLLABORATIVE
        # Default to collaborative for most cases
        return InteractionPattern.COLLABORATIVE

    async def orchestrate_workflow(
        self,
        question: str,
        available_agents: dict[str, AgentType],
        agent_executors: dict[str, Any],
        pattern_preference: InteractionPattern | None = None,
        coordination_requirements: dict[str, Any] | None = None,
        config: dict[str, Any] | None = None,
    ) -> AgentResult:
        """Orchestrate workflow with optimal pattern selection."""
        try:
            start_time = time.time()

            # Prepare input data
            input_data = {"question": question}

            # Select pattern if not specified
            if pattern_preference is None:
                selected_pattern = self._select_optimal_pattern(
                    problem_complexity="medium",  # Would be analyzed from question
                    agent_count=len(available_agents),
                    agent_capabilities=list(available_agents.values()),
                    coordination_requirements=coordination_requirements,
                )
            else:
                selected_pattern = pattern_preference

            # Prepare agents
            agents = list(available_agents.keys())
            agent_types = available_agents

            # Execute with selected pattern
            if selected_pattern == InteractionPattern.COLLABORATIVE:
                result = await self.collaborative_agent.execute_collaborative_workflow(
                    agents=agents,
                    agent_types=agent_types,
                    agent_executors=agent_executors,
                    input_data=input_data,
                    config=config,
                )
            elif selected_pattern == InteractionPattern.SEQUENTIAL:
                result = await self.sequential_agent.execute_sequential_workflow(
                    agent_order=agents,
                    agent_types=agent_types,
                    agent_executors=agent_executors,
                    input_data=input_data,
                    config=config,
                )
            elif selected_pattern == InteractionPattern.HIERARCHICAL:
                coordinator_id = agents[0] if agents else ""
                subordinate_ids = agents[1:] if len(agents) > 1 else []

                result = await self.hierarchical_agent.execute_hierarchical_workflow(
                    coordinator_id=coordinator_id,
                    subordinate_ids=subordinate_ids,
                    agent_types=agent_types,
                    agent_executors=agent_executors,
                    input_data=input_data,
                    config=config,
                )
            else:
                return AgentResult(
                    success=False,
                    error=f"Unsupported pattern: {selected_pattern}",
                    agent_type=self.agent_type,
                )

            execution_time = time.time() - start_time

            # Add orchestration metadata
            if result.success:
                result.data["orchestration"] = {
                    "selected_pattern": selected_pattern.value,
                    "pattern_selection_rationale": "Based on agent count and requirements",
                    "total_execution_time": execution_time,
                    "orchestrator": "PatternOrchestratorAgent",
                }
                result.metadata["orchestration"] = {
                    "selected_pattern": selected_pattern.value,
                    "execution_time": execution_time,
                }

            return result

        except Exception as e:
            return AgentResult(
                success=False,
                error=f"Workflow orchestration failed: {e!s}",
                agent_type=self.agent_type,
            )


class AdaptivePatternAgent(BaseAgent):
    """Agent that adapts interaction patterns based on execution results."""

    def __init__(
        self,
        model_name: str = "anthropic:claude-sonnet-4-0",
        dependencies: AgentDependencies | None = None,
    ):
        super().__init__(
            agent_type=AgentType.ORCHESTRATOR,
            model_name=model_name,
            dependencies=dependencies,
        )

        # Initialize orchestrator
        self.orchestrator = PatternOrchestratorAgent(model_name, dependencies)

    def _get_default_system_prompt(self) -> str:
        """Get default system prompt for adaptive pattern agent."""
        prompts = WorkflowPatternAgentPrompts()
        return prompts.get_adaptive_prompt()

    async def execute_adaptive_workflow(
        self,
        question: str,
        available_agents: dict[str, AgentType],
        agent_executors: dict[str, Any],
        max_attempts: int = 3,
        config: dict[str, Any] | None = None,
    ) -> AgentResult:
        """Execute workflow with adaptive pattern selection."""
        try:
            start_time = time.time()

            best_result = None
            pattern_attempts = {}

            # Try different patterns
            patterns_to_try = [
                InteractionPattern.COLLABORATIVE,
                InteractionPattern.SEQUENTIAL,
                InteractionPattern.HIERARCHICAL,
            ]

            for attempt in range(min(max_attempts, len(patterns_to_try))):
                pattern = patterns_to_try[attempt]

                # Execute with current pattern
                result = await self.orchestrator.orchestrate_workflow(
                    question=question,
                    available_agents=available_agents,
                    agent_executors=agent_executors,
                    pattern_preference=pattern,
                    config=config,
                )

                pattern_attempts[pattern.value] = result

                # Keep track of the best result
                if result.success:
                    if best_result is None or self._is_better_result(
                        result, best_result
                    ):
                        best_result = result

            execution_time = time.time() - start_time

            if best_result:
                # Add adaptive metadata
                best_result.data["adaptive_execution"] = {
                    "attempts": len(pattern_attempts),
                    "best_pattern": best_result.data.get("pattern"),
                    "total_execution_time": execution_time,
                    "pattern_attempts": {
                        pattern: attempt_result.success
                        for pattern, attempt_result in pattern_attempts.items()
                    },
                }

                return best_result
            # Return the last attempt if all failed
            last_attempt = (
                list(pattern_attempts.values())[-1] if pattern_attempts else None
            )
            if last_attempt:
                return last_attempt

            return AgentResult(
                success=False,
                error="All pattern attempts failed",
                agent_type=self.agent_type,
            )

        except Exception as e:
            return AgentResult(
                success=False,
                error=f"Adaptive workflow execution failed: {e!s}",
                agent_type=self.agent_type,
            )

    def _is_better_result(self, result1: AgentResult, result2: AgentResult) -> bool:
        """Determine if result1 is better than result2."""
        # Simple heuristic: compare execution time and success
        if not result1.success and not result2.success:
            return result1.execution_time < result2.execution_time
        if result1.success and not result2.success:
            return True
        if not result1.success and result2.success:
            return False
        # Both successful, compare execution time
        return result1.execution_time < result2.execution_time


# Factory functions for creating pattern agents
def create_collaborative_agent(
    model_name: str = "anthropic:claude-sonnet-4-0",
    dependencies: AgentDependencies | None = None,
) -> CollaborativePatternAgent:
    """Create a collaborative pattern agent."""
    return CollaborativePatternAgent(model_name, dependencies)


def create_sequential_agent(
    model_name: str = "anthropic:claude-sonnet-4-0",
    dependencies: AgentDependencies | None = None,
) -> SequentialPatternAgent:
    """Create a sequential pattern agent."""
    return SequentialPatternAgent(model_name, dependencies)


def create_hierarchical_agent(
    model_name: str = "anthropic:claude-sonnet-4-0",
    dependencies: AgentDependencies | None = None,
) -> HierarchicalPatternAgent:
    """Create a hierarchical pattern agent."""
    return HierarchicalPatternAgent(model_name, dependencies)


def create_pattern_orchestrator(
    model_name: str = "anthropic:claude-sonnet-4-0",
    dependencies: AgentDependencies | None = None,
) -> PatternOrchestratorAgent:
    """Create a pattern orchestrator agent."""
    return PatternOrchestratorAgent(model_name, dependencies)


def create_adaptive_pattern_agent(
    model_name: str = "anthropic:claude-sonnet-4-0",
    dependencies: AgentDependencies | None = None,
) -> AdaptivePatternAgent:
    """Create an adaptive pattern agent."""
    return AdaptivePatternAgent(model_name, dependencies)


# Export all agents
__all__ = [
    "AdaptivePatternAgent",
    "CollaborativePatternAgent",
    "HierarchicalPatternAgent",
    "PatternOrchestratorAgent",
    "SequentialPatternAgent",
    "WorkflowPatternAgent",
    "create_adaptive_pattern_agent",
    "create_collaborative_agent",
    "create_hierarchical_agent",
    "create_pattern_orchestrator",
    "create_sequential_agent",
]
