"""
DeepAgent Tools - Pydantic AI tools for DeepAgent operations.

This module implements tools for todo management, filesystem operations, and
other DeepAgent functionality using Pydantic AI patterns that align with
DeepCritical's architecture.
"""

from __future__ import annotations

import asyncio
import inspect
import uuid
from typing import Any, Sequence

from pydantic import BaseModel, Field, field_validator
from pydantic_ai import RunContext, Tool

from ..datatypes.deep_agent_runtime import DeepAgentDeps

# Note: defer decorator is not available in current pydantic-ai version
# Import existing DeepCritical types
from ..datatypes.deep_agent_state import (
    DeepAgentState,
    create_file_info,
    create_todo,
)
from ..datatypes.deep_agent_tools import TodoInput
from ..datatypes.deep_agent_types import TaskRequest
from .base import ExecutionResult, ToolRunner, ToolSpec, registry


class WriteTodosRequest(BaseModel):
    """Request for writing todos."""

    todos: list[TodoInput] = Field(..., description="List of todos to write")

    @field_validator("todos")
    @classmethod
    def validate_todos(cls, v: Any) -> list[TodoInput]:
        if not v:
            raise ValueError("Todos list cannot be empty")
        return v


class WriteTodosResponse(BaseModel):
    """Response from writing todos."""

    success: bool = Field(..., description="Whether operation succeeded")
    todos_created: int = Field(..., description="Number of todos created")
    message: str = Field(..., description="Response message")


class ListFilesResponse(BaseModel):
    """Response from listing files."""

    files: list[str] = Field(..., description="List of file paths")
    count: int = Field(..., description="Number of files")


class ReadFileRequest(BaseModel):
    """Request for reading a file."""

    file_path: str = Field(..., description="Path to the file to read")
    offset: int = Field(0, ge=0, description="Line offset to start reading from")
    limit: int = Field(2000, gt=0, description="Maximum number of lines to read")

    @field_validator("file_path", mode="before")
    @classmethod
    def validate_file_path(cls, v: Any) -> str:
        if not v or not str(v).strip():
            raise ValueError("File path cannot be empty")
        return str(v).strip()


class ReadFileResponse(BaseModel):
    """Response from reading a file."""

    content: str = Field(..., description="File content")
    file_path: str = Field(..., description="File path")
    lines_read: int = Field(..., description="Number of lines read")
    total_lines: int = Field(..., description="Total lines in file")


class WriteFileRequest(BaseModel):
    """Request for writing a file."""

    file_path: str = Field(..., description="Path to the file to write")
    content: str = Field(..., description="Content to write to the file")

    @field_validator("file_path", mode="before")
    @classmethod
    def validate_file_path_write(cls, v: Any) -> str:
        if not v or not str(v).strip():
            raise ValueError("File path cannot be empty")
        return str(v).strip()


class WriteFileResponse(BaseModel):
    """Response from writing a file."""

    success: bool = Field(..., description="Whether operation succeeded")
    file_path: str = Field(..., description="File path")
    bytes_written: int = Field(..., description="Number of bytes written")
    message: str = Field(..., description="Response message")


class EditFileRequest(BaseModel):
    """Request for editing a file."""

    file_path: str = Field(..., description="Path to the file to edit")
    old_string: str = Field(..., description="String to replace")
    new_string: str = Field(..., description="Replacement string")
    replace_all: bool = Field(False, description="Whether to replace all occurrences")

    @field_validator("file_path", mode="before")
    @classmethod
    def validate_file_path_edit(cls, v: Any) -> str:
        if not v or not str(v).strip():
            raise ValueError("File path cannot be empty")
        return str(v).strip()

    @field_validator("old_string", mode="before")
    @classmethod
    def validate_old_string(cls, v: Any) -> str:
        if not v:
            raise ValueError("Old string cannot be empty")
        return str(v)


class EditFileResponse(BaseModel):
    """Response from editing a file."""

    success: bool = Field(..., description="Whether operation succeeded")
    file_path: str = Field(..., description="File path")
    replacements_made: int = Field(..., description="Number of replacements made")
    message: str = Field(..., description="Response message")


