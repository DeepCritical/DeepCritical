"""
Workflow orchestration data types for DeepCritical's workflow-of-workflows architecture.

This module defines Pydantic models for orchestrating multiple specialized workflows
including RAG, bioinformatics, search, and multi-agent systems.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


class WorkflowType(str, Enum):
    """Types of workflows that can be orchestrated."""

    PRIMARY_REACT = "primary_react"
    RAG_WORKFLOW = "rag_workflow"
    BIOINFORMATICS_WORKFLOW = "bioinformatics_workflow"
    SEARCH_WORKFLOW = "search_workflow"
    MULTI_AGENT_WORKFLOW = "multi_agent_workflow"
    HYPOTHESIS_GENERATION = "hypothesis_generation"
    HYPOTHESIS_TESTING = "hypothesis_testing"
    REASONING_WORKFLOW = "reasoning_workflow"
    CODE_EXECUTION_WORKFLOW = "code_execution_workflow"
    EVALUATION_WORKFLOW = "evaluation_workflow"
    NESTED_REACT_LOOP = "nested_react_loop"
    GROUP_CHAT_WORKFLOW = "group_chat_workflow"
    SEQUENTIAL_WORKFLOW = "sequential_workflow"
    SUBGRAPH_WORKFLOW = "subgraph_workflow"


class WorkflowStatus(str, Enum):
    """Status of workflow execution."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    PAUSED = "paused"


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


class DataLoaderType(str, Enum):
    """Types of data loaders for RAG workflows."""

    DOCUMENT_LOADER = "document_loader"
    WEB_SCRAPER = "web_scraper"
    DATABASE_LOADER = "database_loader"
    API_LOADER = "api_loader"
    FILE_LOADER = "file_loader"
    BIOINFORMATICS_LOADER = "bioinformatics_loader"
    SCIENTIFIC_PAPER_LOADER = "scientific_paper_loader"
    GENE_ONTOLOGY_LOADER = "gene_ontology_loader"
    PUBMED_LOADER = "pubmed_loader"
    GEO_LOADER = "geo_loader"


class WorkflowConfig(BaseModel):
    """Configuration for a specific workflow."""

    workflow_type: WorkflowType = Field(..., description="Type of workflow")
    name: str = Field(..., description="Workflow name")
    enabled: bool = Field(True, description="Whether workflow is enabled")
    priority: int = Field(0, description="Execution priority (higher = more priority)")
    max_retries: int = Field(3, description="Maximum retry attempts")
    timeout: float | None = Field(None, description="Timeout in seconds")
    dependencies: list[str] = Field(
        default_factory=list, description="Dependent workflow names"
    )
    parameters: dict[str, Any] = Field(
        default_factory=dict, description="Workflow-specific parameters"
    )
    output_format: str = Field("default", description="Expected output format")

    model_config = ConfigDict(json_schema_extra={})


class AgentConfig(BaseModel):
    """Configuration for an agent in multi-agent systems."""

    agent_id: str = Field(..., description="Unique agent identifier")
    role: AgentRole = Field(..., description="Agent role")
    model_name: str = Field("anthropic:claude-sonnet-4-0", description="Model to use")
    system_prompt: str | None = Field(None, description="Custom system prompt")
    tools: list[str] = Field(default_factory=list, description="Available tools")
    max_iterations: int = Field(10, description="Maximum iterations")
    temperature: float = Field(0.7, description="Model temperature")
    enabled: bool = Field(True, description="Whether agent is enabled")

    model_config = ConfigDict(json_schema_extra={})


class DataLoaderConfig(BaseModel):
    """Configuration for data loaders in RAG workflows."""

    loader_type: DataLoaderType = Field(..., description="Type of data loader")
    name: str = Field(..., description="Loader name")
    enabled: bool = Field(True, description="Whether loader is enabled")
    parameters: dict[str, Any] = Field(
        default_factory=dict, description="Loader parameters"
    )
    output_collection: str = Field(..., description="Output collection name")
    chunk_size: int = Field(1000, description="Chunk size for documents")
    chunk_overlap: int = Field(200, description="Chunk overlap")

    model_config = ConfigDict(json_schema_extra={})


