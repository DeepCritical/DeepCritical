from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import Annotated, Any

import hydra
from omegaconf import DictConfig
from pydantic_graph import BaseNode, Edge, End, Graph, GraphRunContext

from .agents import ExecutionHistory, ExecutorAgent, ParserAgent, PlannerAgent
from .src.agents.agent_orchestrator import AgentOrchestrator
from .src.agents.prime_executor import ExecutionContext, ToolExecutor
from .src.agents.prime_parser import QueryParser, StructuredProblem
from .src.agents.prime_planner import PlanGenerator, WorkflowDAG
from .src.agents.workflow_orchestrator import (
    PrimaryWorkflowOrchestrator,
    WorkflowOrchestrationConfig,
)
from .src.datatypes.orchestrator import Orchestrator  # type: ignore
from .src.datatypes.workflow_orchestration import (
    AgentOrchestratorConfig,
    AgentRole,
    AppConfiguration,
    AppMode,
    BreakCondition,
    DataLoaderType,
    HypothesisDataset,
    HypothesisTestingEnvironment,
    LossFunctionType,
    MultiStateMachineMode,
    NestedReactConfig,
    OrchestrationState,
    ReasoningResult,
    SubgraphConfig,
    SubgraphType,
    WorkflowType,
)
from .src.utils.execution_history import ExecutionHistory as PrimeExecutionHistory
from .src.utils.tool_registry import ToolRegistry

# from .src.tools import bioinformatics_tools


# --- State for the deep research workflow ---
@dataclass
class ResearchState:
    """State object for the research workflow.

    This dataclass maintains the state of a research workflow execution,
    containing the original question, planning results, intermediate notes,
    and final answers.

    Attributes:
        question: The original research question being answered.
        plan: High-level plan steps (optional).
        full_plan: Detailed execution plan with parameters.
        notes: Intermediate notes and observations.
        answers: Final answers and results.
        structured_problem: PRIME-specific structured problem representation.
        workflow_dag: PRIME workflow DAG for execution.
        execution_results: Results from tool execution.
        config: Global configuration object.
    """

    question: str
    plan: list[str] | None = field(default_factory=list)
    full_plan: list[dict[str, Any]] | None = field(default_factory=list)
    notes: list[str] = field(default_factory=list)
    answers: list[str] = field(default_factory=list)
    # PRIME-specific state
    structured_problem: StructuredProblem | None = None
    workflow_dag: WorkflowDAG | None = None
    execution_results: dict[str, Any] = field(default_factory=dict)
    # Global config for access by nodes
    config: DictConfig | None = None
    # Workflow orchestration state
    orchestration_config: WorkflowOrchestrationConfig | None = None
    orchestration_state: OrchestrationState | None = None
    spawned_workflows: list[str] = field(default_factory=list)
    multi_agent_results: dict[str, Any] = field(default_factory=dict)
    hypothesis_datasets: list[HypothesisDataset] = field(default_factory=list)
    testing_environments: list[HypothesisTestingEnvironment] = field(
        default_factory=list
    )
    reasoning_results: list[ReasoningResult] = field(default_factory=list)
    judge_evaluations: dict[str, Any] = field(default_factory=dict)
    # Enhanced REACT architecture state
    app_configuration: AppConfiguration | None = None
    agent_orchestrator: AgentOrchestrator | None = None
    nested_loops: dict[str, Any] = field(default_factory=dict)
    active_subgraphs: dict[str, Any] = field(default_factory=dict)
    break_conditions_met: list[str] = field(default_factory=list)
    loss_function_values: dict[str, float] = field(default_factory=dict)
    current_mode: AppMode | None = None


