#!/usr/bin/env python3
"""
Script to run VLLM-based prompt tests with Hydra configuration.

This script provides a convenient way to run VLLM tests for all prompt modules
with proper logging, artifact collection, and single instance optimization.
"""

import argparse
import logging
import subprocess
import sys
from pathlib import Path

from omegaconf import DictConfig

# Set up logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def setup_artifacts_directory(config: DictConfig | None = None):
    """Set up the test artifacts directory using configuration."""
    if config is None:
        config = load_vllm_test_config()

    artifacts_config = config.get("vllm_tests", {}).get("artifacts", {})
    artifacts_dir = Path(
        artifacts_config.get("base_directory", "test_artifacts/vllm_tests")
    )
    artifacts_dir.mkdir(parents=True, exist_ok=True)
    logger.info(f"Artifacts directory: {artifacts_dir}")
    return artifacts_dir


def load_vllm_test_config() -> DictConfig:
    """Load VLLM test configuration using Hydra."""
    try:
        from pathlib import Path

        from hydra import compose, initialize_config_dir

        config_dir = Path("configs")
        if config_dir.exists():
            with initialize_config_dir(config_dir=str(config_dir), version_base=None):
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
            logger.warning("Config directory not found, using default configuration")
            return create_default_test_config()

    except Exception as e:
        logger.warning(f"Could not load Hydra config for VLLM tests: {e}")
        return create_default_test_config()


def create_default_test_config() -> DictConfig:
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


def run_vllm_tests(
    modules: list[str] | None = None,
    verbose: bool = False,
    coverage: bool = False,
    parallel: bool = False,
    config: DictConfig | None = None,
    use_hydra_config: bool = True,
):
    """Run VLLM tests for specified modules or all modules with Hydra configuration.

    Args:
        modules: List of module names to test (None for all)
        verbose: Enable verbose output
        coverage: Enable coverage reporting
        parallel: Run tests in parallel (disabled for single instance optimization)
        config: Hydra configuration object (if use_hydra_config=False)
        use_hydra_config: Whether to use Hydra configuration loading
    """
    # Load configuration
    if use_hydra_config and config is None:
        config = load_vllm_test_config()

    # Check if VLLM tests are enabled
    vllm_config = config.get("vllm_tests", {}) if config else {}
    if not vllm_config.get("enabled", True):
        logger.info("VLLM tests are disabled in configuration")
        return 0

    # Set up artifacts directory
    artifacts_dir = setup_artifacts_directory(config)

    # Single instance optimization: disable parallel execution
    if parallel:
        logger.warning(
            "Parallel execution disabled for single VLLM instance optimization"
        )
        parallel = False

    # Base pytest command with configuration-aware settings
    cmd = ["python", "-m", "pytest"]

    if verbose:
        cmd.append("-v")

    if coverage:
        cmd.extend(["--cov=DeepResearch", "--cov-report=html"])

    # Add markers for VLLM tests (respects CI skip settings)
    cmd.extend(["-m", "vllm"])

    # Add timeout and other options from configuration
    test_config = config.get("testing", {}) if config else {}
    timeout = test_config.get("pytest_timeout", 600)
    cmd.extend([f"--timeout={timeout}", "--tb=short", "--durations=10"])

    # Disable parallel execution for single instance optimization
    # (pytest parallel execution would spawn multiple VLLM containers)

    # Determine which test files to run based on configuration
    test_dir = Path("tests")
    if modules:
        # Filter modules based on configuration
        scope_config = test_config.get("scope", {})
        if not scope_config.get("test_all_modules", True):
            allowed_modules = scope_config.get("modules_to_test", [])
            modules = [m for m in modules if m in allowed_modules]
            if not modules:
                logger.warning(
                    f"No modules to test from allowed list: {allowed_modules}"
                )
                return 0

        test_files = [
            f"test_prompts_vllm/test_prompts_{module}_vllm.py"
            for module in modules
            if (test_dir / f"test_prompts_vllm/test_prompts_{module}_vllm.py").exists()
        ]
        if not test_files:
            logger.error(f"No test files found for modules: {modules}")
            return 1
    else:
        # Run all VLLM test files, respecting module filtering
        all_test_files = list(test_dir.glob("test_prompts_vllm/test_prompts_*_vllm.py"))
        scope_config = test_config.get("scope", {})

        if scope_config.get("test_all_modules", True):
            test_files = all_test_files
        else:
            allowed_modules = scope_config.get("modules_to_test", [])
            test_files = [
                f
                for f in all_test_files
                if any(module in f.name for module in allowed_modules)
            ]

    if not test_files:
        logger.error("No VLLM test files found")
        return 1

    # Add test files to command
    for test_file in test_files:
        cmd.append(str(test_file))

    logger.info(f"Running VLLM tests for {len(test_files)} modules: {' '.join(cmd)}")

    # Run the tests
    try:
        result = subprocess.run(cmd, cwd=Path.cwd(), check=False)

        # Generate test report using configuration
        if result.returncode == 0:
            logger.info("✅ All VLLM tests passed!")
            _generate_summary_report(test_files, config, artifacts_dir)
        else:
            logger.error("❌ Some VLLM tests failed")
            logger.info("Check test artifacts for detailed results")

        return result.returncode

    except KeyboardInterrupt:
        logger.info("Tests interrupted by user")
        return 130
    except Exception:
        logger.exception("Error running tests")
        return 1


