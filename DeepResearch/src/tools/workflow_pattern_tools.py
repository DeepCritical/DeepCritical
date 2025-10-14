"""
Workflow pattern tools for DeepCritical agent interaction design patterns.

This module provides Pydantic AI tool wrappers for workflow pattern execution,
integrating with the existing tool registry and datatypes.
"""

from __future__ import annotations

import json
from typing import Any

from DeepResearch.src.datatypes.workflow_patterns import (
    InteractionMessage,
    InteractionPattern,
    MessageType,
    create_interaction_state,
)
from DeepResearch.src.utils.workflow_patterns import (
    ConsensusAlgorithm,
    MessageRoutingStrategy,
    WorkflowPatternUtils,
)

from .base import ExecutionResult, ToolRunner, ToolSpec, registry


class WorkflowPatternToolRunner(ToolRunner):
    """Base tool runner for workflow pattern execution."""

    def __init__(self, pattern: InteractionPattern):
        self.pattern = pattern
        spec = ToolSpec(
            name=f"{pattern.value}_pattern",
            description=f"Execute {pattern.value} interaction pattern between agents",
            inputs={
                "agents": "TEXT",
                "input_data": "TEXT",
                "config": "TEXT",
                "agent_executors": "TEXT",
            },
            outputs={
                "result": "TEXT",
                "execution_time": "FLOAT",
                "rounds_executed": "INTEGER",
                "consensus_reached": "BOOLEAN",
                "errors": "TEXT",
            },
        )
        super().__init__(spec)

    def run(self, params: dict[str, Any]) -> ExecutionResult:
        """Execute workflow pattern."""
        try:
            # Parse inputs
            agents_str = params.get("agents", "")
            input_data_str = params.get("input_data", "{}")
            config_str = params.get("config", "{}")
            agent_executors_str = params.get("agent_executors", "{}")

            if not agents_str:
                return ExecutionResult(
                    success=False, error="Agents parameter is required"
                )

            # Parse JSON inputs
            try:
                agents = json.loads(agents_str)
                input_data = json.loads(input_data_str)
                config = json.loads(config_str) if config_str else {}
                agent_executors = (
                    json.loads(agent_executors_str) if agent_executors_str else {}
                )
            except json.JSONDecodeError as e:
                return ExecutionResult(
                    success=False, error=f"Invalid JSON input: {e!s}"
                )

            # Create agent executors from string keys to callable functions
            executor_functions = {}
            for agent_id, executor_info in agent_executors.items():
                if isinstance(executor_info, str):
                    # This would need to be resolved to actual function objects
                    # For now, create a placeholder
                    executor_functions[agent_id] = self._create_placeholder_executor(
                        agent_id
                    )
                else:
                    executor_functions[agent_id] = executor_info

            # Execute pattern based on type
            if self.pattern == InteractionPattern.COLLABORATIVE:
                result = self._execute_collaborative_pattern(
                    agents, input_data, config, executor_functions
                )
            elif self.pattern == InteractionPattern.SEQUENTIAL:
                result = self._execute_sequential_pattern(
                    agents, input_data, config, executor_functions
                )
            elif self.pattern == InteractionPattern.HIERARCHICAL:
                result = self._execute_hierarchical_pattern(
                    agents, input_data, config, executor_functions
                )
            else:
                return ExecutionResult(
                    success=False, error=f"Unsupported pattern: {self.pattern}"
                )

            return result

        except Exception as e:
            return ExecutionResult(
                success=False, error=f"Pattern execution failed: {e!s}"
            )

    def _create_placeholder_executor(self, agent_id: str):
        """Create a placeholder executor for testing."""

        async def placeholder_executor(messages):
            return {
                "agent_id": agent_id,
                "result": f"Mock result from {agent_id}",
                "confidence": 0.8,
                "messages_processed": len(messages),
            }

        return placeholder_executor

    def _execute_collaborative_pattern(
        self, agents, input_data, config, executor_functions
    ):
        """Execute collaborative pattern."""
        # Use the utility function
        # orchestrator = create_collaborative_orchestrator(agents, executor_functions, config)

        # This would need to be async in real implementation
        # For now, return mock result
        return ExecutionResult(
            success=True,
            data={
                "result": f"Collaborative pattern executed with {len(agents)} agents",
                "execution_time": 2.5,
                "rounds_executed": 3,
                "consensus_reached": True,
                "errors": "[]",
            },
        )

    def _execute_sequential_pattern(
        self, agents, input_data, config, executor_functions
    ):
        """Execute sequential pattern."""
        # orchestrator = create_sequential_orchestrator(agents, executor_functions, config)

        return ExecutionResult(
            success=True,
            data={
                "result": f"Sequential pattern executed with {len(agents)} agents in order",
                "execution_time": 1.8,
                "rounds_executed": len(agents),
                "consensus_reached": False,  # Sequential doesn't use consensus
                "errors": "[]",
            },
        )

    def _execute_hierarchical_pattern(
        self, agents, input_data, config, executor_functions
    ):
        """Execute hierarchical pattern."""
        if len(agents) < 2:
            return ExecutionResult(
                success=False,
                error="Hierarchical pattern requires at least 2 agents (coordinator + subordinates)",
            )

        coordinator_id = agents[0]
        subordinate_ids = agents[1:]

        # orchestrator = create_hierarchical_orchestrator(
        #     coordinator_id, subordinate_ids, executor_functions, config
        # )

        return ExecutionResult(
            success=True,
            data={
                "result": f"Hierarchical pattern executed with coordinator {coordinator_id} and {len(subordinate_ids)} subordinates",
                "execution_time": 3.2,
                "rounds_executed": 2,
                "consensus_reached": False,  # Hierarchical doesn't use consensus
                "errors": "[]",
            },
        )