# --- Nodes ---
@dataclass
class Plan(BaseNode[ResearchState]):
    """Planning node for research workflow.

    This node analyzes the research question and determines the appropriate
    workflow path based on configuration flags and question characteristics.
    Routes to different execution paths including search, REACT workflows,
    or challenge mode.
    """

    async def run(
        self, ctx: GraphRunContext[ResearchState]
    ) -> (
        Search
        | PrimaryREACTWorkflow
        | EnhancedREACTWorkflow
        | PrepareChallenge
        | PrimeParse
        | BioinformaticsParse
        | RAGParse
        | DSPlan
    ):
        cfg = ctx.state.config

        # Check for enhanced REACT architecture modes
        app_mode_cfg = getattr(cfg, "app_mode", None)
        if app_mode_cfg:
            ctx.state.current_mode = AppMode(app_mode_cfg)
            ctx.state.notes.append(f"Enhanced REACT architecture mode: {app_mode_cfg}")
            return EnhancedREACTWorkflow()

        # Check if primary REACT workflow orchestration is enabled
        orchestration_cfg = getattr(cfg, "workflow_orchestration", None)
        if getattr(orchestration_cfg or {}, "enabled", False):
            ctx.state.notes.append("Primary REACT workflow orchestration enabled")
            return PrimaryREACTWorkflow()

        # Switch to challenge flow if enabled
        if (
            hasattr(cfg, "challenge")
            and cfg.challenge
            and getattr(cfg.challenge, "enabled", False)
        ):
            ctx.state.notes.append("Challenge mode enabled")
            return PrepareChallenge()

        # Route to PRIME flow if enabled
        prime_cfg = getattr(getattr(cfg, "flows", {}), "prime", None)
        if getattr(prime_cfg or {}, "enabled", False):
            ctx.state.notes.append("PRIME flow enabled")
            return PrimeParse()

        # Route to Bioinformatics flow if enabled
        bioinformatics_cfg = getattr(getattr(cfg, "flows", {}), "bioinformatics", None)
        if getattr(bioinformatics_cfg or {}, "enabled", False):
            ctx.state.notes.append("Bioinformatics flow enabled")
            return BioinformaticsParse()

        # Route to RAG flow if enabled
        rag_cfg = getattr(getattr(cfg, "flows", {}), "rag", None)
        if getattr(rag_cfg or {}, "enabled", False):
            ctx.state.notes.append("RAG flow enabled")
            return RAGParse()

        # Route to DeepSearch flow if enabled
        deepsearch_cfg = getattr(getattr(cfg, "flows", {}), "deepsearch", None)
        node_example_cfg = getattr(getattr(cfg, "flows", {}), "node_example", None)
        jina_ai_cfg = getattr(getattr(cfg, "flows", {}), "jina_ai", None)
        if any(
            [
                getattr(deepsearch_cfg or {}, "enabled", False),
                getattr(node_example_cfg or {}, "enabled", False),
                getattr(jina_ai_cfg or {}, "enabled", False),
            ]
        ):
            ctx.state.notes.append("DeepSearch flow enabled")
            return DSPlan()

        # Default flow
        parser = ParserAgent()
        planner = PlannerAgent()
        parsed = parser.parse(ctx.state.question)
        plan = planner.plan(parsed)
        ctx.state.full_plan = plan
        ctx.state.plan = [f"{s['tool']}" for s in plan]
        ctx.state.notes.append(f"Planned steps: {ctx.state.plan}")
        return Search()


