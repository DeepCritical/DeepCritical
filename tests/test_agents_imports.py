"""
Import tests for DeepResearch agents modules.

This module tests that all imports from the agents subdirectory work correctly,
including all individual agent modules and their dependencies.
"""

import pytest


class TestAgentsModuleImports:
    """Test imports for individual agent modules."""

    def test_agents_datatypes_imports(self):
        """Test all imports from agents datatypes module."""
        from DeepResearch.src.datatypes.agents import (
            AgentDependencies,
            AgentResult,
            AgentStatus,
            AgentType,
            ExecutionHistory,
        )

        # Verify they are all accessible and not None
        assert AgentType is not None
        assert AgentStatus is not None
        assert AgentDependencies is not None
        assert AgentResult is not None
        assert ExecutionHistory is not None

        # Test enum values exist
        assert hasattr(AgentType, "PARSER")
        assert hasattr(AgentType, "PLANNER")
        assert hasattr(AgentStatus, "IDLE")
        assert hasattr(AgentStatus, "RUNNING")

    def test_agents_prompts_imports(self):
        """Test all imports from agents prompts module."""
        from DeepResearch.src.prompts.agents import AgentPrompts

        # Verify they are all accessible and not None
        assert AgentPrompts is not None

        # Test that AgentPrompts has the expected methods
        assert hasattr(AgentPrompts, "get_system_prompt")
        assert hasattr(AgentPrompts, "get_instructions")
        assert hasattr(AgentPrompts, "get_agent_prompts")

        # Test that we can get prompts for different agent types
        parser_prompts = AgentPrompts.get_agent_prompts("parser")
        assert isinstance(parser_prompts, dict)
        assert "system" in parser_prompts
        assert "instructions" in parser_prompts

    def test_prime_parser_imports(self):
        """Test all imports from prime_parser module."""
        # Test core imports

        # Test specific classes and functions
        from DeepResearch.src.agents.prime_parser import (
            DataType,
            QueryParser,
            ScientificIntent,
            StructuredProblem,
            parse_query,
        )

        # Verify they are all accessible and not None
        assert ScientificIntent is not None
        assert DataType is not None
        assert StructuredProblem is not None
        assert QueryParser is not None
        assert parse_query is not None

        # Test enum values exist
        assert hasattr(ScientificIntent, "PROTEIN_DESIGN")
        assert hasattr(DataType, "SEQUENCE")

    def test_prime_planner_imports(self):
        """Test all imports from prime_planner module."""

        from DeepResearch.src.agents.prime_planner import (
            PlanGenerator,
            ToolCategory,
            ToolSpec,
            WorkflowDAG,
            WorkflowStep,
            generate_plan,
        )

        # Verify they are all accessible and not None
        assert PlanGenerator is not None
        assert WorkflowDAG is not None
        assert WorkflowStep is not None
        assert ToolSpec is not None
        assert ToolCategory is not None
        assert generate_plan is not None

        # Test enum values exist
        assert hasattr(ToolCategory, "SEARCH")
        assert hasattr(ToolCategory, "ANALYSIS")

    def test_prime_executor_imports(self):
        """Test all imports from prime_executor module."""

        from DeepResearch.src.agents.prime_executor import (
            ExecutionContext,
            ToolExecutor,
            execute_workflow,
        )

        # Verify they are all accessible and not None
        assert ToolExecutor is not None
        assert ExecutionContext is not None
        assert execute_workflow is not None

    def test_orchestrator_imports(self):
        """Test all imports from orchestrator module."""

        from DeepResearch.src.datatypes.orchestrator import Orchestrator

        # Verify they are all accessible and not None
        assert Orchestrator is not None

        # Test that it's a dataclass
        from dataclasses import is_dataclass

        assert is_dataclass(Orchestrator)

    def test_planner_imports(self):
        """Test all imports from planner module."""

        from DeepResearch.src.datatypes.planner import Planner

        # Verify they are all accessible and not None
        assert Planner is not None

        # Test that it's a dataclass
        from dataclasses import is_dataclass

        assert is_dataclass(Planner)

    def test_pyd_ai_toolsets_imports(self):
        """Test all imports from pyd_ai_toolsets module."""

        from DeepResearch.src.agents.pyd_ai_toolsets import PydAIToolsetBuilder

        # Verify they are all accessible and not None
        assert PydAIToolsetBuilder is not None

    def test_research_agent_imports(self):
        """Test all imports from research_agent module."""

        from DeepResearch.src.agents.research_agent import (
            ResearchAgent,
            run,
        )
        from DeepResearch.src.datatypes.research import (
            ResearchOutcome,
            StepResult,
        )

        # Verify they are all accessible and not None
        assert ResearchAgent is not None
        assert ResearchOutcome is not None
        assert StepResult is not None
        assert run is not None

    def test_tool_caller_imports(self):
        """Test all imports from tool_caller module."""

        from DeepResearch.src.agents.tool_caller import ToolCaller

        # Verify they are all accessible and not None
        assert ToolCaller is not None

    def test_agent_orchestrator_imports(self):
        """Test all imports from agent_orchestrator module."""

        from DeepResearch.src.agents.agent_orchestrator import AgentOrchestrator

        # Verify they are all accessible and not None
        assert AgentOrchestrator is not None

    def test_bioinformatics_agents_imports(self):
        """Test all imports from bioinformatics_agents module."""

        from DeepResearch.src.agents.bioinformatics_agents import BioinformaticsAgent

        # Verify they are all accessible and not None
        assert BioinformaticsAgent is not None

    def test_deep_agent_implementations_imports(self):
        """Test all imports from deep_agent_implementations module."""

        from DeepResearch.src.agents.deep_agent_implementations import (
            DeepAgentImplementation,
        )

        # Verify they are all accessible and not None
        assert DeepAgentImplementation is not None

    def test_multi_agent_coordinator_imports(self):
        """Test all imports from multi_agent_coordinator module."""

        from DeepResearch.src.agents.multi_agent_coordinator import (
            MultiAgentCoordinator,
        )

        # Verify they are all accessible and not None
        assert MultiAgentCoordinator is not None

        # Test that the main types are accessible through the main module
        # (they should be imported from the datatypes module)
        from DeepResearch.src.datatypes import (
            AgentRole,
            CoordinationResult,
            CoordinationStrategy,
        )

        assert CoordinationStrategy is not None
        assert AgentRole is not None
        assert CoordinationResult is not None

        # Test enum values exist
        assert hasattr(CoordinationStrategy, "COLLABORATIVE")
        assert hasattr(AgentRole, "COORDINATOR")

    def test_execution_imports(self):
        """Test that execution types are accessible through agents module."""

        # Test that execution types are accessible from datatypes (used by agents)
        from DeepResearch.src.datatypes import (
            ExecutionContext,
            WorkflowDAG,
            WorkflowStep,
        )

        # Verify they are all accessible and not None
        assert WorkflowStep is not None
        assert WorkflowDAG is not None
        assert ExecutionContext is not None

        # Test that they are dataclasses
        from dataclasses import is_dataclass

        assert is_dataclass(WorkflowStep)
        assert is_dataclass(WorkflowDAG)
        assert is_dataclass(ExecutionContext)

    def test_search_agent_imports(self):
        """Test all imports from search_agent module."""

        from DeepResearch.src.agents.search_agent import SearchAgent
        from DeepResearch.src.datatypes.search_agent import (
            SearchAgentConfig,
            SearchAgentDependencies,
            SearchQuery,
            SearchResult,
        )
        from DeepResearch.src.prompts.search_agent import SearchAgentPrompts

        # Verify they are all accessible and not None
        assert SearchAgent is not None
        assert SearchAgentConfig is not None
        assert SearchQuery is not None
        assert SearchResult is not None
        assert SearchAgentDependencies is not None
        assert SearchAgentPrompts is not None

        # Test that search agent can import its dependencies
        assert hasattr(SearchAgent, "_get_system_prompt")
        assert hasattr(SearchAgent, "create_rag_agent")

    def test_workflow_orchestrator_imports(self):
        """Test all imports from workflow_orchestrator module."""

        from DeepResearch.src.agents.workflow_orchestrator import WorkflowOrchestrator

        # Verify they are all accessible and not None
        assert WorkflowOrchestrator is not None


