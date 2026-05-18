from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from DeepResearch.src.datatypes.deep_agent_runtime import DeepAgentDeps
from DeepResearch.src.datatypes.deep_agent_state import DeepAgentState, TaskStatus
from DeepResearch.src.tools.deep_agent_tools import (
    EditFileRequest,
    ReadFileRequest,
    TaskRequestModel,
    TodoInput,
    WriteFileRequest,
    WriteTodosRequest,
    edit_file_tool,
    list_files_tool,
    read_file_tool,
    task_tool,
    write_file_tool,
    write_todos_tool,
)


def _ctx(state: DeepAgentState, **deps_kwargs) -> SimpleNamespace:
    return SimpleNamespace(deps=DeepAgentDeps(state=state, **deps_kwargs))


def test_todo_tool_mutates_state() -> None:
    state = DeepAgentState(session_id="state-tools")

    response = write_todos_tool(
        _ctx(state),
        WriteTodosRequest(
            todos=[
                TodoInput(content="Draft plan", priority=2),
                TodoInput(content="Run tests", status=TaskStatus.IN_PROGRESS),
            ]
        ),
    )

    assert response.success
    assert response.todos_created == 2
    assert [todo.content for todo in state.todos] == ["Draft plan", "Run tests"]
    assert state.todos[1].status.value == "in_progress"


def test_write_todos_request_schema_exposes_todo_content() -> None:
    schema = WriteTodosRequest.model_json_schema()
    todo_items_schema = schema["properties"]["todos"]["items"]

    if "$ref" in todo_items_schema:
        ref_name = todo_items_schema["$ref"].rsplit("/", 1)[-1]
        todo_items_schema = schema["$defs"][ref_name]

    assert "content" in todo_items_schema["properties"]
    assert "content" in todo_items_schema["required"]


def test_write_todos_request_accepts_dict_payloads() -> None:
    request = WriteTodosRequest.model_validate(
        {"todos": [{"content": "Draft plan", "status": "in_progress"}]}
    )

    assert request.todos[0].content == "Draft plan"
    assert request.todos[0].status.value == "in_progress"


def test_file_tools_use_state_backed_filesystem() -> None:
    state = DeepAgentState(session_id="files")
    ctx = _ctx(state)

    write_response = write_file_tool(
        ctx,
        WriteFileRequest(file_path="/notes.md", content="alpha\nbeta\nalpha"),
    )
    assert write_response.success
    assert list_files_tool(ctx).files == ["/notes.md"]

    read_response = read_file_tool(ctx, ReadFileRequest(file_path="/notes.md", limit=2))
    assert read_response.lines_read == 2
    assert "alpha" in read_response.content

    edit_response = edit_file_tool(
        ctx,
        EditFileRequest(
            file_path="/notes.md",
            old_string="alpha",
            new_string="gamma",
            replace_all=True,
        ),
    )
    assert edit_response.success
    assert edit_response.replacements_made == 2
    file_info = state.get_file("/notes.md")
    assert file_info is not None
    assert file_info.content == "gamma\nbeta\ngamma"


def test_read_missing_file_is_deterministic() -> None:
    state = DeepAgentState(session_id="missing")

    response = read_file_tool(_ctx(state), ReadFileRequest(file_path="/missing.md"))

    assert response.lines_read == 0
    assert response.total_lines == 0
    assert "not found" in response.content


@pytest.mark.asyncio
async def test_task_tool_runs_registered_subagent() -> None:
    state = DeepAgentState(session_id="task")
    subagent = MagicMock()
    subagent.run = AsyncMock(return_value=SimpleNamespace(output={"answer": "yes"}))
    state.shared_state["subagent_registry"] = {"research": subagent}

    response = await task_tool(
        _ctx(state),
        TaskRequestModel(
            description="Investigate CRISPR safety",
            subagent_type="research",
            parameters={},
        ),
    )

    assert response.success
    assert response.result is not None
    assert response.result["answer"] == "yes"
    assert response.task_id in state.completed_tasks
    assert response.task_id not in state.active_tasks
    subagent.run.assert_awaited_once_with("Investigate CRISPR safety")


@pytest.mark.asyncio
async def test_task_tool_reports_missing_subagent() -> None:
    state = DeepAgentState(session_id="missing-task")

    response = await task_tool(
        _ctx(state),
        TaskRequestModel(
            description="Do work",
            subagent_type="unknown",
            parameters={},
        ),
    )

    assert response.success is False
    assert "No subagent" in response.message
    assert response.task_id not in state.active_tasks


@pytest.mark.asyncio
async def test_task_tool_propagates_orchestrator_failure() -> None:
    state = DeepAgentState(session_id="orchestrator-failure")
    orchestrator = SimpleNamespace(
        execute_with_agent=AsyncMock(
            return_value=SimpleNamespace(
                success=False, error="agent failed", result=None
            )
        )
    )

    response = await task_tool(
        _ctx(state, orchestrator=orchestrator),
        TaskRequestModel(
            description="Do work",
            subagent_type="research",
            parameters={},
        ),
    )

    assert response.success is False
    assert response.message == "agent failed"
    assert response.task_id not in state.active_tasks
    assert response.task_id not in state.completed_tasks