class WorkflowExecution(BaseModel):
    """Execution context for a workflow."""

    execution_id: str = Field(
        default_factory=lambda: str(uuid.uuid4()), description="Unique execution ID"
    )
    workflow_config: WorkflowConfig = Field(..., description="Workflow configuration")
    status: WorkflowStatus = Field(WorkflowStatus.PENDING, description="Current status")
    start_time: datetime | None = Field(None, description="Start time")
    end_time: datetime | None = Field(None, description="End time")
    input_data: dict[str, Any] = Field(default_factory=dict, description="Input data")
    output_data: dict[str, Any] = Field(default_factory=dict, description="Output data")
    error_message: str | None = Field(None, description="Error message if failed")
    retry_count: int = Field(0, description="Number of retries attempted")
    parent_execution_id: str | None = Field(None, description="Parent execution ID")
    child_execution_ids: list[str] = Field(
        default_factory=list, description="Child execution IDs"
    )

    @property
    def duration(self) -> float | None:
        """Get execution duration in seconds."""
        if self.start_time and self.end_time:
            return (self.end_time - self.start_time).total_seconds()
        return None

    @property
    def is_completed(self) -> bool:
        """Check if execution is completed."""
        return self.status == WorkflowStatus.COMPLETED

    @property
    def is_failed(self) -> bool:
        """Check if execution failed."""
        return self.status == WorkflowStatus.FAILED

    model_config = ConfigDict(json_schema_extra={})


class MultiAgentSystemConfig(BaseModel):
    """Configuration for multi-agent systems."""

    system_id: str = Field(..., description="System identifier")
    name: str = Field(..., description="System name")
    agents: list[AgentConfig] = Field(..., description="Agent configurations")
    coordination_strategy: str = Field(
        "sequential", description="Coordination strategy"
    )
    communication_protocol: str = Field("direct", description="Communication protocol")
    max_rounds: int = Field(10, description="Maximum coordination rounds")
    consensus_threshold: float = Field(0.8, description="Consensus threshold")
    enabled: bool = Field(True, description="Whether system is enabled")

    model_config = ConfigDict(json_schema_extra={})


class JudgeConfig(BaseModel):
    """Configuration for LLM judges."""

    judge_id: str = Field(..., description="Judge identifier")
    name: str = Field(..., description="Judge name")
    model_name: str = Field("anthropic:claude-sonnet-4-0", description="Model to use")
    evaluation_criteria: list[str] = Field(..., description="Evaluation criteria")
    scoring_scale: str = Field("1-10", description="Scoring scale")
    enabled: bool = Field(True, description="Whether judge is enabled")

    model_config = ConfigDict(json_schema_extra={})


class WorkflowOrchestrationConfig(BaseModel):
    """Main configuration for workflow orchestration."""

    primary_workflow: WorkflowConfig = Field(
        ..., description="Primary REACT workflow config"
    )
    sub_workflows: list[WorkflowConfig] = Field(
        default_factory=list, description="Sub-workflow configs"
    )
    data_loaders: list[DataLoaderConfig] = Field(
        default_factory=list, description="Data loader configs"
    )
    multi_agent_systems: list[MultiAgentSystemConfig] = Field(
        default_factory=list, description="Multi-agent system configs"
    )
    judges: list[JudgeConfig] = Field(default_factory=list, description="Judge configs")
    execution_strategy: str = Field(
        "parallel", description="Execution strategy (parallel, sequential, hybrid)"
    )
    max_concurrent_workflows: int = Field(5, description="Maximum concurrent workflows")
    global_timeout: float | None = Field(None, description="Global timeout in seconds")
    enable_monitoring: bool = Field(True, description="Enable execution monitoring")
    enable_caching: bool = Field(True, description="Enable result caching")

    @field_validator("sub_workflows")
    @classmethod
    def validate_sub_workflows(cls, v):
        """Validate sub-workflow configurations."""
        names = [w.name for w in v]
        if len(names) != len(set(names)):
            msg = "Sub-workflow names must be unique"
            raise ValueError(msg)
        return v

    model_config = ConfigDict(json_schema_extra={})


class WorkflowResult(BaseModel):
    """Result from workflow execution."""

    execution_id: str = Field(..., description="Execution ID")
    workflow_name: str = Field(..., description="Workflow name")
    status: WorkflowStatus = Field(..., description="Final status")
    output_data: dict[str, Any] = Field(..., description="Output data")
    metadata: dict[str, Any] = Field(
        default_factory=dict, description="Execution metadata"
    )
    quality_score: float | None = Field(None, description="Quality score from judges")
    execution_time: float = Field(..., description="Execution time in seconds")
    error_details: dict[str, Any] | None = Field(
        None, description="Error details if failed"
    )

    model_config = ConfigDict(json_schema_extra={})