# --- Primary REACT Workflow Node ---
@dataclass
class PrimaryREACTWorkflow(BaseNode[ResearchState]):
    async def run(
        self, ctx: GraphRunContext[ResearchState]
    ) -> Annotated[End[str], Edge(label="done")]:
        """Execute the primary REACT workflow with orchestration."""
        cfg = ctx.state.config
        orchestration_cfg = getattr(cfg, "workflow_orchestration", {})

        try:
            # Initialize orchestration configuration
            orchestration_config = self._create_orchestration_config(orchestration_cfg)
            ctx.state.orchestration_config = orchestration_config

            # Create primary workflow orchestrator
            orchestrator = PrimaryWorkflowOrchestrator(orchestration_config)
            ctx.state.orchestration_state = orchestrator.state

            # Execute primary workflow
            if cfg is None:
                from omegaconf import DictConfig

                cfg = DictConfig({})
            result = await orchestrator.execute_primary_workflow(
                ctx.state.question, cfg
            )

            # Process results
            if result["success"]:
                # Extract spawned workflows
                ctx.state.spawned_workflows = list(
                    orchestrator.state.active_executions
                ) + [
                    exec.execution_id
                    for exec in orchestrator.state.completed_executions
                ]

                # Extract multi-agent results
                ctx.state.multi_agent_results = result.get("result", {})

                # Generate comprehensive output
                final_answer = self._generate_comprehensive_output(
                    ctx.state.question, result, orchestrator.state
                )

                ctx.state.answers.append(final_answer)
                ctx.state.notes.append(
                    "Primary REACT workflow orchestration completed successfully"
                )

                return End(final_answer)
            error_msg = (
                f"Primary REACT workflow failed: {result.get('error', 'Unknown error')}"
            )
            ctx.state.notes.append(error_msg)
            return End(f"Error: {error_msg}")

        except Exception as e:
            error_msg = f"Primary REACT workflow orchestration failed: {e!s}"
            ctx.state.notes.append(error_msg)
            return End(f"Error: {error_msg}")

    def _create_orchestration_config(
        self, orchestration_cfg: dict[str, Any]
    ) -> WorkflowOrchestrationConfig:
        """Create orchestration configuration from Hydra config."""
        from .src.datatypes.workflow_orchestration import (
            DataLoaderConfig,
            JudgeConfig,
            MultiAgentSystemConfig,
            WorkflowConfig,
        )

        # Create primary workflow config
        primary_workflow = WorkflowConfig(
            workflow_type=WorkflowType.PRIMARY_REACT,
            name="main_research_workflow",
            enabled=True,
            priority=10,
            max_retries=3,
            timeout=300.0,
            parameters=orchestration_cfg.get("primary_workflow", {}).get(
                "parameters", {}
            ),
        )

        # Create sub-workflow configs
        sub_workflows = []
        for workflow_data in orchestration_cfg.get("sub_workflows", []):
            workflow_config = WorkflowConfig(
                workflow_type=WorkflowType(
                    workflow_data.get("workflow_type", "rag_workflow")
                ),
                name=workflow_data.get("name", "unnamed_workflow"),
                enabled=workflow_data.get("enabled", True),
                priority=workflow_data.get("priority", 0),
                max_retries=workflow_data.get("max_retries", 3),
                timeout=workflow_data.get("timeout", 120.0),
                parameters=workflow_data.get("parameters", {}),
            )
            sub_workflows.append(workflow_config)

        # Create data loader configs
        data_loaders = []
        for loader_data in orchestration_cfg.get("data_loaders", []):
            loader_config = DataLoaderConfig(
                loader_type=DataLoaderType(
                    loader_data.get("loader_type", "document_loader")
                ),
                name=loader_data.get("name", "unnamed_loader"),
                enabled=loader_data.get("enabled", True),
                parameters=loader_data.get("parameters", {}),
                output_collection=loader_data.get(
                    "output_collection", "default_collection"
                ),
                chunk_size=loader_data.get("chunk_size", 1000),
                chunk_overlap=loader_data.get("chunk_overlap", 200),
            )
            data_loaders.append(loader_config)

        # Create multi-agent system configs
        multi_agent_systems = []
        for system_data in orchestration_cfg.get("multi_agent_systems", []):
            agents = []
            for agent_data in system_data.get("agents", []):
                from .src.datatypes.workflow_orchestration import AgentConfig

                agent_config = AgentConfig(
                    agent_id=agent_data.get("agent_id", "unnamed_agent"),
                    role=AgentRole(agent_data.get("role", "executor")),
                    model_name=agent_data.get(
                        "model_name", "anthropic:claude-sonnet-4-0"
                    ),
                    system_prompt=agent_data.get("system_prompt"),
                    tools=agent_data.get("tools", []),
                    max_iterations=agent_data.get("max_iterations", 10),
                    temperature=agent_data.get("temperature", 0.7),
                    enabled=agent_data.get("enabled", True),
                )
                agents.append(agent_config)

            system_config = MultiAgentSystemConfig(
                system_id=system_data.get("system_id", "unnamed_system"),
                name=system_data.get("name", "Unnamed System"),
                agents=agents,
                coordination_strategy=system_data.get(
                    "coordination_strategy", "collaborative"
                ),
                communication_protocol=system_data.get(
                    "communication_protocol", "direct"
                ),
                max_rounds=system_data.get("max_rounds", 10),
                consensus_threshold=system_data.get("consensus_threshold", 0.8),
                enabled=system_data.get("enabled", True),
            )
            multi_agent_systems.append(system_config)

        # Create judge configs
        judges = []
        for judge_data in orchestration_cfg.get("judges", []):
            judge_config = JudgeConfig(
                judge_id=judge_data.get("judge_id", "unnamed_judge"),
                name=judge_data.get("name", "Unnamed Judge"),
                model_name=judge_data.get("model_name", "anthropic:claude-sonnet-4-0"),
                evaluation_criteria=judge_data.get(
                    "evaluation_criteria", ["quality", "accuracy"]
                ),
                scoring_scale=judge_data.get("scoring_scale", "1-10"),
                enabled=judge_data.get("enabled", True),
            )
            judges.append(judge_config)

        return WorkflowOrchestrationConfig(
            primary_workflow=primary_workflow,
            sub_workflows=sub_workflows,
            data_loaders=data_loaders,
            multi_agent_systems=multi_agent_systems,
            judges=judges,
            execution_strategy=orchestration_cfg.get("execution_strategy", "parallel"),
            max_concurrent_workflows=orchestration_cfg.get(
                "max_concurrent_workflows", 5
            ),
            global_timeout=orchestration_cfg.get("global_timeout"),
            enable_monitoring=orchestration_cfg.get("enable_monitoring", True),
            enable_caching=orchestration_cfg.get("enable_caching", True),
        )

    def _generate_comprehensive_output(
        self,
        question: str,
        result: dict[str, Any],
        orchestration_state: OrchestrationState,
    ) -> str:
        """Generate comprehensive output from orchestration results."""
        output_parts = [
            "# Primary REACT Workflow Orchestration Results",
            "",
            f"**Question:** {question}",
            "",
            "## Execution Summary",
            f"- **Status:** {'Success' if result['success'] else 'Failed'}",
            f"- **Workflows Spawned:** {len(orchestration_state.active_executions) + len(orchestration_state.completed_executions)}",
            f"- **Active Executions:** {len(orchestration_state.active_executions)}",
            f"- **Completed Executions:** {len(orchestration_state.completed_executions)}",
            "",
        ]

        # Add workflow results
        if orchestration_state.completed_executions:
            output_parts.extend(["## Workflow Results", ""])

            for execution in orchestration_state.completed_executions:
                output_parts.extend(
                    [
                        f"### {execution.workflow_name}",
                        f"- **Status:** {execution.status.value}",
                        f"- **Execution Time:** {execution.execution_time:.2f}s",
                        f"- **Quality Score:** {execution.quality_score or 'N/A'}",
                        "",
                    ]
                )

                if execution.output_data:
                    output_parts.extend(
                        [
                            "**Output:**",
                            "```json",
                            f"{execution.output_data}",
                            "```",
                            "",
                        ]
                    )

        # Add multi-agent results
        if result.get("result"):
            output_parts.extend(
                [
                    "## Multi-Agent Coordination Results",
                    "",
                    "**Primary Agent Result:**",
                    "```json",
                    f"{result['result']}",
                    "```",
                    "",
                ]
            )

        # Add system metrics
        if orchestration_state.system_metrics:
            output_parts.extend(["## System Metrics", ""])

            for metric, value in orchestration_state.system_metrics.items():
                output_parts.append(f"- **{metric}:** {value}")

            output_parts.append("")

        # Add execution metadata
        if result.get("execution_metadata"):
            output_parts.extend(["## Execution Metadata", ""])

            for key, value in result["execution_metadata"].items():
                output_parts.append(f"- **{key}:** {value}")

            output_parts.append("")

        return "\n".join(output_parts)