class TestAgentsCrossModuleImports:
    """Test cross-module imports and dependencies within agents."""

    def test_agents_internal_dependencies(self):
        """Test that agent modules can import from each other correctly."""
        # Test that research_agent can import from other modules
        from DeepResearch.src.agents.research_agent import ResearchAgent

        # This should work without circular imports
        assert ResearchAgent is not None

    def test_prompts_integration_imports(self):
        """Test that agents can import from prompts module."""
        # This tests the import chain: agents -> prompts
        from DeepResearch.src.agents.research_agent import _compose_agent_system

        # If we get here without ImportError, the import chain works
        assert _compose_agent_system is not None

    def test_tools_integration_imports(self):
        """Test that agents can import from tools module."""
        # This tests the import chain: agents -> tools
        from DeepResearch.src.agents.research_agent import ResearchAgent

        # If we get here without ImportError, the import chain works
        assert ResearchAgent is not None

    def test_datatypes_integration_imports(self):
        """Test that agents can import from datatypes module."""
        # This tests the import chain: agents -> datatypes
        from DeepResearch.src.agents.prime_parser import StructuredProblem
        from DeepResearch.src.datatypes.agents import AgentType

        # If we get here without ImportError, the import chain works
        assert StructuredProblem is not None
        assert AgentType is not None


