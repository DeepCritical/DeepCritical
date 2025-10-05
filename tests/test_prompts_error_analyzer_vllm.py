"""
VLLM-based tests for error_analyzer.py prompts.

This module tests all prompts defined in the error_analyzer module using VLLM containers.
These tests are optional and disabled in CI by default.
"""

import pytest

from scripts.prompt_testing.test_prompts_vllm_base import VLLMPromptTestBase


class TestErrorAnalyzerPromptsVLLM(VLLMPromptTestBase):
    """Test error_analyzer.py prompts with VLLM."""

    @pytest.mark.vllm
    @pytest.mark.optional
    def test_error_analyzer_prompts_vllm(self, vllm_tester):
        """Test all prompts from error_analyzer module with VLLM."""
        # Run tests for error_analyzer module
        results = self.run_module_prompt_tests(
            "error_analyzer",
            vllm_tester,
            max_tokens=256,
            temperature=0.7
        )

        # Assert minimum success rate
        self.assert_prompt_test_success(results, min_success_rate=0.8)

        # Check that we tested some prompts
        assert len(results) > 0, "No prompts were tested from error_analyzer module"

    @pytest.mark.vllm
    @pytest.mark.optional
    def test_error_analyzer_system_prompt(self, vllm_tester):
        """Test error analyzer system prompt specifically."""
        from DeepResearch.src.prompts.error_analyzer import SYSTEM

        result = self._test_single_prompt(
            vllm_tester,
            "SYSTEM",
            SYSTEM,
            expected_placeholders=["error_sequence"],
            max_tokens=128,
            temperature=0.5
        )

        assert result["success"]
        assert "reasoning" in result

        # Verify the system prompt contains expected content
        assert "expert at analyzing search and reasoning processes" in SYSTEM.lower()
        assert "sequence of steps" in SYSTEM.lower()
        assert "what went wrong" in SYSTEM.lower()

    @pytest.mark.vllm
    @pytest.mark.optional
    def test_analyze_error_prompt(self, vllm_tester):
        """Test analyze error prompt template specifically."""
        from DeepResearch.src.prompts.error_analyzer import ERROR_ANALYZER_PROMPTS

        analyze_prompt = ERROR_ANALYZER_PROMPTS["analyze_error"]

        result = self._test_single_prompt(
            vllm_tester,
            "analyze_error",
            analyze_prompt,
            expected_placeholders=["error_sequence"],
            max_tokens=128,
            temperature=0.5
        )

        assert result["success"]

        # Verify the prompt template contains expected structure
        assert "Analyze the following error sequence" in analyze_prompt
        assert "{error_sequence}" in analyze_prompt

    @pytest.mark.vllm
    @pytest.mark.optional
    def test_error_analyzer_prompts_class(self, vllm_tester):
        """Test the ErrorAnalyzerPrompts class functionality."""
        from DeepResearch.src.prompts.error_analyzer import ErrorAnalyzerPrompts

        # Test that ErrorAnalyzerPrompts class works
        assert ErrorAnalyzerPrompts is not None

        # Test SYSTEM attribute
        assert hasattr(ErrorAnalyzerPrompts, "SYSTEM")
        assert isinstance(ErrorAnalyzerPrompts.SYSTEM, str)
        assert len(ErrorAnalyzerPrompts.SYSTEM) > 0

        # Test PROMPTS attribute
        assert hasattr(ErrorAnalyzerPrompts, "PROMPTS")
        assert isinstance(ErrorAnalyzerPrompts.PROMPTS, dict)
        assert len(ErrorAnalyzerPrompts.PROMPTS) > 0

        # Test that all prompts are properly structured
        for prompt_key, prompt_value in ErrorAnalyzerPrompts.PROMPTS.items():
            assert isinstance(prompt_value, str), f"Prompt {prompt_key} is not a string"
            assert len(prompt_value.strip()) > 0, f"Prompt {prompt_key} is empty"

    @pytest.mark.vllm
    @pytest.mark.optional
    def test_error_analysis_with_search_sequence(self, vllm_tester):
        """Test error analysis with a realistic search sequence."""
        from DeepResearch.src.prompts.error_analyzer import ERROR_ANALYZER_PROMPTS

        # Create a realistic error sequence for testing
        # Note: This would be used for testing the prompt template with realistic data

        analyze_prompt = ERROR_ANALYZER_PROMPTS["analyze_error"]

        result = self._test_single_prompt(
            vllm_tester,
            "search_error_analysis",
            analyze_prompt,
            expected_placeholders=["error_sequence"],
            max_tokens=128,
            temperature=0.3  # Lower temperature for more focused analysis
        )

        assert result["success"]
        assert "generated_response" in result

        # The response should be related to error analysis
        response = result["generated_response"]
        assert isinstance(response, str)
        assert len(response) > 0

        # Should contain analysis-related keywords
        analysis_keywords = ["analysis", "problem", "issue", "failed", "wrong", "improve"]
        has_analysis_keywords = any(keyword in response.lower() for keyword in analysis_keywords)
        assert has_analysis_keywords, "Response should contain analysis-related keywords"

    @pytest.mark.vllm
    @pytest.mark.optional
    def test_system_prompt_structure_validation(self, vllm_tester):
        """Test that the system prompt has proper structure and rules."""
        from DeepResearch.src.prompts.error_analyzer import SYSTEM

        # Verify the system prompt contains all expected sections
        assert "<rules>" in SYSTEM
        assert "sequence of actions" in SYSTEM.lower()
        assert "effectiveness of each step" in SYSTEM.lower()
        assert "alternative approaches" in SYSTEM.lower()
        assert "recap:" in SYSTEM.lower()
        assert "blame:" in SYSTEM.lower()
        assert "improvement:" in SYSTEM.lower()

        # Test the prompt formatting
        result = self._test_single_prompt(
            vllm_tester,
            "system_prompt_validation",
            SYSTEM,
            max_tokens=64,
            temperature=0.1  # Very low temperature for predictable output
        )

        assert result["success"]