class HypothesisDataset(BaseModel):
    """Dataset of hypotheses generated by workflows."""

    dataset_id: str = Field(
        default_factory=lambda: str(uuid.uuid4()), description="Dataset ID"
    )
    name: str = Field(..., description="Dataset name")
    description: str = Field(..., description="Dataset description")
    hypotheses: list[dict[str, Any]] = Field(..., description="Generated hypotheses")
    metadata: dict[str, Any] = Field(
        default_factory=dict, description="Dataset metadata"
    )
    creation_date: datetime = Field(
        default_factory=datetime.now, description="Creation date"
    )
    source_workflows: list[str] = Field(
        default_factory=list, description="Source workflow names"
    )

    model_config = ConfigDict(json_schema_extra={})


class HypothesisTestingEnvironment(BaseModel):
    """Environment for testing hypotheses."""

    environment_id: str = Field(
        default_factory=lambda: str(uuid.uuid4()), description="Environment ID"
    )
    name: str = Field(..., description="Environment name")
    hypothesis: dict[str, Any] = Field(..., description="Hypothesis to test")
    test_configuration: dict[str, Any] = Field(..., description="Test configuration")
    expected_outcomes: list[str] = Field(..., description="Expected outcomes")
    success_criteria: dict[str, Any] = Field(..., description="Success criteria")
    test_data: dict[str, Any] = Field(default_factory=dict, description="Test data")
    results: dict[str, Any] | None = Field(None, description="Test results")
    status: WorkflowStatus = Field(WorkflowStatus.PENDING, description="Test status")

    model_config = ConfigDict(json_schema_extra={})


class ReasoningResult(BaseModel):
    """Result from reasoning workflows."""

    reasoning_id: str = Field(
        default_factory=lambda: str(uuid.uuid4()), description="Reasoning ID"
    )
    question: str = Field(..., description="Reasoning question")
    answer: str = Field(..., description="Reasoning answer")
    reasoning_chain: list[str] = Field(..., description="Reasoning steps")
    confidence: float = Field(..., description="Confidence score")
    supporting_evidence: list[dict[str, Any]] = Field(
        ..., description="Supporting evidence"
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict, description="Reasoning metadata"
    )

    model_config = ConfigDict(json_schema_extra={})


class WorkflowComposition(BaseModel):
    """Dynamic composition of workflows based on user input and config."""

    composition_id: str = Field(
        default_factory=lambda: str(uuid.uuid4()), description="Composition ID"
    )
    user_input: str = Field(..., description="User input/query")
    selected_workflows: list[str] = Field(..., description="Selected workflow names")
    workflow_dependencies: dict[str, list[str]] = Field(
        default_factory=dict, description="Workflow dependencies"
    )
    execution_order: list[str] = Field(..., description="Execution order")
    expected_outputs: dict[str, str] = Field(
        default_factory=dict, description="Expected outputs by workflow"
    )
    composition_strategy: str = Field("adaptive", description="Composition strategy")

    model_config = ConfigDict(json_schema_extra={})


class OrchestrationState(BaseModel):
    """State of the workflow orchestration system."""

    state_id: str = Field(
        default_factory=lambda: str(uuid.uuid4()), description="State ID"
    )
    active_executions: list[WorkflowExecution] = Field(
        default_factory=list, description="Active executions"
    )
    completed_executions: list[WorkflowResult] = Field(
        default_factory=list, description="Completed executions"
    )
    pending_workflows: list[WorkflowConfig] = Field(
        default_factory=list, description="Pending workflows"
    )
    current_composition: WorkflowComposition | None = Field(
        None, description="Current composition"
    )
    system_metrics: dict[str, Any] = Field(
        default_factory=dict, description="System metrics"
    )
    last_updated: datetime = Field(
        default_factory=datetime.now, description="Last update time"
    )