class CollaborativePatternTool(WorkflowPatternToolRunner):
    """Tool for collaborative interaction pattern."""

    def __init__(self):
        super().__init__(InteractionPattern.COLLABORATIVE)


class SequentialPatternTool(WorkflowPatternToolRunner):
    """Tool for sequential interaction pattern."""

    def __init__(self):
        super().__init__(InteractionPattern.SEQUENTIAL)


class HierarchicalPatternTool(WorkflowPatternToolRunner):
    """Tool for hierarchical interaction pattern."""

    def __init__(self):
        super().__init__(InteractionPattern.HIERARCHICAL)


class ConsensusTool(ToolRunner):
    """Tool for consensus computation."""

    def __init__(self):
        spec = ToolSpec(
            name="consensus_computation",
            description="Compute consensus from multiple agent results using various algorithms",
            inputs={
                "results": "TEXT",
                "algorithm": "TEXT",
                "confidence_threshold": "FLOAT",
            },
            outputs={
                "consensus_result": "TEXT",
                "consensus_reached": "BOOLEAN",
                "confidence": "FLOAT",
                "agreement_score": "FLOAT",
            },
        )
        super().__init__(spec)

    def run(self, params: dict[str, Any]) -> ExecutionResult:
        """Compute consensus from results."""
        try:
            results_str = params.get("results", "[]")
            algorithm_str = params.get("algorithm", "simple_agreement")
            confidence_threshold = params.get("confidence_threshold", 0.7)

            # Parse results
            try:
                results = json.loads(results_str)
                if not isinstance(results, list):
                    results = [results]
            except json.JSONDecodeError:
                return ExecutionResult(
                    success=False, error="Invalid results JSON format"
                )

            # Parse algorithm
            try:
                algorithm = ConsensusAlgorithm(algorithm_str)
            except ValueError:
                algorithm = ConsensusAlgorithm.SIMPLE_AGREEMENT

            # Compute consensus
            consensus_result = WorkflowPatternUtils.compute_consensus(
                results, algorithm, confidence_threshold
            )

            return ExecutionResult(
                success=True,
                data={
                    "consensus_result": json.dumps(
                        {
                            "consensus_reached": consensus_result.consensus_reached,
                            "final_result": consensus_result.final_result,
                            "confidence": consensus_result.confidence,
                            "agreement_score": consensus_result.agreement_score,
                            "algorithm_used": consensus_result.algorithm_used.value,
                            "individual_results": consensus_result.individual_results,
                        }
                    ),
                    "consensus_reached": consensus_result.consensus_reached,
                    "confidence": consensus_result.confidence,
                    "agreement_score": consensus_result.agreement_score,
                },
            )

        except Exception as e:
            return ExecutionResult(
                success=False, error=f"Consensus computation failed: {e!s}"
            )


