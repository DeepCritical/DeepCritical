"""
Workflow pattern utilities for DeepCritical agent interaction design patterns.

This module provides utility functions for implementing agent interaction patterns
with minimal external dependencies, focusing on Pydantic AI and Pydantic Graph integration.
"""

from __future__ import annotations

import asyncio
import json
import time
from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING, Any

# Import existing DeepCritical types
from DeepResearch.src.datatypes.workflow_patterns import (
    AgentInteractionMode,
    AgentInteractionState,
    InteractionMessage,
    InteractionPattern,
    MessageType,
    WorkflowOrchestrator,
)

if TYPE_CHECKING:
    from collections.abc import Callable


class ConsensusAlgorithm(str, Enum):
    """Consensus algorithms for collaborative patterns."""

    MAJORITY_VOTE = "majority_vote"
    WEIGHTED_AVERAGE = "weighted_average"
    CONFIDENCE_BASED = "confidence_based"
    SIMPLE_AGREEMENT = "simple_agreement"


class MessageRoutingStrategy(str, Enum):
    """Message routing strategies for agent interactions."""

    DIRECT = "direct"
    BROADCAST = "broadcast"
    ROUND_ROBIN = "round_robin"
    PRIORITY_BASED = "priority_based"
    LOAD_BALANCED = "load_balanced"


@dataclass
class ConsensusResult:
    """Result of consensus computation."""

    consensus_reached: bool
    final_result: Any
    confidence: float
    agreement_score: float
    individual_results: list[Any]
    algorithm_used: ConsensusAlgorithm


@dataclass
class InteractionMetrics:
    """Metrics for agent interaction patterns."""

    total_messages: int = 0
    successful_rounds: int = 0
    failed_rounds: int = 0
    average_response_time: float = 0.0
    consensus_reached_count: int = 0
    total_agents_participated: int = 0

    def record_round(
        self, success: bool, response_time: float, consensus: bool, agents_count: int
    ):
        """Record metrics for a round."""
        self.total_messages += agents_count
        if success:
            self.successful_rounds += 1
        else:
            self.failed_rounds += 1

        # Update average response time
        total_rounds = self.successful_rounds + self.failed_rounds
        if total_rounds == 1:
            self.average_response_time = response_time
        else:
            self.average_response_time = (
                (self.average_response_time * (total_rounds - 1)) + response_time
            ) / total_rounds

        if consensus:
            self.consensus_reached_count += 1

        self.total_agents_participated += agents_count


