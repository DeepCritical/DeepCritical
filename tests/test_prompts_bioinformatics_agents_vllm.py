"""
VLLM-based tests for bioinformatics_agents.py prompts.

This module tests all prompts defined in the bioinformatics_agents module using VLLM containers.
These tests are optional and disabled in CI by default.
"""

import pytest

from scripts.prompt_testing.test_prompts_vllm_base import VLLMPromptTestBase


class TestBioinformaticsAgentsPromptsVLLM(VLLMPromptTestBase):
    """Test bioinformatics_agents.py prompts with VLLM."""

    @pytest.mark.vllm
    @pytest.mark.optional
    def test_bioinformatics_agents_prompts_vllm(self, vllm_tester):
        """Test all prompts from bioinformatics_agents module with VLLM."""
        # Run tests for bioinformatics_agents module
        results = self.run_module_prompt_tests(
            "bioinformatics_agents", vllm_tester, max_tokens=256, temperature=0.7
        )

        # Assert minimum success rate
        self.assert_prompt_test_success(results, min_success_rate=0.8)

        # Check that we tested some prompts
        assert (
            len(results) > 0
        ), "No prompts were tested from bioinformatics_agents module"

    @pytest.mark.vllm
    @pytest.mark.optional
    def test_data_fusion_system_prompt(self, vllm_tester):
        """Test data fusion system prompt specifically."""
        from DeepResearch.src.prompts.bioinformatics_agents import (
            DATA_FUSION_SYSTEM_PROMPT,
        )

        result = self._test_single_prompt(
            vllm_tester,
            "DATA_FUSION_SYSTEM_PROMPT",
            DATA_FUSION_SYSTEM_PROMPT,
            expected_placeholders=["fusion_type", "source_databases"],
            max_tokens=128,
            temperature=0.5,
        )

        assert result["success"]
        assert "reasoning" in result

    @pytest.mark.vllm
    @pytest.mark.optional
    def test_go_annotation_system_prompt(self, vllm_tester):
        """Test GO annotation system prompt specifically."""
        from DeepResearch.src.prompts.bioinformatics_agents import (
            GO_ANNOTATION_SYSTEM_PROMPT,
        )

        result = self._test_single_prompt(
            vllm_tester,
            "GO_ANNOTATION_SYSTEM_PROMPT",
            GO_ANNOTATION_SYSTEM_PROMPT,
            max_tokens=128,
            temperature=0.5,
        )

        assert result["success"]

    @pytest.mark.vllm
    @pytest.mark.optional
    def test_reasoning_system_prompt(self, vllm_tester):
        """Test reasoning system prompt specifically."""
        from DeepResearch.src.prompts.bioinformatics_agents import (
            REASONING_SYSTEM_PROMPT,
        )

        result = self._test_single_prompt(
            vllm_tester,
            "REASONING_SYSTEM_PROMPT",
            REASONING_SYSTEM_PROMPT,
            expected_placeholders=["task_type", "question"],
            max_tokens=128,
            temperature=0.5,
        )

        assert result["success"]

    @pytest.mark.vllm
    @pytest.mark.optional
    def test_data_quality_system_prompt(self, vllm_tester):
        """Test data quality system prompt specifically."""
        from DeepResearch.src.prompts.bioinformatics_agents import (
            DATA_QUALITY_SYSTEM_PROMPT,
        )

        result = self._test_single_prompt(
            vllm_tester,
            "DATA_QUALITY_SYSTEM_PROMPT",
            DATA_QUALITY_SYSTEM_PROMPT,
            max_tokens=128,
            temperature=0.5,
        )

        assert result["success"]

    @pytest.mark.vllm
    @pytest.mark.optional
    def test_data_fusion_prompt_template(self, vllm_tester):
        """Test data fusion prompt template specifically."""
        from DeepResearch.src.prompts.bioinformatics_agents import (
            BIOINFORMATICS_AGENT_PROMPTS,
        )

        data_fusion_prompt = BIOINFORMATICS_AGENT_PROMPTS["data_fusion"]

        result = self._test_single_prompt(
            vllm_tester,
            "data_fusion_template",
            data_fusion_prompt,
            expected_placeholders=["fusion_type", "source_databases", "filters"],
            max_tokens=128,
            temperature=0.5,
        )

        assert result["success"]

    @pytest.mark.vllm
    @pytest.mark.optional
    def test_go_annotation_processing_template(self, vllm_tester):
        """Test GO annotation processing prompt template specifically."""
        from DeepResearch.src.prompts.bioinformatics_agents import (
            BIOINFORMATICS_AGENT_PROMPTS,
        )

        go_processing_prompt = BIOINFORMATICS_AGENT_PROMPTS["go_annotation_processing"]

        result = self._test_single_prompt(
            vllm_tester,
            "go_annotation_processing_template",
            go_processing_prompt,
            expected_placeholders=["annotation_count", "paper_count"],
            max_tokens=128,
            temperature=0.5,
        )

        assert result["success"]

    @pytest.mark.vllm
    @pytest.mark.optional
    def test_reasoning_task_template(self, vllm_tester):
        """Test reasoning task prompt template specifically."""
        from DeepResearch.src.prompts.bioinformatics_agents import (
            BIOINFORMATICS_AGENT_PROMPTS,
        )

        reasoning_prompt = BIOINFORMATICS_AGENT_PROMPTS["reasoning_task"]

        result = self._test_single_prompt(
            vllm_tester,
            "reasoning_task_template",
            reasoning_prompt,
            expected_placeholders=["task_type", "question", "dataset_name"],
            max_tokens=128,
            temperature=0.5,
        )

        assert result["success"]

    @pytest.mark.vllm
    @pytest.mark.optional
    def test_quality_assessment_template(self, vllm_tester):
        """Test quality assessment prompt template specifically."""
        from DeepResearch.src.prompts.bioinformatics_agents import (
            BIOINFORMATICS_AGENT_PROMPTS,
        )

        quality_prompt = BIOINFORMATICS_AGENT_PROMPTS["quality_assessment"]

        result = self._test_single_prompt(
            vllm_tester,
            "quality_assessment_template",
            quality_prompt,
            expected_placeholders=["dataset_name", "source_databases"],
            max_tokens=128,
            temperature=0.5,
        )

        assert result["success"]

    @pytest.mark.vllm
    @pytest.mark.optional
    def test_bioinformatics_agent_prompts_class(self, vllm_tester):
        """Test the BioinformaticsAgentPrompts class functionality."""
        from DeepResearch.src.prompts.bioinformatics_agents import (
            BioinformaticsAgentPrompts,
        )

        # Test that BioinformaticsAgentPrompts class works
        assert BioinformaticsAgentPrompts is not None

        # Test system prompts
        assert hasattr(BioinformaticsAgentPrompts, "DATA_FUSION_SYSTEM")
        assert hasattr(BioinformaticsAgentPrompts, "GO_ANNOTATION_SYSTEM")
        assert hasattr(BioinformaticsAgentPrompts, "REASONING_SYSTEM")
        assert hasattr(BioinformaticsAgentPrompts, "DATA_QUALITY_SYSTEM")

        # Test that system prompts are strings
        assert isinstance(BioinformaticsAgentPrompts.DATA_FUSION_SYSTEM, str)
        assert isinstance(BioinformaticsAgentPrompts.GO_ANNOTATION_SYSTEM, str)
        assert isinstance(BioinformaticsAgentPrompts.REASONING_SYSTEM, str)
        assert isinstance(BioinformaticsAgentPrompts.DATA_QUALITY_SYSTEM, str)

        # Test PROMPTS attribute
        assert hasattr(BioinformaticsAgentPrompts, "PROMPTS")
        assert isinstance(BioinformaticsAgentPrompts.PROMPTS, dict)
        assert len(BioinformaticsAgentPrompts.PROMPTS) > 0

        # Test that all prompt templates are strings
        for prompt_key, prompt_value in BioinformaticsAgentPrompts.PROMPTS.items():
            assert isinstance(prompt_value, str), f"Prompt {prompt_key} is not a string"
            assert len(prompt_value.strip()) > 0, f"Prompt {prompt_key} is empty"
