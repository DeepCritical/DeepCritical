"""
Multi-agent coordination data types for DeepCritical's workflow orchestration.

This module defines Pydantic models for multi-agent coordination patterns including
collaborative, sequential, hierarchical, and peer-to-peer coordination strategies.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class CoordinationStrategy(str, Enum):
    """Coordination strategies for multi-agent systems."""

    COLLABORATIVE = "collaborative"
    SEQUENTIAL = "sequential"
    HIERARCHICAL = "hierarchical"
    PEER_TO_PEER = "peer_to_peer"
    PIPELINE = "pipeline"
    CONSENSUS = "consensus"
    GROUP_CHAT = "group_chat"
    STATE_MACHINE_ENTRY = "state_machine_entry"
    SUBGRAPH_COORDINATION = "subgraph_coordination"


class CommunicationProtocol(str, Enum):
    """Communication protocols for agent coordination."""

    DIRECT = "direct"
    BROADCAST = "broadcast"
    HIERARCHICAL = "hierarchical"
    PEER_TO_PEER = "peer_to_peer"
    MESSAGE_PASSING = "message_passing"


class AgentState(BaseModel):
    """State of an individual agent."""

    agent_id: str = Field(..., description="Agent identifier")
    role: str = Field(..., description="Agent role")
    status: str = Field("pending", description="Agent status")
    current_task: str | None = Field(None, description="Current task")
    input_data: dict[str, Any] = Field(default_factory=dict, description="Input data")
    output_data: dict[str, Any] = Field(default_factory=dict, description="Output data")
    error_message: str | None = Field(None, description="Error message if failed")
    start_time: datetime | None = Field(None, description="Start time")
    end_time: datetime | None = Field(None, description="End time")
    iteration_count: int = Field(0, description="Number of iterations")
    max_iterations: int = Field(10, description="Maximum iterations")


class CoordinationMessage(BaseModel):
    """Message for agent coordination."""

    message_id: str = Field(..., description="Message identifier")
    sender_id: str = Field(..., description="Sender agent ID")
    receiver_id: str | None = Field(
        None, description="Receiver agent ID (None for broadcast)"
    )
    message_type: str = Field(..., description="Message type")
    content: dict[str, Any] = Field(..., description="Message content")
    timestamp: datetime = Field(
        default_factory=datetime.now, description="Message timestamp"
    )
    priority: int = Field(0, description="Message priority")


class CoordinationRound(BaseModel):
    """A single coordination round."""

    round_id: str = Field(..., description="Round identifier")
    round_number: int = Field(..., description="Round number")
    start_time: datetime = Field(
        default_factory=datetime.now, description="Round start time"
    )
    end_time: datetime | None = Field(None, description="Round end time")
    messages: list[CoordinationMessage] = Field(
        default_factory=list, description="Messages in this round"
    )
    agent_states: dict[str, AgentState] = Field(
        default_factory=dict, description="Agent states"
    )
    consensus_reached: bool = Field(False, description="Whether consensus was reached")
    consensus_score: float = Field(0.0, description="Consensus score")


class CoordinationResult(BaseModel):
    """Result of multi-agent coordination."""

    coordination_id: str = Field(..., description="Coordination identifier")
    system_id: str = Field(..., description="System identifier")
    strategy: CoordinationStrategy = Field(..., description="Coordination strategy")
    success: bool = Field(..., description="Whether coordination was successful")
    total_rounds: int = Field(..., description="Total coordination rounds")
    final_result: dict[str, Any] = Field(..., description="Final coordination result")
    agent_results: dict[str, dict[str, Any]] = Field(
        default_factory=dict, description="Individual agent results"
    )
    consensus_score: float = Field(0.0, description="Final consensus score")
    coordination_rounds: list[CoordinationRound] = Field(
        default_factory=list, description="Coordination rounds"
    )
    execution_time: float = Field(0.0, description="Total execution time")
    error_message: str | None = Field(None, description="Error message if failed")


class MultiAgentCoordinatorConfig(BaseModel):
    """Configuration for multi-agent coordinator."""

    system_id: str = Field(..., description="System identifier")
    coordination_strategy: CoordinationStrategy = Field(
        CoordinationStrategy.SEQUENTIAL, description="Coordination strategy"
    )
    max_rounds: int = Field(10, description="Maximum coordination rounds")
    consensus_threshold: float = Field(0.8, description="Consensus threshold")
    timeout: float = Field(300.0, description="Timeout in seconds")
    retry_attempts: int = Field(3, description="Retry attempts")
    enable_monitoring: bool = Field(True, description="Enable execution monitoring")


class AgentRole(str, Enum):
    """Roles for agents in multi-agent systems."""

    COORDINATOR = "coordinator"
    EXECUTOR = "executor"
    EVALUATOR = "evaluator"
    JUDGE = "judge"
    REVIEWER = "reviewer"
    LINTER = "linter"
    CODE_EXECUTOR = "code_executor"
    HYPOTHESIS_GENERATOR = "hypothesis_generator"
    HYPOTHESIS_TESTER = "hypothesis_tester"
    REASONING_AGENT = "reasoning_agent"
    SEARCH_AGENT = "search_agent"
    RAG_AGENT = "rag_agent"
    BIOINFORMATICS_AGENT = "bioinformatics_agent"
    ORCHESTRATOR_AGENT = "orchestrator_agent"
    SUBGRAPH_AGENT = "subgraph_agent"
    GROUP_CHAT_AGENT = "group_chat_agent"
    SEQUENTIAL_AGENT = "sequential_agent"