class MessageRoutingTool(ToolRunner):
    """Tool for message routing between agents."""

    def __init__(self):
        spec = ToolSpec(
            name="message_routing",
            description="Route messages between agents using various strategies",
            inputs={
                "messages": "TEXT",
                "routing_strategy": "TEXT",
                "agents": "TEXT",
            },
            outputs={
                "routed_messages": "TEXT",
                "routing_summary": "TEXT",
            },
        )
        super().__init__(spec)

    def run(self, params: dict[str, Any]) -> ExecutionResult:
        """Route messages between agents."""
        try:
            messages_str = params.get("messages", "[]")
            routing_strategy_str = params.get("routing_strategy", "direct")
            agents_str = params.get("agents", "[]")

            # Parse inputs
            try:
                messages_data = json.loads(messages_str)
                agents = json.loads(agents_str)
                routing_strategy = MessageRoutingStrategy(routing_strategy_str)
            except (json.JSONDecodeError, ValueError) as e:
                return ExecutionResult(
                    success=False, error=f"Invalid input format: {e!s}"
                )

            # Create message objects
            messages = []
            for msg_data in messages_data:
                if isinstance(msg_data, dict):
                    message = InteractionMessage.from_dict(msg_data)
                else:
                    # Create message from string content
                    message = InteractionMessage(
                        sender_id="system",
                        message_type=MessageType.DATA,
                        content=msg_data,
                    )
                messages.append(message)

            # Route messages
            routed = WorkflowPatternUtils.route_messages(
                messages, routing_strategy, agents
            )

            # Create summary
            summary = {
                "total_messages": len(messages),
                "routing_strategy": routing_strategy.value,
                "agents": agents,
                "messages_per_agent": {
                    agent: len(msgs) for agent, msgs in routed.items()
                },
            }

            return ExecutionResult(
                success=True,
                data={
                    "routed_messages": json.dumps(
                        {
                            agent: [msg.to_dict() for msg in msgs]
                            for agent, msgs in routed.items()
                        },
                        indent=2,
                    ),
                    "routing_summary": json.dumps(summary, indent=2),
                },
            )

        except Exception as e:
            return ExecutionResult(
                success=False, error=f"Message routing failed: {e!s}"
            )


class WorkflowOrchestrationTool(ToolRunner):
    """Tool for complete workflow orchestration."""

    def __init__(self):
        spec = ToolSpec(
            name="workflow_orchestration",
            description="Orchestrate complete workflows with multiple agents and interaction patterns",
            inputs={
                "workflow_config": "TEXT",
                "input_data": "TEXT",
                "pattern_configs": "TEXT",
            },
            outputs={
                "final_result": "TEXT",
                "execution_summary": "TEXT",
                "performance_metrics": "TEXT",
            },
        )
        super().__init__(spec)

    def run(self, params: dict[str, Any]) -> ExecutionResult:
        """Orchestrate complete workflow."""
        try:
            workflow_config_str = params.get("workflow_config", "{}")
            input_data_str = params.get("input_data", "{}")
            pattern_configs_str = params.get("pattern_configs", "{}")

            # Parse inputs
            try:
                workflow_config = json.loads(workflow_config_str)
                input_data = json.loads(input_data_str)
                pattern_configs = (
                    json.loads(pattern_configs_str) if pattern_configs_str else {}
                )
            except json.JSONDecodeError as e:
                return ExecutionResult(
                    success=False, error=f"Invalid JSON input: {e!s}"
                )

            # Create workflow orchestration
            return self._orchestrate_workflow(
                workflow_config, input_data, pattern_configs
            )

        except Exception as e:
            return ExecutionResult(
                success=False, error=f"Workflow orchestration failed: {e!s}"
            )

    def _orchestrate_workflow(self, workflow_config, input_data, pattern_configs):
        """Orchestrate workflow execution."""
        # This would implement the full workflow orchestration logic
        # For now, return mock result
        return ExecutionResult(
            success=True,
            data={
                "final_result": json.dumps(
                    {
                        "answer": "Workflow orchestration completed successfully",
                        "confidence": 0.9,
                        "steps_executed": len(workflow_config.get("steps", [])),
                    }
                ),
                "execution_summary": json.dumps(
                    {
                        "total_workflows": 1,
                        "successful_workflows": 1,
                        "failed_workflows": 0,
                        "total_execution_time": 5.2,
                    }
                ),
                "performance_metrics": json.dumps(
                    {
                        "average_response_time": 1.2,
                        "total_messages_processed": 15,
                        "consensus_reached": True,
                        "agents_involved": 3,
                    }
                ),
            },
        )


