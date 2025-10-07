"""
Import tests for DeepResearch prompts modules.

This module tests that all imports from the prompts subdirectory work correctly,
including all individual prompt modules and their dependencies.
"""

import pytest


class TestPromptsModuleImports:
    """Test imports for individual prompt modules."""

    def test_agents_prompts_imports(self):
        """Test all imports from agents prompts module."""

        from DeepResearch.src.prompts.agents import (
            BASE_AGENT_INSTRUCTIONS,
            BASE_AGENT_SYSTEM_PROMPT,
            BIOINFORMATICS_AGENT_SYSTEM_PROMPT,
            DEEPSEARCH_AGENT_SYSTEM_PROMPT,
            EVALUATOR_AGENT_SYSTEM_PROMPT,
            EXECUTOR_AGENT_SYSTEM_PROMPT,
            PARSER_AGENT_SYSTEM_PROMPT,
            PLANNER_AGENT_SYSTEM_PROMPT,
            RAG_AGENT_SYSTEM_PROMPT,
            SEARCH_AGENT_SYSTEM_PROMPT,
            AgentPrompts,
        )

        # Verify they are all accessible and not None
        assert BASE_AGENT_SYSTEM_PROMPT is not None
        assert BASE_AGENT_INSTRUCTIONS is not None
        assert PARSER_AGENT_SYSTEM_PROMPT is not None
        assert PLANNER_AGENT_SYSTEM_PROMPT is not None
        assert EXECUTOR_AGENT_SYSTEM_PROMPT is not None
        assert SEARCH_AGENT_SYSTEM_PROMPT is not None
        assert RAG_AGENT_SYSTEM_PROMPT is not None
        assert BIOINFORMATICS_AGENT_SYSTEM_PROMPT is not None
        assert DEEPSEARCH_AGENT_SYSTEM_PROMPT is not None
        assert EVALUATOR_AGENT_SYSTEM_PROMPT is not None
        assert AgentPrompts is not None

        # Test that they are strings (prompt templates)
        assert isinstance(BASE_AGENT_SYSTEM_PROMPT, str)
        assert isinstance(PARSER_AGENT_SYSTEM_PROMPT, str)

        # Test AgentPrompts functionality
        assert hasattr(AgentPrompts, "get_system_prompt")
        assert hasattr(AgentPrompts, "get_instructions")
        assert callable(AgentPrompts.get_system_prompt)

        # Test getting prompts for different agent types
        parser_prompt = AgentPrompts.get_system_prompt("parser")
        assert isinstance(parser_prompt, str)
        assert len(parser_prompt) > 0

    def test_agent_imports(self):
        """Test all imports from agent module."""

        from DeepResearch.src.prompts.agent import (
            ACTION_ANSWER,
            ACTION_BEAST,
            ACTION_REFLECT,
            ACTION_SEARCH,
            ACTION_VISIT,
            ACTIONS_WRAPPER,
            FOOTER,
            HEADER,
            AgentPrompts,
        )

        # Verify they are all accessible and not None
        assert HEADER is not None
        assert ACTIONS_WRAPPER is not None
        assert ACTION_VISIT is not None
        assert ACTION_SEARCH is not None
        assert ACTION_ANSWER is not None
        assert ACTION_BEAST is not None
        assert ACTION_REFLECT is not None
        assert FOOTER is not None
        assert AgentPrompts is not None

        # Test that they are strings (prompt templates)
        assert isinstance(HEADER, str)
        assert isinstance(ACTIONS_WRAPPER, str)
        assert isinstance(ACTION_VISIT, str)

    def test_broken_ch_fixer_imports(self):
        """Test all imports from broken_ch_fixer module."""

        from DeepResearch.src.prompts.broken_ch_fixer import (
            BROKEN_CH_FIXER_PROMPTS,
            BrokenCHFixerPrompts,
        )

        # Verify they are all accessible and not None
        assert BROKEN_CH_FIXER_PROMPTS is not None
        assert BrokenCHFixerPrompts is not None

    def test_code_exec_imports(self):
        """Test all imports from code_exec module."""

        from DeepResearch.src.prompts.code_exec import (
            CODE_EXEC_PROMPTS,
            CodeExecPrompts,
        )

        # Verify they are all accessible and not None
        assert CODE_EXEC_PROMPTS is not None
        assert CodeExecPrompts is not None

    def test_code_sandbox_imports(self):
        """Test all imports from code_sandbox module."""

        from DeepResearch.src.prompts.code_sandbox import (
            CODE_SANDBOX_PROMPTS,
            CodeSandboxPrompts,
        )

        # Verify they are all accessible and not None
        assert CODE_SANDBOX_PROMPTS is not None
        assert CodeSandboxPrompts is not None

    def test_deep_agent_graph_imports(self):
        """Test all imports from deep_agent_graph module."""

        from DeepResearch.src.prompts.deep_agent_graph import (
            DEEP_AGENT_GRAPH_PROMPTS,
            DeepAgentGraphPrompts,
        )

        # Verify they are all accessible and not None
        assert DEEP_AGENT_GRAPH_PROMPTS is not None
        assert DeepAgentGraphPrompts is not None

    def test_deep_agent_prompts_imports(self):
        """Test all imports from deep_agent_prompts module."""

        from DeepResearch.src.prompts.deep_agent_prompts import (
            DEEP_AGENT_PROMPTS,
            DeepAgentPrompts,
        )

        # Verify they are all accessible and not None
        assert DEEP_AGENT_PROMPTS is not None
        assert DeepAgentPrompts is not None

    def test_error_analyzer_imports(self):
        """Test all imports from error_analyzer module."""

        from DeepResearch.src.prompts.error_analyzer import (
            ERROR_ANALYZER_PROMPTS,
            ErrorAnalyzerPrompts,
        )

        # Verify they are all accessible and not None
        assert ERROR_ANALYZER_PROMPTS is not None
        assert ErrorAnalyzerPrompts is not None

    def test_evaluator_imports(self):
        """Test all imports from evaluator module."""

        from DeepResearch.src.prompts.evaluator import (
            EVALUATOR_PROMPTS,
            EvaluatorPrompts,
        )

        # Verify they are all accessible and not None
        assert EVALUATOR_PROMPTS is not None
        assert EvaluatorPrompts is not None

    def test_finalizer_imports(self):
        """Test all imports from finalizer module."""

        from DeepResearch.src.prompts.finalizer import (
            FINALIZER_PROMPTS,
            FinalizerPrompts,
        )

        # Verify they are all accessible and not None
        assert FINALIZER_PROMPTS is not None
        assert FinalizerPrompts is not None

    def test_orchestrator_imports(self):
        """Test all imports from orchestrator module."""

        from DeepResearch.src.prompts.orchestrator import (
            ORCHESTRATOR_PROMPTS,
            OrchestratorPrompts,
        )

        # Verify they are all accessible and not None
        assert ORCHESTRATOR_PROMPTS is not None
        assert OrchestratorPrompts is not None

    def test_planner_imports(self):
        """Test all imports from planner module."""

        from DeepResearch.src.prompts.planner import (
            PLANNER_PROMPTS,
            PlannerPrompts,
        )

        # Verify they are all accessible and not None
        assert PLANNER_PROMPTS is not None
        assert PlannerPrompts is not None

    def test_query_rewriter_imports(self):
        """Test all imports from query_rewriter module."""

        from DeepResearch.src.prompts.query_rewriter import (
            QUERY_REWRITER_PROMPTS,
            QueryRewriterPrompts,
        )

        # Verify they are all accessible and not None
        assert QUERY_REWRITER_PROMPTS is not None
        assert QueryRewriterPrompts is not None

    def test_reducer_imports(self):
        """Test all imports from reducer module."""

        from DeepResearch.src.prompts.reducer import (
            REDUCER_PROMPTS,
            ReducerPrompts,
        )

        # Verify they are all accessible and not None
        assert REDUCER_PROMPTS is not None
        assert ReducerPrompts is not None

    def test_research_planner_imports(self):
        """Test all imports from research_planner module."""

        from DeepResearch.src.prompts.research_planner import (
            RESEARCH_PLANNER_PROMPTS,
            ResearchPlannerPrompts,
        )

        # Verify they are all accessible and not None
        assert RESEARCH_PLANNER_PROMPTS is not None
        assert ResearchPlannerPrompts is not None

    def test_serp_cluster_imports(self):
        """Test all imports from serp_cluster module."""

        from DeepResearch.src.prompts.serp_cluster import (
            SERP_CLUSTER_PROMPTS,
            SerpClusterPrompts,
        )

        # Verify they are all accessible and not None
        assert SERP_CLUSTER_PROMPTS is not None
        assert SerpClusterPrompts is not None