# --- Enhanced REACT Workflow Node ---
@dataclass
class EnhancedREACTWorkflow(BaseNode[ResearchState]):
    async def run(
        self, ctx: GraphRunContext[ResearchState]
    ) -> Annotated[End[str], Edge(label="done")]:
        """Execute the enhanced REACT workflow with nested loops and subgraphs."""
        cfg = ctx.state.config
        app_mode = ctx.state.current_mode

        try:
            # Create app configuration from Hydra config
            app_config = self._create_app_configuration(cfg, app_mode)
            ctx.state.app_configuration = app_config

            # Create agent orchestrator
            agent_orchestrator = AgentOrchestrator(app_config.primary_orchestrator)
            ctx.state.agent_orchestrator = agent_orchestrator

            # Execute orchestration based on mode
            if app_mode == AppMode.SINGLE_REACT:
                result = await self._execute_single_react(ctx, agent_orchestrator)
            elif app_mode == AppMode.MULTI_LEVEL_REACT:
                result = await self._execute_multi_level_react(ctx, agent_orchestrator)
            elif app_mode == AppMode.NESTED_ORCHESTRATION:
                result = await self._execute_nested_orchestration(
                    ctx, agent_orchestrator
                )
            elif app_mode == AppMode.LOSS_DRIVEN:
                result = await self._execute_loss_driven(ctx, agent_orchestrator)
            else:
                result = await self._execute_custom_mode(ctx, agent_orchestrator)

            # Process results
            if result.success:
                final_answer = self._generate_enhanced_output(
                    ctx.state.question, result, app_config, agent_orchestrator
                )

                ctx.state.answers.append(final_answer)
                ctx.state.notes.append(
                    f"Enhanced REACT workflow ({app_mode.value if app_mode else 'unknown'}) completed successfully"
                )

                return End(final_answer)
            error_msg = f"Enhanced REACT workflow failed: {result.break_reason or 'Unknown error'}"
            ctx.state.notes.append(error_msg)
            return End(f"Error: {error_msg}")

        except Exception as e:
            error_msg = f"Enhanced REACT workflow orchestration failed: {e!s}"
            ctx.state.notes.append(error_msg)
            return End(f"Error: {error_msg}")

    def _create_app_configuration(
        self, cfg: DictConfig, app_mode: AppMode
    ) -> AppConfiguration:
        """Create app configuration from Hydra config."""
        # Create primary orchestrator config
        primary_orchestrator = AgentOrchestratorConfig(
            orchestrator_id="primary_orchestrator",
            agent_role=AgentRole.ORCHESTRATOR_AGENT,
            model_name=cfg.get("model_name", "anthropic:claude-sonnet-4-0"),
            max_nested_loops=cfg.get("max_nested_loops", 5),
            coordination_strategy=cfg.get("coordination_strategy", "collaborative"),
            can_spawn_subgraphs=cfg.get("can_spawn_subgraphs", True),
            can_spawn_agents=cfg.get("can_spawn_agents", True),
            break_conditions=self._create_break_conditions(
                cfg.get("break_conditions", [])
            ),
        )

        # Create nested REACT configs
        nested_react_configs = []
        for nested_cfg in cfg.get("nested_react_configs", []):
            nested_config = NestedReactConfig(
                loop_id=nested_cfg.get("loop_id", "unnamed_loop"),
                parent_loop_id=nested_cfg.get("parent_loop_id"),
                max_iterations=nested_cfg.get("max_iterations", 10),
                state_machine_mode=MultiStateMachineMode(
                    nested_cfg.get("state_machine_mode", "group_chat")
                ),
                subgraphs=[SubgraphType(sg) for sg in nested_cfg.get("subgraphs", [])],
                agent_roles=[
                    AgentRole(role) for role in nested_cfg.get("agent_roles", [])
                ],
                tools=nested_cfg.get("tools", []),
                priority=nested_cfg.get("priority", 0),
                break_conditions=self._create_break_conditions(
                    nested_cfg.get("break_conditions", [])
                ),
            )
            nested_react_configs.append(nested_config)

        # Create subgraph configs
        subgraph_configs = []
        for subgraph_cfg in cfg.get("subgraph_configs", []):
            subgraph_config = SubgraphConfig(
                subgraph_id=subgraph_cfg.get("subgraph_id", "unnamed_subgraph"),
                subgraph_type=SubgraphType(
                    subgraph_cfg.get("subgraph_type", "custom_subgraph")
                ),
                state_machine_path=subgraph_cfg.get("state_machine_path", ""),
                entry_node=subgraph_cfg.get("entry_node", "start"),
                exit_node=subgraph_cfg.get("exit_node", "end"),
                parameters=subgraph_cfg.get("parameters", {}),
                tools=subgraph_cfg.get("tools", []),
                max_execution_time=subgraph_cfg.get("max_execution_time", 300.0),
                enabled=subgraph_cfg.get("enabled", True),
            )
            subgraph_configs.append(subgraph_config)

        # Create loss functions and break conditions
        loss_functions = self._create_break_conditions(cfg.get("loss_functions", []))
        global_break_conditions = self._create_break_conditions(
            cfg.get("global_break_conditions", [])
        )

        return AppConfiguration(
            mode=app_mode,
            primary_orchestrator=primary_orchestrator,
            nested_react_configs=nested_react_configs,
            subgraph_configs=subgraph_configs,
            loss_functions=loss_functions,
            global_break_conditions=global_break_conditions,
            execution_strategy=cfg.get("execution_strategy", "adaptive"),
            max_total_iterations=cfg.get("max_total_iterations", 100),
            max_total_time=cfg.get("max_total_time", 3600.0),
        )

    def _create_break_conditions(
        self, break_conditions_cfg: list[dict[str, Any]]
    ) -> list[BreakCondition]:
        """Create break conditions from config."""
        break_conditions = []
        for bc_cfg in break_conditions_cfg:
            break_condition = BreakCondition(
                condition_type=LossFunctionType(
                    bc_cfg.get("condition_type", "iteration_limit")
                ),
                threshold=bc_cfg.get("threshold", 10.0),
                operator=bc_cfg.get("operator", ">="),
                enabled=bc_cfg.get("enabled", True),
                custom_function=bc_cfg.get("custom_function"),
            )
            break_conditions.append(break_condition)
        return break_conditions

    async def _execute_single_react(
        self, ctx: GraphRunContext[ResearchState], orchestrator: AgentOrchestrator
    ):
        """Execute single REACT mode."""
        cfg = ctx.state.config or DictConfig({})
        return await orchestrator.execute_orchestration(ctx.state.question, cfg)

    async def _execute_multi_level_react(
        self, ctx: GraphRunContext[ResearchState], orchestrator: AgentOrchestrator
    ):
        """Execute multi-level REACT mode."""
        # This would implement multi-level REACT with nested loops
        cfg = ctx.state.config or DictConfig({})
        return await orchestrator.execute_orchestration(ctx.state.question, cfg)

    async def _execute_nested_orchestration(
        self, ctx: GraphRunContext[ResearchState], orchestrator: AgentOrchestrator
    ):
        """Execute nested orchestration mode."""
        # This would implement nested orchestration with subgraphs
        cfg = ctx.state.config or DictConfig({})
        return await orchestrator.execute_orchestration(ctx.state.question, cfg)

    async def _execute_loss_driven(
        self, ctx: GraphRunContext[ResearchState], orchestrator: AgentOrchestrator
    ):
        """Execute loss-driven mode."""
        # This would implement loss-driven execution with quality metrics
        cfg = ctx.state.config or DictConfig({})
        return await orchestrator.execute_orchestration(ctx.state.question, cfg)

    async def _execute_custom_mode(
        self, ctx: GraphRunContext[ResearchState], orchestrator: AgentOrchestrator
    ):
        """Execute custom mode."""
        # This would implement custom execution logic
        cfg = ctx.state.config or DictConfig({})
        return await orchestrator.execute_orchestration(ctx.state.question, cfg)

    def _generate_enhanced_output(
        self,
        question: str,
        result: Any,
        app_config: AppConfiguration,
        orchestrator: AgentOrchestrator,
    ) -> str:
        """Generate enhanced output from orchestration results."""
        output_parts = [
            "# Enhanced REACT Workflow Results",
            "",
            f"**Question:** {question}",
            f"**Mode:** {app_config.mode.value}",
            "",
            "## Execution Summary",
            f"- **Status:** {'Success' if result.success else 'Failed'}",
            f"- **Nested Loops Spawned:** {len(result.nested_loops_spawned)}",
            f"- **Subgraphs Executed:** {len(result.subgraphs_executed)}",
            f"- **Total Iterations:** {result.total_iterations}",
            "",
        ]

        # Add nested loops results
        if result.nested_loops_spawned:
            output_parts.extend(["## Nested Loops", ""])

            for loop_id in result.nested_loops_spawned:
                output_parts.extend(
                    [
                        f"### {loop_id}",
                        "- **Status:** Completed",
                        "- **Type:** Nested REACT Loop",
                        "",
                    ]
                )

        # Add subgraph results
        if result.subgraphs_executed:
            output_parts.extend(["## Subgraphs", ""])

            for subgraph_id in result.subgraphs_executed:
                output_parts.extend(
                    [
                        f"### {subgraph_id}",
                        "- **Status:** Executed",
                        "- **Type:** Subgraph",
                        "",
                    ]
                )

        # Add final answer
        output_parts.extend(["## Final Answer", "", f"{result.final_answer}", ""])

        # Add execution metadata
        if result.execution_metadata:
            output_parts.extend(["## Execution Metadata", ""])

            for key, value in result.execution_metadata.items():
                output_parts.append(f"- **{key}:** {value}")

            output_parts.append("")

        return "\n".join(output_parts)


