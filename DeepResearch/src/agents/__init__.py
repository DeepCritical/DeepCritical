from __future__ import annotations

from importlib import import_module
from typing import Any

_SUBMODULE_EXPORTS = {
    "agent_orchestrator",
    "code_execution_orchestrator",
    "code_generation_agent",
    "code_improvement_agent",
    "hypothesis_agents",
    "prime_executor",
    "prime_parser",
    "prime_planner",
    "pyd_ai_toolsets",
    "rag_agent",
    "research_agent",
    "search_agent",
    "tool_caller",
    "workflow_orchestrator",
}

_ATTR_EXPORTS = {
    "AgentOrchestrator": ("agent_orchestrator", "AgentOrchestrator"),
    "CodeExecutionAgent": ("code_generation_agent", "CodeExecutionAgent"),
    "CodeExecutionAgentSystem": (
        "code_generation_agent",
        "CodeExecutionAgentSystem",
    ),
    "CodeExecutionConfig": (
        "code_execution_orchestrator",
        "CodeExecutionConfig",
    ),
    "CodeExecutionOrchestrator": (
        "code_execution_orchestrator",
        "CodeExecutionOrchestrator",
    ),
    "CodeGenerationAgent": ("code_generation_agent", "CodeGenerationAgent"),
    "CodeImprovementAgent": ("code_improvement_agent", "CodeImprovementAgent"),
    "DataType": ("prime_parser", "DataType"),
    "ExecutionContext": (
        "DeepResearch.src.datatypes.execution",
        "ExecutionContext",
    ),
    "HypothesisEvaluatorAgent": (
        "hypothesis_agents",
        "HypothesisEvaluatorAgent",
    ),
    "HypothesisGeneratorAgent": (
        "hypothesis_agents",
        "HypothesisGeneratorAgent",
    ),
    "HypothesisPlannerAgent": ("hypothesis_agents", "HypothesisPlannerAgent"),
    "Orchestrator": ("agent_orchestrator", "AgentOrchestrator"),
    "PlanGenerator": ("prime_planner", "PlanGenerator"),
    "Planner": ("prime_planner", "PlanGenerator"),
    "PrimaryWorkflowOrchestrator": (
        "workflow_orchestrator",
        "PrimaryWorkflowOrchestrator",
    ),
    "PydAIToolsetBuilder": ("pyd_ai_toolsets", "PydAIToolsetBuilder"),
    "QueryParser": ("prime_parser", "QueryParser"),
    "RAGAgent": ("rag_agent", "RAGAgent"),
    "ResearchAgent": ("research_agent", "ResearchAgent"),
    "ResearchOutcome": (
        "DeepResearch.src.datatypes.research",
        "ResearchOutcome",
    ),
    "ScientificIntent": ("prime_parser", "ScientificIntent"),
    "SearchAgent": ("search_agent", "SearchAgent"),
    "SearchAgentConfig": ("search_agent", "SearchAgentConfig"),
    "SearchQuery": ("search_agent", "SearchQuery"),
    "SearchResult": ("search_agent", "SearchResult"),
    "StepResult": ("DeepResearch.src.datatypes.research", "StepResult"),
    "StructuredProblem": ("prime_parser", "StructuredProblem"),
    "TestcontainersDeployer": (
        "DeepResearch.src.utils.testcontainers_deployer",
        "TestcontainersDeployer",
    ),
    "ToolCaller": ("tool_caller", "ToolCaller"),
    "ToolCategory": ("prime_planner", "ToolCategory"),
    "ToolExecutor": ("prime_executor", "ToolExecutor"),
    "ToolSpec": ("prime_planner", "ToolSpec"),
    "WorkflowDAG": ("prime_planner", "WorkflowDAG"),
    "WorkflowStep": ("prime_planner", "WorkflowStep"),
    "create_code_execution_orchestrator": (
        "code_execution_orchestrator",
        "create_code_execution_orchestrator",
    ),
    "execute_auto_code": (
        "code_execution_orchestrator",
        "execute_auto_code",
    ),
    "execute_bash_command": (
        "code_execution_orchestrator",
        "execute_bash_command",
    ),
    "execute_python_script": (
        "code_execution_orchestrator",
        "execute_python_script",
    ),
    "execute_workflow": ("prime_executor", "execute_workflow"),
    "generate_plan": ("prime_planner", "generate_plan"),
    "parse_query": ("prime_parser", "parse_query"),
    "process_message_to_command_log": (
        "code_execution_orchestrator",
        "process_message_to_command_log",
    ),
    "run": ("research_agent", "run"),
    "run_code_execution_agent": (
        "code_execution_orchestrator",
        "run_code_execution_agent",
    ),
    "testcontainers_deployer": (
        "DeepResearch.src.utils.testcontainers_deployer",
        "testcontainers_deployer",
    ),
}


def _import_target(module_name: str) -> Any:
    if module_name.startswith("DeepResearch."):
        return import_module(module_name)
    return import_module(f"{__name__}.{module_name}")


def __getattr__(name: str) -> Any:
    if name in _SUBMODULE_EXPORTS:
        return _import_target(name)

    if name in _ATTR_EXPORTS:
        module_name, attr_name = _ATTR_EXPORTS[name]
        module = _import_target(module_name)
        return getattr(module, attr_name)

    msg = f"module {__name__!r} has no attribute {name!r}"
    raise AttributeError(msg)


__all__ = [
    "AgentOrchestrator",
    "CodeExecutionAgent",
    "CodeExecutionAgentSystem",
    "CodeExecutionConfig",
    "CodeExecutionOrchestrator",
    "CodeGenerationAgent",
    "CodeImprovementAgent",
    "DataType",
    "ExecutionContext",
    "HypothesisEvaluatorAgent",
    "HypothesisGeneratorAgent",
    "HypothesisPlannerAgent",
    "Orchestrator",
    "PlanGenerator",
    "Planner",
    "PrimaryWorkflowOrchestrator",
    "PydAIToolsetBuilder",
    "QueryParser",
    "RAGAgent",
    "ResearchAgent",
    "ResearchOutcome",
    "ScientificIntent",
    "SearchAgent",
    "SearchAgentConfig",
    "SearchQuery",
    "SearchResult",
    "StepResult",
    "StructuredProblem",
    "TestcontainersDeployer",
    "ToolCaller",
    "ToolCategory",
    "ToolExecutor",
    "ToolSpec",
    "WorkflowDAG",
    "WorkflowStep",
    "agent_orchestrator",
    "code_execution_orchestrator",
    "code_generation_agent",
    "code_improvement_agent",
    "create_code_execution_orchestrator",
    "execute_auto_code",
    "execute_bash_command",
    "execute_python_script",
    "execute_workflow",
    "generate_plan",
    "hypothesis_agents",
    "parse_query",
    "prime_executor",
    "prime_parser",
    "prime_planner",
    "process_message_to_command_log",
    "pyd_ai_toolsets",
    "rag_agent",
    "research_agent",
    "run",
    "run_code_execution_agent",
    "search_agent",
    "testcontainers_deployer",
    "tool_caller",
    "workflow_orchestrator",
]