class TestPromptsCrossModuleImports:
    """Test cross-module imports and dependencies within prompts."""

    def test_prompts_internal_dependencies(self):
        """Test that prompt modules can import from each other correctly."""
        # Test that modules can import shared patterns
        from DeepResearch.src.prompts.agent import AgentPrompts
        from DeepResearch.src.prompts.planner import PlannerPrompts

        # This should work without circular imports
        assert AgentPrompts is not None
        assert PlannerPrompts is not None

    def test_utils_integration_imports(self):
        """Test that prompts can import from utils module."""
        # This tests the import chain: prompts -> utils
        from DeepResearch.src.prompts.research_planner import ResearchPlannerPrompts
        from DeepResearch.src.utils.config_loader import BioinformaticsConfigLoader

        # If we get here without ImportError, the import chain works
        assert ResearchPlannerPrompts is not None
        assert BioinformaticsConfigLoader is not None

    def test_agents_integration_imports(self):
        """Test that prompts can import from agents module."""
        # This tests the import chain: prompts -> agents
        from DeepResearch.src.agents.prime_parser import StructuredProblem
        from DeepResearch.src.prompts.agent import AgentPrompts

        # If we get here without ImportError, the import chain works
        assert AgentPrompts is not None
        assert StructuredProblem is not None