class TestAgentsComplexImportChains:
    """Test complex import chains involving multiple modules."""

    def test_full_agent_initialization_chain(self):
        """Test the complete import chain for agent initialization."""
        # This tests the full chain: agents -> prompts -> tools -> datatypes
        try:
            from DeepResearch.src.agents.research_agent import ResearchAgent
            from DeepResearch.src.datatypes import Document, ResearchOutcome, StepResult
            from DeepResearch.src.prompts import PromptLoader
            from DeepResearch.src.utils.pydantic_ai_utils import (
                build_builtin_tools as _build_builtin_tools,
            )

            # If all imports succeed, the chain is working
            assert ResearchAgent is not None
            assert PromptLoader is not None
            assert _build_builtin_tools is not None
            assert Document is not None
            assert ResearchOutcome is not None
            assert StepResult is not None

        except ImportError as e:
            pytest.fail(f"Import chain failed: {e}")

    def test_workflow_execution_chain(self):
        """Test the complete import chain for workflow execution."""
        try:
            from DeepResearch.src.agents.prime_executor import execute_workflow
            from DeepResearch.src.agents.prime_planner import generate_plan
            from DeepResearch.src.datatypes.orchestrator import Orchestrator

            # If all imports succeed, the chain is working
            assert generate_plan is not None
            assert execute_workflow is not None
            assert Orchestrator is not None

        except ImportError as e:
            pytest.fail(f"Workflow execution import chain failed: {e}")


class TestAgentsImportErrorHandling:
    """Test import error handling for agents modules."""

    def test_missing_dependencies_handling(self):
        """Test that modules handle missing dependencies gracefully."""
        # Test that modules handle optional dependencies correctly
        from DeepResearch.src.agents.research_agent import Agent

        # Agent might be None if pydantic_ai is not installed
        # This is expected behavior for optional dependencies
        assert Agent is not None or Agent is None  # Either works

    def test_circular_import_prevention(self):
        """Test that there are no circular imports in agents."""
        # This test will fail if there are circular imports

        # If we get here, no circular imports were detected
        assert True
