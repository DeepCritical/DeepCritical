"""
DeepCritical Agents - Pydantic AI-based agent system for research workflows.

This module provides a comprehensive agent system following Pydantic AI patterns,
integrating with existing tools and state machines for bioinformatics, search,
and RAG workflows.
"""

from __future__ import annotations

import asyncio
import time
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any

from pydantic_ai import Agent

# Import existing tools and schemas
from .src.tools.base import registry, ExecutionResult
from .src.datatypes.rag import RAGQuery, RAGResponse
from .src.datatypes.bioinformatics import FusedDataset, ReasoningTask, DataFusionRequest
from .src.datatypes.agents import (
    AgentType,
    AgentStatus,
    AgentDependencies,
    AgentResult,
    ExecutionHistory,
)
from .src.prompts.agents import AgentPrompts

# Import DeepAgent components
from .src.datatypes.deep_agent_state import DeepAgentState
from .src.datatypes.deep_agent_types import AgentCapability
from .src.agents.deep_agent_implementations import (
    PlanningAgent,
    FilesystemAgent,
    ResearchAgent,
    TaskOrchestrationAgent,
    GeneralPurposeAgent,
    AgentOrchestrator,
    AgentConfig,
    AgentExecutionResult,
)


class BaseAgent(ABC):
    """Base class for all DeepCritical agents following Pydantic AI patterns."""

    def __init__(
        self,
        agent_type: AgentType,
        model_name: str = "anthropic:claude-sonnet-4-0",
        dependencies: Optional[AgentDependencies] = None,
        system_prompt: Optional[str] = None,
        instructions: Optional[str] = None,
    ):
        self.agent_type = agent_type
        self.model_name = model_name
        self.dependencies = dependencies or AgentDependencies()
        self.status = AgentStatus.IDLE
        self.history = ExecutionHistory()
        self._agent: Optional[Agent] = None

        # Initialize Pydantic AI agent
        self._initialize_agent(system_prompt, instructions)

    def _initialize_agent(
        self, system_prompt: Optional[str], instructions: Optional[str]
    ):
        """Initialize the Pydantic AI agent."""
        try:
            self._agent = Agent(
                self.model_name,
                deps_type=AgentDependencies,
                system_prompt=system_prompt or self._get_default_system_prompt(),
                instructions=instructions or self._get_default_instructions(),
            )

            # Register tools
            self._register_tools()

        except Exception as e:
            print(f"Warning: Failed to initialize Pydantic AI agent: {e}")
            self._agent = None

    def _get_default_system_prompt(self) -> str:
        """Get default system prompt for this agent type."""
        return AgentPrompts.get_system_prompt(self.agent_type.value)

    def _get_default_instructions(self) -> str:
        """Get default instructions for this agent type."""
        return AgentPrompts.get_instructions(self.agent_type.value)

    @abstractmethod
    def _register_tools(self):
        """Register tools with the agent."""
        pass

    async def execute(
        self, input_data: Any, deps: Optional[AgentDependencies] = None
    ) -> AgentResult:
        """Execute the agent with input data."""
        start_time = time.time()
        self.status = AgentStatus.RUNNING

        try:
            if not self._agent:
                return AgentResult(
                    success=False,
                    error="Agent not properly initialized",
                    agent_type=self.agent_type,
                )

            # Use provided deps or default
            execution_deps = deps or self.dependencies

            # Execute with Pydantic AI
            result = await self._agent.run(input_data, deps=execution_deps)

            execution_time = time.time() - start_time

            agent_result = AgentResult(
                success=True,
                data=self._process_result(result),
                execution_time=execution_time,
                agent_type=self.agent_type,
            )

            self.status = AgentStatus.COMPLETED
            self.history.record(self.agent_type, agent_result)
            return agent_result

        except Exception as e:
            execution_time = time.time() - start_time
            agent_result = AgentResult(
                success=False,
                error=str(e),
                execution_time=execution_time,
                agent_type=self.agent_type,
            )

            self.status = AgentStatus.FAILED
            self.history.record(self.agent_type, agent_result)
            return agent_result

    def execute_sync(
        self, input_data: Any, deps: Optional[AgentDependencies] = None
    ) -> AgentResult:
        """Synchronous execution wrapper."""
        return asyncio.run(self.execute(input_data, deps))

    def _process_result(self, result: Any) -> Dict[str, Any]:
        """Process the result from Pydantic AI agent."""
        if hasattr(result, "output"):
            return {"output": result.output}
        elif hasattr(result, "data"):
            return result.data
        else:
            return {"result": str(result)}