@dataclass
class Search(BaseNode[ResearchState]):
    async def run(self, ctx: GraphRunContext[ResearchState]) -> Analyze:
        history = ExecutionHistory()
        plan = getattr(ctx.state, "full_plan", []) or []
        retries = int(getattr(ctx.state.config, "retries", 2))
        exec_agent = ExecutorAgent(retries=retries)
        bag = exec_agent.run_plan(plan, history)
        ctx.state.execution_results["history"] = history
        ctx.state.execution_results["bag"] = bag
        ctx.state.notes.append("Executed plan with tool runners")
        return Analyze()


@dataclass
class Analyze(BaseNode[ResearchState]):
    async def run(self, ctx: GraphRunContext[ResearchState]) -> Synthesize:
        history = ctx.state.execution_results.get("history")
        n = len(history.items) if history else 0
        ctx.state.notes.append(f"Analysis: executed {n} steps")
        return Synthesize()


@dataclass
class Synthesize(BaseNode[ResearchState]):
    async def run(
        self, ctx: GraphRunContext[ResearchState]
    ) -> Annotated[End[str], Edge(label="done")]:
        bag = ctx.state.execution_results.get("bag") or {}
        final = (
            bag.get("final")
            or bag.get("finalize.final")
            or bag.get("references.answer_with_refs")
            or bag.get("summarize.summary")
        )
        if not final:
            final = "No summary available."
        answer = f"Q: {ctx.state.question}\n{final}"
        ctx.state.answers.append(answer)
        return End(answer)


