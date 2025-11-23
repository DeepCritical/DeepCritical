"""Mgrep agent with Pydantic AI integration."""

from pydantic_ai import Agent, RunContext

from DeepResearch.src.tools.mgrep_server import MgrepServer
from DeepResearch.src.utils.config_loader import ModelConfigLoader
from examples.mgrep_semantic_search.mgrep_deps import MgrepDeps

# Load model from config
_model_config = ModelConfigLoader()

# Create agent (matches genomics_agent.py pattern)
mgrep_agent = Agent[MgrepDeps, str](
    model=_model_config.get_default_llm_model(),
    deps_type=MgrepDeps,
    output_type=str,  # Agent will return a string summary
    system_prompt="""You are a code search assistant that helps find relevant code.

    Use the mgrep_search tool to perform semantic code search.
    Analyze results and provide helpful summaries.""",
)


@mgrep_agent.tool
async def mgrep_search(ctx: RunContext[MgrepDeps], query: str, top_k: int = 5) -> str:
    """Search codebase semantically."""
    server = MgrepServer.get_instance()
    results = await server.search(query, top_k=top_k)

    if not results:
        return "No results found."

    output = f"Found {len(results)} results:\n\n"
    for i, result in enumerate(results, 1):
        file_path = result.document.metadata.get("file_path", "unknown")
        score = result.score
        snippet = (
            result.document.content[:200] + "..."
            if len(result.document.content) > 200
            else result.document.content
        )
        output += f"{i}. {file_path} (score: {score:.3f})\n   {snippet}\n\n"

    return output


async def run_mgrep_analysis(prompt: str) -> str:
    """Run mgrep agent analysis."""
    # Ensure server is running
    server = MgrepServer.get_instance()
    server.start()

    # Wait for indexing
    await server.wait_until_ready(min_files=1, idle_grace_seconds=2.0)

    # Run agent
    deps = MgrepDeps()
    result = await mgrep_agent.run(prompt, deps=deps)

    server.stop()
    return result.output  # Correct API: use .output not .data