class TaskRequestModel(BaseModel):
    """Request for task execution."""

    description: str = Field(..., description="Task description")
    subagent_type: str = Field(..., description="Type of subagent to use")
    parameters: dict[str, Any] = Field(
        default_factory=dict, description="Task parameters"
    )

    @field_validator("description", mode="before")
    @classmethod
    def validate_description(cls, v: Any) -> str:
        if not v or not str(v).strip():
            raise ValueError("Task description cannot be empty")
        return str(v).strip()

    @field_validator("subagent_type", mode="before")
    @classmethod
    def validate_subagent_type(cls, v: Any) -> str:
        if not v or not str(v).strip():
            raise ValueError("Subagent type cannot be empty")
        return str(v).strip()


class TaskResponse(BaseModel):
    """Response from task execution."""

    success: bool = Field(..., description="Whether task succeeded")
    task_id: str = Field(..., description="Task identifier")
    result: dict[str, Any] | None = Field(None, description="Task result")
    message: str = Field(..., description="Response message")


def _state_from_context(ctx: RunContext[DeepAgentDeps] | Any) -> DeepAgentState:
    """Extract DeepAgentState from current deps or legacy test contexts."""

    direct_state = getattr(ctx, "state", None)
    if isinstance(direct_state, DeepAgentState):
        return direct_state

    deps = getattr(ctx, "deps", None)
    if isinstance(deps, DeepAgentDeps):
        return deps.state
    if deps is not None and isinstance(getattr(deps, "state", None), DeepAgentState):
        return deps.state
    if isinstance(ctx, DeepAgentState):
        return ctx
    raise TypeError("DeepAgent tool context must provide deps.state or state")


def _deps_from_context(ctx: RunContext[DeepAgentDeps] | Any) -> DeepAgentDeps:
    deps = getattr(ctx, "deps", None)
    if isinstance(deps, DeepAgentDeps):
        return deps
    return DeepAgentDeps(state=_state_from_context(ctx))


def _state_from_params(params: dict[str, Any]) -> DeepAgentState:
    state = params.get("state") or params.get("deep_agent_state")
    if isinstance(state, DeepAgentState):
        return state
    return DeepAgentState(session_id=str(params.get("session_id", "tool_runner")))


def _deps_from_params(params: dict[str, Any]) -> DeepAgentDeps:
    return DeepAgentDeps(
        state=_state_from_params(params),
        orchestrator=params.get("orchestrator"),
        tool_registry=params.get("tool_registry"),
        config=params.get("config", {}),
        metadata=params.get("metadata", {}),
    )


def write_todos_to_state(
    state: DeepAgentState, request: WriteTodosRequest
) -> WriteTodosResponse:
    """Create todo items in ``state``."""

    try:
        todos_created = 0
        for todo_data in request.todos:
            todo = create_todo(
                content=todo_data.content,
                priority=todo_data.priority,
                tags=todo_data.tags,
                metadata=todo_data.metadata,
            )

            todo.status = todo_data.status

            state.add_todo(todo)
            todos_created += 1

        return WriteTodosResponse(
            success=True,
            todos_created=todos_created,
            message=f"Successfully created {todos_created} todos",
        )

    except Exception as e:
        return WriteTodosResponse(
            success=False, todos_created=0, message=f"Error creating todos: {e!s}"
        )


def list_state_files(state: DeepAgentState) -> ListFilesResponse:
    """List files in the state-backed virtual filesystem."""

    try:
        files = list(state.files.keys())
        return ListFilesResponse(files=files, count=len(files))
    except Exception:
        return ListFilesResponse(files=[], count=0)


