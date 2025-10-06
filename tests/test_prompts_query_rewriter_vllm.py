"""
VLLM-based tests for query_rewriter.py prompts.

This module tests all prompts defined in the query_rewriter module using VLLM containers.
These tests are optional and disabled in CI by default.
"""

import pytest
from scripts.prompt_testing.test_prompts_vllm_base import VLLMPromptTestBase


class TestQueryRewriterPromptsVLLM(VLLMPromptTestBase):
    """Test query_rewriter.py prompts with VLLM."""

    @pytest.mark.vllm
    @pytest.mark.optional
    def test_query_rewriter_prompts_vllm(self, vllm_tester):
        """Test all prompts from query_rewriter module with VLLM."""
        results = self.run_module_prompt_tests(
            "query_rewriter", vllm_tester, max_tokens=256, temperature=0.7
        )

        self.assert_prompt_test_success(results, min_success_rate=0.8)
        assert len(results) > 0, "No prompts were tested from query_rewriter module"