class WorkflowPatternUtils:
    """Utility functions for workflow pattern implementation."""

    @staticmethod
    def create_message(
        sender_id: str,
        receiver_id: str | None = None,
        message_type: MessageType = MessageType.DATA,
        content: Any = None,
        priority: int = 0,
        metadata: dict[str, Any] | None = None,
    ) -> InteractionMessage:
        """Create a new interaction message."""
        return InteractionMessage(
            sender_id=sender_id,
            receiver_id=receiver_id,
            message_type=message_type,
            content=content,
            priority=priority,
            metadata=metadata or {},
        )

    @staticmethod
    def create_broadcast_message(
        sender_id: str,
        content: Any,
        message_type: MessageType = MessageType.BROADCAST,
        priority: int = 0,
    ) -> InteractionMessage:
        """Create a broadcast message."""
        return InteractionMessage(
            sender_id=sender_id,
            receiver_id=None,  # None means broadcast
            message_type=message_type,
            content=content,
            priority=priority,
        )

    @staticmethod
    def create_request_message(
        sender_id: str,
        receiver_id: str,
        request_data: Any,
        request_type: str = "general",
        priority: int = 0,
    ) -> InteractionMessage:
        """Create a request message."""
        metadata = {
            "request_type": request_type,
            "timestamp": time.time(),
        }

        return InteractionMessage(
            sender_id=sender_id,
            receiver_id=receiver_id,
            message_type=MessageType.REQUEST,
            content=request_data,
            priority=priority,
            metadata=metadata,
        )

    @staticmethod
    def create_response_message(
        sender_id: str,
        receiver_id: str,
        request_id: str,
        response_data: Any,
        success: bool = True,
        error: str | None = None,
    ) -> InteractionMessage:
        """Create a response message."""
        metadata = {
            "request_id": request_id,
            "success": success,
            "timestamp": time.time(),
        }

        if error:
            metadata["error"] = error

        return InteractionMessage(
            sender_id=sender_id,
            receiver_id=receiver_id,
            message_type=MessageType.RESPONSE,
            content=response_data,
            metadata=metadata,
        )

    @staticmethod
    async def execute_agents_parallel(
        agent_executors: dict[str, Callable],
        messages: dict[str, list[InteractionMessage]],
        timeout: float = 30.0,
    ) -> dict[str, dict[str, Any]]:
        """Execute multiple agents in parallel with timeout."""

        async def execute_single_agent(
            agent_id: str, executor: Callable
        ) -> tuple[str, dict[str, Any]]:
            try:
                start_time = time.time()

                # Get messages for this agent
                agent_messages = messages.get(agent_id, [])

                # Execute agent
                result = await asyncio.wait_for(
                    executor(agent_messages), timeout=timeout
                )

                execution_time = time.time() - start_time

                return agent_id, {
                    "success": True,
                    "data": result,
                    "execution_time": execution_time,
                    "messages_processed": len(agent_messages),
                }

            except asyncio.TimeoutError:
                return agent_id, {
                    "success": False,
                    "error": f"Agent {agent_id} timed out after {timeout}s",
                    "execution_time": timeout,
                    "messages_processed": 0,
                }
            except Exception as e:
                return agent_id, {
                    "success": False,
                    "error": str(e),
                    "execution_time": time.time() - start_time,
                    "messages_processed": 0,
                }

        # Execute all agents in parallel
        tasks = [
            execute_single_agent(agent_id, executor)
            for agent_id, executor in agent_executors.items()
        ]

        results = {}
        for task in asyncio.as_completed(tasks):
            agent_id, result = await task
            results[agent_id] = result

        return results

    @staticmethod
    def compute_consensus(
        results: list[Any],
        algorithm: ConsensusAlgorithm = ConsensusAlgorithm.SIMPLE_AGREEMENT,
        confidence_threshold: float = 0.7,
    ) -> ConsensusResult:
        """Compute consensus from multiple agent results."""

        if not results:
            return ConsensusResult(
                consensus_reached=False,
                final_result=None,
                confidence=0.0,
                agreement_score=0.0,
                individual_results=results,
                algorithm_used=algorithm,
            )

        if len(results) == 1:
            return ConsensusResult(
                consensus_reached=True,
                final_result=results[0],
                confidence=1.0,
                agreement_score=1.0,
                individual_results=results,
                algorithm_used=algorithm,
            )

        # Extract confidence scores if available
        confidences = []
        for result in results:
            if isinstance(result, dict) and "confidence" in result:
                confidences.append(result["confidence"])
            else:
                confidences.append(0.5)  # Default confidence

        if algorithm == ConsensusAlgorithm.SIMPLE_AGREEMENT:
            return WorkflowPatternUtils._simple_agreement_consensus(
                results, confidences
            )
        if algorithm == ConsensusAlgorithm.MAJORITY_VOTE:
            return WorkflowPatternUtils._majority_vote_consensus(results, confidences)
        if algorithm == ConsensusAlgorithm.WEIGHTED_AVERAGE:
            return WorkflowPatternUtils._weighted_average_consensus(
                results, confidences
            )
        if algorithm == ConsensusAlgorithm.CONFIDENCE_BASED:
            return WorkflowPatternUtils._confidence_based_consensus(
                results, confidences, confidence_threshold
            )
        # Default to simple agreement
        return WorkflowPatternUtils._simple_agreement_consensus(results, confidences)

    @staticmethod
    def _simple_agreement_consensus(
        results: list[Any], confidences: list[float]
    ) -> ConsensusResult:
        """Simple agreement consensus - all results must be identical."""
        first_result = results[0]
        all_agree = all(
            WorkflowPatternUtils._results_equal(result, first_result)
            for result in results
        )

        if all_agree:
            # Calculate average confidence
            avg_confidence = sum(confidences) / len(confidences)
            return ConsensusResult(
                consensus_reached=True,
                final_result=first_result,
                confidence=avg_confidence,
                agreement_score=1.0,
                individual_results=results,
                algorithm_used=ConsensusAlgorithm.SIMPLE_AGREEMENT,
            )
        return ConsensusResult(
            consensus_reached=False,
            final_result=None,
            confidence=0.0,
            agreement_score=0.0,
            individual_results=results,
            algorithm_used=ConsensusAlgorithm.SIMPLE_AGREEMENT,
        )

    @staticmethod
    def _majority_vote_consensus(
        results: list[Any], confidences: list[float]
    ) -> ConsensusResult:
        """Majority vote consensus."""
        # Count occurrences of each result
        result_counts = {}
        for result in results:
            result_str = json.dumps(result, sort_keys=True)
            result_counts[result_str] = result_counts.get(result_str, 0) + 1

        # Find the most common result
        if result_counts:
            most_common_result_str = max(result_counts, key=result_counts.get)
            most_common_count = result_counts[most_common_result_str]
            total_results = len(results)

            agreement_score = most_common_count / total_results

            if agreement_score >= 0.5:  # Simple majority
                # Find the actual result object
                for result in results:
                    if json.dumps(result, sort_keys=True) == most_common_result_str:
                        most_common_result = result
                        break

                # Calculate weighted confidence
                weighted_confidence = (
                    sum(
                        conf
                        * (
                            1
                            if json.dumps(r, sort_keys=True) == most_common_result_str
                            else 0
                        )
                        for r, conf in zip(results, confidences, strict=False)
                    )
                    / sum(confidences)
                    if confidences
                    else 0.0
                )

                return ConsensusResult(
                    consensus_reached=True,
                    final_result=most_common_result,
                    confidence=weighted_confidence,
                    agreement_score=agreement_score,
                    individual_results=results,
                    algorithm_used=ConsensusAlgorithm.MAJORITY_VOTE,
                )

        return ConsensusResult(
            consensus_reached=False,
            final_result=None,
            confidence=0.0,
            agreement_score=0.0,
            individual_results=results,
            algorithm_used=ConsensusAlgorithm.MAJORITY_VOTE,
        )

    @staticmethod
    def _weighted_average_consensus(
        results: list[Any], confidences: list[float]
    ) -> ConsensusResult:
        """Weighted average consensus for numeric results."""
        numeric_results = []
        for result in results:
            try:
                numeric_results.append(float(result))
            except (ValueError, TypeError):
                # Non-numeric result, fall back to simple agreement
                return WorkflowPatternUtils._simple_agreement_consensus(
                    results, confidences
                )

        if numeric_results:
            # Weighted average
            weighted_sum = sum(
                r * c for r, c in zip(numeric_results, confidences, strict=False)
            )
            total_confidence = sum(confidences)

            if total_confidence > 0:
                final_result = weighted_sum / total_confidence
                avg_confidence = total_confidence / len(confidences)

                return ConsensusResult(
                    consensus_reached=True,
                    final_result=final_result,
                    confidence=avg_confidence,
                    agreement_score=1.0,  # Numeric consensus always agrees on the average
                    individual_results=results,
                    algorithm_used=ConsensusAlgorithm.WEIGHTED_AVERAGE,
                )

        return ConsensusResult(
            consensus_reached=False,
            final_result=None,
            confidence=0.0,
            agreement_score=0.0,
            individual_results=results,
            algorithm_used=ConsensusAlgorithm.WEIGHTED_AVERAGE,
        )

    @staticmethod
    def _confidence_based_consensus(
        results: list[Any], confidences: list[float], threshold: float
    ) -> ConsensusResult:
        """Confidence-based consensus."""
        # Find results with high confidence
        high_confidence_results = [
            (result, conf)
            for result, conf in zip(results, confidences, strict=False)
            if conf >= threshold
        ]

        if high_confidence_results:
            # Use the highest confidence result
            best_result, best_confidence = max(
                high_confidence_results, key=lambda x: x[1]
            )

            return ConsensusResult(
                consensus_reached=True,
                final_result=best_result,
                confidence=best_confidence,
                agreement_score=len(high_confidence_results) / len(results),
                individual_results=results,
                algorithm_used=ConsensusAlgorithm.CONFIDENCE_BASED,
            )

        return ConsensusResult(
            consensus_reached=False,
            final_result=None,
            confidence=0.0,
            agreement_score=0.0,
            individual_results=results,
            algorithm_used=ConsensusAlgorithm.CONFIDENCE_BASED,
        )

    @staticmethod
    def _results_equal(result1: Any, result2: Any) -> bool:
        """Check if two results are equal."""
        try:
            return json.dumps(result1, sort_keys=True) == json.dumps(
                result2, sort_keys=True
            )
        except (TypeError, ValueError):
            # Fallback to direct comparison
            return result1 == result2

    @staticmethod
    def route_messages(
        messages: list[InteractionMessage],
        routing_strategy: MessageRoutingStrategy,
        agents: list[str],
    ) -> dict[str, list[InteractionMessage]]:
        """Route messages to agents based on strategy."""
        routed_messages = {agent_id: [] for agent_id in agents}

        for message in messages:
            if routing_strategy == MessageRoutingStrategy.DIRECT:
                if message.receiver_id and message.receiver_id in agents:
                    routed_messages[message.receiver_id].append(message)

            elif routing_strategy == MessageRoutingStrategy.BROADCAST:
                for agent_id in agents:
                    routed_messages[agent_id].append(message)

            elif routing_strategy == MessageRoutingStrategy.ROUND_ROBIN:
                # Simple round-robin distribution
                if agents:
                    agent_index = hash(message.message_id) % len(agents)
                    target_agent = agents[agent_index]
                    routed_messages[target_agent].append(message)

            elif routing_strategy == MessageRoutingStrategy.PRIORITY_BASED:
                # Route by priority (highest priority first)
                if message.receiver_id and message.receiver_id in agents:
                    routed_messages[message.receiver_id].append(message)
                else:
                    # Broadcast to all if no specific receiver
                    for agent_id in agents:
                        routed_messages[agent_id].append(message)

            elif routing_strategy == MessageRoutingStrategy.LOAD_BALANCED:
                # Simple load balancing - send to agent with fewest messages
                target_agent = min(agents, key=lambda a: len(routed_messages[a]))
                routed_messages[target_agent].append(message)

        return routed_messages

    @staticmethod
    def validate_interaction_state(state: AgentInteractionState) -> list[str]:
        """Validate interaction state and return any errors."""
        errors = []

        if not state.agents:
            errors.append("No agents registered in interaction state")

        if state.max_rounds <= 0:
            errors.append("Max rounds must be positive")

        if not (0 <= state.consensus_threshold <= 1):
            errors.append("Consensus threshold must be between 0 and 1")

        return errors

    @staticmethod
    def create_agent_executor_wrapper(
        agent_instance: Any,
        message_handler: Callable | None = None,
    ) -> Callable:
        """Create a wrapper for agent execution."""

        async def executor(messages: list[InteractionMessage]) -> Any:
            """Execute agent with messages."""
            if not messages:
                return {"result": "No messages to process"}

            try:
                # Extract content from messages
                message_content = [
                    msg.content for msg in messages if msg.content is not None
                ]

                if message_handler:
                    # Use custom message handler
                    result = await message_handler(message_content)
                # Default agent execution
                elif hasattr(agent_instance, "execute"):
                    result = await agent_instance.execute(message_content)
                elif hasattr(agent_instance, "run"):
                    result = await agent_instance.run(message_content)
                elif hasattr(agent_instance, "process"):
                    result = await agent_instance.process(message_content)
                else:
                    result = {"result": "Agent executed successfully"}

                return result

            except Exception as e:
                return {"error": str(e), "success": False}

        return executor

    @staticmethod
    def create_sequential_executor_chain(
        agent_executors: dict[str, Callable],
        agent_order: list[str],
    ) -> Callable:
        """Create a sequential executor chain."""

        async def sequential_executor(messages: list[InteractionMessage]) -> Any:
            """Execute agents in sequence."""
            results = {}
            current_messages = messages

            for agent_id in agent_order:
                if agent_id not in agent_executors:
                    continue

                executor = agent_executors[agent_id]

                try:
                    result = await executor(current_messages)
                    results[agent_id] = result

                    # Pass result to next agent
                    if agent_id != agent_order[-1]:
                        # Create response message with result
                        response_message = InteractionMessage(
                            sender_id=agent_id,
                            receiver_id=agent_order[agent_order.index(agent_id) + 1],
                            message_type=MessageType.DATA,
                            content=result,
                        )
                        current_messages = [response_message]

                except Exception as e:
                    results[agent_id] = {"error": str(e), "success": False}
                    break

            return results

        return sequential_executor

    @staticmethod
    def create_hierarchical_executor(
        coordinator_executor: Callable,
        subordinate_executors: dict[str, Callable],
    ) -> Callable:
        """Create a hierarchical executor."""

        async def hierarchical_executor(messages: list[InteractionMessage]) -> Any:
            """Execute coordinator then subordinates."""
            results = {}

            try:
                # Execute coordinator first
                coordinator_result = await coordinator_executor(messages)
                results["coordinator"] = coordinator_result

                # Execute subordinates based on coordinator result
                if coordinator_result.get("success", False):
                    subordinate_tasks = []

                    for sub_id, sub_executor in subordinate_executors.items():
                        task = sub_executor(
                            [
                                *messages,
                                InteractionMessage(
                                    sender_id="coordinator",
                                    receiver_id=sub_id,
                                    message_type=MessageType.DATA,
                                    content=coordinator_result,
                                ),
                            ]
                        )
                        subordinate_tasks.append((sub_id, task))

                    # Execute subordinates in parallel
                    for sub_id, task in subordinate_tasks:
                        try:
                            sub_result = await task
                            results[sub_id] = sub_result
                        except Exception as e:
                            results[sub_id] = {"error": str(e), "success": False}

                return results

            except Exception as e:
                return {"error": str(e), "success": False}

        return hierarchical_executor

    @staticmethod
    def create_timeout_wrapper(
        executor: Callable,
        timeout: float = 30.0,
    ) -> Callable:
        """Wrap executor with timeout."""

        async def timeout_executor(messages: list[InteractionMessage]) -> Any:
            try:
                return await asyncio.wait_for(executor(messages), timeout=timeout)
            except asyncio.TimeoutError:
                return {
                    "error": f"Execution timed out after {timeout}s",
                    "success": False,
                }

        return timeout_executor

    @staticmethod
    def create_retry_wrapper(
        executor: Callable,
        max_retries: int = 3,
        retry_delay: float = 1.0,
    ) -> Callable:
        """Wrap executor with retry logic."""

        async def retry_executor(messages: list[InteractionMessage]) -> Any:
            last_error = None

            for attempt in range(max_retries + 1):
                try:
                    return await executor(messages)
                except Exception as e:
                    last_error = str(e)

                    if attempt < max_retries:
                        await asyncio.sleep(
                            retry_delay * (2**attempt)
                        )  # Exponential backoff
                        continue
                    return {
                        "error": f"Failed after {max_retries + 1} attempts: {last_error}",
                        "success": False,
                    }

            return {"error": "Unexpected retry failure", "success": False}

        return retry_executor

    @staticmethod
    def create_monitoring_wrapper(
        executor: Callable,
        metrics: InteractionMetrics | None = None,
    ) -> Callable:
        """Wrap executor with monitoring."""

        async def monitored_executor(messages: list[InteractionMessage]) -> Any:
            start_time = time.time()
            try:
                result = await executor(messages)
                execution_time = time.time() - start_time

                if metrics:
                    success = (
                        result.get("success", True)
                        if isinstance(result, dict)
                        else True
                    )
                    metrics.record_round(success, execution_time, True, 1)

                return result

            except Exception:
                execution_time = time.time() - start_time

                if metrics:
                    metrics.record_round(False, execution_time, False, 1)

                raise

        return monitored_executor

    @staticmethod
    def serialize_interaction_state(state: AgentInteractionState) -> dict[str, Any]:
        """Serialize interaction state for persistence."""
        return {
            "interaction_id": state.interaction_id,
            "pattern": state.pattern.value,
            "mode": state.mode.value,
            "agents": state.agents,
            "active_agents": state.active_agents,
            "agent_states": {k: v.value for k, v in state.agent_states.items()},
            "messages": [msg.to_dict() for msg in state.messages],
            "message_queue": [msg.to_dict() for msg in state.message_queue],
            "current_round": state.current_round,
            "max_rounds": state.max_rounds,
            "consensus_threshold": state.consensus_threshold,
            "execution_status": state.execution_status.value,
            "results": state.results,
            "final_result": state.final_result,
            "consensus_reached": state.consensus_reached,
            "start_time": state.start_time,
            "end_time": state.end_time,
            "errors": state.errors,
        }

    @staticmethod
    def deserialize_interaction_state(data: dict[str, Any]) -> AgentInteractionState:
        """Deserialize interaction state from persistence."""
        from DeepResearch.src.datatypes.agents import AgentStatus
        from DeepResearch.src.utils.execution_status import ExecutionStatus

        state = AgentInteractionState()
        state.interaction_id = data.get("interaction_id", state.interaction_id)
        state.pattern = InteractionPattern(
            data.get("pattern", InteractionPattern.COLLABORATIVE.value)
        )
        state.mode = AgentInteractionMode(
            data.get("mode", AgentInteractionMode.SYNC.value)
        )
        state.agents = data.get("agents", {})
        state.active_agents = data.get("active_agents", [])
        state.agent_states = {
            k: AgentStatus(v) for k, v in data.get("agent_states", {}).items()
        }
        state.messages = [
            InteractionMessage.from_dict(msg_data)
            for msg_data in data.get("messages", [])
        ]
        state.message_queue = [
            InteractionMessage.from_dict(msg_data)
            for msg_data in data.get("message_queue", [])
        ]
        state.current_round = data.get("current_round", 0)
        state.max_rounds = data.get("max_rounds", 10)
        state.consensus_threshold = data.get("consensus_threshold", 0.8)
        state.execution_status = ExecutionStatus(
            data.get("execution_status", ExecutionStatus.PENDING.value)
        )
        state.results = data.get("results", {})
        state.final_result = data.get("final_result")
        state.consensus_reached = data.get("consensus_reached", False)
        state.start_time = data.get("start_time", time.time())
        state.end_time = data.get("end_time")
        state.errors = data.get("errors", [])

        return state


