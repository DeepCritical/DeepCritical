#!/usr/bin/env python3
"""
Script to fix hardcoded model strings across the codebase.

This script replaces hardcoded "anthropic:claude-sonnet-4-0" default parameters
with None, allowing the config loader to provide the default value.
"""

import re
from pathlib import Path


def fix_hardcoded_model_defaults(file_path: Path) -> int:
    """
    Fix hardcoded model defaults in a Python file.

    Args:
        file_path: Path to the Python file

    Returns:
        Number of replacements made
    """
    content = file_path.read_text()
    original_content = content

    # Pattern 1: model_name: str = "anthropic:claude-sonnet-4-0"
    pattern1 = r'model_name:\s*str\s*=\s*"anthropic:claude-sonnet-4-0"'
    replacement1 = 'model_name: str | None = None'
    content = re.sub(pattern1, replacement1, content)

    # Pattern 2: model_name="anthropic:claude-sonnet-4-0" in Field()
    pattern2 = r'model_name\s*=\s*"anthropic:claude-sonnet-4-0"'
    replacement2 = 'model_name = None  # Uses config default'
    # Only replace in Field() context
    content = re.sub(
        r'(Field\s*\([^)]*?)model_name\s*=\s*"anthropic:claude-sonnet-4-0"',
        r'\1model_name = None  # Uses config default',
        content
    )

    # Pattern 3: Default parameters in function signatures
    pattern3 = r'(\w+:\s*str\s*=\s*)"anthropic:claude-sonnet-4-0"'
    # This is tricky - only replace if it's a parameter named 'model' or 'model_name'
    content = re.sub(
        r'(model(?:_name)?:\s*str\s*=\s*)"anthropic:claude-sonnet-4-0"',
        r'\1None  # Uses config default',
        content
    )

    replacements = content.count('Uses config default')

    if content != original_content:
        file_path.write_text(content)
        return replacements

    return 0


def main():
    """Main function to fix all files."""
    # Find all Python files in DeepResearch
    deep_research_dir = Path(__file__).parent.parent / "DeepResearch"

    python_files = [
        deep_research_dir / "agents.py",
        deep_research_dir / "app.py",
        deep_research_dir / "src" / "workflow_patterns.py",
        deep_research_dir / "src" / "agents" / "workflow_pattern_agents.py",
        deep_research_dir / "src" / "agents" / "bioinformatics_agents.py",
        deep_research_dir / "src" / "agents" / "code_generation_agent.py",
        deep_research_dir / "src" / "agents" / "code_execution_orchestrator.py",
        deep_research_dir / "src" / "agents" / "code_improvement_agent.py",
        deep_research_dir / "src" / "agents" / "workflow_orchestrator.py",
        deep_research_dir / "src" / "agents" / "deep_agent_implementations.py",
        deep_research_dir / "src" / "statemachines" / "deep_agent_graph.py",
        deep_research_dir / "src" / "statemachines" / "search_workflow.py",
        deep_research_dir / "src" / "datatypes" / "mcp.py",
        deep_research_dir / "src" / "datatypes" / "bioinformatics_mcp.py",
        deep_research_dir / "src" / "datatypes" / "middleware.py",
        deep_research_dir / "src" / "datatypes" / "workflow_orchestration.py",
        deep_research_dir / "src" / "prompts" / "bioinformatics_agent_implementations.py",
        deep_research_dir / "src" / "tools" / "bioinformatics_tools.py",
        deep_research_dir / "src" / "utils" / "pydantic_ai_utils.py",
    ]

    total_replacements = 0
    files_modified = 0

    for file_path in python_files:
        if file_path.exists():
            replacements = fix_hardcoded_model_defaults(file_path)
            if replacements > 0:
                print(f"✓ {file_path.relative_to(deep_research_dir.parent)}: {replacements} replacements")
                total_replacements += replacements
                files_modified += 1
        else:
            print(f"✗ {file_path.relative_to(deep_research_dir.parent)}: File not found")

    print(f"\n✓ Total: {total_replacements} replacements across {files_modified} files")


if __name__ == "__main__":
    main()