class OrchestratorDependencies(BaseModel):
    """Dependencies for the workflow orchestrator."""

    config: dict[str, Any] = Field(default_factory=dict)
    user_input: str = Field(..., description="User input/query")
    context: dict[str, Any] = Field(default_factory=dict)
    available_workflows: list[str] = Field(default_factory=list)
    available_agents: list[str] = Field(default_factory=list)
    available_judges: list[str] = Field(default_factory=list)


class WorkflowSpawnRequest(BaseModel):
    """Request to spawn a new workflow."""

    workflow_type: WorkflowType = Field(..., description="Type of workflow to spawn")
    workflow_name: str = Field(..., description="Name of the workflow")
    input_data: dict[str, Any] = Field(..., description="Input data for the workflow")
    parameters: dict[str, Any] = Field(
        default_factory=dict, description="Workflow parameters"
    )
    priority: int = Field(0, description="Execution priority")
    dependencies: list[str] = Field(
        default_factory=list, description="Dependent workflow names"
    )


class WorkflowSpawnResult(BaseModel):
    """Result of spawning a workflow."""

    success: bool = Field(..., description="Whether spawning was successful")
    execution_id: str = Field(..., description="Execution ID of the spawned workflow")
    workflow_name: str = Field(..., description="Name of the spawned workflow")
    status: WorkflowStatus = Field(..., description="Initial status")
    error_message: str | None = Field(None, description="Error message if failed")


class MultiAgentCoordinationRequest(BaseModel):
    """Request for multi-agent coordination."""

    system_id: str = Field(..., description="Multi-agent system ID")
    task_description: str = Field(..., description="Task description")
    input_data: dict[str, Any] = Field(..., description="Input data")
    coordination_strategy: str = Field(
        "collaborative", description="Coordination strategy"
    )
    max_rounds: int = Field(10, description="Maximum coordination rounds")


class MultiAgentCoordinationResult(BaseModel):
    """Result of multi-agent coordination."""

    success: bool = Field(..., description="Whether coordination was successful")
    system_id: str = Field(..., description="System ID")
    final_result: dict[str, Any] = Field(..., description="Final coordination result")
    coordination_rounds: int = Field(..., description="Number of coordination rounds")
    agent_results: dict[str, Any] = Field(
        default_factory=dict, description="Individual agent results"
    )
    consensus_score: float = Field(0.0, description="Consensus score")


class JudgeEvaluationRequest(BaseModel):
    """Request for judge evaluation."""

    judge_id: str = Field(..., description="Judge ID")
    content_to_evaluate: dict[str, Any] = Field(..., description="Content to evaluate")
    evaluation_criteria: list[str] = Field(..., description="Evaluation criteria")
    context: dict[str, Any] = Field(
        default_factory=dict, description="Evaluation context"
    )


class JudgeEvaluationResult(BaseModel):
    """Result of judge evaluation."""

    success: bool = Field(..., description="Whether evaluation was successful")
    judge_id: str = Field(..., description="Judge ID")
    overall_score: float = Field(..., description="Overall evaluation score")
    criterion_scores: dict[str, float] = Field(
        default_factory=dict, description="Scores by criterion"
    )
    feedback: str = Field(..., description="Detailed feedback")
    recommendations: list[str] = Field(
        default_factory=list, description="Improvement recommendations"
    )

    model_config = ConfigDict(json_schema_extra={})


class MultiStateMachineMode(str, Enum):
    """Modes for multi-statemachine coordination."""

    GROUP_CHAT = "group_chat"
    SEQUENTIAL = "sequential"
    HIERARCHICAL = "hierarchical"
    PARALLEL = "parallel"
    PIPELINE = "pipeline"
    CONSENSUS = "consensus"


class SubgraphType(str, Enum):
    """Types of subgraphs that can be spawned."""

    RAG_SUBGRAPH = "rag_subgraph"
    SEARCH_SUBGRAPH = "search_subgraph"
    CODE_SUBGRAPH = "code_subgraph"
    BIOINFORMATICS_SUBGRAPH = "bioinformatics_subgraph"
    REASONING_SUBGRAPH = "reasoning_subgraph"
    EVALUATION_SUBGRAPH = "evaluation_subgraph"
    CUSTOM_SUBGRAPH = "custom_subgraph"