def _generate_summary_report(
    test_files: list[Path],
    config: DictConfig | None = None,
    artifacts_dir: Path | None = None,
):
    """Generate a summary report of test results using configuration."""
    if config is None:
        config = create_default_test_config()

    if artifacts_dir is None:
        artifacts_dir = setup_artifacts_directory(config)

    # Get reporting configuration
    reporting_config = config.get("vllm_tests", {}).get("artifacts", {})
    if not reporting_config.get("save_global_summary", True):
        logger.info("Global summary reporting disabled in configuration")
        return

    report_file = artifacts_dir / "test_summary.md"

    summary = "# VLLM Prompt Tests Summary\n\n"
    summary += f"**Test Files:** {len(test_files)}\n\n"

    # Check for artifact files
    if artifacts_dir.exists():
        json_files = list(artifacts_dir.glob("*.json"))
        summary += f"**Artifacts Generated:** {len(json_files)}\n\n"

        # Group artifacts by module
        artifacts_by_module = {}
        for json_file in json_files:
            # Extract module name from filename (test_prompts_{module}_vllm.py results in {module}_*.json)
            filename = json_file.stem
            module_name = filename.split("_")[0] if "_" in filename else "unknown"

            if module_name not in artifacts_by_module:
                artifacts_by_module[module_name] = []
            artifacts_by_module[module_name].append(json_file)

        summary += "## Artifacts by Module\n\n"
        for module, files in artifacts_by_module.items():
            summary += f"- **{module}:** {len(files)} artifacts\n"

    # Add configuration information
    summary += "\n## Configuration Used\n\n"
    summary += f"- **Model:** {config.get('model', {}).get('name', 'unknown')}\n"
    summary += f"- **Test Strategy:** {config.get('testing', {}).get('scope', {}).get('test_all_modules', True)}\n"
    summary += f"- **Data Generation:** {config.get('data_generation', {}).get('strategy', 'unknown')}\n"
    summary += f"- **Artifacts Enabled:** {reporting_config.get('enabled', True)}\n"

    # Write summary
    with report_file.open("w") as f:
        f.write(summary)

    logger.info(f"Summary report written to: {report_file}")


def list_available_modules():
    """List all available VLLM test modules."""
    test_dir = Path("tests")
    vllm_test_files = list(test_dir.glob("test_prompts_*_vllm.py"))

    modules = []
    for test_file in vllm_test_files:
        # Extract module name from filename (test_prompts_{module}_vllm.py)
        module_name = test_file.stem.replace("test_prompts_", "").replace("_vllm", "")
        modules.append(module_name)

    return sorted(modules)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Run VLLM-based prompt tests with Hydra configuration"
    )

    parser.add_argument(
        "modules", nargs="*", help="Specific modules to test (default: all modules)"
    )

    parser.add_argument(
        "-v", "--verbose", action="store_true", help="Enable verbose output"
    )

    parser.add_argument(
        "--coverage", action="store_true", help="Enable coverage reporting"
    )

    parser.add_argument(
        "-p",
        "--parallel",
        action="store_true",
        help="Run tests in parallel (disabled for single instance optimization)",
    )

    parser.add_argument(
        "--list-modules", action="store_true", help="List available test modules"
    )

    parser.add_argument(
        "--config-file", type=str, help="Path to custom Hydra config file"
    )

    parser.add_argument(
        "--config-name",
        type=str,
        default="vllm_tests",
        help="Hydra config name (default: vllm_tests)",
    )

    parser.add_argument(
        "--no-hydra", action="store_true", help="Disable Hydra configuration loading"
    )

    args = parser.parse_args()

    if args.list_modules:
        modules = list_available_modules()
        if modules:
            for _module in modules:
                pass
        else:
            pass
        return 0

    # Load configuration
    config = None
    if not args.no_hydra:
        try:
            config = load_vllm_test_config()
            logger.info("Loaded Hydra configuration for VLLM tests")
        except Exception as e:
            logger.warning(f"Could not load Hydra config, using defaults: {e}")

    # Run the tests with configuration
    if args.modules:
        # Validate that specified modules exist
        available_modules = list_available_modules()
        invalid_modules = [m for m in args.modules if m not in available_modules]

        if invalid_modules:
            logger.error(f"Invalid modules: {invalid_modules}")
            logger.info(f"Available modules: {available_modules}")
            return 1

        modules_to_test = args.modules
    else:
        modules_to_test = None

    return run_vllm_tests(
        modules=modules_to_test,
        verbose=args.verbose,
        coverage=args.coverage,
        parallel=args.parallel,
        config=config,
        use_hydra_config=not args.no_hydra,
    )


if __name__ == "__main__":
    sys.exit(main())
