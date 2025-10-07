#!/bin/bash

# VLLM Test Matrix Script
# This script runs the VLLM test matrix for DeepCritical prompt testing

set -e

# Default configuration
CONFIG_DIR="configs"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}VLLM Test Matrix Script${NC}"
echo "=========================="

# Check if we're in the right directory
if [[ ! -d "${PROJECT_ROOT}/DeepResearch" ]]; then
    echo -e "${RED}Error: Not in the correct project directory${NC}"
    exit 1
fi

# Function to run tests with different configurations
run_test_matrix() {
    local config="$1"
    echo -e "${YELLOW}Running tests with configuration: $config${NC}"

    # Run pytest with the specified configuration
    python -m pytest tests/ -v -k "vllm" --tb=short || {
        echo -e "${RED}Tests failed for configuration: $config${NC}"
        return 1
    }

    echo -e "${GREEN}Tests passed for configuration: $config${NC}"
}

# Main execution
cd "${PROJECT_ROOT}"

# Check if required files exist
if [[ ! -f "${PROJECT_ROOT}/scripts/prompt_testing/testcontainers_vllm.py" ]]; then
    echo -e "${RED}Error: testcontainers_vllm.py not found${NC}"
    exit 1
fi

if [[ ! -f "${PROJECT_ROOT}/scripts/prompt_testing/test_prompts_vllm_base.py" ]]; then
    echo -e "${RED}Error: test_prompts_vllm_base.py not found${NC}"
    exit 1
fi

# Run test matrix
echo -e "${YELLOW}Starting VLLM test matrix...${NC}"

# Test different configurations if they exist
configs=("fast" "balanced" "comprehensive" "focused")

for config in "${configs[@]}"; do
    if [[ -f "${CONFIG_DIR}/vllm_tests/testing/${config}.yaml" ]]; then
        run_test_matrix "$config"
    else
        echo -e "${YELLOW}Skipping configuration: $config (file not found)${NC}"
    fi
done

echo -e "${GREEN}VLLM test matrix completed successfully!${NC}"
