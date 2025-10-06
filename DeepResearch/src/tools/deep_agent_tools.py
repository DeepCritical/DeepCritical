"""
DeepAgent Tools - Pydantic AI tools for DeepAgent operations.

This module implements tools for todo management, filesystem operations, and
other DeepAgent functionality using Pydantic AI patterns that align with
DeepCritical's architecture.
"""

from __future__ import annotations

import uuid
from typing import Any, Dict
from pydantic_ai import RunContext

# Note: defer decorator is not available in current pydantic-ai version

# Import existing DeepCritical types
from ..datatypes.deep_agent_state import (
    TaskStatus,
    DeepAgentState,
    create_todo,
    create_file_info,
)
from ..datatypes.deep_agent_types import TaskRequest
from ..datatypes.deep_agent_tools import (
    WriteTodosRequest,
    WriteTodosResponse,
    ListFilesResponse,
    ReadFileRequest,
    ReadFileResponse,
    WriteFileRequest,
    WriteFileResponse,
    EditFileRequest,
    EditFileResponse,
    TaskRequestModel,
    TaskResponse,
)
from .base import ToolRunner, ToolSpec, ExecutionResult


# Pydantic AI tool functions
# @defer - not available in current pydantic-ai version
def write_todos_tool(
    request: WriteTodosRequest, ctx: RunContext[DeepAgentState]
) -> WriteTodosResponse:
    """Tool for writing todos to the agent state."""
    try:
        todos_created = 0
        for todo_data in request.todos:
            # Create todo with validation
            todo = create_todo(
                content=todo_data["content"],
                priority=todo_data.get("priority", 0),
                tags=todo_data.get("tags", []),
                metadata=todo_data.get("metadata", {}),
            )

            # Set status if provided
            if "status" in todo_data:
                try:
                    todo.status = TaskStatus(todo_data["status"])
                except ValueError:
                    todo.status = TaskStatus.PENDING

            # Add to state
            ctx.state.add_todo(todo)
            todos_created += 1

        return WriteTodosResponse(
            success=True,
            todos_created=todos_created,
            message=f"Successfully created {todos_created} todos",
        )

    except Exception as e:
        return WriteTodosResponse(
            success=False, todos_created=0, message=f"Error creating todos: {str(e)}"
        )


# @defer - not available in current pydantic-ai version
def list_files_tool(ctx: RunContext[DeepAgentState]) -> ListFilesResponse:
    """Tool for listing files in the filesystem."""
    try:
        files = list(ctx.state.files.keys())
        return ListFilesResponse(files=files, count=len(files))
    except Exception:
        return ListFilesResponse(files=[], count=0)


# @defer - not available in current pydantic-ai version
def read_file_tool(
    request: ReadFileRequest, ctx: RunContext[DeepAgentState]
) -> ReadFileResponse:
    """Tool for reading a file from the filesystem."""
    try:
        file_info = ctx.state.get_file(request.file_path)
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
            content=f"Error reading file: {str(e)}",
            file_path=request.file_path,
            lines_read=0,
            total_lines=0,
        )


# @defer - not available in current pydantic-ai version
def write_file_tool(
    request: WriteFileRequest, ctx: RunContext[DeepAgentState]
) -> WriteFileResponse:
    """Tool for writing a file to the filesystem."""
    try:
        # Create or update file info
        file_info = create_file_info(path=request.file_path, content=request.content)

        # Add to state
        ctx.state.add_file(file_info)

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
            message=f"Error writing file: {str(e)}",
        )


# @defer - not available in current pydantic-ai version
def edit_file_tool(
    request: EditFileRequest, ctx: RunContext[DeepAgentState]
) -> EditFileResponse:
    """Tool for editing a file in the filesystem."""
    try:
        file_info = ctx.state.get_file(request.file_path)
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
            elif occurrences == 0:
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

        # Update the file
        ctx.state.update_file_content(request.file_path, new_content)

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
            message=f"Error editing file: {str(e)}",
        )


