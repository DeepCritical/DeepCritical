"""
Tests for run_agent_demo.py demo script.

These are basic structural tests - actual end-to-end testing
happens in Phase 7 manual testing.

Reference: burner_docs/haplotype_agent/02_implementation_plan.md Phase 6
"""

from pathlib import Path

import pytest


class TestDemoScriptStructure:
    """Test basic structure of demo script."""

    def test_demo_script_exists(self):
        """Test that run_agent_demo.py file exists."""
        demo_script = Path("examples/simple_genomics_discovery/run_agent_demo.py")
        assert demo_script.exists(), f"Demo script not found at {demo_script}"

    def test_demo_script_is_executable(self):
        """Test that demo script has shebang and is executable."""
        demo_script = Path("examples/simple_genomics_discovery/run_agent_demo.py")

        if demo_script.exists():
            with open(demo_script) as f:
                first_line = f.readline()
                # Should have python shebang
                assert first_line.startswith("#!"), "Missing shebang"
                assert "python" in first_line.lower(), "Shebang should reference python"

    def test_demo_script_imports_genomics_agent(self):
        """Test that demo script imports from genomics_agent."""
        demo_script = Path("examples/simple_genomics_discovery/run_agent_demo.py")

        if demo_script.exists():
            with open(demo_script) as f:
                content = f.read()
                assert (
                    "from genomics_agent import" in content
                    or "import genomics_agent" in content
                    or "from examples.simple_genomics_discovery.genomics_agent import"
                    in content
                )

    def test_demo_script_imports_run_genomics_analysis(self):
        """Test that demo script imports run_genomics_analysis function."""
        demo_script = Path("examples/simple_genomics_discovery/run_agent_demo.py")

        if demo_script.exists():
            with open(demo_script) as f:
                content = f.read()
                assert "run_genomics_analysis" in content

    def test_demo_script_has_main_function(self):
        """Test that demo script has main() function."""
        demo_script = Path("examples/simple_genomics_discovery/run_agent_demo.py")

        if demo_script.exists():
            with open(demo_script) as f:
                content = f.read()
                assert "async def main()" in content or "def main()" in content

    def test_demo_script_handles_cli_args(self):
        """Test that demo script handles command line arguments."""
        demo_script = Path("examples/simple_genomics_discovery/run_agent_demo.py")

        if demo_script.exists():
            with open(demo_script) as f:
                content = f.read()
                # Should parse sys.argv for prompt
                assert "sys.argv" in content

    def test_demo_script_validates_data_directory(self):
        """Test that demo script validates data directory exists."""
        demo_script = Path("examples/simple_genomics_discovery/run_agent_demo.py")

        if demo_script.exists():
            with open(demo_script) as f:
                content = f.read()
                # Should check if data dir exists
                assert "data_dir" in content or "data/" in content
                assert "exists()" in content or "is_dir()" in content

    def test_demo_script_validates_reference_genome(self):
        """Test that demo script validates reference genome exists."""
        demo_script = Path("examples/simple_genomics_discovery/run_agent_demo.py")

        if demo_script.exists():
            with open(demo_script) as f:
                content = f.read()
                # Should check reference genome
                assert "reference" in content
                assert "fasta" in content.lower()

    def test_demo_script_displays_results(self):
        """Test that demo script displays results to user."""
        demo_script = Path("examples/simple_genomics_discovery/run_agent_demo.py")

        if demo_script.exists():
            with open(demo_script) as f:
                content = f.read()
                # Should print results
                assert "print(" in content
                # Should show analysis type, success, tools used
                assert "analysis_type" in content or "success" in content

    def test_demo_script_has_asyncio_run(self):
        """Test that demo script uses asyncio.run() for async main."""
        demo_script = Path("examples/simple_genomics_discovery/run_agent_demo.py")

        if demo_script.exists():
            with open(demo_script) as f:
                content = f.read()
                # Should use asyncio.run(main())
                assert "asyncio.run(main())" in content or "asyncio.run(main" in content

    def test_demo_script_has_usage_instructions(self):
        """Test that demo script provides usage instructions."""
        demo_script = Path("examples/simple_genomics_discovery/run_agent_demo.py")

        if demo_script.exists():
            with open(demo_script) as f:
                content = f.read()
                # Should have usage message
                assert "Usage:" in content or "usage:" in content
                # Should show example
                assert (
                    "Example:" in content
                    or "example:" in content
                    or "uv run" in content
                )
