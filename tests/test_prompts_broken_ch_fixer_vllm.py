"""
VLLM-based tests for broken_ch_fixer.py prompts.

This module tests all prompts defined in the broken_ch_fixer module using VLLM containers.
These tests are optional and disabled in CI by default.
"""

import pytest

from scripts.prompt_testing.test_prompts_vllm_base import VLLMPromptTestBase


class TestBrokenCHFixerPromptsVLLM(VLLMPromptTestBase):
    """Test broken_ch_fixer.py prompts with VLLM."""

    @pytest.mark.vllm
    @pytest.mark.optional
    def test_broken_ch_fixer_prompts_vllm(self, vllm_tester):
        """Test all prompts from broken_ch_fixer module with VLLM."""
        # Run tests for broken_ch_fixer module
        results = self.run_module_prompt_tests(
            "broken_ch_fixer", vllm_tester, max_tokens=256, temperature=0.7
        )

        # Assert minimum success rate
        self.assert_prompt_test_success(results, min_success_rate=0.8)

        # Check that we tested some prompts
        assert len(results) > 0, "No prompts were tested from broken_ch_fixer module"

    @pytest.mark.vllm
    @pytest.mark.optional
    def test_broken_ch_fixer_system_prompt(self, vllm_tester):
        """Test broken character fixer system prompt specifically."""
        from DeepResearch.src.prompts.broken_ch_fixer import SYSTEM

        result = self._test_single_prompt(
            vllm_tester, "SYSTEM", SYSTEM, max_tokens=128, temperature=0.5
        )

        assert result["success"]
        assert "reasoning" in result

        # Verify the system prompt contains expected content
        assert "corrupted scanned markdown document" in SYSTEM.lower()
        assert "stains" in SYSTEM.lower()
        assert "represented by" in SYSTEM.lower()

    @pytest.mark.vllm
    @pytest.mark.optional
    def test_fix_broken_characters_prompt(self, vllm_tester):
        """Test fix broken characters prompt template specifically."""
        from DeepResearch.src.prompts.broken_ch_fixer import BROKEN_CH_FIXER_PROMPTS

        fix_prompt = BROKEN_CH_FIXER_PROMPTS["fix_broken_characters"]

        result = self._test_single_prompt(
            vllm_tester,
            "fix_broken_characters",
            fix_prompt,
            expected_placeholders=["text"],
            max_tokens=128,
            temperature=0.5,
        )

        assert result["success"]

        # Verify the prompt template contains expected structure
        assert "Fix the broken characters" in fix_prompt
        assert "{text}" in fix_prompt

    @pytest.mark.vllm
    @pytest.mark.optional
    def test_broken_ch_fixer_prompts_class(self, vllm_tester):
        """Test the BrokenCHFixerPrompts class functionality."""
        from DeepResearch.src.prompts.broken_ch_fixer import BrokenCHFixerPrompts

        # Test that BrokenCHFixerPrompts class works
        assert BrokenCHFixerPrompts is not None

        # Test SYSTEM attribute
        assert hasattr(BrokenCHFixerPrompts, "SYSTEM")
        assert isinstance(BrokenCHFixerPrompts.SYSTEM, str)
        assert len(BrokenCHFixerPrompts.SYSTEM) > 0

        # Test PROMPTS attribute
        assert hasattr(BrokenCHFixerPrompts, "PROMPTS")
        assert isinstance(BrokenCHFixerPrompts.PROMPTS, dict)
        assert len(BrokenCHFixerPrompts.PROMPTS) > 0

        # Test that all prompts are properly structured
        for prompt_key, prompt_value in BrokenCHFixerPrompts.PROMPTS.items():
            assert isinstance(prompt_value, str), f"Prompt {prompt_key} is not a string"
            assert len(prompt_value.strip()) > 0, f"Prompt {prompt_key} is empty"

    @pytest.mark.vllm
    @pytest.mark.optional
    def test_broken_character_fixing_with_dummy_data(self, vllm_tester):
        """Test broken character fixing with realistic dummy data."""
        from DeepResearch.src.prompts.broken_ch_fixer import BROKEN_CH_FIXER_PROMPTS

        # Create dummy text with "broken" characters (represented by �)
        # Note: This would be used for testing the prompt template with realistic data

        fix_prompt = BROKEN_CH_FIXER_PROMPTS["fix_broken_characters"]

        result = self._test_single_prompt(
            vllm_tester,
            "broken_character_fixing",
            fix_prompt,
            expected_placeholders=["text"],
            max_tokens=128,
            temperature=0.3,  # Lower temperature for more consistent results
        )

        assert result["success"]
        assert "generated_response" in result

        # The response should be a reasonable attempt to fix the broken characters
        response = result["generated_response"]
        assert isinstance(response, str)
        assert len(response) > 0

        # Should not contain the � characters in the final output (as per the system prompt)
        assert "�" not in response, (
            "Response should not contain broken character symbols"
        )
