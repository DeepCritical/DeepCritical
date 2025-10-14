"""
Multi-agent coordination patterns for DeepCritical's workflow orchestration.

This module implements coordination strategies for multi-agent systems including
collaborative, sequential, hierarchical, and peer-to-peer coordination patterns.
"""

from __future__ import annotations

import asyncio
import time
from dataclasses import field
from datetime import datetime
from typing import Any

from pydantic_ai import Agent, RunContext

from DeepResearch.src.datatypes.multi_agent import (
    AgentRole,
    AgentState,
    CoordinationMessage,
    CoordinationResult,
    CoordinationRound,
    CoordinationStrategy,
)
from DeepResearch.src.datatypes.workflow_orchestration import (
    AgentConfig,
    MultiAgentSystemConfig,
    WorkflowStatus,
)
from DeepResearch.src.prompts.multi_agent_coordinator import (
    get_instructions,
    get_system_prompt,
)

# Note: JudgeEvaluationRequest and JudgeEvaluationResult are defined in workflow_orchestrator.py
# Import them from there if needed in the future


class MultiAgentCoordinator:
    """Coordinator for multi-agent systems."""

    def __init__(self, system_config: MultiAgentSystemConfig):
        self.system_config = system_config
        self.agents: dict[str, Agent] = {}
        self.judges: dict[str, Any] = field(default_factory=dict)
        self.message_queue: list[CoordinationMessage] = field(default_factory=list)
        self.coordination_history: list[CoordinationRound] = field(default_factory=list)

    def __post_init__(self):
        """Initialize the coordinator."""
        self.initialize_agents()
        self._create_judges()

    def initialize_agents(self) -> None:
        """Create agent instances."""
        for agent_config in self.system_config.agents:
            if agent_config.enabled:
                agent = Agent(
                    model=agent_config.model_name,
                    system_prompt=agent_config.system_prompt
                    or self._get_default_system_prompt(agent_config.role),
                    instructions=self._get_default_instructions(agent_config.role),
                )
                self._register_agent_tools(agent, agent_config)
                self.agents[agent_config.agent_id] = agent

    def _create_judges(self):
        """Create judge instances."""
        # This would create actual judge instances
        # For now, we'll use placeholder judges
        self.judges = {
            "quality_judge": None,
            "consensus_judge": None,
            "coordination_judge": None,
        }

    def _get_default_system_prompt(self, role: AgentRole) -> str:
        """Get default system prompt for an agent role."""
        return get_system_prompt(role.value)

    def _get_default_instructions(self, role: AgentRole) -> list[str]:
        """Get default instructions for an agent role."""
        return get_instructions(role.value)

    def _register_agent_tools(self, agent: Agent, agent_config: AgentConfig):
        """Register tools for an agent."""

        @agent.tool
        def send_message(
            ctx: RunContext,
            receiver_id: str,
            message_type: str,
            content: dict[str, Any],
            priority: int = 0,
        ) -> bool:
            """Send a message to another agent."""
            message = CoordinationMessage(
                message_id=f"msg_{int(time.time())}",
                sender_id=agent_config.agent_id,
                receiver_id=receiver_id,
                message_type=message_type,
                content=content,
                priority=priority,
            )
            self.message_queue.append(message)
            return True

        @agent.tool
        def broadcast_message(
            ctx: RunContext,
            message_type: str,
            content: dict[str, Any],
            priority: int = 0,
        ) -> bool:
            """Broadcast a message to all agents."""
            message = CoordinationMessage(
                message_id=f"msg_{int(time.time())}",
                sender_id=agent_config.agent_id,
                receiver_id=None,  # None for broadcast
                message_type=message_type,
                content=content,
                priority=priority,
            )
            self.message_queue.append(message)
            return True

        @agent.tool
        def get_agent_status(ctx: RunContext, agent_id: str) -> dict[str, Any]:
            """Get the status of another agent."""
            # This would return actual agent status
            return {"agent_id": agent_id, "status": "active", "current_task": "working"}

        @agent.tool
        def request_consensus(
            ctx: RunContext, topic: str, options: list[str]
        ) -> dict[str, Any]:
            """Request consensus on a topic."""
            # This would implement consensus building
            return {"topic": topic, "consensus": "placeholder", "score": 0.8}

    async def coordinate(
        self,
        task_description: str,
        input_data: dict[str, Any],
        max_rounds: int | None = None,
    ) -> CoordinationResult:
        """Coordinate the multi-agent system."""
        start_time = time.time()
        coordination_id = f"coord_{int(time.time())}"

        try:
            # Initialize agent states
            agent_states = {}
            for agent_id in self.agents:
                agent_states[agent_id] = AgentState(
                    agent_id=agent_id,
                    role=self._get_agent_role(agent_id),
                    input_data=input_data,
                )

            # Execute coordination strategy
            if (
                self.system_config.coordination_strategy
                == CoordinationStrategy.COLLABORATIVE
            ):
                result = await self._coordinate_collaborative(
                    coordination_id, task_description, agent_states, max_rounds
                )
            elif (
                self.system_config.coordination_strategy
                == CoordinationStrategy.SEQUENTIAL
            ):
                result = await self._coordinate_sequential(
                    coordination_id, task_description, agent_states, max_rounds
                )
            elif (
                self.system_config.coordination_strategy
                == CoordinationStrategy.HIERARCHICAL
            ):
                result = await self._coordinate_hierarchical(
                    coordination_id, task_description, agent_states, max_rounds
                )
            elif (
                self.system_config.coordination_strategy
                == CoordinationStrategy.PEER_TO_PEER
            ):
                result = await self._coordinate_peer_to_peer(
                    coordination_id, task_description, agent_states, max_rounds
                )
            elif (
                self.system_config.coordination_strategy
                == CoordinationStrategy.PIPELINE
            ):
                result = await self._coordinate_pipeline(
                    coordination_id, task_description, agent_states, max_rounds
                )
            elif (
                self.system_config.coordination_strategy
                == CoordinationStrategy.CONSENSUS
            ):
                result = await self._coordinate_consensus(
                    coordination_id, task_description, agent_states, max_rounds
                )
            elif (
                self.system_config.coordination_strategy
                == CoordinationStrategy.GROUP_CHAT
            ):
                result = await self._coordinate_group_chat(
                    coordination_id, task_description, agent_states, max_rounds
                )
            elif (
                self.system_config.coordination_strategy
                == CoordinationStrategy.STATE_MACHINE_ENTRY
            ):
                result = await self._coordinate_state_machine_entry(
                    coordination_id, task_description, agent_states, max_rounds
                )
            elif (
                self.system_config.coordination_strategy
                == CoordinationStrategy.SUBGRAPH_COORDINATION
            ):
                result = await self._coordinate_subgraph_coordination(
                    coordination_id, task_description, agent_states, max_rounds
                )
            else:
                msg = f"Unknown coordination strategy: {self.system_config.coordination_strategy}"
                raise ValueError(msg)

            result.execution_time = time.time() - start_time
            return result

        except Exception as e:
            return CoordinationResult(
                coordination_id=coordination_id,
                system_id=self.system_config.system_id,
                strategy=CoordinationStrategy(self.system_config.coordination_strategy),
                success=False,
                total_rounds=0,
                final_result={},
                execution_time=time.time() - start_time,
                error_message=str(e),
            )

    async def _coordinate_collaborative(
        self,
        coordination_id: str,
        task_description: str,
        agent_states: dict[str, AgentState],
        max_rounds: int | None,
    ) -> CoordinationResult:
        """Coordinate agents collaboratively."""
        max_rounds = max_rounds or self.system_config.max_rounds
        rounds = []

        for round_num in range(max_rounds):
            round_id = f"{coordination_id}_round_{round_num}"
            round_start = datetime.now()

            # Create coordination round
            coordination_round = CoordinationRound(
                round_id=round_id, round_number=round_num, start_time=round_start
            )

            # Execute agents in parallel
            tasks = []
            for agent_id, agent in self.agents.items():
                if agent_states[agent_id].status != WorkflowStatus.FAILED:
                    task = self._execute_agent_round(
                        agent_id,
                        agent,
                        task_description,
                        agent_states[agent_id],
                        round_num,
                    )
                    tasks.append(task)

            # Wait for all agents to complete
            results = await asyncio.gather(*tasks, return_exceptions=True)

            # Process results
            for i, result in enumerate(results):
                agent_id = list(self.agents.keys())[i]
                if isinstance(result, Exception):
                    agent_states[agent_id].status = WorkflowStatus.FAILED
                    agent_states[agent_id].error_message = str(result)
                else:
                    agent_states[agent_id].output_data = (
                        result if isinstance(result, dict) else {"result": result}
                    )
                    agent_states[agent_id].status = WorkflowStatus.COMPLETED

            # Check for consensus
            consensus_score = self._calculate_consensus(agent_states)
            coordination_round.consensus_score = consensus_score
            coordination_round.consensus_reached = (
                consensus_score >= self.system_config.consensus_threshold
            )

            coordination_round.end_time = datetime.now()
            coordination_round.agent_states = agent_states.copy()
            rounds.append(coordination_round)

            # Break if consensus reached
            if coordination_round.consensus_reached:
                break

        # Generate final result
        final_result = self._synthesize_results(agent_states)

        return CoordinationResult(
            coordination_id=coordination_id,
            system_id=self.system_config.system_id,
            strategy=CoordinationStrategy.COLLABORATIVE,
            success=True,
            total_rounds=len(rounds),
            final_result=final_result,
            agent_results={
                agent_id: state.output_data for agent_id, state in agent_states.items()
            },
            consensus_score=rounds[-1].consensus_score if rounds else 0.0,
            coordination_rounds=rounds,
        )

    async def _coordinate_sequential(
        self,
        coordination_id: str,
        task_description: str,
        agent_states: dict[str, AgentState],
        max_rounds: int | None,
    ) -> CoordinationResult:
        """Coordinate agents sequentially."""
        max_rounds = max_rounds or self.system_config.max_rounds
        rounds = []

        for round_num in range(max_rounds):
            round_id = f"{coordination_id}_round_{round_num}"
            round_start = datetime.now()

            coordination_round = CoordinationRound(
                round_id=round_id, round_number=round_num, start_time=round_start
            )

            # Execute agents sequentially
            for agent_id, agent in self.agents.items():
                if agent_states[agent_id].status != WorkflowStatus.FAILED:
                    try:
                        result = await self._execute_agent_round(
                            agent_id,
                            agent,
                            task_description,
                            agent_states[agent_id],
                            round_num,
                        )
                        agent_states[agent_id].output_data = (
                            result if isinstance(result, dict) else {"result": result}
                        )
                        agent_states[agent_id].status = WorkflowStatus.COMPLETED
                    except Exception as e:
                        agent_states[agent_id].status = WorkflowStatus.FAILED
                        agent_states[agent_id].error_message = str(e)

            # Check for completion
            all_completed = all(
                state.status in [WorkflowStatus.COMPLETED, WorkflowStatus.FAILED]
                for state in agent_states.values()
            )

            coordination_round.end_time = datetime.now()
            coordination_round.agent_states = agent_states.copy()
            rounds.append(coordination_round)

            if all_completed:
                break

        # Generate final result
        final_result = self._synthesize_results(agent_states)

        return CoordinationResult(
            coordination_id=coordination_id,
            system_id=self.system_config.system_id,
            strategy=CoordinationStrategy.SEQUENTIAL,
            success=True,
            total_rounds=len(rounds),
            final_result=final_result,
            agent_results={
                agent_id: state.output_data for agent_id, state in agent_states.items()
            },
            consensus_score=1.0,  # Sequential doesn't use consensus
            coordination_rounds=rounds,
        )

    async def _coordinate_hierarchical(
        self,
        coordination_id: str,
        task_description: str,
        agent_states: dict[str, AgentState],
        max_rounds: int | None,
    ) -> CoordinationResult:
        """Coordinate agents hierarchically."""
        # Find coordinator agent
        coordinator_id = None
        for agent_id, state in agent_states.items():
            if AgentRole(state.role) == AgentRole.COORDINATOR:
                coordinator_id = agent_id
                break

        if not coordinator_id:
            msg = "No coordinator agent found for hierarchical coordination"
            raise ValueError(msg)

        # Execute coordinator first
        coordinator = self.agents[coordinator_id]
        coordinator_result = await self._execute_agent_round(
            coordinator_id,
            coordinator,
            task_description,
            agent_states[coordinator_id],
            0,
        )
        agent_states[coordinator_id].output_data = coordinator_result
        agent_states[coordinator_id].status = WorkflowStatus.COMPLETED

        # Coordinator distributes tasks to other agents
        task_distribution = coordinator_result.get("task_distribution", {})

        # Execute other agents based on coordinator's distribution
        for agent_id, agent in self.agents.items():
            if (
                agent_id != coordinator_id
                and agent_states[agent_id].status != WorkflowStatus.FAILED
            ):
                agent_task = task_distribution.get(agent_id, task_description)
                try:
                    result = await self._execute_agent_round(
                        agent_id, agent, agent_task, agent_states[agent_id], 1
                    )
                    agent_states[agent_id].output_data = (
                        result if isinstance(result, dict) else {"result": result}
                    )
                    agent_states[agent_id].status = WorkflowStatus.COMPLETED
                except Exception as e:
                    agent_states[agent_id].status = WorkflowStatus.FAILED
                    agent_states[agent_id].error_message = str(e)

        # Create coordination round
        coordination_round = CoordinationRound(
            round_id=f"{coordination_id}_hierarchical",
            round_number=0,
            start_time=datetime.now(),
            end_time=datetime.now(),
            agent_states=agent_states.copy(),
            consensus_reached=True,
            consensus_score=1.0,
        )

        # Generate final result
        final_result = self._synthesize_results(agent_states)

        return CoordinationResult(
            coordination_id=coordination_id,
            system_id=self.system_config.system_id,
            strategy=CoordinationStrategy.HIERARCHICAL,
            success=True,
            total_rounds=1,
            final_result=final_result,
            agent_results={
                agent_id: state.output_data for agent_id, state in agent_states.items()
            },
            consensus_score=1.0,
            coordination_rounds=[coordination_round],
        )

    async def _coordinate_peer_to_peer(
        self,
        coordination_id: str,
        task_description: str,
        agent_states: dict[str, AgentState],
        max_rounds: int | None,
    ) -> CoordinationResult:
        """Coordinate agents in peer-to-peer fashion."""
        # Similar to collaborative but with more direct communication
        return await self._coordinate_collaborative(
            coordination_id, task_description, agent_states, max_rounds
        )

    async def _coordinate_pipeline(
        self,
        coordination_id: str,
        task_description: str,
        agent_states: dict[str, AgentState],
        max_rounds: int | None,
    ) -> CoordinationResult:
        """Coordinate agents in pipeline fashion."""
        # Execute agents in a pipeline where output of one becomes input of next
        pipeline_order = self._determine_pipeline_order(agent_states)

        current_data = {
            "task": task_description,
            "input": agent_states[next(iter(agent_states.keys()))].input_data,
        }

        for agent_id in pipeline_order:
            if agent_states[agent_id].status != WorkflowStatus.FAILED:
                agent_states[agent_id].input_data = current_data
                try:
                    result = await self._execute_agent_round(
                        agent_id,
                        self.agents[agent_id],
                        task_description,
                        agent_states[agent_id],
                        0,
                    )
                    agent_states[agent_id].output_data = (
                        result if isinstance(result, dict) else {"result": result}
                    )
                    agent_states[agent_id].status = WorkflowStatus.COMPLETED
                    current_data = result  # Pass output to next agent
                except Exception as e:
                    agent_states[agent_id].status = WorkflowStatus.FAILED
                    agent_states[agent_id].error_message = str(e)
                    break

        # Create coordination round
        coordination_round = CoordinationRound(
            round_id=f"{coordination_id}_pipeline",
            round_number=0,
            start_time=datetime.now(),
            end_time=datetime.now(),
            agent_states=agent_states.copy(),
            consensus_reached=True,
            consensus_score=1.0,
        )

        # Generate final result
        final_result = self._synthesize_results(agent_states)

        return CoordinationResult(
            coordination_id=coordination_id,
            system_id=self.system_config.system_id,
            strategy=CoordinationStrategy.PIPELINE,
            success=True,
            total_rounds=1,
            final_result=final_result,
            agent_results={
                agent_id: state.output_data for agent_id, state in agent_states.items()
            },
            consensus_score=1.0,
            coordination_rounds=[coordination_round],
        )

    async def _coordinate_consensus(
        self,
        coordination_id: str,
        task_description: str,
        agent_states: dict[str, AgentState],
        max_rounds: int | None,
    ) -> CoordinationResult:
        """Coordinate agents to reach consensus."""
        max_rounds = max_rounds or self.system_config.max_rounds
        rounds = []

        for round_num in range(max_rounds):
            round_id = f"{coordination_id}_consensus_round_{round_num}"
            round_start = datetime.now()

            coordination_round = CoordinationRound(
                round_id=round_id, round_number=round_num, start_time=round_start
            )

            # Each agent provides their opinion
            opinions = {}
            for agent_id, agent in self.agents.items():
                if agent_states[agent_id].status != WorkflowStatus.FAILED:
                    try:
                        result = await self._execute_agent_round(
                            agent_id,
                            agent,
                            task_description,
                            agent_states[agent_id],
                            round_num,
                        )
                        opinions[agent_id] = result
                        agent_states[agent_id].output_data = (
                            result if isinstance(result, dict) else {"result": result}
                        )
                    except Exception as e:
                        agent_states[agent_id].status = WorkflowStatus.FAILED
                        agent_states[agent_id].error_message = str(e)

            # Calculate consensus
            consensus_score = self._calculate_consensus_from_opinions(opinions)
            coordination_round.consensus_score = consensus_score
            coordination_round.consensus_reached = (
                consensus_score >= self.system_config.consensus_threshold
            )

            coordination_round.end_time = datetime.now()
            coordination_round.agent_states = agent_states.copy()
            rounds.append(coordination_round)

            if coordination_round.consensus_reached:
                break

        # Generate final result based on consensus
        final_result = self._synthesize_consensus_results(
            agent_states, rounds[-1].consensus_score
        )

        return CoordinationResult(
            coordination_id=coordination_id,
            system_id=self.system_config.system_id,
            strategy=CoordinationStrategy.CONSENSUS,
            success=True,
            total_rounds=len(rounds),
            final_result=final_result,
            agent_results={
                agent_id: state.output_data for agent_id, state in agent_states.items()
            },
            consensus_score=rounds[-1].consensus_score if rounds else 0.0,
            coordination_rounds=rounds,
        )

    async def _execute_agent_round(
        self,
        agent_id: str,
        agent: Agent,
        task_description: str,
        agent_state: AgentState,
        round_num: int,
    ) -> dict[str, Any]:
        """Execute a single round for an agent."""
        agent_state.status = WorkflowStatus.RUNNING
        agent_state.start_time = datetime.now()
        agent_state.iteration_count += 1

        try:
            # Prepare input for agent
            agent_input = {
                "task": task_description,
                "round": round_num,
                "input_data": agent_state.input_data,
                "previous_output": agent_state.output_data,
                "iteration": agent_state.iteration_count,
            }

            # Execute agent
            result = await agent.run(str(agent_input))

            agent_state.status = WorkflowStatus.COMPLETED
            agent_state.end_time = datetime.now()

            if hasattr(result, "model_dump"):
                model_dump_method = getattr(result, "model_dump", None)
                if model_dump_method is not None and callable(model_dump_method):
                    return model_dump_method()
            return {"result": str(result)}

        except Exception as e:
            agent_state.status = WorkflowStatus.FAILED
            agent_state.error_message = str(e)
            agent_state.end_time = datetime.now()
            raise

    def _get_agent_role(self, agent_id: str) -> AgentRole:
        """Get the role of an agent."""
        for agent_config in self.system_config.agents:
            if agent_config.agent_id == agent_id:
                return AgentRole(agent_config.role.value)
        return AgentRole.EXECUTOR

    def _determine_pipeline_order(
        self, agent_states: dict[str, AgentState]
    ) -> list[str]:
        """Determine the order of agents in a pipeline."""
        # Simple ordering based on role priority
        role_priority = {
            AgentRole.COORDINATOR: 0,
            AgentRole.EXECUTOR: 1,
            AgentRole.REASONING_AGENT: 2,
            AgentRole.EVALUATOR: 3,
            AgentRole.REVIEWER: 4,
            AgentRole.JUDGE: 5,
        }

        return sorted(
            agent_states.keys(),
            key=lambda x: role_priority.get(AgentRole(agent_states[x].role), 10),
        )

    def _calculate_consensus(self, agent_states: dict[str, AgentState]) -> float:
        """Calculate consensus score from agent states."""
        # Simple consensus calculation based on output similarity
        outputs = [
            state.output_data
            for state in agent_states.values()
            if state.status == WorkflowStatus.COMPLETED
        ]
        if len(outputs) < 2:
            return 1.0

        # Placeholder consensus calculation
        return 0.8

    def _calculate_consensus_from_opinions(
        self, opinions: dict[str, dict[str, Any]]
    ) -> float:
        """Calculate consensus score from agent opinions."""
        # Placeholder consensus calculation
        return 0.8

    def _synthesize_results(
        self, agent_states: dict[str, AgentState]
    ) -> dict[str, Any]:
        """Synthesize results from all agent states."""
        results = {}
        for agent_id, state in agent_states.items():
            if state.status == WorkflowStatus.COMPLETED:
                results[agent_id] = state.output_data

        return {
            "synthesized_result": "Combined results from all agents",
            "agent_results": results,
            "success_count": sum(
                1
                for state in agent_states.values()
                if state.status == WorkflowStatus.COMPLETED
            ),
            "total_agents": len(agent_states),
        }

    def _synthesize_consensus_results(
        self, agent_states: dict[str, AgentState], consensus_score: float
    ) -> dict[str, Any]:
        """Synthesize results based on consensus."""
        results = self._synthesize_results(agent_states)
        results["consensus_score"] = consensus_score
        results["consensus_reached"] = (
            consensus_score >= self.system_config.consensus_threshold
        )
        return results

    async def _coordinate_group_chat(
        self,
        coordination_id: str,
        task_description: str,
        agent_states: dict[str, AgentState],
        max_rounds: int | None,
    ) -> CoordinationResult:
        """Coordinate agents in group chat mode (no strict turn-taking)."""
        max_rounds = max_rounds or self.system_config.max_rounds
        rounds = []

        for round_num in range(max_rounds):
            round_id = f"{coordination_id}_group_chat_round_{round_num}"
            round_start = datetime.now()

            coordination_round = CoordinationRound(
                round_id=round_id, round_number=round_num, start_time=round_start
            )

            # In group chat, agents can speak when they have something to contribute
            # This is more flexible than strict turn-taking
            active_agents = []
            for agent_id in self.agents:
                if agent_states[agent_id].status != WorkflowStatus.FAILED:
                    # Check if agent wants to contribute (simplified logic)
                    if self._agent_wants_to_contribute(
                        agent_id, agent_states[agent_id], round_num
                    ):
                        active_agents.append(agent_id)

            # Execute active agents in parallel
            tasks = []
            for agent_id in active_agents:
                task = self._execute_agent_round(
                    agent_id,
                    self.agents[agent_id],
                    task_description,
                    agent_states[agent_id],
                    round_num,
                )
                tasks.append(task)

            if tasks:
                results = await asyncio.gather(*tasks, return_exceptions=True)

                # Process results
                for i, result in enumerate(results):
                    agent_id = active_agents[i]
                    if isinstance(result, Exception):
                        agent_states[agent_id].status = WorkflowStatus.FAILED
                        agent_states[agent_id].error_message = str(result)
                    else:
                        agent_states[agent_id].output_data = (
                            result if isinstance(result, dict) else {"result": result}
                        )
                        agent_states[agent_id].status = WorkflowStatus.COMPLETED

            # Check for natural conversation end
            if self._conversation_should_end(agent_states, round_num):
                break

            coordination_round.end_time = datetime.now()
            coordination_round.agent_states = agent_states.copy()
            rounds.append(coordination_round)

        # Generate final result
        final_result = self._synthesize_results(agent_states)

        return CoordinationResult(
            coordination_id=coordination_id,
            system_id=self.system_config.system_id,
            strategy=CoordinationStrategy.GROUP_CHAT,
            success=True,
            total_rounds=len(rounds),
            final_result=final_result,
            agent_results={
                agent_id: state.output_data for agent_id, state in agent_states.items()
            },
            consensus_score=1.0,  # Group chat doesn't use consensus
            coordination_rounds=rounds,
        )

    async def _coordinate_state_machine_entry(
        self,
        coordination_id: str,
        task_description: str,
        agent_states: dict[str, AgentState],
        max_rounds: int | None,
    ) -> CoordinationResult:
        """Coordinate agents by entering state machines."""
        max_rounds = max_rounds or self.system_config.max_rounds
        rounds = []

        # Determine which state machines to enter based on task
        state_machines = self._identify_relevant_state_machines(task_description)

        for round_num in range(max_rounds):
            round_id = f"{coordination_id}_state_machine_round_{round_num}"
            round_start = datetime.now()

            coordination_round = CoordinationRound(
                round_id=round_id, round_number=round_num, start_time=round_start
            )

            # Execute agents by entering state machines
            for agent_id, agent in self.agents.items():
                if agent_states[agent_id].status != WorkflowStatus.FAILED:
                    # Determine which state machine this agent should enter
                    state_machine = self._select_state_machine_for_agent(
                        agent_id, state_machines
                    )

                    if state_machine:
                        try:
                            result = await self._enter_state_machine(
                                agent_id,
                                agent,
                                state_machine,
                                task_description,
                                agent_states[agent_id],
                            )
                            agent_states[agent_id].output_data = (
                                result
                                if isinstance(result, dict)
                                else {"result": result}
                            )
                            agent_states[agent_id].status = WorkflowStatus.COMPLETED
                        except Exception as e:
                            agent_states[agent_id].status = WorkflowStatus.FAILED
                            agent_states[agent_id].error_message = str(e)

            coordination_round.end_time = datetime.now()
            coordination_round.agent_states = agent_states.copy()
            rounds.append(coordination_round)

            # Check if all state machines have been processed
            if self._all_state_machines_processed(state_machines):
                break

        # Generate final result
        final_result = self._synthesize_results(agent_states)

        return CoordinationResult(
            coordination_id=coordination_id,
            system_id=self.system_config.system_id,
            strategy=CoordinationStrategy.STATE_MACHINE_ENTRY,
            success=True,
            total_rounds=len(rounds),
            final_result=final_result,
            agent_results={
                agent_id: state.output_data for agent_id, state in agent_states.items()
            },
            consensus_score=1.0,
            coordination_rounds=rounds,
        )

    async def _coordinate_subgraph_coordination(
        self,
        coordination_id: str,
        task_description: str,
        agent_states: dict[str, AgentState],
        max_rounds: int | None,
    ) -> CoordinationResult:
        """Coordinate agents by executing subgraphs."""
        max_rounds = max_rounds or self.system_config.max_rounds
        rounds = []

        # Identify relevant subgraphs
        subgraphs = self._identify_relevant_subgraphs(task_description)

        for round_num in range(max_rounds):
            round_id = f"{coordination_id}_subgraph_round_{round_num}"
            round_start = datetime.now()

            coordination_round = CoordinationRound(
                round_id=round_id, round_number=round_num, start_time=round_start
            )

            # Execute subgraphs with agents
            for subgraph in subgraphs:
                try:
                    subgraph_result = await self._execute_subgraph_with_agents(
                        subgraph, task_description, agent_states
                    )

                    # Update agent states with subgraph results
                    for agent_id, result in subgraph_result.items():
                        if agent_id in agent_states:
                            agent_states[agent_id].output_data = (
                                result
                                if isinstance(result, dict)
                                else {"result": result}
                            )
                            agent_states[agent_id].status = WorkflowStatus.COMPLETED

                except Exception as e:
                    # Handle subgraph execution errors
                    for agent_id, agent_state in agent_states.items():
                        if agent_state.status != WorkflowStatus.FAILED:
                            agent_state.error_message = (
                                f"Subgraph {subgraph} failed: {e!s}"
                            )

            coordination_round.end_time = datetime.now()
            coordination_round.agent_states = agent_states.copy()
            rounds.append(coordination_round)

            # Check if all subgraphs have been processed
            if self._all_subgraphs_processed(subgraphs):
                break

        # Generate final result
        final_result = self._synthesize_results(agent_states)

        return CoordinationResult(
            coordination_id=coordination_id,
            system_id=self.system_config.system_id,
            strategy=CoordinationStrategy.SUBGRAPH_COORDINATION,
            success=True,
            total_rounds=len(rounds),
            final_result=final_result,
            agent_results={
                agent_id: state.output_data for agent_id, state in agent_states.items()
            },
            consensus_score=1.0,
            coordination_rounds=rounds,
        )

    def _agent_wants_to_contribute(
        self, agent_id: str, agent_state: AgentState, round_num: int
    ) -> bool:
        """Determine if an agent wants to contribute in group chat mode."""
        # Simplified logic - in practice, this would be more sophisticated
        return round_num % 2 == 0 or agent_state.iteration_count < 3

    def _conversation_should_end(
        self, agent_states: dict[str, AgentState], round_num: int
    ) -> bool:
        """Determine if the group chat conversation should end."""
        # Check if all agents have contributed meaningfully
        active_agents = [
            state
            for state in agent_states.values()
            if state.status == WorkflowStatus.COMPLETED
        ]
        return len(active_agents) >= len(agent_states) * 0.8 or round_num >= 5

    def _identify_relevant_state_machines(self, task_description: str) -> list[str]:
        """Identify relevant state machines for the task."""
        # This would analyze the task and determine which state machines to use
        state_machines = []

        task_lower = task_description.lower()
        if any(term in task_lower for term in ["search", "find", "look"]):
            state_machines.append("search_workflow")
        if any(term in task_lower for term in ["rag", "retrieve", "document"]):
            state_machines.append("rag_workflow")
        if any(term in task_lower for term in ["code", "program", "script"]):
            state_machines.append("code_execution_workflow")
        if any(term in task_lower for term in ["bioinformatics", "protein", "gene"]):
            state_machines.append("bioinformatics_workflow")

        return state_machines if state_machines else ["search_workflow"]

    def _select_state_machine_for_agent(
        self, agent_id: str, state_machines: list[str]
    ) -> str | None:
        """Select the appropriate state machine for an agent."""
        # This would match agent roles to state machines
        agent_role = self._get_agent_role(agent_id)

        if agent_role == AgentRole.SEARCH_AGENT and "search_workflow" in state_machines:
            return "search_workflow"
        if agent_role == AgentRole.RAG_AGENT and "rag_workflow" in state_machines:
            return "rag_workflow"
        if (
            agent_role == AgentRole.CODE_EXECUTOR
            and "code_execution_workflow" in state_machines
        ):
            return "code_execution_workflow"
        if (
            agent_role == AgentRole.BIOINFORMATICS_AGENT
            and "bioinformatics_workflow" in state_machines
        ):
            return "bioinformatics_workflow"

        # Default to first available state machine
        return state_machines[0] if state_machines else None

    async def _enter_state_machine(
        self,
        agent_id: str,
        agent: Agent,
        state_machine: str,
        task_description: str,
        agent_state: AgentState,
    ) -> dict[str, Any]:
        """Enter a state machine with an agent."""
        # This would actually enter the state machine
        # For now, return a placeholder
        return {
            "agent_id": agent_id,
            "state_machine": state_machine,
            "result": f"Agent {agent_id} executed {state_machine}",
            "status": "completed",
        }

    def _identify_relevant_subgraphs(self, task_description: str) -> list[str]:
        """Identify relevant subgraphs for the task."""
        # Similar to state machines but for subgraphs
        subgraphs = []

        task_lower = task_description.lower()
        if any(term in task_lower for term in ["search", "find", "look"]):
            subgraphs.append("search_subgraph")
        if any(term in task_lower for term in ["rag", "retrieve", "document"]):
            subgraphs.append("rag_subgraph")
        if any(term in task_lower for term in ["code", "program", "script"]):
            subgraphs.append("code_subgraph")
        if any(term in task_lower for term in ["bioinformatics", "protein", "gene"]):
            subgraphs.append("bioinformatics_subgraph")

        return subgraphs if subgraphs else ["search_subgraph"]

    async def _execute_subgraph_with_agents(
        self, subgraph: str, task_description: str, agent_states: dict[str, AgentState]
    ) -> dict[str, dict[str, Any]]:
        """Execute a subgraph with agents."""
        # This would execute the actual subgraph
        # For now, return placeholder results
        results = {}
        for agent_id in agent_states:
            results[agent_id] = {
                "subgraph": subgraph,
                "result": f"Agent {agent_id} executed {subgraph}",
                "status": "completed",
            }
        return results

    def _all_state_machines_processed(self, state_machines: list[str]) -> bool:
        """Check if all state machines have been processed."""
        # This would track which state machines have been processed
        return True  # Simplified for now

    def _all_subgraphs_processed(self, subgraphs: list[str]) -> bool:
        """Check if all subgraphs have been processed."""
        # This would track which subgraphs have been processed
        return True  # Simplified for now
