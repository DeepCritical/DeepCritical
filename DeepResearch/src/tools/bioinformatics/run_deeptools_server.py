"""
Standalone runner for the Deeptools MCP Server.

This script can be used to run the Deeptools MCP server either as a FastMCP server
or as a standalone MCP server with Pydantic AI integration.
"""

import argparse
import sys
from pathlib import Path

# Add the parent directory to the path so we can import the server
sys.path.insert(0, str(Path(__file__).parent))

from deeptools_server import DeeptoolsServer  # type: ignore[import]


def main():
    parser = argparse.ArgumentParser(description="Run Deeptools MCP Server")
    parser.add_argument(
        "--mode",
        choices=["fastmcp", "mcp", "test"],
        default="fastmcp",
        help="Server mode: fastmcp (FastMCP server), mcp (MCP with Pydantic AI), test (test mode)",
    )
    parser.add_argument(
        "--port", type=int, default=8000, help="Port for HTTP server mode"
    )
    parser.add_argument("--host", default="0.0.0.0", help="Host for HTTP server mode")
    parser.add_argument(
        "--no-fastmcp", action="store_true", help="Disable FastMCP integration"
    )

    args = parser.parse_args()

    # Create server instance
    enable_fastmcp = not args.no_fastmcp
    server = DeeptoolsServer(enable_fastmcp=enable_fastmcp)

    if args.mode == "fastmcp":
        if not enable_fastmcp:
            sys.exit(1)
        server.run_fastmcp_server()

    elif args.mode == "mcp":
        # For MCP mode, you would typically integrate with an MCP client
        # This is a placeholder for the actual MCP integration
        pass

    elif args.mode == "test":
        # Test some basic functionality
        server.list_tools()

        server.get_server_info()

        # Test a mock operation
        server.run(
            {
                "operation": "compute_gc_bias",
                "bamfile": "/tmp/test.bam",
                "effective_genome_size": 3000000000,
                "genome": "/tmp/test.2bit",
                "fragment_length": 200,
            }
        )


if __name__ == "__main__":
    main()