def read_state_file(
    state: DeepAgentState, request: ReadFileRequest
) -> ReadFileResponse:
    """Read a file from the state-backed virtual filesystem."""

    try:
        file_info = state.get_file(request.file_path)
        if not file_info:
            return ReadFileResponse(
                content=f"Error: File '{request.file_path}' not found",
                file_path=request.file_path,
                lines_read=0,
                total_lines=0,
            )

        # Handle empty file
        if not file_info.content or file_info.content.strip() == "":
            return ReadFileResponse(
                content="System reminder: File exists but has empty contents",
                file_path=request.file_path,
                lines_read=0,
                total_lines=0,
            )

        # Split content into lines
        lines = file_info.content.splitlines()
        total_lines = len(lines)

        # Apply line offset and limit
        start_idx = request.offset
        end_idx = min(start_idx + request.limit, total_lines)

        # Handle case where offset is beyond file length
        if start_idx >= total_lines:
            return ReadFileResponse(
                content=f"Error: Line offset {request.offset} exceeds file length ({total_lines} lines)",
                file_path=request.file_path,
                lines_read=0,
                total_lines=total_lines,
            )

        # Format output with line numbers (cat -n format)
        result_lines = []
        for i in range(start_idx, end_idx):
            line_content = lines[i]

            # Truncate lines longer than 2000 characters
            if len(line_content) > 2000:
                line_content = line_content[:2000]

            # Line numbers start at 1, so add 1 to the index
            line_number = i + 1
            result_lines.append(f"{line_number:6d}\t{line_content}")

        content = "\n".join(result_lines)
        lines_read = len(result_lines)

        return ReadFileResponse(
            content=content,
            file_path=request.file_path,
            lines_read=lines_read,
            total_lines=total_lines,
        )

    except Exception as e:
        return ReadFileResponse(
            content=f"Error reading file: {e!s}",
            file_path=request.file_path,
            lines_read=0,
            total_lines=0,
        )


def write_state_file(
    state: DeepAgentState, request: WriteFileRequest
) -> WriteFileResponse:
    """Write a file to the state-backed virtual filesystem."""

    try:
        file_info = create_file_info(path=request.file_path, content=request.content)
        state.add_file(file_info)

        return WriteFileResponse(
            success=True,
            file_path=request.file_path,
            bytes_written=len(request.content.encode("utf-8")),
            message=f"Successfully wrote file {request.file_path}",
        )

    except Exception as e:
        return WriteFileResponse(
            success=False,
            file_path=request.file_path,
            bytes_written=0,
            message=f"Error writing file: {e!s}",
        )


def edit_state_file(
    state: DeepAgentState, request: EditFileRequest
) -> EditFileResponse:
    """Edit a file in the state-backed virtual filesystem."""

    try:
        file_info = state.get_file(request.file_path)
        if not file_info:
            return EditFileResponse(
                success=False,
                file_path=request.file_path,
                replacements_made=0,
                message=f"Error: File '{request.file_path}' not found",
            )

        # Check if old_string exists in the file
        if request.old_string not in file_info.content:
            return EditFileResponse(
                success=False,
                file_path=request.file_path,
                replacements_made=0,
                message=f"Error: String not found in file: '{request.old_string}'",
            )

        # If not replace_all, check for uniqueness
        if not request.replace_all:
            occurrences = file_info.content.count(request.old_string)
            if occurrences > 1:
                return EditFileResponse(
                    success=False,
                    file_path=request.file_path,
                    replacements_made=0,
                    message=f"Error: String '{request.old_string}' appears {occurrences} times in file. Use replace_all=True to replace all instances, or provide a more specific string with surrounding context.",
                )
            if occurrences == 0:
                return EditFileResponse(
                    success=False,
                    file_path=request.file_path,
                    replacements_made=0,
                    message=f"Error: String not found in file: '{request.old_string}'",
                )

        # Perform the replacement
        if request.replace_all:
            new_content = file_info.content.replace(
                request.old_string, request.new_string
            )
            replacement_count = file_info.content.count(request.old_string)
            result_msg = f"Successfully replaced {replacement_count} instance(s) of the string in '{request.file_path}'"
        else:
            new_content = file_info.content.replace(
                request.old_string, request.new_string, 1
            )
            replacement_count = 1
            result_msg = f"Successfully replaced string in '{request.file_path}'"

        state.update_file_content(request.file_path, new_content)

        return EditFileResponse(
            success=True,
            file_path=request.file_path,
            replacements_made=replacement_count,
            message=result_msg,
        )

    except Exception as e:
        return EditFileResponse(
            success=False,
            file_path=request.file_path,
            replacements_made=0,
            message=f"Error editing file: {e!s}",
        )


async def _maybe_await(value: Any) -> Any:
    if inspect.isawaitable(value):
        return await value
    return value