# Factory functions for common patterns
def create_collaborative_orchestrator(
    agents: list[str],
    agent_executors: dict[str, Callable],
    config: dict[str, Any] | None = None,
) -> WorkflowOrchestrator:
    """Create a collaborative interaction orchestrator."""

    config = config or {}
    interaction_state = AgentInteractionState(
        pattern=InteractionPattern.COLLABORATIVE,
        max_rounds=config.get("max_rounds", 10),
        consensus_threshold=config.get("consensus_threshold", 0.8),
    )

    # Add agents
    for agent_id in agents:
        agent_type = agent_executors.get(f"{agent_id}_type")
        if agent_type and hasattr(agent_type, "__name__"):
            # Convert function to AgentType if possible
            from DeepResearch.src.datatypes.agents import AgentType

            try:
                agent_type_enum = getattr(
                    AgentType, getattr(agent_type, "__name__", "unknown").upper(), None
                )
                if agent_type_enum:
                    interaction_state.add_agent(agent_id, agent_type_enum)
            except (AttributeError, TypeError):
                pass  # Skip if conversion fails

    orchestrator = WorkflowOrchestrator(interaction_state)

    # Register executors
    for agent_id, executor in agent_executors.items():
        if agent_id.endswith("_type"):
            continue  # Skip type mappings
        orchestrator.register_agent_executor(agent_id, executor)

    return orchestrator


