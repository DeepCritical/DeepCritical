"""Mgrep agent with Pydantic AI integration."""

from functools import lru_cache

from pydantic_ai import Agent, RunContext

from DeepResearch.src.tools.mgrep_server import MgrepServer
from DeepResearch.src.utils.config_loader import ModelConfigLoader
from examples.mgrep_semantic_search.mgrep_deps import MgrepDeps


@lru_cache(maxsize=1)
def _get_model_config() -> ModelConfigLoader:
    """
    Get model config loader singleton.

    Uncle Bob: "Avoid module-level side effects!" - Defer file I/O until first use.
    Uses lru_cache to ensure config is only loaded once.
    """
    return ModelConfigLoader()


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


@lru_cache(maxsize=1)
def get_mgrep_agent() -> Agent[MgrepDeps, str]:
    """
    Get or create mgrep agent singleton.

    Uncle Bob: "Defer expensive operations" - Create agent on first use, not at import.

    Returns:
        Configured mgrep agent with mgrep_search tool registered
    """
    config = _get_model_config()

    agent = Agent[MgrepDeps, str](
        model=config.get_default_llm_model(),
        deps_type=MgrepDeps,
        output_type=str,
        system_prompt="""You are a code search assistant that helps find relevant code.

    Use the mgrep_search tool to perform semantic code search.
    Analyze results and provide helpful summaries.""",
    )

    # Register tool
    agent.tool(mgrep_search)

    return agent


# Backward compatibility: provide mgrep_agent at module level
# But now it's a lazy property that creates agent on first access
def __getattr__(name: str):
    """Lazy module attribute access for backward compatibility."""
    if name == "mgrep_agent":
        return get_mgrep_agent()
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


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