# --- Graph ---
# Note: The actual graph is created in run_graph() with all nodes instantiated
# This creates a minimal graph for reference, but the full graph with all nodes is in run_graph()
research_graph = Graph(
    nodes=(
        Plan,
        Search,
        Analyze,
        Synthesize,
        PrimaryREACTWorkflow,
        EnhancedREACTWorkflow,
    ),
    state_type=ResearchState,
)


# --- Challenge-specific nodes ---
@dataclass
class PrepareChallenge(BaseNode[ResearchState]):
    async def run(self, ctx: GraphRunContext[ResearchState]) -> RunChallenge:
        ch = getattr(ctx.state.config, "challenge", None) if ctx.state.config else None
        if ch:
            ctx.state.notes.append(f"Prepare: {ch.name} in {ch.domain}")
        else:
            ctx.state.notes.append("Prepare: Challenge configuration not found")
        return RunChallenge()


@dataclass
class RunChallenge(BaseNode[ResearchState]):
    async def run(self, ctx: GraphRunContext[ResearchState]) -> EvaluateChallenge:
        ctx.state.notes.append(
            "Run: release material, collect methods/answers (placeholder)"
        )
        return EvaluateChallenge()


@dataclass
class EvaluateChallenge(BaseNode[ResearchState]):
    async def run(self, ctx: GraphRunContext[ResearchState]) -> Synthesize:
        ctx.state.notes.append(
            "Evaluate: participant cross-assessment, expert review, pilot AI (placeholder)"
        )
        return Synthesize()


# --- DeepSearch flow nodes (replicate example/jina-ai/src agent prompts and flow structure at high level) ---
@dataclass
class DSPlan(BaseNode[ResearchState]):
    async def run(self, ctx: GraphRunContext[ResearchState]) -> DSExecute:
        # Orchestrate plan selection based on enabled subflows
        flows_cfg = getattr(ctx.state.config, "flows", {})
        orchestrator = Orchestrator()
        active = orchestrator.build_plan(ctx.state.question, flows_cfg)
        ctx.state.active_subgraphs["deepsearch"] = active
        # Default deepsearch-style plan
        parser = ParserAgent()
        parsed = parser.parse(ctx.state.question)
        planner = PlannerAgent()
        plan = planner.plan(parsed)
        # Prefer Pydantic web_search + summarize + finalize
        ctx.state.full_plan = plan
        ctx.state.plan = [f"{s['tool']}" for s in plan]
        ctx.state.notes.append(f"DeepSearch planned: {ctx.state.plan}")
        return DSExecute()


@dataclass
class DSExecute(BaseNode[ResearchState]):
    async def run(self, ctx: GraphRunContext[ResearchState]) -> DSAnalyze:
        history = ExecutionHistory()
        plan = getattr(ctx.state, "full_plan", []) or []
        retries = int(getattr(ctx.state.config, "retries", 2))
        exec_agent = ExecutorAgent(retries=retries)
        bag = exec_agent.run_plan(plan, history)
        ctx.state.execution_results["history"] = history
        ctx.state.execution_results["bag"] = bag
        ctx.state.notes.append("DeepSearch executed plan")
        return DSAnalyze()


@dataclass
class DSAnalyze(BaseNode[ResearchState]):
    async def run(self, ctx: GraphRunContext[ResearchState]) -> DSSynthesize:
        history = ctx.state.execution_results.get("history")
        n = len(history.items) if history else 0
        ctx.state.notes.append(f"DeepSearch analysis: {n} steps")
        return DSSynthesize()


