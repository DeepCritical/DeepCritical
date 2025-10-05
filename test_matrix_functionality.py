#!/usr/bin/env python3
"""
Test script to verify VLLM test matrix functionality.

This script tests the basic functionality of the VLLM test matrix
without actually running the full test suite.
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def test_script_exists():
    """Test that the VLLM test matrix script exists."""
    script_path = project_root / "scripts" / "prompt_testing" / "vllm_test_matrix.sh"
    assert script_path.exists(), f"Script not found: {script_path}"
    print("✅ VLLM test matrix script exists")

def test_config_files_exist():
    """Test that required configuration files exist."""
    config_files = [
        "configs/vllm_tests/default.yaml",
        "configs/vllm_tests/matrix_configurations.yaml",
        "configs/vllm_tests/model/local_model.yaml",
        "configs/vllm_tests/performance/balanced.yaml",
        "configs/vllm_tests/testing/comprehensive.yaml",
        "configs/vllm_tests/output/structured.yaml",
    ]

    for config_file in config_files:
        config_path = project_root / config_file
        assert config_path.exists(), f"Config file not found: {config_path}"
        print(f"✅ Config file exists: {config_file}")

def test_test_files_exist():
    """Test that test files exist."""
    test_files = [
        "tests/testcontainers_vllm.py",
        "tests/test_prompts_vllm_base.py",
        "tests/test_prompts_agents_vllm.py",
        "tests/test_prompts_bioinformatics_agents_vllm.py",
        "tests/test_prompts_broken_ch_fixer_vllm.py",
        "tests/test_prompts_code_exec_vllm.py",
        "tests/test_prompts_code_sandbox_vllm.py",
        "tests/test_prompts_deep_agent_prompts_vllm.py",
        "tests/test_prompts_error_analyzer_vllm.py",
        "tests/test_prompts_evaluator_vllm.py",
        "tests/test_prompts_finalizer_vllm.py",
    ]

    for test_file in test_files:
        test_path = project_root / test_file
        assert test_path.exists(), f"Test file not found: {test_path}"
        print(f"✅ Test file exists: {test_file}")

def test_prompt_modules_exist():
    """Test that prompt modules exist."""
    prompt_modules = [
        "DeepResearch/src/prompts/agents.py",
        "DeepResearch/src/prompts/bioinformatics_agents.py",
        "DeepResearch/src/prompts/broken_ch_fixer.py",
        "DeepResearch/src/prompts/code_exec.py",
        "DeepResearch/src/prompts/code_sandbox.py",
        "DeepResearch/src/prompts/deep_agent_prompts.py",
        "DeepResearch/src/prompts/error_analyzer.py",
        "DeepResearch/src/prompts/evaluator.py",
        "DeepResearch/src/prompts/finalizer.py",
    ]

    for prompt_module in prompt_modules:
        prompt_path = project_root / prompt_module
        assert prompt_path.exists(), f"Prompt module not found: {prompt_path}"
        print(f"✅ Prompt module exists: {prompt_module}")

def main():
    """Run all tests."""
    print("🧪 Testing VLLM Test Matrix Functionality")
    print("=" * 50)

    try:
        test_script_exists()
        test_config_files_exist()
        test_test_files_exist()
        test_prompt_modules_exist()
        print("=" * 50)
        print("✅ All tests passed! VLLM test matrix is ready.")

    except AssertionError as e:
        print(f"❌ Test failed: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
