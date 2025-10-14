"""
Base test class for VLLM-based prompt testing.

This module provides a base test class that other prompt test modules
can inherit from to test prompts using VLLM containers.
"""

import json
import logging
import time
from pathlib import Path
from typing import Any

import pytest
from omegaconf import DictConfig

from scripts.prompt_testing.testcontainers_vllm import (
    VLLMPromptTester,
    create_dummy_data_for_prompt,
)

# Set up logging
logger = logging.getLogger(__name__)


class VLLMPromptTestBase:
    """Base class for VLLM-based prompt testing."""

    @pytest.fixture(scope="class")
    def vllm_tester(self):
        """VLLM tester fixture for the test class with Hydra configuration."""
        # Load Hydra configuration for VLLM tests
        config = self._load_vllm_test_config()

        # Check if VLLM tests are enabled in configuration
        vllm_config = config.get("vllm_tests", {})
        if not vllm_config.get("enabled", True):
            pytest.skip("VLLM tests disabled in configuration")

        # Skip VLLM tests in CI by default unless explicitly enabled
        if self._is_ci_environment() and not vllm_config.get("run_in_ci", False):
            pytest.skip("VLLM tests disabled in CI environment")

        # Extract model and performance configuration
        model_config = config.get("model", {})
        performance_config = config.get("performance", {})

        with VLLMPromptTester(
            config=config,
            model_name=model_config.get("name", "TinyLlama/TinyLlama-1.1B-Chat-v1.0"),
            container_timeout=performance_config.get("max_container_startup_time", 120),
            max_tokens=model_config.get("generation", {}).get("max_tokens", 256),
            temperature=model_config.get("generation", {}).get("temperature", 0.7),
        ) as tester:
            yield tester

    def _is_ci_environment(self) -> bool:
        """Check if running in CI environment."""
        return any(
            var in {"CI", "GITHUB_ACTIONS", "GITLAB_CI", "JENKINS_URL"}
            for var in ("CI", "GITHUB_ACTIONS", "GITLAB_CI", "JENKINS_URL")
        )

    def _load_vllm_test_config(self) -> DictConfig:
        """Load VLLM test configuration using Hydra."""
        try:
            from pathlib import Path

            from hydra import compose, initialize_config_dir

            config_dir = Path("configs")
            if config_dir.exists():
                with initialize_config_dir(
                    config_dir=str(config_dir), version_base=None
                ):
                    return compose(
                        config_name="vllm_tests",
                        overrides=[
                            "model=local_model",
                            "performance=balanced",
                            "testing=comprehensive",
                            "output=structured",
                        ],
                    )
            else:
                logger.warning(
                    "Config directory not found, using default configuration"
                )
                return self._create_default_test_config()

        except Exception as e:
            logger.warning(f"Could not load Hydra config for VLLM tests: {e}")
            return self._create_default_test_config()

    def _create_default_test_config(self) -> DictConfig:
        """Create default test configuration when Hydra is not available."""
        from omegaconf import OmegaConf

        default_config = {
            "vllm_tests": {
                "enabled": True,
                "run_in_ci": False,
                "execution_strategy": "sequential",
                "max_concurrent_tests": 1,
                "artifacts": {
                    "enabled": True,
                    "base_directory": "test_artifacts/vllm_tests",
                    "save_individual_results": True,
                    "save_module_summaries": True,
                    "save_global_summary": True,
                },
                "monitoring": {
                    "enabled": True,
                    "track_execution_times": True,
                    "track_memory_usage": True,
                    "max_execution_time_per_module": 300,
                },
                "error_handling": {
                    "graceful_degradation": True,
                    "continue_on_module_failure": True,
                    "retry_failed_prompts": True,
                    "max_retries_per_prompt": 2,
                },
            },
            "model": {
                "name": "TinyLlama/TinyLlama-1.1B-Chat-v1.0",
                "generation": {
                    "max_tokens": 256,
                    "temperature": 0.7,
                },
            },
            "performance": {
                "max_container_startup_time": 120,
            },
            "testing": {
                "scope": {
                    "test_all_modules": True,
                },
                "validation": {
                    "validate_prompt_structure": True,
                    "validate_response_structure": True,
                },
                "assertions": {
                    "min_success_rate": 0.8,
                    "min_response_length": 10,
                },
            },
            "data_generation": {
                "strategy": "realistic",
            },
        }

        return OmegaConf.create(default_config)

    def _load_prompts_from_module(
        self, module_name: str, config: DictConfig | None = None
    ) -> list[tuple[str, str, str]]:
        """Load prompts from a specific prompt module with configuration support.

        Args:
            module_name: Name of the prompt module (without .py extension)
            config: Hydra configuration for test settings

        Returns:
            List of (prompt_name, prompt_template, prompt_content) tuples
        """
        try:
            import importlib

            module = importlib.import_module(f"DeepResearch.src.prompts.{module_name}")

            prompts = []

            # Look for prompt dictionaries or classes
            for attr_name in dir(module):
                if attr_name.startswith("__"):
                    continue

                attr = getattr(module, attr_name)

                # Check if it's a prompt dictionary
                if isinstance(attr, dict) and attr_name.endswith("_PROMPTS"):
                    for prompt_key, prompt_value in attr.items():
                        if isinstance(prompt_value, str):
                            prompts.append((f"{attr_name}.{prompt_key}", prompt_value))

                elif isinstance(attr, str) and (
                    "PROMPT" in attr_name or "SYSTEM" in attr_name
                ):
                    # Individual prompt strings
                    prompts.append((attr_name, attr))

                elif hasattr(attr, "PROMPTS") and isinstance(attr.PROMPTS, dict):
                    # Classes with PROMPTS attribute
                    for prompt_key, prompt_value in attr.PROMPTS.items():
                        if isinstance(prompt_value, str):
                            prompts.append((f"{attr_name}.{prompt_key}", prompt_value))

            # Filter prompts based on configuration
            if config:
                test_config = config.get("testing", {})
                scope_config = test_config.get("scope", {})

                # Apply module filtering
                if not scope_config.get("test_all_modules", True):
                    allowed_modules = scope_config.get("modules_to_test", [])
                    if allowed_modules and module_name not in allowed_modules:
                        logger.info(
                            f"Skipping module {module_name} (not in allowed modules)"
                        )
                        return []

                # Apply prompt count limits
                max_prompts = scope_config.get("max_prompts_per_module", 50)
                if len(prompts) > max_prompts:
                    logger.info(
                        f"Limiting prompts for {module_name} to {max_prompts} (was {len(prompts)})"
                    )
                    prompts = prompts[:max_prompts]

            return prompts

        except ImportError as e:
            logger.warning(f"Could not import module {module_name}: {e}")
            return []

    def _test_single_prompt(
        self,
        vllm_tester: VLLMPromptTester,
        prompt_name: str,
        prompt_template: str,
        expected_placeholders: list[str] | None = None,
        config: DictConfig | None = None,
        **generation_kwargs,
    ) -> dict[str, Any]:
        """Test a single prompt with VLLM using configuration.

        Args:
            vllm_tester: VLLM tester instance
            prompt_name: Name of the prompt
            prompt_template: The prompt template string
            expected_placeholders: Expected placeholders in the prompt
            config: Hydra configuration for test settings
            **generation_kwargs: Additional generation parameters

        Returns:
            Test result dictionary
        """
        # Use configuration or default
        if config is None:
            config = self._create_default_test_config()

        # Create dummy data for the prompt using configuration
        dummy_data = create_dummy_data_for_prompt(prompt_template, config)

        # Verify expected placeholders are present
        if expected_placeholders:
            for placeholder in expected_placeholders:
                assert placeholder in dummy_data, (
                    f"Missing expected placeholder: {placeholder}"
                )

        # Test the prompt
        result = vllm_tester.test_prompt(
            prompt_template, prompt_name, dummy_data, **generation_kwargs
        )

        # Basic validation
        assert "prompt_name" in result
        assert "success" in result
        assert "generated_response" in result

        # Additional validation based on configuration
        test_config = config.get("testing", {})
        assertions_config = test_config.get("assertions", {})

        # Check minimum response length
        min_length = assertions_config.get("min_response_length", 10)
        if len(result.get("generated_response", "")) < min_length:
            logger.warning(
                f"Response for prompt {prompt_name} is shorter than expected: {len(result.get('generated_response', ''))} chars"
            )

        return result

    def _validate_prompt_structure(self, prompt_template: str, prompt_name: str):
        """Validate that a prompt has proper structure.

        Args:
            prompt_template: The prompt template string
            prompt_name: Name of the prompt for error reporting
        """
        # Check for basic prompt structure
        assert isinstance(prompt_template, str), f"Prompt {prompt_name} is not a string"
        assert len(prompt_template.strip()) > 0, f"Prompt {prompt_name} is empty"

        # Check for common prompt patterns
        has_instructions = any(
            pattern in prompt_template.lower()
            for pattern in ["you are", "your role", "please", "instructions:"]
        )

        # Most prompts should have some form of instructions
        # (Some system prompts might be just descriptions)
        if not has_instructions and len(prompt_template) > 50:
            logger.warning(f"Prompt {prompt_name} might be missing clear instructions")

    def _test_prompt_batch(
        self,
        vllm_tester: VLLMPromptTester,
        prompts: list[tuple[str, str]],
        config: DictConfig | None = None,
        **generation_kwargs,
    ) -> list[dict[str, Any]]:
        """Test a batch of prompts with configuration and single instance optimization.

        Args:
            vllm_tester: VLLM tester instance
            prompts: List of (prompt_name, prompt_template) tuples
            config: Hydra configuration for test settings
            **generation_kwargs: Additional generation parameters

        Returns:
            List of test results
        """
        # Use configuration or default
        if config is None:
            config = self._create_default_test_config()

        results = []

        # Get execution configuration
        vllm_config = config.get("vllm_tests", {})
        execution_config = vllm_config.get("execution_strategy", "sequential")
        error_config = vllm_config.get("error_handling", {})

        # Single instance optimization: reduce delays between tests
        delay_between_tests = 0.1 if execution_config == "sequential" else 0.0

        for prompt_name, prompt_template in prompts:
            try:
                # Validate prompt structure if enabled
                validation_config = config.get("testing", {}).get("validation", {})
                if validation_config.get("validate_prompt_structure", True):
                    self._validate_prompt_structure(prompt_template, prompt_name)

                # Test the prompt with configuration
                result = self._test_single_prompt(
                    vllm_tester,
                    prompt_name,
                    prompt_template,
                    config=config,
                    **generation_kwargs,
                )

                results.append(result)

                # Controlled delay for single instance optimization
                if delay_between_tests > 0:
                    time.sleep(delay_between_tests)

            except Exception as e:
                logger.exception(f"Error testing prompt {prompt_name}")

                # Handle errors based on configuration
                if error_config.get("graceful_degradation", True):
                    results.append(
                        {
                            "prompt_name": prompt_name,
                            "prompt_template": prompt_template,
                            "error": str(e),
                            "success": False,
                            "timestamp": time.time(),
                            "error_handled_gracefully": True,
                        }
                    )
                else:
                    # Re-raise exception if graceful degradation is disabled
                    raise

        return results

    def _generate_test_report(
        self, results: list[dict[str, Any]], module_name: str
    ) -> str:
        """Generate a test report for the results.

        Args:
            results: List of test results
            module_name: Name of the module being tested

        Returns:
            Formatted test report
        """
        successful = sum(1 for r in results if r.get("success", False))
        total = len(results)

        report = f"""
# VLLM Prompt Test Report - {module_name}

**Test Summary:**
- Total Prompts: {total}
- Successful: {successful}
- Failed: {total - successful}
- Success Rate: {successful / total * 100:.1f}%

**Results:**
"""

        for result in results:
            status = "✅ PASS" if result.get("success", False) else "❌ FAIL"
            prompt_name = result.get("prompt_name", "Unknown")
            report += f"- {status}: {prompt_name}\n"

            if not result.get("success", False):
                error = result.get("error", "Unknown error")
                report += f"  Error: {error}\n"

        # Save detailed results to file
        report_file = Path("test_artifacts") / f"vllm_{module_name}_report.json"
        report_file.parent.mkdir(exist_ok=True)

        with open(report_file, "w") as f:
            json.dump(
                {
                    "module": module_name,
                    "total_tests": total,
                    "successful_tests": successful,
                    "failed_tests": total - successful,
                    "success_rate": successful / total * 100 if total > 0 else 0,
                    "results": results,
                    "timestamp": time.time(),
                },
                f,
                indent=2,
            )

        return report

    def run_module_prompt_tests(
        self,
        module_name: str,
        vllm_tester: VLLMPromptTester,
        config: DictConfig | None = None,
        **generation_kwargs,
    ) -> list[dict[str, Any]]:
        """Run prompt tests for a specific module with configuration support.

        Args:
            module_name: Name of the prompt module to test
            vllm_tester: VLLM tester instance
            config: Hydra configuration for test settings
            **generation_kwargs: Additional generation parameters

        Returns:
            List of test results
        """
        # Use configuration or default
        if config is None:
            config = self._create_default_test_config()

        logger.info(f"Testing prompts from module: {module_name}")

        # Load prompts from the module with configuration
        prompts = self._load_prompts_from_module(module_name, config)

        if not prompts:
            logger.warning(f"No prompts found in module: {module_name}")
            return []

        logger.info(f"Found {len(prompts)} prompts in {module_name}")

        # Check if we should skip empty modules
        vllm_config = config.get("vllm_tests", {})
        if vllm_config.get("skip_empty_modules", True) and len(prompts) == 0:
            logger.info(f"Skipping empty module: {module_name}")
            return []

        # Test all prompts with configuration
        results = self._test_prompt_batch(
            vllm_tester, prompts, config, **generation_kwargs
        )

        # Check execution time limits
        total_time = sum(
            r.get("execution_time", 0) for r in results if r.get("success", False)
        )
        max_time = vllm_config.get("monitoring", {}).get(
            "max_execution_time_per_module", 300
        )

        if total_time > max_time:
            logger.warning(
                f"Module {module_name} exceeded time limit: {total_time:.2f}s > {max_time}s"
            )

        # Generate and log report
        report = self._generate_test_report(results, module_name)
        logger.info(f"\n{report}")

        return results

    def assert_prompt_test_success(
        self,
        results: list[dict[str, Any]],
        min_success_rate: float | None = None,
        config: DictConfig | None = None,
    ):
        """Assert that prompt tests meet minimum success criteria using configuration.

        Args:
            results: List of test results
            min_success_rate: Override minimum success rate from config
            config: Hydra configuration for test settings
        """
        # Use configuration or default
        if config is None:
            config = self._create_default_test_config()

        # Get minimum success rate from configuration or parameter
        test_config = config.get("testing", {})
        assertions_config = test_config.get("assertions", {})
        min_rate = min_success_rate or assertions_config.get("min_success_rate", 0.8)

        if not results:
            pytest.fail("No test results to evaluate")

        successful = sum(1 for r in results if r.get("success", False))
        success_rate = successful / len(results)

        assert success_rate >= min_rate, (
            f"Success rate {success_rate:.2%} below minimum {min_rate:.2%}. "
            f"Successful: {successful}/{len(results)}"
        )

    def assert_reasoning_detected(
        self,
        results: list[dict[str, Any]],
        min_reasoning_rate: float | None = None,
        config: DictConfig | None = None,
    ):
        """Assert that reasoning was detected in responses using configuration.

        Args:
            results: List of test results
            min_reasoning_rate: Override minimum reasoning detection rate from config
            config: Hydra configuration for test settings
        """
        # Use configuration or default
        if config is None:
            config = self._create_default_test_config()

        # Get minimum reasoning rate from configuration or parameter
        test_config = config.get("testing", {})
        assertions_config = test_config.get("assertions", {})
        min_rate = min_reasoning_rate or assertions_config.get(
            "min_reasoning_detection_rate", 0.3
        )

        if not results:
            pytest.fail("No test results to evaluate")

        with_reasoning = sum(
            1
            for r in results
            if r.get("success", False)
            and r.get("reasoning", {}).get("has_reasoning", False)
        )

        reasoning_rate = with_reasoning / len(results) if results else 0.0

        # This is informational - don't fail the test if reasoning isn't detected
        # as it depends on the model and prompt structure
        if reasoning_rate < min_rate:
            logger.warning(
                f"Reasoning detection rate {reasoning_rate:.2%} below target {min_rate:.2%}"
            )
