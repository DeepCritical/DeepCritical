#!/usr/bin/env python3
"""
Demo script for genomics agent with MCP server integration.

Usage:
    uv run python run_agent_demo.py "Find variants in sample.bam"

Reference: burner_docs/haplotype_agent/02_implementation_plan.md Phase 6
"""

import asyncio
import sys
from pathlib import Path

from examples.simple_genomics_discovery.genomics_agent import run_genomics_analysis


async def main():
    if len(sys.argv) < 2:
        print("Usage: uv run python run_agent_demo.py <prompt>")
        print("Example: uv run python run_agent_demo.py 'Find variants in sample.bam'")
        sys.exit(1)

    prompt = sys.argv[1]

    # Setup paths
    demo_dir = Path(__file__).parent
    data_dir = demo_dir / "data"
    output_dir = demo_dir / "output"
    reference = data_dir / "human_g1k_v37.20.21.fasta"

    # Validate setup
    if not data_dir.exists():
        print("ERROR: data/ directory not found. Run ./download_data.sh first")
        sys.exit(1)

    if not reference.exists():
        print(f"ERROR: Reference genome not found: {reference}")
        print("Run ./download_data.sh to download reference")
        sys.exit(1)

    output_dir.mkdir(exist_ok=True)

    print("Running genomics analysis...")
    print(f"Prompt: {prompt}")
    print(f"Data: {data_dir}")
    print(f"Output: {output_dir}")
    print()

    # Run agent
    try:
        result = await run_genomics_analysis(
            prompt=prompt,
            data_dir=data_dir,
            output_dir=output_dir,
            reference_genome=reference,
        )
    except Exception as e:
        print(f"ERROR: Agent execution failed: {e}")
        sys.exit(1)

    # Display results
    print("=" * 60)
    print("RESULTS")
    print("=" * 60)
    print(f"Analysis Type: {result.analysis_type}")
    print(f"Success: {result.success}")
    print(f"Tools Used: {', '.join(result.tools_used)}")
    print("\nOutput Files:")
    for name, path in result.output_files.items():
        print(f"  - {name}: {path}")

    if result.variants_found is not None:
        print(f"\nVariants Found: {result.variants_found}")

    print("\nSummary:")
    print(f"  {result.summary}")

    if result.error:
        print(f"\nError: {result.error}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