async def delegate_task(deps: DeepAgentDeps, request: TaskRequestModel) -> TaskResponse:
    """Delegate work to an orchestrator or registered in-process subagent."""

    task_id = str(uuid.uuid4())
    try:
        task_request = TaskRequest(
            task_id=task_id,
            description=request.description,
            subagent_type=request.subagent_type,
            parameters=request.parameters,
        )

        deps.state.active_tasks.append(task_id)

        result_payload: dict[str, Any]
        orchestrator = deps.orchestrator
        if orchestrator is not None:
            if hasattr(orchestrator, "execute_task"):
                raw_result = await _maybe_await(orchestrator.execute_task(task_request))
            elif hasattr(orchestrator, "execute_with_agent"):
                raw_result = await _maybe_await(
                    orchestrator.execute_with_agent(
                        request.subagent_type, request.description, deps.state
                    )
                )
            else:
                raw_result = None

            if raw_result is None:
                if task_id in deps.state.active_tasks:
                    deps.state.active_tasks.remove(task_id)
                return TaskResponse(
                    success=False,
                    task_id=task_id,
                    result=None,
                    message="Configured orchestrator does not expose a DeepAgent task execution method",
                )
            if getattr(raw_result, "success", True) is False:
                if task_id in deps.state.active_tasks:
                    deps.state.active_tasks.remove(task_id)
                return TaskResponse(
                    success=False,
                    task_id=task_id,
                    result=None,
                    message=getattr(raw_result, "error", None)
                    or "Subagent task execution failed",
                )
            if isinstance(raw_result, dict):
                result_payload = raw_result
            elif hasattr(raw_result, "result") and raw_result.result is not None:
                result_payload = dict(raw_result.result)
            else:
                result_payload = {"output": raw_result}
        else:
            registry_map = deps.state.shared_state.get("subagent_registry", {})
            subagent = registry_map.get(request.subagent_type)
            if subagent is None:
                if task_id in deps.state.active_tasks:
                    deps.state.active_tasks.remove(task_id)
                return TaskResponse(
                    success=False,
                    task_id=task_id,
                    result=None,
                    message=f"No subagent '{request.subagent_type}' registered",
                )

            raw_result = await _maybe_await(subagent.run(request.description))
            payload = getattr(raw_result, "output", raw_result)
            result_payload = (
                dict(payload) if isinstance(payload, dict) else {"output": payload}
            )

        result_payload.update(
            {
                "task_id": task_id,
                "description": request.description,
                "subagent_type": request.subagent_type,
                "status": "completed",
            }
        )

        if task_id in deps.state.active_tasks:
            deps.state.active_tasks.remove(task_id)
        deps.state.completed_tasks.append(task_id)

        return TaskResponse(
            success=True,
            task_id=task_id,
            result=result_payload,
            message=f"Task {task_id} executed successfully",
        )

    except Exception as e:
        if task_id in deps.state.active_tasks:
            deps.state.active_tasks.remove(task_id)
        return TaskResponse(
            success=False,
            task_id=task_id,
            result=None,
            message=f"Error executing task: {e!s}",
        )


def _run_task_delegation_sync(
    deps: DeepAgentDeps, request: TaskRequestModel
) -> TaskResponse:
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(delegate_task(deps, request))
    raise RuntimeError(
        "TaskToolRunner cannot execute async task delegation while an event loop is running"
    )


# Pydantic AI tool functions
def write_todos_tool(
    ctx: RunContext[DeepAgentDeps], request: WriteTodosRequest
) -> WriteTodosResponse:
    """Tool for writing todos to the agent state."""

    return write_todos_to_state(_state_from_context(ctx), request)


def list_files_tool(ctx: RunContext[DeepAgentDeps]) -> ListFilesResponse:
    """Tool for listing files in the state-backed filesystem."""

    return list_state_files(_state_from_context(ctx))


def read_file_tool(
    ctx: RunContext[DeepAgentDeps], request: ReadFileRequest
) -> ReadFileResponse:
    """Tool for reading a file from the state-backed filesystem."""

    return read_state_file(_state_from_context(ctx), request)


def write_file_tool(
    ctx: RunContext[DeepAgentDeps], request: WriteFileRequest
) -> WriteFileResponse:
    """Tool for writing a file to the state-backed filesystem."""

    return write_state_file(_state_from_context(ctx), request)


def edit_file_tool(
    ctx: RunContext[DeepAgentDeps], request: EditFileRequest
) -> EditFileResponse:
    """Tool for editing a file in the state-backed filesystem."""

    return edit_state_file(_state_from_context(ctx), request)


