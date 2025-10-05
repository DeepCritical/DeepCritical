"""
VLLM-based tests for research_planner.py prompts.

This module tests all prompts defined in the research_planner module using VLLM containers.
These tests are optional and disabled in CI by default.
"""

import pytest
from scripts.prompt_testing.test_prompts_vllm_base import VLLMPromptTestBase

class TestResearchPlannerPromptsVLLM(VLLMPromptTestBase):
    """Test research_planner.py prompts with VLLM."""

    @pytest.mark.vllm
    @pytest.mark.optional
    def test_research_planner_prompts_vllm(self, vllm_tester):
        """Test all prompts from research_planner module with VLLM."""
        results = self.run_module_prompt_tests(
            "research_planner",
            vllm_tester,
            max_tokens=256,
            temperature=0.7
        )

        self.assert_prompt_test_success(results, min_success_rate=0.8)
        assert len(results) > 0, "No prompts were tested from research_planner module"



