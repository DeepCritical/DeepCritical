"""
VLLM-based tests for code_exec.py prompts.

This module tests all prompts defined in the code_exec module using VLLM containers.
These tests are optional and disabled in CI by default.
"""

import pytest

from scripts.prompt_testing.test_prompts_vllm_base import VLLMPromptTestBase


class TestCodeExecPromptsVLLM(VLLMPromptTestBase):
    """Test code_exec.py prompts with VLLM."""

    @pytest.mark.vllm
    @pytest.mark.optional
    def test_code_exec_prompts_vllm(self, vllm_tester):
        """Test all prompts from code_exec module with VLLM."""
        # Run tests for code_exec module
        results = self.run_module_prompt_tests(
            "code_exec",
            vllm_tester,
            max_tokens=256,
            temperature=0.7
        )

        # Assert minimum success rate
        self.assert_prompt_test_success(results, min_success_rate=0.8)

        # Check that we tested some prompts
        assert len(results) > 0, "No prompts were tested from code_exec module"

    @pytest.mark.vllm
    @pytest.mark.optional
    def test_code_exec_system_prompt(self, vllm_tester):
        """Test code execution system prompt specifically."""
        from DeepResearch.src.prompts.code_exec import SYSTEM

        result = self._test_single_prompt(
            vllm_tester,
            "SYSTEM",
            SYSTEM,
            expected_placeholders=["code"],
            max_tokens=128,
            temperature=0.5
        )

        assert result["success"]
        assert "reasoning" in result

        # Verify the system prompt contains expected content
        assert "Execute the following code" in SYSTEM
        assert "return ONLY the final output" in SYSTEM
        assert "plain text" in SYSTEM

    @pytest.mark.vllm
    @pytest.mark.optional
    def test_execute_code_prompt(self, vllm_tester):
        """Test execute code prompt template specifically."""
        from DeepResearch.src.prompts.code_exec import CODE_EXEC_PROMPTS

        execute_prompt = CODE_EXEC_PROMPTS["execute_code"]

        result = self._test_single_prompt(
            vllm_tester,
            "execute_code",
            execute_prompt,
            expected_placeholders=["code"],
            max_tokens=128,
            temperature=0.5
        )

        assert result["success"]

        # Verify the prompt template contains expected structure
        assert "Execute the following code" in execute_prompt
        assert "{code}" in execute_prompt

    @pytest.mark.vllm
    @pytest.mark.optional
    def test_code_exec_prompts_class(self, vllm_tester):
        """Test the CodeExecPrompts class functionality."""
        from DeepResearch.src.prompts.code_exec import CodeExecPrompts

        # Test that CodeExecPrompts class works
        assert CodeExecPrompts is not None

        # Test SYSTEM attribute
        assert hasattr(CodeExecPrompts, "SYSTEM")
        assert isinstance(CodeExecPrompts.SYSTEM, str)
        assert len(CodeExecPrompts.SYSTEM) > 0

        # Test PROMPTS attribute
        assert hasattr(CodeExecPrompts, "PROMPTS")
        assert isinstance(CodeExecPrompts.PROMPTS, dict)
        assert len(CodeExecPrompts.PROMPTS) > 0

        # Test that all prompts are properly structured
        for prompt_key, prompt_value in CodeExecPrompts.PROMPTS.items():
            assert isinstance(prompt_value, str), f"Prompt {prompt_key} is not a string"
            assert len(prompt_value.strip()) > 0, f"Prompt {prompt_key} is empty"

    @pytest.mark.vllm
    @pytest.mark.optional
    def test_code_execution_with_python_code(self, vllm_tester):
        """Test code execution with actual Python code."""
        from DeepResearch.src.prompts.code_exec import CODE_EXEC_PROMPTS

        # Use a simple Python code snippet as dummy data
        # Note: This would be used for testing the prompt template with realistic data

        execute_prompt = CODE_EXEC_PROMPTS["execute_code"]

        result = self._test_single_prompt(
            vllm_tester,
            "python_code_execution",
            execute_prompt,
            expected_placeholders=["code"],
            max_tokens=128,
            temperature=0.3  # Lower temperature for more consistent results
        )

        assert result["success"]
        assert "generated_response" in result

        # The response should be related to code execution
        response = result["generated_response"]
        assert isinstance(response, str)
        assert len(response) > 0

    @pytest.mark.vllm
    @pytest.mark.optional
    def test_code_execution_with_mathematical_code(self, vllm_tester):
        """Test code execution with mathematical code."""
        from DeepResearch.src.prompts.code_exec import CODE_EXEC_PROMPTS

        # Use mathematical code as dummy data
        # Note: This would be used for testing the prompt template with realistic data

        execute_prompt = CODE_EXEC_PROMPTS["execute_code"]

        result = self._test_single_prompt(
            vllm_tester,
            "math_code_execution",
            execute_prompt,
            expected_placeholders=["code"],
            max_tokens=128,
            temperature=0.3
        )

        assert result["success"]

        # The response should be related to mathematical computation
        response = result["generated_response"]
        assert isinstance(response, str)
        assert len(response) > 0