async def task_tool(
    ctx: RunContext[DeepAgentDeps], request: TaskRequestModel
) -> TaskResponse:
    """Tool for executing tasks with registered subagents."""

    return await delegate_task(_deps_from_context(ctx), request)


# Tool runner implementations for compatibility with existing system
class WriteTodosToolRunner(ToolRunner):
    """Tool runner for write todos functionality."""

    def __init__(self):
        super().__init__(
            ToolSpec(
                name="write_todos",
                description="Create and manage a structured task list for your current work session",
                inputs={
                    "todos": "JSON list of todo objects with content, status, priority fields"
                },
                outputs={
                    "success": "BOOLEAN",
                    "todos_created": "INTEGER",
                    "message": "TEXT",
                },
            )
        )

    def run(self, params: dict[str, Any]) -> ExecutionResult:
        try:
            request = WriteTodosRequest(todos=params.get("todos", []))
            response = write_todos_to_state(_state_from_params(params), request)
            return ExecutionResult(success=response.success, data=response.model_dump())
        except Exception as e:
            return ExecutionResult(success=False, error=str(e))


class ListFilesToolRunner(ToolRunner):
    """Tool runner for list files functionality."""

    def __init__(self):
        super().__init__(
            ToolSpec(
                name="list_files",
                description="List all files in the local filesystem",
                inputs={},
                outputs={"files": "JSON list of file paths", "count": "INTEGER"},
            )
        )

    def run(self, params: dict[str, Any]) -> ExecutionResult:
        try:
            response = list_state_files(_state_from_params(params))
            return ExecutionResult(success=True, data=response.model_dump())
        except Exception as e:
            return ExecutionResult(success=False, error=str(e))


class ReadFileToolRunner(ToolRunner):
    """Tool runner for read file functionality."""

    def __init__(self):
        super().__init__(
            ToolSpec(
                name="read_file",
                description="Read a file from the local filesystem",
                inputs={"file_path": "TEXT", "offset": "INTEGER", "limit": "INTEGER"},
                outputs={
                    "content": "TEXT",
                    "file_path": "TEXT",
                    "lines_read": "INTEGER",
                    "total_lines": "INTEGER",
                },
            )
        )

    def run(self, params: dict[str, Any]) -> ExecutionResult:
        try:
            request = ReadFileRequest(
                file_path=params.get("file_path", ""),
                offset=params.get("offset", 0),
                limit=params.get("limit", 2000),
            )

            response = read_state_file(_state_from_params(params), request)
            return ExecutionResult(success=True, data=response.model_dump())
        except Exception as e:
            return ExecutionResult(success=False, error=str(e))


class WriteFileToolRunner(ToolRunner):
    """Tool runner for write file functionality."""

    def __init__(self):
        super().__init__(
            ToolSpec(
                name="write_file",
                description="Write content to a file in the local filesystem",
                inputs={"file_path": "TEXT", "content": "TEXT"},
                outputs={
                    "success": "BOOLEAN",
                    "file_path": "TEXT",
                    "bytes_written": "INTEGER",
                    "message": "TEXT",
                },
            )
        )

    def run(self, params: dict[str, Any]) -> ExecutionResult:
        try:
            request = WriteFileRequest(
                file_path=params.get("file_path", ""), content=params.get("content", "")
            )

            response = write_state_file(_state_from_params(params), request)
            return ExecutionResult(success=response.success, data=response.model_dump())
        except Exception as e:
            return ExecutionResult(success=False, error=str(e))


class EditFileToolRunner(ToolRunner):
    """Tool runner for edit file functionality."""

    def __init__(self):
        super().__init__(
            ToolSpec(
                name="edit_file",
                description="Edit a file by replacing strings",
                inputs={
                    "file_path": "TEXT",
                    "old_string": "TEXT",
                    "new_string": "TEXT",
                    "replace_all": "BOOLEAN",
                },
                outputs={
                    "success": "BOOLEAN",
                    "file_path": "TEXT",
                    "replacements_made": "INTEGER",
                    "message": "TEXT",
                },
            )
        )

    def run(self, params: dict[str, Any]) -> ExecutionResult:
        try:
            request = EditFileRequest(
                file_path=params.get("file_path", ""),
                old_string=params.get("old_string", ""),
                new_string=params.get("new_string", ""),
                replace_all=params.get("replace_all", False),
            )

            response = edit_state_file(_state_from_params(params), request)
            return ExecutionResult(success=response.success, data=response.model_dump())
        except Exception as e:
            return ExecutionResult(success=False, error=str(e))