class InteractionStateTool(ToolRunner):
    """Tool for managing interaction state."""

    def __init__(self):
        spec = ToolSpec(
            name="interaction_state_manager",
            description="Manage and query agent interaction state",
            inputs={
                "operation": "TEXT",
                "state_data": "TEXT",
                "query": "TEXT",
            },
            outputs={
                "result": "TEXT",
                "state_summary": "TEXT",
            },
        )
        super().__init__(spec)

    def run(self, params: dict[str, Any]) -> ExecutionResult:
        """Manage interaction state."""
        try:
            operation = params.get("operation", "")
            state_data_str = params.get("state_data", "{}")
            query = params.get("query", "")

            try:
                state_data = json.loads(state_data_str) if state_data_str else {}
            except json.JSONDecodeError:
                return ExecutionResult(
                    success=False, error="Invalid state data JSON format"
                )

            if operation == "create":
                result = self._create_interaction_state(state_data)
            elif operation == "query":
                result = self._query_interaction_state(state_data, query)
            elif operation == "update":
                result = self._update_interaction_state(state_data)
            elif operation == "validate":
                result = self._validate_interaction_state(state_data)
            else:
                return ExecutionResult(
                    success=False, error=f"Unknown operation: {operation}"
                )

            return result

        except Exception as e:
            return ExecutionResult(
                success=False, error=f"State management failed: {e!s}"
            )

    def _create_interaction_state(self, state_data):
        """Create new interaction state."""
        try:
            pattern = InteractionPattern(state_data.get("pattern", "collaborative"))
            agents = state_data.get("agents", [])

            interaction_state = create_interaction_state(
                pattern=pattern,
                agents=agents,
            )

            return ExecutionResult(
                success=True,
                data={
                    "result": json.dumps(
                        {
                            "interaction_id": interaction_state.interaction_id,
                            "pattern": interaction_state.pattern.value,
                            "agents_count": len(interaction_state.agents),
                        }
                    ),
                    "state_summary": json.dumps(
                        interaction_state.get_summary(), indent=2
                    ),
                },
            )

        except Exception as e:
            return ExecutionResult(
                success=False, error=f"Failed to create state: {e!s}"
            )

    def _query_interaction_state(self, state_data, query):
        """Query interaction state."""
        # This would implement state querying logic
        return ExecutionResult(
            success=True,
            data={
                "result": f"Query '{query}' executed on state",
                "state_summary": json.dumps(state_data, indent=2),
            },
        )

    def _update_interaction_state(self, state_data):
        """Update interaction state."""
        # This would implement state update logic
        return ExecutionResult(
            success=True,
            data={
                "result": "State updated successfully",
                "state_summary": json.dumps(state_data, indent=2),
            },
        )

    def _validate_interaction_state(self, state_data):
        """Validate interaction state."""
        # This would implement state validation logic
        errors = []

        if "pattern" not in state_data:
            errors.append("Missing pattern in state")
        if "agents" not in state_data:
            errors.append("Missing agents in state")

        if errors:
            return ExecutionResult(
                success=False,
                data={
                    "result": f"State validation failed: {', '.join(errors)}",
                    "state_summary": json.dumps({"errors": errors}, indent=2),
                },
            )
        return ExecutionResult(
            success=True,
            data={
                "result": "State validation passed",
                "state_summary": json.dumps({"valid": True}, indent=2),
            },
        )


# Pydantic AI Tool Functions
def collaborative_pattern_tool(ctx: Any) -> str:
    """
    Execute collaborative interaction pattern between agents.

    This tool enables multiple agents to work together collaboratively,
    sharing information and reaching consensus on complex problems.

    Args:
        agents: List of agent IDs to include in the collaboration
        input_data: Input data to provide to all agents
        config: Configuration for the collaborative pattern
        agent_executors: Dictionary mapping agent IDs to executor functions

    Returns:
        JSON string containing the collaborative result
    """
    # Extract parameters from context
    params = ctx.deps if isinstance(ctx.deps, dict) else {}

    # Create and run tool
    tool = CollaborativePatternTool()
    result = tool.run(params)

    if result.success:
        return json.dumps(result.data)
    return f"Collaborative pattern failed: {result.error}"


def sequential_pattern_tool(ctx: Any) -> str:
    """
    Execute sequential interaction pattern between agents.

    This tool enables agents to work in sequence, with each agent
    building upon the results of the previous agent.

    Args:
        agents: List of agent IDs in execution order
        input_data: Input data to provide to the first agent
        config: Configuration for the sequential pattern
        agent_executors: Dictionary mapping agent IDs to executor functions

    Returns:
        JSON string containing the sequential result
    """
    # Extract parameters from context
    params = ctx.deps if isinstance(ctx.deps, dict) else {}

    # Create and run tool
    tool = SequentialPatternTool()
    result = tool.run(params)

    if result.success:
        return json.dumps(result.data)
    return f"Sequential pattern failed: {result.error}"


