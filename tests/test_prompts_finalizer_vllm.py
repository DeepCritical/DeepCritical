"""
VLLM-based tests for finalizer.py prompts.

This module tests all prompts defined in the finalizer module using VLLM containers.
These tests are optional and disabled in CI by default.
"""

import pytest

from scripts.prompt_testing.test_prompts_vllm_base import VLLMPromptTestBase


class TestFinalizerPromptsVLLM(VLLMPromptTestBase):
    """Test finalizer.py prompts with VLLM."""

    @pytest.mark.vllm
    @pytest.mark.optional
    def test_finalizer_prompts_vllm(self, vllm_tester):
        """Test all prompts from finalizer module with VLLM."""
        # Run tests for finalizer module
        results = self.run_module_prompt_tests(
            "finalizer",
            vllm_tester,
            max_tokens=256,
            temperature=0.7
        )

        # Assert minimum success rate
        self.assert_prompt_test_success(results, min_success_rate=0.8)

        # Check that we tested some prompts
        assert len(results) > 0, "No prompts were tested from finalizer module"

    @pytest.mark.vllm
    @pytest.mark.optional
    def test_finalizer_system_prompt(self, vllm_tester):
        """Test finalizer system prompt specifically."""
        from DeepResearch.src.prompts.finalizer import SYSTEM

        result = self._test_single_prompt(
            vllm_tester,
            "SYSTEM",
            SYSTEM,
            expected_placeholders=["knowledge_str", "language_style"],
            max_tokens=128,
            temperature=0.5
        )

        assert result["success"]
        assert "reasoning" in result

    @pytest.mark.vllm
    @pytest.mark.optional
    def test_finalizer_prompts_class(self, vllm_tester):
        """Test the FinalizerPrompts class functionality."""
        from DeepResearch.src.prompts.finalizer import FinalizerPrompts

        # Test that FinalizerPrompts class works
        assert FinalizerPrompts is not None

        # Test SYSTEM attribute
        assert hasattr(FinalizerPrompts, "SYSTEM")
        assert isinstance(FinalizerPrompts.SYSTEM, str)

        # Test PROMPTS attribute
        assert hasattr(FinalizerPrompts, "PROMPTS")
        assert isinstance(FinalizerPrompts.PROMPTS, dict)
