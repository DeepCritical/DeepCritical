"""Shared fixtures for Pydantic AI integration tests."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Iterable, Sequence, TypedDict

import pytest

try:
    from DeepResearch.src.datatypes.agents import AgentDependencies
except ImportError as exc:  # pragma: no cover - exercised in missing-deps envs
    pytest.skip(
        f"DeepResearch optional dependencies unavailable: {exc}",
        allow_module_level=True,
    )

try:
    from pydantic_ai import Agent, RunContext
    from pydantic_ai.models.test import TestModel
except ModuleNotFoundError as exc:  # pragma: no cover - exercised in CI skips
    pytest.skip(
        f"pydantic_ai dependency unavailable: {exc}",
        allow_module_level=True,
    )


class ContextState(TypedDict):
    """Structured context captured during tool execution."""

    queries: list[str]
    numbers: list[list[int]]
    combined: list[str]


class AgentExecutionState(TypedDict, total=False):
    """Execution metadata collected for assertions."""

    calls: list[tuple[str, Any]]
    deps: list[Any]
    context: ContextState
    failures: int
    formatter_calls: int
    unstable_calls: int
    resilient_calls: int


@dataclass(slots=True)
class AgentTestBundle:
    """Container for a test agent instance and captured execution state."""

    agent: Agent
    state: AgentExecutionState


ToolOverride = Callable[[Agent, AgentExecutionState], None]


@pytest.fixture
def make_test_agent() -> Callable[
    [Sequence[str] | None, int, dict[str, ToolOverride] | None], AgentTestBundle
]:
    """Factory fixture that creates configured test agents.

    The returned callable builds a Pydantic AI ``Agent`` backed by ``TestModel`` that
    automatically exercises the registered tools. Execution metadata such as tool
    order and dependency objects are captured in the returned bundle's ``state``
    dictionary for downstream assertions.
    """

    def _factory(
        call_tools: Sequence[str] | None = None,
        seed: int = 2024,
        overrides: dict[str, ToolOverride] | None = None,
    ) -> AgentTestBundle:
        tools_to_register: list[str] = list(call_tools or ("web_search", "calculator"))
        overrides = overrides or {}
        state: AgentExecutionState = {
            "calls": [],
            "deps": [],
            "context": {"queries": [], "numbers": [], "combined": []},
        }

        agent = Agent(
            model=TestModel(call_tools=tools_to_register, seed=seed),
            deps_type=AgentDependencies,
            system_prompt="You are a reliable research copilot.",
            instructions="Respond with structured JSON output.",
        )

        def _register_default_web_search() -> None:
            @agent.tool
            async def web_search(
                ctx: RunContext[AgentDependencies],
                query: str,
            ) -> dict[str, Any]:
                """Mock web search tool returning deterministic results."""
                state["calls"].append(("web_search", query))
                state["deps"].append(ctx.deps)
                state["context"]["queries"].append(query)
                ctx.deps.tools.append("web_search")
                return {
                    "query": query,
                    "results": [f"Insight for {query}"],
                    "source_count": 1,
                }

        def _register_default_calculator() -> None:
            @agent.tool
            async def calculator(
                ctx: RunContext[AgentDependencies],
                numbers: list[int],
            ) -> dict[str, Any]:
                """Aggregate numeric inputs and expose summary statistics."""
                state["calls"].append(("calculator", tuple(numbers)))
                state["deps"].append(ctx.deps)
                state["context"]["numbers"].append(list(numbers))
                ctx.deps.tools.append("calculator")
                if state["context"]["queries"]:
                    latest_query = state["context"]["queries"][-1]
                    state["context"]["combined"].append(
                        f"{latest_query}->{sum(numbers)}"
                    )
                return {"total": sum(numbers), "count": len(numbers)}

        for tool_name in tools_to_register:
            if tool_name in overrides:
                overrides[tool_name](agent, state)
            elif tool_name == "web_search":
                _register_default_web_search()
            elif tool_name == "calculator":
                _register_default_calculator()
            else:  # pragma: no cover - safety for unexpected tools
                raise ValueError(f"Unknown default tool '{tool_name}'")

        bundle = AgentTestBundle(agent=agent, state=state)
        agent._test_state = state  # type: ignore[attr-defined]
        return bundle

    return _factory


@pytest.fixture
def agent_bundle(make_test_agent: Callable[..., AgentTestBundle]) -> AgentTestBundle:
    """Default agent bundle with web search and calculator tools."""

    return make_test_agent()


@pytest.fixture
def agent_dependencies() -> AgentDependencies:
    """Provide representative dependencies for agent execution."""

    return AgentDependencies(
        config={"api_key": "test-key", "timeout": 30},
        tools=["bootstrap"],
        other_agents=["planner", "executor"],
        data_sources=["knowledge_base", "vector_store"],
    )


@pytest.fixture
def collect_tool_names(agent_bundle: AgentTestBundle) -> Iterable[str]:
    """Helper fixture returning registered tool names for assertions."""

    return agent_bundle.agent._function_toolset.tools.keys()