class ParserAgent(BaseAgent):
    """Agent for parsing and understanding research questions."""

    def __init__(self, model_name: str = "anthropic:claude-sonnet-4-0", **kwargs):
        super().__init__(AgentType.PARSER, model_name, **kwargs)

    def _register_tools(self):
        """Register parsing tools."""
        # Add any specific parsing tools here
        pass

    async def parse_question(self, question: str) -> Dict[str, Any]:
        """Parse a research question."""
        result = await self.execute(question)
        if result.success:
            return result.data
        else:
            return {"intent": "research", "query": question, "error": result.error}

    def parse(self, question: str) -> Dict[str, Any]:
        """Legacy synchronous parse method."""
        result = self.execute_sync(question)
        return (
            result.data if result.success else {"intent": "research", "query": question}
        )


class PlannerAgent(BaseAgent):
    """Agent for planning research workflows."""

    def __init__(self, model_name: str = "anthropic:claude-sonnet-4-0", **kwargs):
        super().__init__(AgentType.PLANNER, model_name, **kwargs)

    def _register_tools(self):
        """Register planning tools."""
        pass

    async def create_plan(
        self, parsed_question: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Create an execution plan from parsed question."""
        result = await self.execute(parsed_question)
        if result.success and "steps" in result.data:
            return result.data["steps"]
        else:
            # Fallback to default plan
            return self._get_default_plan(parsed_question.get("query", ""))

    def _get_default_plan(self, query: str) -> List[Dict[str, Any]]:
        """Get default execution plan."""
        return [
            {"tool": "rewrite", "params": {"query": query}},
            {"tool": "web_search", "params": {"query": "${rewrite.queries}"}},
            {"tool": "summarize", "params": {"snippets": "${web_search.results}"}},
            {
                "tool": "references",
                "params": {
                    "answer": "${summarize.summary}",
                    "web": "${web_search.results}",
                },
            },
            {"tool": "finalize", "params": {"draft": "${references.answer_with_refs}"}},
            {
                "tool": "evaluator",
                "params": {"question": query, "answer": "${finalize.final}"},
            },
        ]

    def plan(self, parsed: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Legacy synchronous plan method."""
        result = self.execute_sync(parsed)
        if result.success and "steps" in result.data:
            return result.data["steps"]
        else:
            return self._get_default_plan(parsed.get("query", ""))


class ExecutorAgent(BaseAgent):
    """Agent for executing research workflows."""

    def __init__(
        self,
        model_name: str = "anthropic:claude-sonnet-4-0",
        retries: int = 2,
        **kwargs,
    ):
        self.retries = retries
        super().__init__(AgentType.EXECUTOR, model_name, **kwargs)

    def _register_tools(self):
        """Register execution tools."""
        # Register all available tools
        for tool_name in registry.list():
            try:
                tool_runner = registry.make(tool_name)
                self._agent.tool(tool_runner.run)
            except Exception as e:
                print(f"Warning: Failed to register tool {tool_name}: {e}")

    async def execute_plan(
        self, plan: List[Dict[str, Any]], history: ExecutionHistory
    ) -> Dict[str, Any]:
        """Execute a research plan."""
        bag: Dict[str, Any] = {}

        for step in plan:
            tool_name = step["tool"]
            params = self._materialize_params(step.get("params", {}), bag)

            attempt = 0
            result: Optional[ExecutionResult] = None

            while attempt <= self.retries:
                try:
                    runner = registry.make(tool_name)
                    result = runner.run(params)
                    history.record(
                        agent_type=AgentType.EXECUTOR,
                        result=AgentResult(
                            success=result.success,
                            data=result.data,
                            error=result.error,
                            agent_type=AgentType.EXECUTOR,
                        ),
                        tool=tool_name,
                        params=params,
                    )

                    if result.success:
                        for k, v in result.data.items():
                            bag[f"{tool_name}.{k}"] = v
                            bag[k] = v  # convenience aliasing
                        break

                except Exception as e:
                    result = ExecutionResult(success=False, error=str(e))

                attempt += 1

                # Adaptive parameter adjustment
                if not result.success and attempt <= self.retries:
                    params = self._adjust_parameters(params, bag)

            if not result or not result.success:
                break

        return bag

    def _materialize_params(
        self, params: Dict[str, Any], bag: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Materialize parameter placeholders with actual values."""
        out: Dict[str, Any] = {}
        for k, v in params.items():
            if isinstance(v, str) and v.startswith("${") and v.endswith("}"):
                key = v[2:-1]
                out[k] = bag.get(key, "")
            else:
                out[k] = v
        return out

    def _adjust_parameters(
        self, params: Dict[str, Any], bag: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Adjust parameters for retry attempts."""
        adjusted = params.copy()

        # Simple adaptive tweaks
        if "query" in adjusted and not adjusted["query"].strip():
            adjusted["query"] = "general information"
        if "snippets" in adjusted and not adjusted["snippets"].strip():
            adjusted["snippets"] = bag.get("search.snippets", "no data")

        return adjusted

    def run_plan(
        self, plan: List[Dict[str, Any]], history: ExecutionHistory
    ) -> Dict[str, Any]:
        """Legacy synchronous run_plan method."""
        return asyncio.run(self.execute_plan(plan, history))


class SearchAgent(BaseAgent):
    """Agent for web search operations."""

    def __init__(self, model_name: str = "anthropic:claude-sonnet-4-0", **kwargs):
        super().__init__(AgentType.SEARCH, model_name, **kwargs)

    def _register_tools(self):
        """Register search tools."""
        try:
            from .src.tools.websearch_tools import WebSearchTool, ChunkedSearchTool

            # Register web search tools
            web_search_tool = WebSearchTool()
            self._agent.tool(web_search_tool.run)

            chunked_search_tool = ChunkedSearchTool()
            self._agent.tool(chunked_search_tool.run)

        except Exception as e:
            print(f"Warning: Failed to register search tools: {e}")

    async def search(
        self, query: str, search_type: str = "search", num_results: int = 10
    ) -> Dict[str, Any]:
        """Perform web search."""
        search_params = {
            "query": query,
            "search_type": search_type,
            "num_results": num_results,
        }

        result = await self.execute(search_params)
        return result.data if result.success else {"error": result.error}


class RAGAgent(BaseAgent):
    """Agent for RAG (Retrieval-Augmented Generation) operations."""

    def __init__(self, model_name: str = "anthropic:claude-sonnet-4-0", **kwargs):
        super().__init__(AgentType.RAG, model_name, **kwargs)

    def _register_tools(self):
        """Register RAG tools."""
        try:
            from .src.tools.integrated_search_tools import (
                IntegratedSearchTool,
                RAGSearchTool,
            )

            # Register RAG tools
            integrated_search_tool = IntegratedSearchTool()
            self._agent.tool(integrated_search_tool.run)

            rag_search_tool = RAGSearchTool()
            self._agent.tool(rag_search_tool.run)

        except Exception as e:
            print(f"Warning: Failed to register RAG tools: {e}")

    async def query(self, rag_query: RAGQuery) -> RAGResponse:
        """Perform RAG query."""
        result = await self.execute(rag_query.model_dump())

        if result.success:
            return RAGResponse(**result.data)
        else:
            return RAGResponse(
                query=rag_query.text,
                retrieved_documents=[],
                generated_answer="",
                context="",
                processing_time=0.0,
                metadata={"error": result.error},
            )


class BioinformaticsAgent(BaseAgent):
    """Agent for bioinformatics data fusion and reasoning."""

    def __init__(self, model_name: str = "anthropic:claude-sonnet-4-0", **kwargs):
        super().__init__(AgentType.BIOINFORMATICS, model_name, **kwargs)

    def _register_tools(self):
        """Register bioinformatics tools."""
        try:
            from .src.tools.bioinformatics_tools import (
                BioinformaticsFusionTool,
                BioinformaticsReasoningTool,
                BioinformaticsWorkflowTool,
                GOAnnotationTool,
                PubMedRetrievalTool,
            )

            # Register bioinformatics tools
            fusion_tool = BioinformaticsFusionTool()
            self._agent.tool(fusion_tool.run)

            reasoning_tool = BioinformaticsReasoningTool()
            self._agent.tool(reasoning_tool.run)

            workflow_tool = BioinformaticsWorkflowTool()
            self._agent.tool(workflow_tool.run)

            go_tool = GOAnnotationTool()
            self._agent.tool(go_tool.run)

            pubmed_tool = PubMedRetrievalTool()
            self._agent.tool(pubmed_tool.run)

        except Exception as e:
            print(f"Warning: Failed to register bioinformatics tools: {e}")

    async def fuse_data(self, fusion_request: DataFusionRequest) -> FusedDataset:
        """Fuse bioinformatics data from multiple sources."""
        result = await self.execute(fusion_request.model_dump())

        if result.success and "fused_dataset" in result.data:
            return FusedDataset(**result.data["fused_dataset"])
        else:
            return FusedDataset(
                dataset_id="error",
                name="Error Dataset",
                description="Failed to fuse data",
                source_databases=[],
            )

    async def perform_reasoning(
        self, task: ReasoningTask, dataset: FusedDataset
    ) -> Dict[str, Any]:
        """Perform reasoning on fused bioinformatics data."""
        reasoning_params = {"task": task.model_dump(), "dataset": dataset.model_dump()}

        result = await self.execute(reasoning_params)
        return result.data if result.success else {"error": result.error}


class DeepSearchAgent(BaseAgent):
    """Agent for deep search operations with iterative refinement."""

    def __init__(self, model_name: str = "anthropic:claude-sonnet-4-0", **kwargs):
        super().__init__(AgentType.DEEPSEARCH, model_name, **kwargs)

    def _register_tools(self):
        """Register deep search tools."""
        try:
            from .src.tools.deepsearch_tools import (
                WebSearchTool,
                URLVisitTool,
                ReflectionTool,
                AnswerGeneratorTool,
                QueryRewriterTool,
            )
            from .src.tools.deepsearch_workflow_tool import (
                DeepSearchWorkflowTool,
                DeepSearchAgentTool,
            )

            # Register deep search tools
            web_search_tool = WebSearchTool()
            self._agent.tool(web_search_tool.run)

            url_visit_tool = URLVisitTool()
            self._agent.tool(url_visit_tool.run)

            reflection_tool = ReflectionTool()
            self._agent.tool(reflection_tool.run)

            answer_tool = AnswerGeneratorTool()
            self._agent.tool(answer_tool.run)

            rewriter_tool = QueryRewriterTool()
            self._agent.tool(rewriter_tool.run)

            workflow_tool = DeepSearchWorkflowTool()
            self._agent.tool(workflow_tool.run)

            agent_tool = DeepSearchAgentTool()
            self._agent.tool(agent_tool.run)

        except Exception as e:
            print(f"Warning: Failed to register deep search tools: {e}")

    async def deep_search(self, question: str, max_steps: int = 20) -> Dict[str, Any]:
        """Perform deep search with iterative refinement."""
        search_params = {"question": question, "max_steps": max_steps}

        result = await self.execute(search_params)
        return result.data if result.success else {"error": result.error}


class EvaluatorAgent(BaseAgent):
    """Agent for evaluating research results and quality."""

    def __init__(self, model_name: str = "anthropic:claude-sonnet-4-0", **kwargs):
        super().__init__(AgentType.EVALUATOR, model_name, **kwargs)

    def _register_tools(self):
        """Register evaluation tools."""
        try:
            from .src.tools.workflow_tools import EvaluatorTool, ErrorAnalyzerTool

            # Register evaluation tools
            evaluator_tool = EvaluatorTool()
            self._agent.tool(evaluator_tool.run)

            error_analyzer_tool = ErrorAnalyzerTool()
            self._agent.tool(error_analyzer_tool.run)

        except Exception as e:
            print(f"Warning: Failed to register evaluation tools: {e}")

    async def evaluate(self, question: str, answer: str) -> Dict[str, Any]:
        """Evaluate research results."""
        eval_params = {"question": question, "answer": answer}

        result = await self.execute(eval_params)
        return result.data if result.success else {"error": result.error}


# DeepAgent Integration Classes


class DeepAgentPlanningAgent(BaseAgent):
    """DeepAgent planning agent integrated with DeepResearch."""

    def __init__(self, model_name: str = "anthropic:claude-sonnet-4-0", **kwargs):
        super().__init__(AgentType.DEEP_AGENT_PLANNING, model_name, **kwargs)
        self._deep_agent = None
        self._initialize_deep_agent()

    def _initialize_deep_agent(self):
        """Initialize the underlying DeepAgent."""
        try:
            config = AgentConfig(
                name="deep_planning_agent",
                model_name=self.model_name,
                system_prompt="You are a planning specialist focused on task organization and workflow management.",
                tools=["write_todos", "task"],
                capabilities=[
                    AgentCapability.PLANNING,
                    AgentCapability.TASK_ORCHESTRATION,
                ],
                max_iterations=5,
                timeout=120.0,
            )
            self._deep_agent = PlanningAgent(config)
        except Exception as e:
            print(f"Warning: Failed to initialize DeepAgent planning agent: {e}")

    def _register_tools(self):
        """Register planning tools."""
        try:
            from .src.tools.deep_agent_tools import write_todos_tool, task_tool

            # Register DeepAgent tools
            self._agent.tool(write_todos_tool)
            self._agent.tool(task_tool)

        except Exception as e:
            print(f"Warning: Failed to register DeepAgent planning tools: {e}")

    async def create_plan(
        self, task_description: str, context: Optional[DeepAgentState] = None
    ) -> AgentExecutionResult:
        """Create a detailed execution plan."""
        if self._deep_agent:
            return await self._deep_agent.create_plan(task_description, context)
        else:
            # Fallback to standard agent execution
            result = await self.execute({"task": task_description, "context": context})
            return AgentExecutionResult(
                success=result.success,
                result=result.data,
                error=result.error,
                execution_time=result.execution_time,
                tools_used=["standard_planning"],
            )


class DeepAgentFilesystemAgent(BaseAgent):
    """DeepAgent filesystem agent integrated with DeepResearch."""

    def __init__(self, model_name: str = "anthropic:claude-sonnet-4-0", **kwargs):
        super().__init__(AgentType.DEEP_AGENT_FILESYSTEM, model_name, **kwargs)
        self._deep_agent = None
        self._initialize_deep_agent()

    def _initialize_deep_agent(self):
        """Initialize the underlying DeepAgent."""
        try:
            config = AgentConfig(
                name="deep_filesystem_agent",
                model_name=self.model_name,
                system_prompt="You are a filesystem specialist focused on file operations and content management.",
                tools=["list_files", "read_file", "write_file", "edit_file"],
                capabilities=[
                    AgentCapability.FILESYSTEM,
                    AgentCapability.DATA_PROCESSING,
                ],
                max_iterations=3,
                timeout=60.0,
            )
            self._deep_agent = FilesystemAgent(config)
        except Exception as e:
            print(f"Warning: Failed to initialize DeepAgent filesystem agent: {e}")

    def _register_tools(self):
        """Register filesystem tools."""
        try:
            from .src.tools.deep_agent_tools import (
                list_files_tool,
                read_file_tool,
                write_file_tool,
                edit_file_tool,
            )

            # Register DeepAgent tools
            self._agent.tool(list_files_tool)
            self._agent.tool(read_file_tool)
            self._agent.tool(write_file_tool)
            self._agent.tool(edit_file_tool)

        except Exception as e:
            print(f"Warning: Failed to register DeepAgent filesystem tools: {e}")

    async def manage_files(
        self, operation: str, context: Optional[DeepAgentState] = None
    ) -> AgentExecutionResult:
        """Manage filesystem operations."""
        if self._deep_agent:
            return await self._deep_agent.manage_files(operation, context)
        else:
            # Fallback to standard agent execution
            result = await self.execute({"operation": operation, "context": context})
            return AgentExecutionResult(
                success=result.success,
                result=result.data,
                error=result.error,
                execution_time=result.execution_time,
                tools_used=["standard_filesystem"],
            )


class DeepAgentResearchAgent(BaseAgent):
    """DeepAgent research agent integrated with DeepResearch."""

    def __init__(self, model_name: str = "anthropic:claude-sonnet-4-0", **kwargs):
        super().__init__(AgentType.DEEP_AGENT_RESEARCH, model_name, **kwargs)
        self._deep_agent = None
        self._initialize_deep_agent()

    def _initialize_deep_agent(self):
        """Initialize the underlying DeepAgent."""
        try:
            config = AgentConfig(
                name="deep_research_agent",
                model_name=self.model_name,
                system_prompt="You are a research specialist focused on information gathering and analysis.",
                tools=["web_search", "rag_query", "task"],
                capabilities=[AgentCapability.SEARCH, AgentCapability.ANALYSIS],
                max_iterations=10,
                timeout=300.0,
            )
            self._deep_agent = ResearchAgent(config)
        except Exception as e:
            print(f"Warning: Failed to initialize DeepAgent research agent: {e}")

    def _register_tools(self):
        """Register research tools."""
        try:
            from .src.tools.deep_agent_tools import task_tool
            from .src.tools.websearch_tools import WebSearchTool
            from .src.tools.integrated_search_tools import RAGSearchTool

            # Register DeepAgent tools
            self._agent.tool(task_tool)

            # Register existing research tools
            web_search_tool = WebSearchTool()
            self._agent.tool(web_search_tool.run)

            rag_search_tool = RAGSearchTool()
            self._agent.tool(rag_search_tool.run)

        except Exception as e:
            print(f"Warning: Failed to register DeepAgent research tools: {e}")

    async def conduct_research(
        self, research_query: str, context: Optional[DeepAgentState] = None
    ) -> AgentExecutionResult:
        """Conduct comprehensive research."""
        if self._deep_agent:
            return await self._deep_agent.conduct_research(research_query, context)
        else:
            # Fallback to standard agent execution
            result = await self.execute({"query": research_query, "context": context})
            return AgentExecutionResult(
                success=result.success,
                result=result.data,
                error=result.error,
                execution_time=result.execution_time,
                tools_used=["standard_research"],
            )


class DeepAgentOrchestrationAgent(BaseAgent):
    """DeepAgent orchestration agent integrated with DeepResearch."""

    def __init__(self, model_name: str = "anthropic:claude-sonnet-4-0", **kwargs):
        super().__init__(AgentType.DEEP_AGENT_ORCHESTRATION, model_name, **kwargs)
        self._deep_agent = None
        self._orchestrator = None
        self._initialize_deep_agent()

    def _initialize_deep_agent(self):
        """Initialize the underlying DeepAgent."""
        try:
            config = AgentConfig(
                name="deep_orchestration_agent",
                model_name=self.model_name,
                system_prompt="You are an orchestration specialist focused on coordinating multiple agents and workflows.",
                tools=["task", "coordinate_agents", "synthesize_results"],
                capabilities=[
                    AgentCapability.TASK_ORCHESTRATION,
                    AgentCapability.PLANNING,
                ],
                max_iterations=15,
                timeout=600.0,
            )
            self._deep_agent = TaskOrchestrationAgent(config)

            # Create orchestrator with all available agents
            self._orchestrator = AgentOrchestrator()

        except Exception as e:
            print(f"Warning: Failed to initialize DeepAgent orchestration agent: {e}")

    def _register_tools(self):
        """Register orchestration tools."""
        try:
            from .src.tools.deep_agent_tools import task_tool

            # Register DeepAgent tools
            self._agent.tool(task_tool)

        except Exception as e:
            print(f"Warning: Failed to register DeepAgent orchestration tools: {e}")

    async def orchestrate_tasks(
        self, task_description: str, context: Optional[DeepAgentState] = None
    ) -> AgentExecutionResult:
        """Orchestrate multiple tasks across agents."""
        if self._deep_agent:
            return await self._deep_agent.orchestrate_tasks(task_description, context)
        else:
            # Fallback to standard agent execution
            result = await self.execute({"task": task_description, "context": context})
            return AgentExecutionResult(
                success=result.success,
                result=result.data,
                error=result.error,
                execution_time=result.execution_time,
                tools_used=["standard_orchestration"],
            )

    async def execute_parallel_tasks(
        self, tasks: List[Dict[str, Any]], context: Optional[DeepAgentState] = None
    ) -> List[AgentExecutionResult]:
        """Execute multiple tasks in parallel."""
        if self._orchestrator:
            return await self._orchestrator.execute_parallel(tasks, context)
        else:
            # Fallback to sequential execution
            results = []
            for task in tasks:
                result = await self.orchestrate_tasks(
                    task.get("description", ""), context
                )
                results.append(result)
            return results


class DeepAgentGeneralAgent(BaseAgent):
    """DeepAgent general-purpose agent integrated with DeepResearch."""

    def __init__(self, model_name: str = "anthropic:claude-sonnet-4-0", **kwargs):
        super().__init__(AgentType.DEEP_AGENT_GENERAL, model_name, **kwargs)
        self._deep_agent = None
        self._initialize_deep_agent()

    def _initialize_deep_agent(self):
        """Initialize the underlying DeepAgent."""
        try:
            config = AgentConfig(
                name="deep_general_agent",
                model_name=self.model_name,
                system_prompt="You are a general-purpose agent that can handle various tasks and delegate to specialized agents.",
                tools=["task", "write_todos", "list_files", "read_file", "web_search"],
                capabilities=[
                    AgentCapability.TASK_ORCHESTRATION,
                    AgentCapability.PLANNING,
                    AgentCapability.SEARCH,
                ],
                max_iterations=20,
                timeout=900.0,
            )
            self._deep_agent = GeneralPurposeAgent(config)
        except Exception as e:
            print(f"Warning: Failed to initialize DeepAgent general agent: {e}")

    def _register_tools(self):
        """Register general tools."""
        try:
            from .src.tools.deep_agent_tools import (
                task_tool,
                write_todos_tool,
                list_files_tool,
                read_file_tool,
            )
            from .src.tools.websearch_tools import WebSearchTool

            # Register DeepAgent tools
            self._agent.tool(task_tool)
            self._agent.tool(write_todos_tool)
            self._agent.tool(list_files_tool)
            self._agent.tool(read_file_tool)

            # Register existing tools
            web_search_tool = WebSearchTool()
            self._agent.tool(web_search_tool.run)

        except Exception as e:
            print(f"Warning: Failed to register DeepAgent general tools: {e}")

    async def handle_general_task(
        self, task_description: str, context: Optional[DeepAgentState] = None
    ) -> AgentExecutionResult:
        """Handle general-purpose tasks."""
        if self._deep_agent:
            return await self._deep_agent.execute(task_description, context)
        else:
            # Fallback to standard agent execution
            result = await self.execute({"task": task_description, "context": context})
            return AgentExecutionResult(
                success=result.success,
                result=result.data,
                error=result.error,
                execution_time=result.execution_time,
                tools_used=["standard_general"],
            )


class MultiAgentOrchestrator:
    """Orchestrator for coordinating multiple agents in complex workflows."""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.agents: Dict[AgentType, BaseAgent] = {}
        self.history = ExecutionHistory()
        self._initialize_agents()

    def _initialize_agents(self):
        """Initialize all available agents."""
        model_name = self.config.get("model", "anthropic:claude-sonnet-4-0")

        # Initialize core agents
        self.agents[AgentType.PARSER] = ParserAgent(model_name)
        self.agents[AgentType.PLANNER] = PlannerAgent(model_name)
        self.agents[AgentType.EXECUTOR] = ExecutorAgent(model_name)
        self.agents[AgentType.SEARCH] = SearchAgent(model_name)
        self.agents[AgentType.RAG] = RAGAgent(model_name)
        self.agents[AgentType.BIOINFORMATICS] = BioinformaticsAgent(model_name)
        self.agents[AgentType.DEEPSEARCH] = DeepSearchAgent(model_name)
        self.agents[AgentType.EVALUATOR] = EvaluatorAgent(model_name)

        # Initialize DeepAgent agents if enabled
        if self.config.get("deep_agent", {}).get("enabled", False):
            self.agents[AgentType.DEEP_AGENT_PLANNING] = DeepAgentPlanningAgent(
                model_name
            )
            self.agents[AgentType.DEEP_AGENT_FILESYSTEM] = DeepAgentFilesystemAgent(
                model_name
            )
            self.agents[AgentType.DEEP_AGENT_RESEARCH] = DeepAgentResearchAgent(
                model_name
            )
            self.agents[AgentType.DEEP_AGENT_ORCHESTRATION] = (
                DeepAgentOrchestrationAgent(model_name)
            )
            self.agents[AgentType.DEEP_AGENT_GENERAL] = DeepAgentGeneralAgent(
                model_name
            )

    async def execute_workflow(
        self, question: str, workflow_type: str = "research"
    ) -> Dict[str, Any]:
        """Execute a complete research workflow."""
        start_time = time.time()

        try:
            # Step 1: Parse the question
            parser = self.agents[AgentType.PARSER]
            parsed = await parser.parse_question(question)

            # Step 2: Create execution plan
            planner = self.agents[AgentType.PLANNER]
            plan = await planner.create_plan(parsed)

            # Step 3: Execute based on workflow type
            if workflow_type == "bioinformatics":
                result = await self._execute_bioinformatics_workflow(
                    question, parsed, plan
                )
            elif workflow_type == "deepsearch":
                result = await self._execute_deepsearch_workflow(question, parsed, plan)
            elif workflow_type == "rag":
                result = await self._execute_rag_workflow(question, parsed, plan)
            elif workflow_type == "deep_agent":
                result = await self._execute_deep_agent_workflow(question, parsed, plan)
            else:
                result = await self._execute_standard_workflow(question, parsed, plan)

            # Step 4: Evaluate results
            evaluator = self.agents[AgentType.EVALUATOR]
            evaluation = await evaluator.evaluate(question, result.get("answer", ""))

            execution_time = time.time() - start_time

            return {
                "question": question,
                "workflow_type": workflow_type,
                "parsed_question": parsed,
                "execution_plan": plan,
                "result": result,
                "evaluation": evaluation,
                "execution_time": execution_time,
                "success": True,
            }

        except Exception as e:
            execution_time = time.time() - start_time
            return {
                "question": question,
                "workflow_type": workflow_type,
                "error": str(e),
                "execution_time": execution_time,
                "success": False,
            }

    async def _execute_standard_workflow(
        self, question: str, parsed: Dict[str, Any], plan: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Execute standard research workflow."""
        executor = self.agents[AgentType.EXECUTOR]
        result = await executor.execute_plan(plan, self.history)
        return result

    async def _execute_bioinformatics_workflow(
        self, question: str, parsed: Dict[str, Any], plan: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Execute bioinformatics workflow."""
        bioinformatics_agent = self.agents[AgentType.BIOINFORMATICS]

        # Create fusion request
        fusion_request = DataFusionRequest(
            request_id=f"fusion_{int(time.time())}",
            fusion_type="MultiSource",
            source_databases=["GO", "PubMed", "GEO"],
            quality_threshold=0.8,
        )

        # Fuse data
        fused_dataset = await bioinformatics_agent.fuse_data(fusion_request)

        # Create reasoning task
        reasoning_task = ReasoningTask(
            task_id=f"reasoning_{int(time.time())}",
            task_type="general_reasoning",
            question=question,
            difficulty_level="medium",
        )

        # Perform reasoning
        reasoning_result = await bioinformatics_agent.perform_reasoning(
            reasoning_task, fused_dataset
        )

        return {
            "fused_dataset": fused_dataset.dict(),
            "reasoning_result": reasoning_result,
            "answer": reasoning_result.get("answer", "No answer generated"),
        }

    async def _execute_deepsearch_workflow(
        self, question: str, parsed: Dict[str, Any], plan: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Execute deep search workflow."""
        deepsearch_agent = self.agents[AgentType.DEEPSEARCH]
        result = await deepsearch_agent.deep_search(question)
        return result

    async def _execute_rag_workflow(
        self, question: str, parsed: Dict[str, Any], plan: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Execute RAG workflow."""
        rag_agent = self.agents[AgentType.RAG]

        # Create RAG query
        rag_query = RAGQuery(text=question, top_k=5)

        # Perform RAG query
        rag_response = await rag_agent.query(rag_query)

        return {
            "rag_response": rag_response.dict(),
            "answer": rag_response.generated_answer or "No answer generated",
        }

    async def _execute_deep_agent_workflow(
        self, question: str, parsed: Dict[str, Any], plan: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Execute DeepAgent workflow."""
        # Create initial state
        initial_state = DeepAgentState(
            session_id=f"deep_agent_{int(time.time())}",
            shared_state={
                "question": question,
                "parsed_question": parsed,
                "execution_plan": plan,
            },
        )

        # Use general DeepAgent for orchestration
        if AgentType.DEEP_AGENT_GENERAL in self.agents:
            general_agent = self.agents[AgentType.DEEP_AGENT_GENERAL]
            result = await general_agent.handle_general_task(question, initial_state)

            if result.success:
                return {
                    "deep_agent_result": result.result,
                    "answer": result.result.get(
                        "final_result", "DeepAgent workflow completed"
                    ),
                    "execution_metadata": {
                        "execution_time": result.execution_time,
                        "tools_used": result.tools_used,
                        "iterations_used": result.iterations_used,
                    },
                }

        # Fallback to orchestration agent
        if AgentType.DEEP_AGENT_ORCHESTRATION in self.agents:
            orchestration_agent = self.agents[AgentType.DEEP_AGENT_ORCHESTRATION]
            result = await orchestration_agent.orchestrate_tasks(
                question, initial_state
            )

            if result.success:
                return {
                    "deep_agent_result": result.result,
                    "answer": result.result.get(
                        "result_synthesis", "DeepAgent orchestration completed"
                    ),
                    "execution_metadata": {
                        "execution_time": result.execution_time,
                        "tools_used": result.tools_used,
                        "iterations_used": result.iterations_used,
                    },
                }

        # Final fallback
        return {
            "answer": "DeepAgent workflow completed with standard execution",
            "execution_metadata": {"fallback": True},
        }


# Factory functions for creating agents
def create_agent(agent_type: AgentType, **kwargs) -> BaseAgent:
    """Create an agent of the specified type."""
    agent_classes = {
        AgentType.PARSER: ParserAgent,
        AgentType.PLANNER: PlannerAgent,
        AgentType.EXECUTOR: ExecutorAgent,
        AgentType.SEARCH: SearchAgent,
        AgentType.RAG: RAGAgent,
        AgentType.BIOINFORMATICS: BioinformaticsAgent,
        AgentType.DEEPSEARCH: DeepSearchAgent,
        AgentType.EVALUATOR: EvaluatorAgent,
        # DeepAgent types
        AgentType.DEEP_AGENT_PLANNING: DeepAgentPlanningAgent,
        AgentType.DEEP_AGENT_FILESYSTEM: DeepAgentFilesystemAgent,
        AgentType.DEEP_AGENT_RESEARCH: DeepAgentResearchAgent,
        AgentType.DEEP_AGENT_ORCHESTRATION: DeepAgentOrchestrationAgent,
        AgentType.DEEP_AGENT_GENERAL: DeepAgentGeneralAgent,
    }

    agent_class = agent_classes.get(agent_type)
    if not agent_class:
        raise ValueError(f"Unknown agent type: {agent_type}")

    return agent_class(**kwargs)


def create_orchestrator(config: Dict[str, Any]) -> MultiAgentOrchestrator:
    """Create a multi-agent orchestrator."""
    return MultiAgentOrchestrator(config)


# Export main classes and functions
__all__ = [
    "BaseAgent",
    "ParserAgent",
    "PlannerAgent",
    "ExecutorAgent",
    "SearchAgent",
    "RAGAgent",
    "BioinformaticsAgent",
    "DeepSearchAgent",
    "EvaluatorAgent",
    "MultiAgentOrchestrator",
    # DeepAgent classes
    "DeepAgentPlanningAgent",
    "DeepAgentFilesystemAgent",
    "DeepAgentResearchAgent",
    "DeepAgentOrchestrationAgent",
    "DeepAgentGeneralAgent",
    "AgentType",
    "AgentStatus",
    "AgentDependencies",
    "AgentResult",
    "ExecutionHistory",
    "create_agent",
    "create_orchestrator",
]