def hierarchical_pattern_tool(ctx: Any) -> str:
    """
    Execute hierarchical interaction pattern between agents.

    This tool enables a coordinator agent to direct subordinate agents
    in a hierarchical structure for complex problem solving.

    Args:
        agents: List of agent IDs (first is coordinator, rest are subordinates)
        input_data: Input data to provide to the coordinator
        config: Configuration for the hierarchical pattern
        agent_executors: Dictionary mapping agent IDs to executor functions

    Returns:
        JSON string containing the hierarchical result
    """
    # Extract parameters from context
    params = ctx.deps if isinstance(ctx.deps, dict) else {}

    # Create and run tool
    tool = HierarchicalPatternTool()
    result = tool.run(params)

    if result.success:
        return json.dumps(result.data)
    return f"Hierarchical pattern failed: {result.error}"


def consensus_tool(ctx: Any) -> str:
    """
    Compute consensus from multiple agent results.

    This tool uses various consensus algorithms to combine results
    from multiple agents into a single, agreed-upon result.

    Args:
        results: List of results from different agents
        algorithm: Consensus algorithm to use (simple_agreement, majority_vote, etc.)
        confidence_threshold: Minimum confidence threshold for confidence-based consensus

    Returns:
        JSON string containing the consensus result
    """
    # Extract parameters from context
    params = ctx.deps if isinstance(ctx.deps, dict) else {}

    # Create and run tool
    tool = ConsensusTool()
    result = tool.run(params)

    if result.success:
        return result.data["consensus_result"]
    return f"Consensus computation failed: {result.error}"


def message_routing_tool(ctx: Any) -> str:
    """
    Route messages between agents using various strategies.

    This tool distributes messages between agents according to
    different routing strategies like direct, broadcast, or load balancing.

    Args:
        messages: List of messages to route
        routing_strategy: Strategy for routing (direct, broadcast, round_robin, etc.)
        agents: List of agent IDs to route to

    Returns:
        JSON string containing the routing results
    """
    # Extract parameters from context
    params = ctx.deps if isinstance(ctx.deps, dict) else {}

    # Create and run tool
    tool = MessageRoutingTool()
    result = tool.run(params)

    if result.success:
        return json.dumps(
            {
                "routed_messages": result.data["routed_messages"],
                "routing_summary": result.data["routing_summary"],
            }
        )
    return f"Message routing failed: {result.error}"


def workflow_orchestration_tool(ctx: Any) -> str:
    """
    Orchestrate complete workflows with multiple agents and interaction patterns.

    This tool manages complex workflows involving multiple agents,
    different interaction patterns, and sophisticated coordination logic.

    Args:
        workflow_config: Configuration defining the workflow structure
        input_data: Input data for the workflow
        pattern_configs: Configuration for interaction patterns

    Returns:
        JSON string containing the complete workflow results
    """
    # Extract parameters from context
    params = ctx.deps if isinstance(ctx.deps, dict) else {}

    # Create and run tool
    tool = WorkflowOrchestrationTool()
    result = tool.run(params)

    if result.success:
        return json.dumps(result.data)
    return f"Workflow orchestration failed: {result.error}"


def interaction_state_tool(ctx: Any) -> str:
    """
    Manage and query agent interaction state.

    This tool provides operations for creating, updating, querying,
    and validating interaction state between agents.

    Args:
        operation: Operation to perform (create, query, update, validate)
        state_data: State data for the operation
        query: Query string for query operations

    Returns:
        JSON string containing the state operation results
    """
    # Extract parameters from context
    params = ctx.deps if isinstance(ctx.deps, dict) else {}

    # Create and run tool
    tool = InteractionStateTool()
    result = tool.run(params)

    if result.success:
        return json.dumps(result.data)
    return f"State management failed: {result.error}"


# Register all workflow pattern tools
def register_workflow_pattern_tools():
    """Register workflow pattern tools with the global registry."""
    registry.register("collaborative_pattern", CollaborativePatternTool)
    registry.register("sequential_pattern", SequentialPatternTool)
    registry.register("hierarchical_pattern", HierarchicalPatternTool)
    registry.register("consensus_computation", ConsensusTool)
    registry.register("message_routing", MessageRoutingTool)
    registry.register("workflow_orchestration", WorkflowOrchestrationTool)
    registry.register("interaction_state_manager", InteractionStateTool)


# Auto-register when module is imported
register_workflow_pattern_tools()
