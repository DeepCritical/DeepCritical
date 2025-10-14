"""
VLLM-based tests for agents.py prompts.

This module tests all prompts defined in the agents module using VLLM containers.
These tests are optional and disabled in CI by default.
"""

import pytest

from .test_prompts_vllm_base import VLLMPromptTestBase


class TestAgentsPromptsVLLM(VLLMPromptTestBase):
    """Test agents.py prompts with VLLM."""

    @pytest.mark.vllm
    @pytest.mark.optional
    def test_agents_prompts_vllm(self, vllm_tester):
        """Test all prompts from agents module with VLLM."""
        # Run tests for agents module
        results = self.run_module_prompt_tests(
            "agents", vllm_tester, max_tokens=256, temperature=0.7
        )

        # Assert minimum success rate
        self.assert_prompt_test_success(results, min_success_rate=0.8)

        # Check that we tested some prompts
        assert len(results) > 0, "No prompts were tested from agents module"

        # Log container info
        vllm_tester.get_container_info()

    @pytest.mark.vllm
    @pytest.mark.optional
    def test_base_agent_prompts(self, vllm_tester):
        """Test base agent prompts specifically."""
        from DeepResearch.src.prompts.agents import (
            BASE_AGENT_INSTRUCTIONS,
            BASE_AGENT_SYSTEM_PROMPT,
        )

        # Test base system prompt
        result = self._test_single_prompt(
            vllm_tester,
            "BASE_AGENT_SYSTEM_PROMPT",
            BASE_AGENT_SYSTEM_PROMPT,
            max_tokens=128,
            temperature=0.5,
        )

        assert result["success"]
        assert "generated_response" in result
        assert len(result["generated_response"]) > 0

        # Test base instructions
        result = self._test_single_prompt(
            vllm_tester,
            "BASE_AGENT_INSTRUCTIONS",
            BASE_AGENT_INSTRUCTIONS,
            max_tokens=128,
            temperature=0.5,
        )

        assert result["success"]

    @pytest.mark.vllm
    @pytest.mark.optional
    def test_parser_agent_prompts(self, vllm_tester):
        """Test parser agent prompts specifically."""
        from DeepResearch.src.prompts.agents import (
            PARSER_AGENT_INSTRUCTIONS,
            PARSER_AGENT_SYSTEM_PROMPT,
        )

        # Test parser system prompt
        result = self._test_single_prompt(
            vllm_tester,
            "PARSER_AGENT_SYSTEM_PROMPT",
            PARSER_AGENT_SYSTEM_PROMPT,
            expected_placeholders=["question", "context"],
            max_tokens=128,
            temperature=0.5,
        )

        assert result["success"]
        assert "reasoning" in result

        # Test parser instructions
        result = self._test_single_prompt(
            vllm_tester,
            "PARSER_AGENT_INSTRUCTIONS",
            PARSER_AGENT_INSTRUCTIONS,
            max_tokens=128,
            temperature=0.5,
        )

        assert result["success"]

    @pytest.mark.vllm
    @pytest.mark.optional
    def test_planner_agent_prompts(self, vllm_tester):
        """Test planner agent prompts specifically."""
        from DeepResearch.src.prompts.agents import (
            PLANNER_AGENT_INSTRUCTIONS,
            PLANNER_AGENT_SYSTEM_PROMPT,
        )

        # Test planner system prompt
        result = self._test_single_prompt(
            vllm_tester,
            "PLANNER_AGENT_SYSTEM_PROMPT",
            PLANNER_AGENT_SYSTEM_PROMPT,
            max_tokens=128,
            temperature=0.5,
        )

        assert result["success"]

        # Test planner instructions
        result = self._test_single_prompt(
            vllm_tester,
            "PLANNER_AGENT_INSTRUCTIONS",
            PLANNER_AGENT_INSTRUCTIONS,
            max_tokens=128,
            temperature=0.5,
        )

        assert result["success"]

    @pytest.mark.vllm
    @pytest.mark.optional
    def test_executor_agent_prompts(self, vllm_tester):
        """Test executor agent prompts specifically."""
        from DeepResearch.src.prompts.agents import (
            EXECUTOR_AGENT_INSTRUCTIONS,
            EXECUTOR_AGENT_SYSTEM_PROMPT,
        )

        # Test executor system prompt
        result = self._test_single_prompt(
            vllm_tester,
            "EXECUTOR_AGENT_SYSTEM_PROMPT",
            EXECUTOR_AGENT_SYSTEM_PROMPT,
            max_tokens=128,
            temperature=0.5,
        )

        assert result["success"]

        # Test executor instructions
        result = self._test_single_prompt(
            vllm_tester,
            "EXECUTOR_AGENT_INSTRUCTIONS",
            EXECUTOR_AGENT_INSTRUCTIONS,
            max_tokens=128,
            temperature=0.5,
        )

        assert result["success"]

    @pytest.mark.vllm
    @pytest.mark.optional
    def test_search_agent_prompts(self, vllm_tester):
        """Test search agent prompts specifically."""
        from DeepResearch.src.prompts.agents import (
            SEARCH_AGENT_INSTRUCTIONS,
            SEARCH_AGENT_SYSTEM_PROMPT,
        )

        # Test search system prompt
        result = self._test_single_prompt(
            vllm_tester,
            "SEARCH_AGENT_SYSTEM_PROMPT",
            SEARCH_AGENT_SYSTEM_PROMPT,
            max_tokens=128,
            temperature=0.5,
        )

        assert result["success"]

        # Test search instructions
        result = self._test_single_prompt(
            vllm_tester,
            "SEARCH_AGENT_INSTRUCTIONS",
            SEARCH_AGENT_INSTRUCTIONS,
            max_tokens=128,
            temperature=0.5,
        )

        assert result["success"]

    @pytest.mark.vllm
    @pytest.mark.optional
    def test_rag_agent_prompts(self, vllm_tester):
        """Test RAG agent prompts specifically."""
        from DeepResearch.src.prompts.agents import (
            RAG_AGENT_INSTRUCTIONS,
            RAG_AGENT_SYSTEM_PROMPT,
        )

        # Test RAG system prompt
        result = self._test_single_prompt(
            vllm_tester,
            "RAG_AGENT_SYSTEM_PROMPT",
            RAG_AGENT_SYSTEM_PROMPT,
            max_tokens=128,
            temperature=0.5,
        )

        assert result["success"]

        # Test RAG instructions
        result = self._test_single_prompt(
            vllm_tester,
            "RAG_AGENT_INSTRUCTIONS",
            RAG_AGENT_INSTRUCTIONS,
            max_tokens=128,
            temperature=0.5,
        )

        assert result["success"]

    @pytest.mark.vllm
    @pytest.mark.optional
    def test_bioinformatics_agent_prompts(self, vllm_tester):
        """Test bioinformatics agent prompts specifically."""
        from DeepResearch.src.prompts.agents import (
            BIOINFORMATICS_AGENT_INSTRUCTIONS,
            BIOINFORMATICS_AGENT_SYSTEM_PROMPT,
        )

        # Test bioinformatics system prompt
        result = self._test_single_prompt(
            vllm_tester,
            "BIOINFORMATICS_AGENT_SYSTEM_PROMPT",
            BIOINFORMATICS_AGENT_SYSTEM_PROMPT,
            max_tokens=128,
            temperature=0.5,
        )

        assert result["success"]

        # Test bioinformatics instructions
        result = self._test_single_prompt(
            vllm_tester,
            "BIOINFORMATICS_AGENT_INSTRUCTIONS",
            BIOINFORMATICS_AGENT_INSTRUCTIONS,
            max_tokens=128,
            temperature=0.5,
        )

        assert result["success"]

    @pytest.mark.vllm
    @pytest.mark.optional
    def test_deepsearch_agent_prompts(self, vllm_tester):
        """Test deepsearch agent prompts specifically."""
        from DeepResearch.src.prompts.agents import (
            DEEPSEARCH_AGENT_INSTRUCTIONS,
            DEEPSEARCH_AGENT_SYSTEM_PROMPT,
        )

        # Test deepsearch system prompt
        result = self._test_single_prompt(
            vllm_tester,
            "DEEPSEARCH_AGENT_SYSTEM_PROMPT",
            DEEPSEARCH_AGENT_SYSTEM_PROMPT,
            max_tokens=128,
            temperature=0.5,
        )

        assert result["success"]

        # Test deepsearch instructions
        result = self._test_single_prompt(
            vllm_tester,
            "DEEPSEARCH_AGENT_INSTRUCTIONS",
            DEEPSEARCH_AGENT_INSTRUCTIONS,
            max_tokens=128,
            temperature=0.5,
        )

        assert result["success"]

    @pytest.mark.vllm
    @pytest.mark.optional
    def test_evaluator_agent_prompts(self, vllm_tester):
        """Test evaluator agent prompts specifically."""
        from DeepResearch.src.prompts.agents import (
            EVALUATOR_AGENT_INSTRUCTIONS,
            EVALUATOR_AGENT_SYSTEM_PROMPT,
        )

        # Test evaluator system prompt
        result = self._test_single_prompt(
            vllm_tester,
            "EVALUATOR_AGENT_SYSTEM_PROMPT",
            EVALUATOR_AGENT_SYSTEM_PROMPT,
            max_tokens=128,
            temperature=0.5,
        )

        assert result["success"]

        # Test evaluator instructions
        result = self._test_single_prompt(
            vllm_tester,
            "EVALUATOR_AGENT_INSTRUCTIONS",
            EVALUATOR_AGENT_INSTRUCTIONS,
            max_tokens=128,
            temperature=0.5,
        )

        assert result["success"]

    @pytest.mark.vllm
    @pytest.mark.optional
    def test_agent_prompts_class(self, vllm_tester):
        """Test the AgentPrompts class functionality."""
        from DeepResearch.src.prompts.agents import AgentPrompts

        # Test that AgentPrompts class works
        assert AgentPrompts is not None

        # Test getting prompts for different agent types
        parser_prompts = AgentPrompts.get_agent_prompts("parser")
        assert isinstance(parser_prompts, dict)
        assert "system" in parser_prompts
        assert "instructions" in parser_prompts

        # Test individual prompt getters
        system_prompt = AgentPrompts.get_system_prompt("parser")
        assert isinstance(system_prompt, str)
        assert len(system_prompt) > 0

        instructions = AgentPrompts.get_instructions("parser")
        assert isinstance(instructions, str)
        assert len(instructions) > 0

        # Test with dummy data
        dummy_data = {
            "question": "What is AI?",
            "context": "AI is artificial intelligence",
        }
        formatted_prompt = parser_prompts["system"].format(**dummy_data)
        assert isinstance(formatted_prompt, str)
        assert len(formatted_prompt) > 0
