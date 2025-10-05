"""
VLLM-based tests for code_sandbox.py prompts.

This module tests all prompts defined in the code_sandbox module using VLLM containers.
These tests are optional and disabled in CI by default.
"""

import pytest

from scripts.prompt_testing.test_prompts_vllm_base import VLLMPromptTestBase


class TestCodeSandboxPromptsVLLM(VLLMPromptTestBase):
    """Test code_sandbox.py prompts with VLLM."""

    @pytest.mark.vllm
    @pytest.mark.optional
    def test_code_sandbox_prompts_vllm(self, vllm_tester):
        """Test all prompts from code_sandbox module with VLLM."""
        # Run tests for code_sandbox module
        results = self.run_module_prompt_tests(
            "code_sandbox",
            vllm_tester,
            max_tokens=256,
            temperature=0.7
        )

        # Assert minimum success rate
        self.assert_prompt_test_success(results, min_success_rate=0.8)

        # Check that we tested some prompts
        assert len(results) > 0, "No prompts were tested from code_sandbox module"

    @pytest.mark.vllm
    @pytest.mark.optional
    def test_code_sandbox_system_prompt(self, vllm_tester):
        """Test code sandbox system prompt specifically."""
        from DeepResearch.src.prompts.code_sandbox import SYSTEM

        result = self._test_single_prompt(
            vllm_tester,
            "SYSTEM",
            SYSTEM,
            expected_placeholders=["available_vars"],
            max_tokens=128,
            temperature=0.5
        )

        assert result["success"]
        assert "reasoning" in result

        # Verify the system prompt contains expected content
        assert "expert JavaScript programmer" in SYSTEM.lower()
        assert "Generate plain JavaScript code" in SYSTEM
        assert "return the result directly" in SYSTEM

    @pytest.mark.vllm
    @pytest.mark.optional
    def test_generate_code_prompt(self, vllm_tester):
        """Test generate code prompt template specifically."""
        from DeepResearch.src.prompts.code_sandbox import CODE_SANDBOX_PROMPTS

        generate_prompt = CODE_SANDBOX_PROMPTS["generate_code"]

        result = self._test_single_prompt(
            vllm_tester,
            "generate_code",
            generate_prompt,
            expected_placeholders=["available_vars"],
            max_tokens=128,
            temperature=0.5
        )

        assert result["success"]

        # Verify the prompt template contains expected structure
        assert "Generate JavaScript code" in generate_prompt
        assert "{available_vars}" in generate_prompt

    @pytest.mark.vllm
    @pytest.mark.optional
    def test_code_sandbox_prompts_class(self, vllm_tester):
        """Test the CodeSandboxPrompts class functionality."""
        from DeepResearch.src.prompts.code_sandbox import CodeSandboxPrompts

        # Test that CodeSandboxPrompts class works
        assert CodeSandboxPrompts is not None

        # Test SYSTEM attribute
        assert hasattr(CodeSandboxPrompts, "SYSTEM")
        assert isinstance(CodeSandboxPrompts.SYSTEM, str)
        assert len(CodeSandboxPrompts.SYSTEM) > 0

        # Test PROMPTS attribute
        assert hasattr(CodeSandboxPrompts, "PROMPTS")
        assert isinstance(CodeSandboxPrompts.PROMPTS, dict)
        assert len(CodeSandboxPrompts.PROMPTS) > 0

        # Test that all prompts are properly structured
        for prompt_key, prompt_value in CodeSandboxPrompts.PROMPTS.items():
            assert isinstance(prompt_value, str), f"Prompt {prompt_key} is not a string"
            assert len(prompt_value.strip()) > 0, f"Prompt {prompt_key} is empty"

    @pytest.mark.vllm
    @pytest.mark.optional
    def test_javascript_code_generation(self, vllm_tester):
        """Test JavaScript code generation with realistic variables."""
        from DeepResearch.src.prompts.code_sandbox import CODE_SANDBOX_PROMPTS

        # Use realistic available variables for JavaScript code generation
        # Note: This would be used for testing the prompt template with realistic data

        generate_prompt = CODE_SANDBOX_PROMPTS["generate_code"]

        result = self._test_single_prompt(
            vllm_tester,
            "javascript_code_generation",
            generate_prompt,
            expected_placeholders=["available_vars"],
            max_tokens=128,
            temperature=0.3  # Lower temperature for more consistent results
        )

        assert result["success"]
        assert "generated_response" in result

        # The response should be related to JavaScript code generation
        response = result["generated_response"]
        assert isinstance(response, str)
        assert len(response) > 0

    @pytest.mark.vllm
    @pytest.mark.optional
    def test_code_generation_with_mathematical_problem(self, vllm_tester):
        """Test code generation for a mathematical problem."""
        from DeepResearch.src.prompts.code_sandbox import CODE_SANDBOX_PROMPTS

        # Test with a mathematical problem scenario
        # Note: This would be used for testing the prompt template with realistic data

        generate_prompt = CODE_SANDBOX_PROMPTS["generate_code"]

        result = self._test_single_prompt(
            vllm_tester,
            "math_code_generation",
            generate_prompt,
            expected_placeholders=["available_vars"],
            max_tokens=128,
            temperature=0.3
        )

        assert result["success"]

        # The response should be a valid JavaScript code snippet
        response = result["generated_response"]
        assert isinstance(response, str)
        assert len(response) > 0

    @pytest.mark.vllm
    @pytest.mark.optional
    def test_system_prompt_structure_validation(self, vllm_tester):
        """Test that the system prompt has proper structure and rules."""
        from DeepResearch.src.prompts.code_sandbox import SYSTEM

        # Verify the system prompt contains all expected sections
        assert "<rules>" in SYSTEM
        assert "<example>" in SYSTEM
        assert "Generate plain JavaScript code" in SYSTEM
        assert "return statement" in SYSTEM
        assert "self-contained code" in SYSTEM

        # Test the prompt formatting
        result = self._test_single_prompt(
            vllm_tester,
            "system_prompt_validation",
            SYSTEM,
            max_tokens=64,
            temperature=0.1  # Very low temperature for predictable output
        )

        assert result["success"]
