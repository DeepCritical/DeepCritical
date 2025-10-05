"""
VLLM-based tests for deep_agent_prompts.py prompts.

This module tests all prompts defined in the deep_agent_prompts module using VLLM containers.
These tests are optional and disabled in CI by default.
"""

import pytest

from scripts.prompt_testing.test_prompts_vllm_base import VLLMPromptTestBase


class TestDeepAgentPromptsVLLM(VLLMPromptTestBase):
    """Test deep_agent_prompts.py prompts with VLLM."""

    @pytest.mark.vllm
    @pytest.mark.optional
    def test_deep_agent_prompts_vllm(self, vllm_tester):
        """Test all prompts from deep_agent_prompts module with VLLM."""
        # Run tests for deep_agent_prompts module
        results = self.run_module_prompt_tests(
            "deep_agent_prompts",
            vllm_tester,
            max_tokens=256,
            temperature=0.7
        )

        # Assert minimum success rate
        self.assert_prompt_test_success(results, min_success_rate=0.8)

        # Check that we tested some prompts
        assert len(results) > 0, "No prompts were tested from deep_agent_prompts module"

    @pytest.mark.vllm
    @pytest.mark.optional
    def test_deep_agent_prompts_constants(self, vllm_tester):
        """Test DEEP_AGENT_PROMPTS constant specifically."""
        from DeepResearch.src.prompts.deep_agent_prompts import DEEP_AGENT_PROMPTS

        # Test that DEEP_AGENT_PROMPTS is accessible and properly structured
        assert DEEP_AGENT_PROMPTS is not None
        assert isinstance(DEEP_AGENT_PROMPTS, dict)
        assert len(DEEP_AGENT_PROMPTS) > 0

        # Test individual prompts
        for prompt_key, prompt_value in DEEP_AGENT_PROMPTS.items():
            assert isinstance(prompt_value, str), f"Prompt {prompt_key} is not a string"
            assert len(prompt_value.strip()) > 0, f"Prompt {prompt_key} is empty"

        # Test that prompts contain expected placeholders
        system_prompt = DEEP_AGENT_PROMPTS.get("system", "")
        assert "{task_description}" in system_prompt or "task_description" in system_prompt

        reasoning_prompt = DEEP_AGENT_PROMPTS.get("reasoning", "")
        assert "{query}" in reasoning_prompt or "query" in reasoning_prompt

    @pytest.mark.vllm
    @pytest.mark.optional
    def test_system_prompt(self, vllm_tester):
        """Test system prompt specifically."""
        from DeepResearch.src.prompts.deep_agent_prompts import DEEP_AGENT_PROMPTS

        system_prompt = DEEP_AGENT_PROMPTS["system"]

        result = self._test_single_prompt(
            vllm_tester,
            "system",
            system_prompt,
            expected_placeholders=["task_description"],
            max_tokens=128,
            temperature=0.5
        )

        assert result["success"]
        assert "reasoning" in result

        # Verify the system prompt contains expected content
        assert "DeepAgent" in system_prompt
        assert "complex reasoning" in system_prompt.lower()
        assert "task execution" in system_prompt.lower()

    @pytest.mark.vllm
    @pytest.mark.optional
    def test_task_execution_prompt(self, vllm_tester):
        """Test task execution prompt specifically."""
        from DeepResearch.src.prompts.deep_agent_prompts import DEEP_AGENT_PROMPTS

        task_prompt = DEEP_AGENT_PROMPTS["task_execution"]

        result = self._test_single_prompt(
            vllm_tester,
            "task_execution",
            task_prompt,
            expected_placeholders=["task_description"],
            max_tokens=128,
            temperature=0.5
        )

        assert result["success"]

        # Verify the prompt template contains expected structure
        assert "Execute the following task" in task_prompt
        assert "{task_description}" in task_prompt

    @pytest.mark.vllm
    @pytest.mark.optional
    def test_reasoning_prompt(self, vllm_tester):
        """Test reasoning prompt specifically."""
        from DeepResearch.src.prompts.deep_agent_prompts import DEEP_AGENT_PROMPTS

        reasoning_prompt = DEEP_AGENT_PROMPTS["reasoning"]

        result = self._test_single_prompt(
            vllm_tester,
            "reasoning",
            reasoning_prompt,
            expected_placeholders=["query"],
            max_tokens=128,
            temperature=0.5
        )

        assert result["success"]

        # Verify the prompt template contains expected structure
        assert "Reason step by step" in reasoning_prompt
        assert "{query}" in reasoning_prompt

    @pytest.mark.vllm
    @pytest.mark.optional
    def test_deep_agent_prompts_class(self, vllm_tester):
        """Test the DeepAgentPrompts class functionality."""
        from DeepResearch.src.prompts.deep_agent_prompts import DeepAgentPrompts

        # Test that DeepAgentPrompts class works
        assert DeepAgentPrompts is not None

        # Test PROMPTS attribute
        assert hasattr(DeepAgentPrompts, "PROMPTS")
        assert isinstance(DeepAgentPrompts.PROMPTS, dict)
        assert len(DeepAgentPrompts.PROMPTS) > 0

        # Test that all prompts are properly structured
        for prompt_key, prompt_value in DeepAgentPrompts.PROMPTS.items():
            assert isinstance(prompt_value, str), f"Prompt {prompt_key} is not a string"
            assert len(prompt_value.strip()) > 0, f"Prompt {prompt_key} is empty"

    @pytest.mark.vllm
    @pytest.mark.optional
    def test_prompt_template_class(self, vllm_tester):
        """Test the PromptTemplate class functionality."""
        from DeepResearch.src.prompts.deep_agent_prompts import PromptTemplate, PromptType

        # Test PromptTemplate instantiation
        template = PromptTemplate(
            name="test_template",
            template="This is a test template with {variable}",
            variables=["variable"],
            prompt_type=PromptType.SYSTEM
        )

        assert template.name == "test_template"
        assert template.template == "This is a test template with {variable}"
        assert template.variables == ["variable"]
        assert template.prompt_type == PromptType.SYSTEM

        # Test template formatting
        formatted = template.format(variable="test_value")
        assert formatted == "This is a test template with test_value"

        # Test validation
        try:
            PromptTemplate(
                name="",
                template="",
                variables=[],
                prompt_type=PromptType.SYSTEM
            )
            assert False, "Should have raised validation error"
        except ValueError:
            pass  # Expected

    @pytest.mark.vllm
    @pytest.mark.optional
    def test_prompt_manager_functionality(self, vllm_tester):
        """Test the PromptManager class functionality."""
        from DeepResearch.src.prompts.deep_agent_prompts import PromptManager

        # Test PromptManager instantiation
        manager = PromptManager()
        assert manager is not None
        assert isinstance(manager.templates, dict)

        # Test template registration and retrieval
        # Template might not exist, but the manager should work
        PromptManager().templates.get("test_template")  # Just test that it doesn't crash

        # Test system prompt generation (basic functionality)
        system_prompt = manager.get_system_prompt(["base_agent"])
        # This might return empty if templates aren't loaded, but shouldn't error
        assert isinstance(system_prompt, str)