class LossFunctionType(str, Enum):
    """Types of loss functions for end conditions."""

    CONFIDENCE_THRESHOLD = "confidence_threshold"
    QUALITY_SCORE = "quality_score"
    CONSENSUS_LEVEL = "consensus_level"
    ITERATION_LIMIT = "iteration_limit"
    TIME_LIMIT = "time_limit"
    CUSTOM_LOSS = "custom_loss"


class BreakCondition(BaseModel):
    """Condition for breaking out of REACT loops."""

    condition_type: LossFunctionType = Field(..., description="Type of break condition")
    threshold: float = Field(..., description="Threshold value for the condition")
    operator: str = Field(">=", description="Comparison operator (>=, <=, ==, !=)")
    enabled: bool = Field(True, description="Whether this condition is enabled")
    custom_function: str | None = Field(
        None, description="Custom function for custom_loss type"
    )


class NestedReactConfig(BaseModel):
    """Configuration for nested REACT loops."""

    loop_id: str = Field(..., description="Unique identifier for the nested loop")
    parent_loop_id: str | None = Field(None, description="Parent loop ID if nested")
    max_iterations: int = Field(10, description="Maximum iterations for this loop")
    break_conditions: list[BreakCondition] = Field(
        default_factory=list, description="Break conditions"
    )
    state_machine_mode: MultiStateMachineMode = Field(
        MultiStateMachineMode.GROUP_CHAT, description="State machine mode"
    )
    subgraphs: list[SubgraphType] = Field(
        default_factory=list, description="Subgraphs to include"
    )
    agent_roles: list[AgentRole] = Field(
        default_factory=list, description="Agent roles for this loop"
    )
    tools: list[str] = Field(
        default_factory=list, description="Tools available to agents"
    )
    priority: int = Field(0, description="Execution priority")


class AgentOrchestratorConfig(BaseModel):
    """Configuration for agent-based orchestrators."""

    orchestrator_id: str = Field(..., description="Orchestrator identifier")
    agent_role: AgentRole = Field(
        AgentRole.ORCHESTRATOR_AGENT, description="Role of the orchestrator agent"
    )
    model_name: str = Field(
        "anthropic:claude-sonnet-4-0", description="Model for the orchestrator"
    )
    break_conditions: list[BreakCondition] = Field(
        default_factory=list, description="Break conditions"
    )
    max_nested_loops: int = Field(5, description="Maximum number of nested loops")
    coordination_strategy: str = Field(
        "collaborative", description="Coordination strategy"
    )
    can_spawn_subgraphs: bool = Field(
        True, description="Whether this orchestrator can spawn subgraphs"
    )
    can_spawn_agents: bool = Field(
        True, description="Whether this orchestrator can spawn agents"
    )


class SubgraphConfig(BaseModel):
    """Configuration for subgraphs."""

    subgraph_id: str = Field(..., description="Subgraph identifier")
    subgraph_type: SubgraphType = Field(..., description="Type of subgraph")
    state_machine_path: str = Field(
        ..., description="Path to state machine implementation"
    )
    entry_node: str = Field(..., description="Entry node for the subgraph")
    exit_node: str = Field(..., description="Exit node for the subgraph")
    parameters: dict[str, Any] = Field(
        default_factory=dict, description="Subgraph parameters"
    )
    tools: list[str] = Field(
        default_factory=list, description="Tools available in subgraph"
    )
    max_execution_time: float = Field(
        300.0, description="Maximum execution time in seconds"
    )
    enabled: bool = Field(True, description="Whether this subgraph is enabled")


class AppMode(str, Enum):
    """Modes for app.py execution."""

    SINGLE_REACT = "single_react"
    MULTI_LEVEL_REACT = "multi_level_react"
    NESTED_ORCHESTRATION = "nested_orchestration"
    SUBGRAPH_COORDINATION = "subgraph_coordination"
    LOSS_DRIVEN = "loss_driven"
    CUSTOM_MODE = "custom_mode"


class NestedLoopRequest(BaseModel):
    """Request to spawn a nested REACT loop."""

    loop_id: str = Field(..., description="Loop identifier")
    parent_loop_id: str | None = Field(None, description="Parent loop ID")
    max_iterations: int = Field(10, description="Maximum iterations")
    break_conditions: list[BreakCondition] = Field(
        default_factory=list, description="Break conditions"
    )
    state_machine_mode: MultiStateMachineMode = Field(
        MultiStateMachineMode.GROUP_CHAT, description="State machine mode"
    )
    subgraphs: list[SubgraphType] = Field(
        default_factory=list, description="Subgraphs to include"
    )
    agent_roles: list[AgentRole] = Field(
        default_factory=list, description="Agent roles"
    )
    tools: list[str] = Field(default_factory=list, description="Available tools")
    priority: int = Field(0, description="Execution priority")