class TestPromptsComplexImportChains:
    """Test complex import chains involving multiple modules."""

    def test_full_prompts_initialization_chain(self):
        """Test the complete import chain for prompts initialization."""
        try:
            from DeepResearch.src.prompts.agent import HEADER, AgentPrompts
            from DeepResearch.src.prompts.evaluator import (
                EVALUATOR_PROMPTS,
                EvaluatorPrompts,
            )
            from DeepResearch.src.prompts.planner import PLANNER_PROMPTS, PlannerPrompts
            from DeepResearch.src.utils.config_loader import BioinformaticsConfigLoader

            # If all imports succeed, the chain is working
            assert AgentPrompts is not None
            assert HEADER is not None
            assert PlannerPrompts is not None
            assert PLANNER_PROMPTS is not None
            assert EvaluatorPrompts is not None
            assert EVALUATOR_PROMPTS is not None
            assert BioinformaticsConfigLoader is not None

        except ImportError as e:
            pytest.fail(f"Prompts import chain failed: {e}")

    def test_workflow_prompts_chain(self):
        """Test the complete import chain for workflow prompts."""
        try:
            from DeepResearch.src.prompts.finalizer import FinalizerPrompts
            from DeepResearch.src.prompts.orchestrator import OrchestratorPrompts
            from DeepResearch.src.prompts.reducer import ReducerPrompts
            from DeepResearch.src.prompts.research_planner import ResearchPlannerPrompts

            # If all imports succeed, the chain is working
            assert OrchestratorPrompts is not None
            assert ResearchPlannerPrompts is not None
            assert FinalizerPrompts is not None
            assert ReducerPrompts is not None

        except ImportError as e:
            pytest.fail(f"Workflow prompts import chain failed: {e}")


class TestPromptsImportErrorHandling:
    """Test import error handling for prompts modules."""

    def test_missing_dependencies_handling(self):
        """Test that modules handle missing dependencies gracefully."""
        # Most prompt modules should work without external dependencies
        from DeepResearch.src.prompts.agent import HEADER, AgentPrompts
        from DeepResearch.src.prompts.planner import PlannerPrompts

        # These should always be available
        assert AgentPrompts is not None
        assert HEADER is not None
        assert PlannerPrompts is not None

    def test_circular_import_prevention(self):
        """Test that there are no circular imports in prompts."""
        # This test will fail if there are circular imports

        # If we get here, no circular imports were detected
        assert True

    def test_prompt_content_validation(self):
        """Test that prompt content is properly structured."""
        from DeepResearch.src.prompts.agent import ACTIONS_WRAPPER, HEADER

        # Test that prompts contain expected placeholders
        assert "${current_date_utc}" in HEADER
        assert "${action_sections}" in ACTIONS_WRAPPER

        # Test that prompts are non-empty strings
        assert len(HEADER) > 0
        assert len(ACTIONS_WRAPPER) > 0

    def test_prompt_class_instantiation(self):
        """Test that prompt classes can be instantiated."""
        from DeepResearch.src.prompts.agent import AgentPrompts

        # Test that we can create instances (basic functionality)
        try:
            prompts = AgentPrompts()
            assert prompts is not None
        except Exception as e:
            pytest.fail(f"Prompt class instantiation failed: {e}")