def create_sequential_orchestrator(
    agent_order: list[str],
    agent_executors: dict[str, Callable],
    config: dict[str, Any] | None = None,
) -> WorkflowOrchestrator:
    """Create a sequential interaction orchestrator."""

    config = config or {}
    interaction_state = AgentInteractionState(
        pattern=InteractionPattern.SEQUENTIAL,
        max_rounds=config.get("max_rounds", len(agent_order)),
    )

    # Add agents in order
    for agent_id in agent_order:
        agent_type = agent_executors.get(f"{agent_id}_type")
        if agent_type and hasattr(agent_type, "__name__"):
            # Convert function to AgentType if possible
            from DeepResearch.src.datatypes.agents import AgentType

            try:
                agent_type_enum = getattr(
                    AgentType, getattr(agent_type, "__name__", "unknown").upper(), None
                )
                if agent_type_enum:
                    interaction_state.add_agent(agent_id, agent_type_enum)
            except (AttributeError, TypeError):
                pass  # Skip if conversion fails

    orchestrator = WorkflowOrchestrator(interaction_state)

    # Register executors
    for agent_id, executor in agent_executors.items():
        if agent_id.endswith("_type"):
            continue  # Skip type mappings
        orchestrator.register_agent_executor(agent_id, executor)

    return orchestrator