class TaskToolRunner(ToolRunner):
    """Tool runner for task execution functionality."""

    def __init__(self):
        super().__init__(
            ToolSpec(
                name="task",
                description="Launch an ephemeral subagent to handle complex, multi-step independent tasks",
                inputs={
                    "description": "TEXT",
                    "subagent_type": "TEXT",
                    "parameters": "JSON",
                },
                outputs={
                    "success": "BOOLEAN",
                    "task_id": "TEXT",
                    "result": "JSON",
                    "message": "TEXT",
                },
            )
        )

    def run(self, params: dict[str, Any]) -> ExecutionResult:
        try:
            request = TaskRequestModel(
                description=params.get("description", ""),
                subagent_type=params.get("subagent_type", ""),
                parameters=params.get("parameters", {}),
            )

            response = _run_task_delegation_sync(_deps_from_params(params), request)
            return ExecutionResult(
                success=response.success,
                data=response.model_dump(),
                error=None if response.success else response.message,
            )
        except Exception as e:
            return ExecutionResult(success=False, error=str(e))


DEEP_AGENT_TOOL_MAP = {
    "write_todos": write_todos_tool,
    "list_files": list_files_tool,
    "read_file": read_file_tool,
    "write_file": write_file_tool,
    "edit_file": edit_file_tool,
    "task": task_tool,
}

DEEP_AGENT_TOOL_RUNNERS = {
    "write_todos": WriteTodosToolRunner,
    "list_files": ListFilesToolRunner,
    "read_file": ReadFileToolRunner,
    "write_file": WriteFileToolRunner,
    "edit_file": EditFileToolRunner,
    "task": TaskToolRunner,
}


def get_deep_agent_tools() -> list[Any]:
    """Return named Pydantic AI tools supported by the MVP runtime."""

    return [Tool(tool, name=name) for name, tool in DEEP_AGENT_TOOL_MAP.items()]


def resolve_deep_agent_tools(tool_names: Sequence[str]) -> list[Any]:
    """Resolve configured DeepAgent tool names to named Pydantic AI tools."""

    unknown = [name for name in tool_names if name not in DEEP_AGENT_TOOL_MAP]
    if unknown:
        known = ", ".join(sorted(DEEP_AGENT_TOOL_MAP))
        raise ValueError(f"Unknown DeepAgent tool(s): {unknown}. Known tools: {known}")
    return [Tool(DEEP_AGENT_TOOL_MAP[name], name=name) for name in tool_names]


def register_deep_agent_tool_runners() -> None:
    """Register DeepAgent ToolRunners with the legacy tool registry."""

    for name, runner in DEEP_AGENT_TOOL_RUNNERS.items():
        registry.register(name, runner)


register_deep_agent_tool_runners()


# Export all tools
__all__ = [
    # Runtime helpers
    "DEEP_AGENT_TOOL_MAP",
    "DEEP_AGENT_TOOL_RUNNERS",
    "EditFileRequest",
    "EditFileResponse",
    "EditFileToolRunner",
    "ListFilesResponse",
    "ListFilesToolRunner",
    "ReadFileRequest",
    "ReadFileResponse",
    "ReadFileToolRunner",
    "TaskRequestModel",
    "TaskResponse",
    "TaskToolRunner",
    "TodoInput",
    "WriteFileRequest",
    "WriteFileResponse",
    "WriteFileToolRunner",
    # Request/Response models
    "WriteTodosRequest",
    "WriteTodosResponse",
    # Tool runners
    "WriteTodosToolRunner",
    "delegate_task",
    "edit_file_tool",
    "edit_state_file",
    "get_deep_agent_tools",
    "list_files_tool",
    "list_state_files",
    "read_file_tool",
    "read_state_file",
    "register_deep_agent_tool_runners",
    "resolve_deep_agent_tools",
    "task_tool",
    "write_file_tool",
    "write_state_file",
    "write_todos_to_state",
    # Pydantic AI tools
    "write_todos_tool",
]