class SubgraphSpawnRequest(BaseModel):
    """Request to spawn a subgraph."""

    subgraph_id: str = Field(..., description="Subgraph identifier")
    subgraph_type: SubgraphType = Field(..., description="Type of subgraph")
    parameters: dict[str, Any] = Field(
        default_factory=dict, description="Subgraph parameters"
    )
    entry_node: str = Field(..., description="Entry node")
    max_execution_time: float = Field(300.0, description="Maximum execution time")
    tools: list[str] = Field(default_factory=list, description="Available tools")


class BreakConditionCheck(BaseModel):
    """Result of break condition evaluation."""

    condition_met: bool = Field(..., description="Whether the condition is met")
    condition_type: LossFunctionType = Field(..., description="Type of condition")
    current_value: float = Field(..., description="Current value")
    threshold: float = Field(..., description="Threshold value")
    should_break: bool = Field(..., description="Whether to break the loop")


class OrchestrationResult(BaseModel):
    """Result of orchestration execution."""

    success: bool = Field(..., description="Whether orchestration was successful")
    final_answer: str = Field(..., description="Final answer")
    nested_loops_spawned: list[str] = Field(
        default_factory=list, description="Nested loops spawned"
    )
    subgraphs_executed: list[str] = Field(
        default_factory=list, description="Subgraphs executed"
    )
    total_iterations: int = Field(..., description="Total iterations")
    break_reason: str | None = Field(None, description="Reason for breaking")
    execution_metadata: dict[str, Any] = Field(
        default_factory=dict, description="Execution metadata"
    )


class AppConfiguration(BaseModel):
    """Main configuration for app.py modes."""

    mode: AppMode = Field(AppMode.SINGLE_REACT, description="Execution mode")
    primary_orchestrator: AgentOrchestratorConfig = Field(
        ..., description="Primary orchestrator config"
    )
    nested_react_configs: list[NestedReactConfig] = Field(
        default_factory=list, description="Nested REACT configurations"
    )
    subgraph_configs: list[SubgraphConfig] = Field(
        default_factory=list, description="Subgraph configurations"
    )
    loss_functions: list[BreakCondition] = Field(
        default_factory=list, description="Loss functions for end conditions"
    )
    global_break_conditions: list[BreakCondition] = Field(
        default_factory=list, description="Global break conditions"
    )
    execution_strategy: str = Field(
        "adaptive", description="Overall execution strategy"
    )
    max_total_iterations: int = Field(
        100, description="Maximum total iterations across all loops"
    )
    max_total_time: float = Field(
        3600.0, description="Maximum total execution time in seconds"
    )


class WorkflowOrchestrationState(BaseModel):
    """State for workflow orchestration execution."""

    workflow_id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        description="Unique workflow identifier",
    )
    workflow_type: WorkflowType = Field(
        ..., description="Type of workflow being orchestrated"
    )
    status: WorkflowStatus = Field(
        default=WorkflowStatus.PENDING, description="Current workflow status"
    )
    current_step: str | None = Field(None, description="Current execution step")
    progress: float = Field(
        default=0.0, ge=0.0, le=1.0, description="Execution progress (0-1)"
    )
    results: dict[str, Any] = Field(
        default_factory=dict, description="Workflow execution results"
    )
    errors: list[str] = Field(default_factory=list, description="Execution errors")
    metadata: dict[str, Any] = Field(
        default_factory=dict, description="Additional metadata"
    )
    started_at: datetime | None = Field(None, description="Workflow start time")
    completed_at: datetime | None = Field(None, description="Workflow completion time")
    sub_workflows: list[dict[str, Any]] = Field(
        default_factory=list, description="Sub-workflow information"
    )

    @field_validator("sub_workflows")
    @classmethod
    def validate_sub_workflows(cls, v):
        """Validate sub-workflows structure."""
        for workflow in v:
            if not isinstance(workflow, dict):
                msg = "Each sub-workflow must be a dictionary"
                raise ValueError(msg)
        return v