@dataclass
class DSSynthesize(BaseNode[ResearchState]):
    async def run(
        self, ctx: GraphRunContext[ResearchState]
    ) -> Annotated[End[str], Edge(label="done")]:
        bag = ctx.state.execution_results.get("bag") or {}
        final = (
            bag.get("final")
            or bag.get("finalize.final")
            or bag.get("summarize.summary")
        )
        if not final:
            final = "No result."
        answer = f"Q: {ctx.state.question}\n{final}"
        ctx.state.answers.append(answer)
        return End(answer)


# --- PRIME flow nodes ---
@dataclass
class PrimeParse(BaseNode[ResearchState]):
    async def run(self, ctx: GraphRunContext[ResearchState]) -> PrimePlan:
        # Parse the query using PRIME Query Parser
        parser = QueryParser()
        structured_problem = parser.parse(ctx.state.question)
        ctx.state.structured_problem = structured_problem
        ctx.state.notes.append(
            f"PRIME parsed: {structured_problem.intent.value} in {structured_problem.domain}"
        )
        return PrimePlan()


@dataclass
class PrimePlan(BaseNode[ResearchState]):
    async def run(self, ctx: GraphRunContext[ResearchState]) -> PrimeExecute:
        # Generate workflow using PRIME Plan Generator
        planner = PlanGenerator()
        if ctx.state.structured_problem is None:
            # Create a simple structured problem from the question
            from .src.agents.prime_parser import ScientificIntent, StructuredProblem

            ctx.state.structured_problem = StructuredProblem(
                intent=ScientificIntent.CLASSIFICATION,
                input_data={"description": ctx.state.question},
                output_requirements={"answer": "comprehensive_response"},
                constraints=[],
                success_criteria=["complete_answer"],
                domain="general",
                complexity="simple",
            )
        workflow_dag = planner.plan(ctx.state.structured_problem)
        ctx.state.workflow_dag = workflow_dag
        ctx.state.notes.append(f"PRIME planned: {len(workflow_dag.steps)} steps")
        return PrimeExecute()


@dataclass
class PrimeExecute(BaseNode[ResearchState]):
    async def run(self, ctx: GraphRunContext[ResearchState]) -> PrimeEvaluate:
        # Execute workflow using PRIME Tool Executor
        cfg = ctx.state.config
        prime_cfg = getattr(getattr(cfg, "flows", {}), "prime", {})

        # Initialize tool registry with PRIME tools
        registry = ToolRegistry()
        registry.enable_mock_mode()  # Use mock tools for development

        # Create execution context
        history = PrimeExecutionHistory()
        if ctx.state.workflow_dag is None:
            from .src.datatypes.execution import WorkflowDAG

            ctx.state.workflow_dag = WorkflowDAG(
                steps=[], dependencies={}, execution_order=[]
            )
        context = ExecutionContext(
            workflow=ctx.state.workflow_dag,
            history=history,
            manual_confirmation=getattr(prime_cfg, "manual_confirmation", False),
            adaptive_replanning=getattr(prime_cfg, "adaptive_replanning", True),
        )

        # Execute workflow
        executor = ToolExecutor(registry)
        results = executor.execute_workflow(context)

        ctx.state.execution_results = results
        ctx.state.notes.append(f"PRIME executed: {results['success']} success")
        return PrimeEvaluate()


@dataclass
class PrimeEvaluate(BaseNode[ResearchState]):
    async def run(
        self, ctx: GraphRunContext[ResearchState]
    ) -> Annotated[End[str], Edge(label="done")]:
        # Evaluate results and generate final answer
        results = ctx.state.execution_results
        problem = ctx.state.structured_problem

        if results["success"]:
            # Extract key results from data bag
            data_bag = results.get("data_bag", {})
            summary = self._extract_summary(data_bag, problem)
            answer = f"PRIME Analysis Complete\n\nQ: {ctx.state.question}\n\n{summary}"
        else:
            # Handle failure case
            history = results.get("history", PrimeExecutionHistory())
            failed_steps = [item.step_name for item in history.get_failed_steps()]
            answer = f"PRIME Analysis Incomplete\n\nQ: {ctx.state.question}\n\nFailed steps: {failed_steps}\n\nPlease review the execution history for details."

        ctx.state.answers.append(answer)
        return End(answer)

    def _extract_summary(
        self, data_bag: dict[str, Any], problem: StructuredProblem
    ) -> str:
        """Extract a summary from the execution results."""
        summary_parts = []

        # Add problem context
        summary_parts.append(f"Scientific Intent: {problem.intent.value}")
        summary_parts.append(f"Domain: {problem.domain}")
        summary_parts.append(f"Complexity: {problem.complexity}")

        # Extract key results based on intent
        if problem.intent.value == "structure_prediction":
            if "structure" in data_bag:
                summary_parts.append("Structure predicted successfully")
            if "confidence" in data_bag:
                conf = data_bag["confidence"]
                if isinstance(conf, dict) and "plddt" in conf:
                    summary_parts.append(f"Confidence (pLDDT): {conf['plddt']}")

        elif problem.intent.value == "binding_analysis":
            if "binding_affinity" in data_bag:
                summary_parts.append(
                    f"Binding Affinity: {data_bag['binding_affinity']}"
                )
            if "poses" in data_bag:
                summary_parts.append(
                    f"Generated {len(data_bag['poses'])} binding poses"
                )

        elif problem.intent.value == "sequence_analysis":
            if "hits" in data_bag:
                summary_parts.append(f"Found {len(data_bag['hits'])} sequence hits")
            if "domains" in data_bag:
                summary_parts.append(
                    f"Identified {len(data_bag['domains'])} protein domains"
                )

        elif problem.intent.value == "de_novo_design":
            if "sequences" in data_bag:
                summary_parts.append(
                    f"Designed {len(data_bag['sequences'])} novel sequences"
                )
            if "structures" in data_bag:
                summary_parts.append(
                    f"Generated {len(data_bag['structures'])} structures"
                )

        # Add any general results
        if "result" in data_bag:
            summary_parts.append(f"Result: {data_bag['result']}")

        return (
            "\n".join(summary_parts)
            if summary_parts
            else "Analysis completed with available results."
        )