# @defer - not available in current pydantic-ai version
def task_tool(
    request: TaskRequestModel, ctx: RunContext[DeepAgentState]
) -> TaskResponse:
    """Tool for executing tasks with subagents."""
    try:
        # Generate task ID
        task_id = str(uuid.uuid4())

        # Create task request
        TaskRequest(
            task_id=task_id,
            description=request.description,
            subagent_type=request.subagent_type,
            parameters=request.parameters,
        )

        # Add to active tasks
        ctx.state.active_tasks.append(task_id)

        # TODO: Implement actual subagent execution
        # For now, return a placeholder response
        result = {
            "task_id": task_id,
            "description": request.description,
            "subagent_type": request.subagent_type,
            "status": "executed",
            "message": f"Task executed by {request.subagent_type} subagent",
        }

        # Move from active to completed
        if task_id in ctx.state.active_tasks:
            ctx.state.active_tasks.remove(task_id)
        ctx.state.completed_tasks.append(task_id)

        return TaskResponse(
            success=True,
            task_id=task_id,
            result=result,
            message=f"Task {task_id} executed successfully",
        )

    except Exception as e:
        return TaskResponse(
            success=False,
            task_id="",
            result=None,
            message=f"Error executing task: {str(e)}",
        )


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

    def run(self, params: Dict[str, Any]) -> ExecutionResult:
        try:
            todos_data = params.get("todos", [])
            WriteTodosRequest(todos=todos_data)

            # This would normally be called through Pydantic AI
            # For now, return a mock result
            return ExecutionResult(
                success=True,
                data={
                    "success": True,
                    "todos_created": len(todos_data),
                    "message": f"Successfully created {len(todos_data)} todos",
                },
            )
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

    def run(self, params: Dict[str, Any]) -> ExecutionResult:
        try:
            # This would normally be called through Pydantic AI
            # For now, return a mock result
            return ExecutionResult(success=True, data={"files": [], "count": 0})
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

    def run(self, params: Dict[str, Any]) -> ExecutionResult:
        try:
            request = ReadFileRequest(
                file_path=params.get("file_path", ""),
                offset=params.get("offset", 0),
                limit=params.get("limit", 2000),
            )

            # This would normally be called through Pydantic AI
            # For now, return a mock result
            return ExecutionResult(
                success=True,
                data={
                    "content": "",
                    "file_path": request.file_path,
                    "lines_read": 0,
                    "total_lines": 0,
                },
            )
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

    def run(self, params: Dict[str, Any]) -> ExecutionResult:
        try:
            request = WriteFileRequest(
                file_path=params.get("file_path", ""), content=params.get("content", "")
            )

            # This would normally be called through Pydantic AI
            # For now, return a mock result
            return ExecutionResult(
                success=True,
                data={
                    "success": True,
                    "file_path": request.file_path,
                    "bytes_written": len(request.content.encode("utf-8")),
                    "message": f"Successfully wrote file {request.file_path}",
                },
            )
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

    def run(self, params: Dict[str, Any]) -> ExecutionResult:
        try:
            request = EditFileRequest(
                file_path=params.get("file_path", ""),
                old_string=params.get("old_string", ""),
                new_string=params.get("new_string", ""),
                replace_all=params.get("replace_all", False),
            )

            # This would normally be called through Pydantic AI
            # For now, return a mock result
            return ExecutionResult(
                success=True,
                data={
                    "success": True,
                    "file_path": request.file_path,
                    "replacements_made": 0,
                    "message": f"Successfully edited file {request.file_path}",
                },
            )
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

    def run(self, params: Dict[str, Any]) -> ExecutionResult:
        try:
            request = TaskRequestModel(
                description=params.get("description", ""),
                subagent_type=params.get("subagent_type", ""),
                parameters=params.get("parameters", {}),
            )

            # This would normally be called through Pydantic AI
            # For now, return a mock result
            task_id = str(uuid.uuid4())
            return ExecutionResult(
                success=True,
                data={
                    "success": True,
                    "task_id": task_id,
                    "result": {
                        "task_id": task_id,
                        "description": request.description,
                        "subagent_type": request.subagent_type,
                        "status": "executed",
                    },
                    "message": f"Task {task_id} executed successfully",
                },
            )
        except Exception as e:
            return ExecutionResult(success=False, error=str(e))


# Export all tools
__all__ = [
    # Pydantic AI tools
    "write_todos_tool",
    "list_files_tool",
    "read_file_tool",
    "write_file_tool",
    "edit_file_tool",
    "task_tool",
    # Tool runners
    "WriteTodosToolRunner",
    "ListFilesToolRunner",
    "ReadFileToolRunner",
    "WriteFileToolRunner",
    "EditFileToolRunner",
    "TaskToolRunner",
]
