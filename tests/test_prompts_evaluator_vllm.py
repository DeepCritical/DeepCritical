"""
VLLM-based tests for evaluator.py prompts.

This module tests all prompts defined in the evaluator module using VLLM containers.
These tests are optional and disabled in CI by default.
"""

import pytest

from scripts.prompt_testing.test_prompts_vllm_base import VLLMPromptTestBase


class TestEvaluatorPromptsVLLM(VLLMPromptTestBase):
    """Test evaluator.py prompts with VLLM."""

    @pytest.mark.vllm
    @pytest.mark.optional
    def test_evaluator_prompts_vllm(self, vllm_tester):
        """Test all prompts from evaluator module with VLLM."""
        # Run tests for evaluator module
        results = self.run_module_prompt_tests(
            "evaluator", vllm_tester, max_tokens=256, temperature=0.7
        )

        # Assert minimum success rate
        self.assert_prompt_test_success(results, min_success_rate=0.8)

        # Check that we tested some prompts
        assert len(results) > 0, "No prompts were tested from evaluator module"

    @pytest.mark.vllm
    @pytest.mark.optional
    def test_definitive_system_prompt(self, vllm_tester):
        """Test definitive system prompt specifically."""
        from DeepResearch.src.prompts.evaluator import DEFINITIVE_SYSTEM

        result = self._test_single_prompt(
            vllm_tester,
            "DEFINITIVE_SYSTEM",
            DEFINITIVE_SYSTEM,
            expected_placeholders=["examples"],
            max_tokens=128,
            temperature=0.5,
        )

        assert result["success"]
        assert "reasoning" in result

        # Verify the system prompt contains expected content
        assert "evaluator of answer definitiveness" in DEFINITIVE_SYSTEM.lower()
        assert "definitive response" in DEFINITIVE_SYSTEM.lower()
        assert "not a direct response" in DEFINITIVE_SYSTEM.lower()

    @pytest.mark.vllm
    @pytest.mark.optional
    def test_plurality_system_prompt(self, vllm_tester):
        """Test plurality system prompt specifically."""
        from DeepResearch.src.prompts.evaluator import PLURALITY_SYSTEM

        result = self._test_single_prompt(
            vllm_tester,
            "PLURALITY_SYSTEM",
            PLURALITY_SYSTEM,
            max_tokens=128,
            temperature=0.5,
        )

        assert result["success"]

        # Verify the system prompt contains expected content
        assert (
            "analyzes if answers provide the appropriate number"
            in PLURALITY_SYSTEM.lower()
        )
        assert "Question Type Reference Table" in PLURALITY_SYSTEM

    @pytest.mark.vllm
    @pytest.mark.optional
    def test_completeness_system_prompt(self, vllm_tester):
        """Test completeness system prompt specifically."""
        from DeepResearch.src.prompts.evaluator import COMPLETENESS_SYSTEM

        result = self._test_single_prompt(
            vllm_tester,
            "COMPLETENESS_SYSTEM",
            COMPLETENESS_SYSTEM,
            expected_placeholders=["completeness_examples"],
            max_tokens=128,
            temperature=0.5,
        )

        assert result["success"]

        # Verify the system prompt contains expected content
        assert (
            "determines if an answer addresses all explicitly mentioned aspects"
            in COMPLETENESS_SYSTEM.lower()
        )
        assert "multi-aspect question" in COMPLETENESS_SYSTEM.lower()

    @pytest.mark.vllm
    @pytest.mark.optional
    def test_freshness_system_prompt(self, vllm_tester):
        """Test freshness system prompt specifically."""
        from DeepResearch.src.prompts.evaluator import FRESHNESS_SYSTEM

        result = self._test_single_prompt(
            vllm_tester,
            "FRESHNESS_SYSTEM",
            FRESHNESS_SYSTEM,
            expected_placeholders=["current_time_iso"],
            max_tokens=128,
            temperature=0.5,
        )

        assert result["success"]

        # Verify the system prompt contains expected content
        assert (
            "analyzes if answer content is likely outdated" in FRESHNESS_SYSTEM.lower()
        )
        assert "mentioned dates" in FRESHNESS_SYSTEM.lower()

    @pytest.mark.vllm
    @pytest.mark.optional
    def test_strict_system_prompt(self, vllm_tester):
        """Test strict system prompt specifically."""
        from DeepResearch.src.prompts.evaluator import STRICT_SYSTEM

        result = self._test_single_prompt(
            vllm_tester,
            "STRICT_SYSTEM",
            STRICT_SYSTEM,
            expected_placeholders=["knowledge_items"],
            max_tokens=128,
            temperature=0.5,
        )

        assert result["success"]

        # Verify the system prompt contains expected content
        assert "ruthless and picky answer evaluator" in STRICT_SYSTEM.lower()
        assert "REJECT answers" in STRICT_SYSTEM
        assert "find ANY weakness" in STRICT_SYSTEM

    @pytest.mark.vllm
    @pytest.mark.optional
    def test_question_evaluation_system_prompt(self, vllm_tester):
        """Test question evaluation system prompt specifically."""
        from DeepResearch.src.prompts.evaluator import QUESTION_EVALUATION_SYSTEM

        result = self._test_single_prompt(
            vllm_tester,
            "QUESTION_EVALUATION_SYSTEM",
            QUESTION_EVALUATION_SYSTEM,
            expected_placeholders=["examples"],
            max_tokens=128,
            temperature=0.5,
        )

        assert result["success"]

        # Verify the system prompt contains expected content
        assert (
            "determines if a question requires definitive"
            in QUESTION_EVALUATION_SYSTEM.lower()
        )
        assert "evaluation_types" in QUESTION_EVALUATION_SYSTEM.lower()

    @pytest.mark.vllm
    @pytest.mark.optional
    def test_evaluator_prompts_class(self, vllm_tester):
        """Test the EvaluatorPrompts class functionality."""
        from DeepResearch.src.prompts.evaluator import EvaluatorPrompts

        # Test that EvaluatorPrompts class works
        assert EvaluatorPrompts is not None

        # Test system prompt attributes
        assert hasattr(EvaluatorPrompts, "DEFINITIVE_SYSTEM")
        assert hasattr(EvaluatorPrompts, "FRESHNESS_SYSTEM")
        assert hasattr(EvaluatorPrompts, "PLURALITY_SYSTEM")

        # Test that system prompts are strings
        assert isinstance(EvaluatorPrompts.DEFINITIVE_SYSTEM, str)
        assert isinstance(EvaluatorPrompts.FRESHNESS_SYSTEM, str)
        assert isinstance(EvaluatorPrompts.PLURALITY_SYSTEM, str)

        # Test PROMPTS attribute
        assert hasattr(EvaluatorPrompts, "PROMPTS")
        assert isinstance(EvaluatorPrompts.PROMPTS, dict)
        assert len(EvaluatorPrompts.PROMPTS) > 0

    @pytest.mark.vllm
    @pytest.mark.optional
    def test_evaluation_prompts_with_real_examples(self, vllm_tester):
        """Test evaluation prompts with realistic examples."""
        from DeepResearch.src.prompts.evaluator import EVALUATOR_PROMPTS

        # Test definitive evaluation
        definitive_prompt = EVALUATOR_PROMPTS["evaluate_definitiveness"]

        result = self._test_single_prompt(
            vllm_tester,
            "definitive_evaluation",
            definitive_prompt,
            expected_placeholders=["answer"],
            max_tokens=128,
            temperature=0.3,
        )

        assert result["success"]

        # Test freshness evaluation
        freshness_prompt = EVALUATOR_PROMPTS["evaluate_freshness"]

        result = self._test_single_prompt(
            vllm_tester,
            "freshness_evaluation",
            freshness_prompt,
            expected_placeholders=["answer"],
            max_tokens=128,
            temperature=0.3,
        )

        assert result["success"]

        # Test plurality evaluation
        plurality_prompt = EVALUATOR_PROMPTS["evaluate_plurality"]

        result = self._test_single_prompt(
            vllm_tester,
            "plurality_evaluation",
            plurality_prompt,
            expected_placeholders=["answer"],
            max_tokens=128,
            temperature=0.3,
        )

        assert result["success"]

    @pytest.mark.vllm
    @pytest.mark.optional
    def test_evaluation_criteria_coverage(self, vllm_tester):
        """Test that evaluation covers all required criteria."""
        from DeepResearch.src.prompts.evaluator import DEFINITIVE_SYSTEM

        # Verify that the definitive system prompt covers all expected criteria
        required_criteria = [
            "direct response",
            "definitive response",
            "uncertainty",
            "personal uncertainty",
            "lack of information",
            "inability statements",
        ]

        for criterion in required_criteria:
            assert (
                criterion.lower() in DEFINITIVE_SYSTEM.lower()
            ), f"Missing criterion: {criterion}"

        # Test the prompt formatting
        result = self._test_single_prompt(
            vllm_tester,
            "evaluation_criteria_test",
            DEFINITIVE_SYSTEM,
            max_tokens=64,
            temperature=0.1,
        )

        assert result["success"]