# --- Bioinformatics flow nodes ---
@dataclass
class BioinformaticsParse(BaseNode[ResearchState]):
    async def run(self, ctx: GraphRunContext[ResearchState]) -> BioinformaticsFuse:
        # Import here to avoid circular imports
        from .src.statemachines.bioinformatics_workflow import (
            run_bioinformatics_workflow,
        )

        question = ctx.state.question
        cfg = ctx.state.config

        ctx.state.notes.append("Starting bioinformatics workflow")

        # Run the complete bioinformatics workflow
        try:
            cfg_dict = cfg.to_container() if hasattr(cfg, "to_container") else {}
            final_answer = run_bioinformatics_workflow(question, cfg_dict)
            ctx.state.answers.append(final_answer)
            ctx.state.notes.append("Bioinformatics workflow completed successfully")
        except Exception as e:
            error_msg = f"Bioinformatics workflow failed: {e!s}"
            ctx.state.notes.append(error_msg)
            ctx.state.answers.append(f"Error: {error_msg}")

        return BioinformaticsFuse()


@dataclass
class BioinformaticsFuse(BaseNode[ResearchState]):
    async def run(
        self, ctx: GraphRunContext[ResearchState]
    ) -> Annotated[End[str], Edge(label="done")]:
        # The bioinformatics workflow is already complete, just return the result
        if ctx.state.answers:
            return End(ctx.state.answers[-1])
        return End("Bioinformatics analysis completed.")


# --- RAG flow nodes ---
@dataclass
class RAGParse(BaseNode[ResearchState]):
    async def run(self, ctx: GraphRunContext[ResearchState]) -> RAGExecute:
        # Import here to avoid circular imports
        from .src.statemachines.rag_workflow import run_rag_workflow

        question = ctx.state.question
        cfg = ctx.state.config

        ctx.state.notes.append("Starting RAG workflow")

        # Run the complete RAG workflow
        try:
            cfg_non_null = cfg or DictConfig({})
            final_answer = run_rag_workflow(question, cfg_non_null)
            ctx.state.answers.append(final_answer)
            ctx.state.notes.append("RAG workflow completed successfully")
        except Exception as e:
            error_msg = f"RAG workflow failed: {e!s}"
            ctx.state.notes.append(error_msg)
            ctx.state.answers.append(f"Error: {error_msg}")

        return RAGExecute()


@dataclass
class RAGExecute(BaseNode[ResearchState]):
    async def run(
        self, ctx: GraphRunContext[ResearchState]
    ) -> Annotated[End[str], Edge(label="done")]:
        # The RAG workflow is already complete, just return the result
        if ctx.state.answers:
            return End(ctx.state.answers[-1])
        return End("RAG analysis completed.")


def run_graph(question: str, cfg: DictConfig) -> str:
    state = ResearchState(question=question, config=cfg)
    # Include all nodes in runtime graph - instantiate them
    nodes = (
        Plan(),
        Search(),
        Analyze(),
        Synthesize(),
        PrepareChallenge(),
        RunChallenge(),
        EvaluateChallenge(),
        DSPlan(),
        DSExecute(),
        DSAnalyze(),
        DSSynthesize(),
        PrimeParse(),
        PrimePlan(),
        PrimeExecute(),
        PrimeEvaluate(),
        BioinformaticsParse(),
        BioinformaticsFuse(),
        RAGParse(),
        RAGExecute(),
        PrimaryREACTWorkflow(),
        EnhancedREACTWorkflow(),
    )
    g = Graph(nodes=nodes)
    # Run the graph starting from Plan node
    loop = asyncio.new_event_loop()
    try:
        asyncio.set_event_loop(loop)
        result = loop.run_until_complete(g.run(Plan(), state=state, deps=None))  # type: ignore
    finally:
        loop.close()
        asyncio.set_event_loop(None)
    return (result.output or "") if hasattr(result, "output") else ""


@hydra.main(version_base=None, config_path="../configs", config_name="config")
def main(cfg: DictConfig) -> None:
    question = cfg.get("question", "What is deep research?")
    run_graph(question, cfg)


if __name__ == "__main__":
    main()