def create_hierarchical_orchestrator(
    coordinator_id: str,
    subordinate_ids: list[str],
    agent_executors: dict[str, Callable],
    config: dict[str, Any] | None = None,
) -> WorkflowOrchestrator:
    """Create a hierarchical interaction orchestrator."""

    config = config or {}
    interaction_state = AgentInteractionState(
        pattern=InteractionPattern.HIERARCHICAL,
        max_rounds=config.get("max_rounds", 5),
    )

    # Add coordinator
    coordinator_type = agent_executors.get(f"{coordinator_id}_type")
    if coordinator_type and hasattr(coordinator_type, "__name__"):
        # Convert function to AgentType if possible
        from DeepResearch.src.datatypes.agents import AgentType

        try:
            agent_type_enum = getattr(
                AgentType,
                getattr(coordinator_type, "__name__", "unknown").upper(),
                None,
            )
            if agent_type_enum:
                interaction_state.add_agent(coordinator_id, agent_type_enum)
        except (AttributeError, TypeError):
            pass  # Skip if conversion fails

    # Add subordinates
    for sub_id in subordinate_ids:
        agent_type = agent_executors.get(f"{sub_id}_type")
        if agent_type and hasattr(agent_type, "__name__"):
            # Convert function to AgentType if possible
            from DeepResearch.src.datatypes.agents import AgentType

            try:
                agent_type_enum = getattr(
                    AgentType, getattr(agent_type, "__name__", "unknown").upper(), None
                )
                if agent_type_enum:
                    interaction_state.add_agent(sub_id, agent_type_enum)
            except (AttributeError, TypeError):
                pass  # Skip if conversion fails

    orchestrator = WorkflowOrchestrator(interaction_state)

    # Register executors
    for agent_id, executor in agent_executors.items():
        if agent_id.endswith("_type"):
            continue  # Skip type mappings
        orchestrator.register_agent_executor(agent_id, executor)

    return orchestrator


# Export all utilities
__all__ = [
    "ConsensusAlgorithm",
    "ConsensusResult",
    "InteractionMetrics",
    "MessageRoutingStrategy",
    "WorkflowPatternUtils",
    "create_collaborative_orchestrator",
    "create_hierarchical_orchestrator",
    "create_sequential_orchestrator",
]
