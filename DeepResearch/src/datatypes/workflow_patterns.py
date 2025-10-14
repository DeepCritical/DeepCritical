"""
Workflow interaction design patterns for DeepCritical agent systems.

This module defines Pydantic models and data structures for implementing
agent interaction patterns with minimal external dependencies, focusing on
Pydantic AI and Pydantic Graph integration.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING, Any
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field

# Optional import for pydantic_graph - may not be available in all environments
try:
    from pydantic_graph import BaseNode, Edge, End, Graph, GraphRunContext
except ImportError:
    # Create placeholder classes for when pydantic_graph is not available
    from typing import Generic, TypeVar

    T = TypeVar("T")

    class BaseNode(Generic[T]):
        def __init__(self, *args, **kwargs):
            pass

    class End:
        def __init__(self, *args, **kwargs):
            pass

    class Graph:
        def __init__(self, *args, **kwargs):
            pass

    class GraphRunContext:
        def __init__(self, *args, **kwargs):
            pass

    class Edge:
        def __init__(self, *args, **kwargs):
            pass


# Import existing DeepCritical types
from DeepResearch.src.utils.execution_status import ExecutionStatus

from .agents import AgentStatus, AgentType
from .deep_agent_state import DeepAgentState

if TYPE_CHECKING:
    from collections.abc import Callable


class InteractionPattern(str, Enum):
    """Types of agent interaction patterns."""

    COLLABORATIVE = "collaborative"
    SEQUENTIAL = "sequential"
    HIERARCHICAL = "hierarchical"
    PEER_TO_PEER = "peer_to_peer"
    PIPELINE = "pipeline"
    CONSENSUS = "consensus"
    GROUP_CHAT = "group_chat"
    STATE_MACHINE = "state_machine"
    SUBGRAPH_COORDINATION = "subgraph_coordination"
    NESTED_REACT = "nested_react"


class MessageType(str, Enum):
    """Types of messages in agent interactions."""

    REQUEST = "request"
    RESPONSE = "response"
    BROADCAST = "broadcast"
    DIRECT = "direct"
    STATUS = "status"
    CONTROL = "control"
    DATA = "data"
    ERROR = "error"


class AgentInteractionMode(str, Enum):
    """Modes for agent interaction execution."""

    SYNC = "sync"
    ASYNC = "async"
    STREAMING = "streaming"
    BATCH = "batch"


@dataclass
class InteractionMessage:
    """Message for agent-to-agent communication."""

    message_id: str = field(default_factory=lambda: str(uuid4()))
    sender_id: str = ""
    receiver_id: str | None = None  # None for broadcast
    message_type: MessageType = MessageType.DATA
    content: Any = None
    metadata: dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)
    priority: int = 0

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "message_id": self.message_id,
            "sender_id": self.sender_id,
            "receiver_id": self.receiver_id,
            "message_type": self.message_type.value,
            "content": self.content,
            "metadata": self.metadata,
            "timestamp": self.timestamp,
            "priority": self.priority,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> InteractionMessage:
        """Create from dictionary."""
        return cls(
            message_id=data.get("message_id", str(uuid4())),
            sender_id=data.get("sender_id", ""),
            receiver_id=data.get("receiver_id"),
            message_type=MessageType(data.get("message_type", MessageType.DATA.value)),
            content=data.get("content"),
            metadata=data.get("metadata", {}),
            timestamp=data.get("timestamp", time.time()),
            priority=data.get("priority", 0),
        )


@dataclass
class AgentInteractionState:
    """State for agent interaction patterns."""

    interaction_id: str = field(default_factory=lambda: str(uuid4()))
    pattern: InteractionPattern = InteractionPattern.COLLABORATIVE
    mode: AgentInteractionMode = AgentInteractionMode.SYNC

    # Agent management
    agents: dict[str, AgentType] = field(default_factory=dict)
    active_agents: list[str] = field(default_factory=list)
    agent_states: dict[str, AgentStatus] = field(default_factory=dict)

    # Message management
    messages: list[InteractionMessage] = field(default_factory=list)
    message_queue: list[InteractionMessage] = field(default_factory=list)

    # Execution state
    current_round: int = 0
    max_rounds: int = 10
    consensus_threshold: float = 0.8
    execution_status: ExecutionStatus = ExecutionStatus.PENDING

    # Results
    results: dict[str, Any] = field(default_factory=dict)
    final_result: Any | None = None
    consensus_reached: bool = False

    # Metadata
    start_time: float = field(default_factory=time.time)
    end_time: float | None = None
    errors: list[str] = field(default_factory=list)

    def add_agent(self, agent_id: str, agent_type: AgentType) -> None:
        """Add an agent to the interaction."""
        self.agents[agent_id] = agent_type
        self.agent_states[agent_id] = AgentStatus.IDLE

    def activate_agent(self, agent_id: str) -> None:
        """Activate an agent for the current round."""
        if agent_id in self.agents:
            self.active_agents.append(agent_id)
            self.agent_states[agent_id] = AgentStatus.RUNNING

    def deactivate_agent(self, agent_id: str) -> None:
        """Deactivate an agent."""
        if agent_id in self.active_agents:
            self.active_agents.remove(agent_id)
        self.agent_states[agent_id] = AgentStatus.COMPLETED

    def send_message(self, message: InteractionMessage) -> None:
        """Send a message in the interaction."""
        self.messages.append(message)
        if message.receiver_id:
            self.message_queue.append(message)

    def get_messages_for_agent(self, agent_id: str) -> list[InteractionMessage]:
        """Get messages addressed to a specific agent."""
        return [msg for msg in self.message_queue if msg.receiver_id == agent_id]

    def get_broadcast_messages(self) -> list[InteractionMessage]:
        """Get broadcast messages."""
        return [msg for msg in self.message_queue if msg.receiver_id is None]

    def clear_message_queue(self) -> None:
        """Clear the message queue."""
        self.message_queue.clear()

    def can_continue(self) -> bool:
        """Check if interaction can continue."""
        if self.current_round >= self.max_rounds:
            return False
        if self.consensus_reached:
            return False
        return self.execution_status != ExecutionStatus.FAILED

    def next_round(self) -> None:
        """Move to the next round."""
        self.current_round += 1
        self.clear_message_queue()

    def finalize(self) -> None:
        """Finalize the interaction."""
        self.end_time = time.time()
        self.execution_status = ExecutionStatus.SUCCESS

    def get_summary(self) -> dict[str, Any]:
        """Get a summary of the interaction state."""
        return {
            "interaction_id": self.interaction_id,
            "pattern": self.pattern.value,
            "current_round": self.current_round,
            "max_rounds": self.max_rounds,
            "active_agents": len(self.active_agents),
            "total_agents": len(self.agents),
            "consensus_reached": self.consensus_reached,
            "execution_status": self.execution_status.value,
            "duration": self.end_time - self.start_time if self.end_time else 0,
            "messages_count": len(self.messages),
            "errors_count": len(self.errors),
        }


class WorkflowOrchestrator:
    """Orchestrator for workflow-based agent interactions."""

    def __init__(self, interaction_state: AgentInteractionState):
        self.state = interaction_state
        self.executors: dict[str, Callable] = {}

    def register_agent_executor(self, agent_id: str, executor: Callable) -> None:
        """Register an executor for an agent."""
        self.executors[agent_id] = executor

    async def execute_collaborative_pattern(self) -> Any:
        """Execute collaborative interaction pattern."""
        self.state.pattern = InteractionPattern.COLLABORATIVE

        while self.state.can_continue():
            # Activate all agents for this round
            for agent_id in self.state.agents:
                self.state.activate_agent(agent_id)

            # Execute agents concurrently
            results = await self._execute_agents_parallel()

            # Process results
            consensus_result = self._process_collaborative_results(results)

            if consensus_result["consensus_reached"]:
                self.state.consensus_reached = True
                self.state.final_result = consensus_result["result"]
                break

            self.state.next_round()

        self.state.finalize()
        return self.state.final_result

    async def execute_sequential_pattern(self) -> Any:
        """Execute sequential interaction pattern."""
        self.state.pattern = InteractionPattern.SEQUENTIAL

        for agent_id in self.state.agents:
            self.state.activate_agent(agent_id)

            result = await self._execute_single_agent(agent_id)

            if result["success"]:
                self.state.results[agent_id] = result["data"]

                # Pass result to next agent
                if agent_id != list(self.state.agents.keys())[-1]:
                    next_agent = self._get_next_agent(agent_id)
                    message = InteractionMessage(
                        sender_id=agent_id,
                        receiver_id=next_agent,
                        message_type=MessageType.DATA,
                        content=result["data"],
                    )
                    self.state.send_message(message)
            else:
                self.state.errors.append(f"Agent {agent_id} failed: {result['error']}")
                break

        self.state.finalize()
        return self.state.results

    async def execute_hierarchical_pattern(self) -> Any:
        """Execute hierarchical interaction pattern."""
        self.state.pattern = InteractionPattern.HIERARCHICAL

        # Execute coordinator first
        coordinator_id = self._get_coordinator_agent()
        if coordinator_id:
            self.state.activate_agent(coordinator_id)
            coord_result = await self._execute_single_agent(coordinator_id)

            if coord_result["success"]:
                # Execute subordinate agents
                sub_results = await self._execute_hierarchical_subordinates(
                    coord_result["data"]
                )
                self.state.results.update(sub_results)
            else:
                self.state.errors.append(f"Coordinator failed: {coord_result['error']}")

        self.state.finalize()
        return self.state.results

    async def _execute_agents_parallel(self) -> dict[str, dict[str, Any]]:
        """Execute all active agents in parallel."""

        tasks = []
        for agent_id in self.state.active_agents:
            if agent_id in self.executors:
                task = self._execute_single_agent(agent_id)
                tasks.append((agent_id, task))

        results = {}
        for agent_id, task in tasks:
            try:
                result = await task
                results[agent_id] = result
            except Exception as e:
                results[agent_id] = {"success": False, "error": str(e)}

        return results

    async def _execute_single_agent(self, agent_id: str) -> dict[str, Any]:
        """Execute a single agent."""
        if agent_id not in self.executors:
            return {"success": False, "error": f"No executor for agent {agent_id}"}

        try:
            executor = self.executors[agent_id]
            # Get messages for this agent
            messages = self.state.get_messages_for_agent(agent_id)

            # Execute agent with messages
            result = await executor(messages, self.state)

            return {"success": True, "data": result}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _process_collaborative_results(
        self, results: dict[str, dict[str, Any]]
    ) -> dict[str, Any]:
        """Process results from collaborative agents."""
        successful_results = {}
        all_results = []

        for agent_id, result in results.items():
            if result["success"]:
                successful_results[agent_id] = result["data"]
                all_results.append(result["data"])

        # Check for consensus
        if len(all_results) >= 2:
            consensus_reached = self._check_consensus(all_results)
            if consensus_reached:
                return {
                    "consensus_reached": True,
                    "result": self._aggregate_results(all_results),
                    "confidence": self._calculate_consensus_confidence(all_results),
                }

        return {
            "consensus_reached": False,
            "result": self._aggregate_results(all_results) if all_results else None,
            "confidence": 0.0,
        }

    def _check_consensus(self, results: list[Any]) -> bool:
        """Check if results reach consensus."""
        if len(results) < 2:
            return False

        # Simple consensus check - results are similar
        first_result = results[0]
        for result in results[1:]:
            if not self._results_similar(first_result, result):
                return False

        return True

    def _results_similar(self, result1: Any, result2: Any) -> bool:
        """Check if two results are similar."""
        # Simple string similarity check
        if isinstance(result1, str) and isinstance(result2, str):
            return result1.lower() == result2.lower()
        if isinstance(result1, dict) and isinstance(result2, dict):
            return (
                result1.get("answer", "").lower() == result2.get("answer", "").lower()
            )

        return result1 == result2

    def _aggregate_results(self, results: list[Any]) -> Any:
        """Aggregate multiple results."""
        if not results:
            return None

        if len(results) == 1:
            return results[0]

        # For strings, return the most common
        if all(isinstance(r, str) for r in results):
            return max(results, key=results.count)

        # For dicts, merge them
        if all(isinstance(r, dict) for r in results):
            merged = {}
            for result in results:
                merged.update(result)
            return merged

        return results[0]

    def _calculate_consensus_confidence(self, results: list[Any]) -> float:
        """Calculate confidence based on result agreement."""
        if len(results) < 2:
            return 0.0

        # Simple confidence calculation
        unique_results = len({str(r) for r in results})
        total_results = len(results)

        return 1.0 - (unique_results - 1) / total_results

    def _execute_hierarchical_subordinates(
        self, _coordinator_data: Any
    ) -> dict[str, Any]:
        """Execute subordinate agents in hierarchical pattern."""
        # This would implement hierarchical execution logic
        return {}

    def _get_next_agent(self, current_agent: str) -> str | None:
        """Get the next agent in sequential pattern."""
        agent_ids = list(self.state.agents.keys())
        try:
            current_index = agent_ids.index(current_agent)
            return (
                agent_ids[current_index + 1]
                if current_index + 1 < len(agent_ids)
                else None
            )
        except ValueError:
            return None

    def _get_coordinator_agent(self) -> str | None:
        """Get the coordinator agent in hierarchical pattern."""
        # In a real implementation, this would identify the coordinator
        # For now, return the first agent
        return next(iter(self.state.agents.keys())) if self.state.agents else None


# Pydantic models for type safety
class InteractionConfig(BaseModel):
    """Configuration for agent interaction patterns."""

    pattern: InteractionPattern = Field(..., description="Interaction pattern to use")
    max_rounds: int = Field(10, description="Maximum number of interaction rounds")
    consensus_threshold: float = Field(0.8, description="Consensus threshold")
    timeout: float = Field(300.0, description="Timeout in seconds")
    enable_monitoring: bool = Field(True, description="Enable execution monitoring")

    model_config = ConfigDict(json_schema_extra={})


class AgentInteractionRequest(BaseModel):
    """Request for agent interaction execution."""

    agents: list[str] = Field(..., description="Agent IDs to include")
    interaction_pattern: InteractionPattern = Field(
        InteractionPattern.COLLABORATIVE, description="Interaction pattern"
    )
    input_data: dict[str, Any] = Field(..., description="Input data for agents")
    config: InteractionConfig | None = Field(
        None, description="Interaction configuration"
    )

    model_config = ConfigDict(json_schema_extra={})


class AgentInteractionResponse(BaseModel):
    """Response from agent interaction execution."""

    success: bool = Field(..., description="Whether interaction was successful")
    result: Any = Field(..., description="Interaction result")
    execution_time: float = Field(..., description="Execution time in seconds")
    rounds_executed: int = Field(..., description="Number of rounds executed")
    errors: list[str] = Field(
        default_factory=list, description="Any errors encountered"
    )

    model_config = ConfigDict(json_schema_extra={})


# Factory functions for creating interaction patterns
def create_interaction_state(
    pattern: InteractionPattern = InteractionPattern.COLLABORATIVE,
    agents: list[str] | None = None,
    agent_types: dict[str, AgentType] | None = None,
) -> AgentInteractionState:
    """Create a new interaction state."""
    state = AgentInteractionState(pattern=pattern)

    if agents and agent_types:
        for agent_id in agents:
            agent_type = agent_types.get(agent_id, AgentType.EXECUTOR)
            state.add_agent(agent_id, agent_type)

    return state


def create_workflow_orchestrator(
    interaction_state: AgentInteractionState,
    agent_executors: dict[str, Callable] | None = None,
) -> WorkflowOrchestrator:
    """Create a workflow orchestrator."""
    orchestrator = WorkflowOrchestrator(interaction_state)

    if agent_executors:
        for agent_id, executor in agent_executors.items():
            orchestrator.register_agent_executor(agent_id, executor)

    return orchestrator


# Integration with existing DeepCritical components
class WorkflowPatternNode(BaseNode[DeepAgentState]):  # type: ignore[unsupported-base]
    """Base node for workflow pattern execution."""

    def __init__(self, pattern: InteractionPattern):
        self.pattern = pattern

    async def run(self, ctx: GraphRunContext[DeepAgentState]) -> Any:
        """Execute the workflow pattern."""
        # This would be implemented by specific pattern nodes


class CollaborativePatternNode(WorkflowPatternNode):
    """Node for collaborative interaction pattern."""

    def __init__(self):
        super().__init__(InteractionPattern.COLLABORATIVE)

    async def run(self, ctx: GraphRunContext[DeepAgentState]) -> Any:
        """Execute collaborative pattern."""
        # Get active agents from context
        active_agents = ctx.state.active_tasks  # This would need to be adapted

        # Create interaction state
        interaction_state = create_interaction_state(
            pattern=self.pattern,
            agents=active_agents,
        )

        # Create orchestrator
        orchestrator = create_workflow_orchestrator(interaction_state)

        # Execute pattern
        result = await orchestrator.execute_collaborative_pattern()

        # Update context state
        ctx.state.shared_state["interaction_result"] = result
        ctx.state.shared_state["interaction_summary"] = interaction_state.get_summary()

        return result


class SequentialPatternNode(WorkflowPatternNode):
    """Node for sequential interaction pattern."""

    def __init__(self):
        super().__init__(InteractionPattern.SEQUENTIAL)

    async def run(self, ctx: GraphRunContext[DeepAgentState]) -> Any:
        """Execute sequential pattern."""
        # Get agents in order
        agent_order = list(ctx.state.active_tasks)

        # Create interaction state
        interaction_state = create_interaction_state(
            pattern=self.pattern,
            agents=agent_order,
        )

        # Create orchestrator
        orchestrator = create_workflow_orchestrator(interaction_state)

        # Execute pattern
        result = await orchestrator.execute_sequential_pattern()

        # Update context state
        ctx.state.shared_state["interaction_result"] = result
        ctx.state.shared_state["interaction_summary"] = interaction_state.get_summary()

        return result


# Utility functions for integration
def create_pattern_graph(
    pattern: InteractionPattern, _agents: list[str]
) -> Graph[DeepAgentState]:
    """Create a Pydantic Graph for the given interaction pattern."""

    if pattern == InteractionPattern.COLLABORATIVE:
        nodes = [CollaborativePatternNode()]
    elif pattern == InteractionPattern.SEQUENTIAL:
        nodes = [SequentialPatternNode()]
    else:
        # Default to collaborative
        nodes = [CollaborativePatternNode()]

    return Graph(nodes=nodes, state_type=DeepAgentState)


async def execute_interaction_pattern(
    pattern: InteractionPattern,
    _agents: list[str],
    _input_data: dict[str, Any],
    _agent_executors: dict[str, Callable],
) -> AgentInteractionResponse:
    """Execute an interaction pattern with the given agents and data."""

    start_time = time.time()

    try:
        # Create interaction state
        interaction_state = create_interaction_state(
            pattern=pattern,
            agents=_agents,
        )

        # Create orchestrator
        orchestrator = create_workflow_orchestrator(interaction_state, _agent_executors)

        # Execute based on pattern
        if pattern == InteractionPattern.COLLABORATIVE:
            result = await orchestrator.execute_collaborative_pattern()
        elif pattern == InteractionPattern.SEQUENTIAL:
            result = await orchestrator.execute_sequential_pattern()
        elif pattern == InteractionPattern.HIERARCHICAL:
            result = await orchestrator.execute_hierarchical_pattern()
        else:
            msg = f"Unsupported pattern: {pattern}"
            raise ValueError(msg)

        execution_time = time.time() - start_time

        return AgentInteractionResponse(
            success=True,
            result=result,
            execution_time=execution_time,
            rounds_executed=interaction_state.current_round,
            errors=interaction_state.errors,
        )

    except Exception as e:
        execution_time = time.time() - start_time
        return AgentInteractionResponse(
            success=False,
            result=None,
            execution_time=execution_time,
            rounds_executed=0,
            errors=[str(e)],
        )


# Export all components
__all__ = [
    "AgentInteractionMode",
    "AgentInteractionRequest",
    "AgentInteractionResponse",
    "AgentInteractionState",
    "CollaborativePatternNode",
    "InteractionConfig",
    "InteractionMessage",
    "InteractionPattern",
    "MessageType",
    "SequentialPatternNode",
    "WorkflowOrchestrator",
    "WorkflowPatternNode",
    "create_interaction_state",
    "create_pattern_graph",
    "create_workflow_orchestrator",
    "execute_interaction_pattern",
]
