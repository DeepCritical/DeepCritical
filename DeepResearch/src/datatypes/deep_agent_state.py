"""
DeepAgent State - Pydantic models for DeepAgent state management.

This module defines Pydantic models for managing agent state, including todos,
filesystem state, and other stateful components that align with DeepCritical's
Pydantic AI architecture.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

# Import existing DeepCritical types
from .deep_agent_types import AgentContext


class TaskStatus(str, Enum):
    """Status of a task."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class Todo(BaseModel):
    """Todo item for task tracking."""

    id: str = Field(..., description="Unique todo identifier")
    content: str = Field(..., description="Todo content/description")
    status: TaskStatus = Field(TaskStatus.PENDING, description="Todo status")
    created_at: datetime = Field(
        default_factory=datetime.now, description="Creation timestamp"
    )
    updated_at: datetime | None = Field(None, description="Last update timestamp")
    priority: int = Field(0, description="Priority level (higher = more important)")
    tags: list[str] = Field(default_factory=list, description="Todo tags")
    metadata: dict[str, Any] = Field(
        default_factory=dict, description="Additional metadata"
    )

    @field_validator("content", mode="before")
    @classmethod
    def validate_content(cls, v):
        if not v or not v.strip():
            msg = "Todo content cannot be empty"
            raise ValueError(msg)
        return v.strip()

    def mark_in_progress(self) -> None:
        """Mark todo as in progress."""
        self.status = TaskStatus.IN_PROGRESS
        self.updated_at = datetime.now()

    def mark_completed(self) -> None:
        """Mark todo as completed."""
        self.status = TaskStatus.COMPLETED
        self.updated_at = datetime.now()

    def mark_failed(self) -> None:
        """Mark todo as failed."""
        self.status = TaskStatus.FAILED
        self.updated_at = datetime.now()

    model_config = ConfigDict(json_schema_extra={})


class FileInfo(BaseModel):
    """Information about a file in the filesystem."""

    path: str = Field(..., description="File path")
    content: str = Field("", description="File content")
    size: int = Field(0, description="File size in bytes")
    created_at: datetime = Field(
        default_factory=datetime.now, description="Creation timestamp"
    )
    updated_at: datetime | None = Field(None, description="Last update timestamp")
    metadata: dict[str, Any] = Field(default_factory=dict, description="File metadata")

    @field_validator("path", mode="before")
    @classmethod
    def validate_path(cls, v):
        if not v or not v.strip():
            msg = "File path cannot be empty"
            raise ValueError(msg)
        return v.strip()

    def update_content(self, new_content: str) -> None:
        """Update file content."""
        self.content = new_content
        self.size = len(new_content.encode("utf-8"))
        self.updated_at = datetime.now()

    model_config = ConfigDict(json_schema_extra={})


class FilesystemState(BaseModel):
    """State for filesystem operations."""

    files: dict[str, FileInfo] = Field(
        default_factory=dict, description="Files in the filesystem"
    )
    current_directory: str = Field("/", description="Current working directory")
    permissions: dict[str, list[str]] = Field(
        default_factory=dict, description="File permissions"
    )

    def add_file(self, file_info: FileInfo) -> None:
        """Add a file to the filesystem."""
        self.files[file_info.path] = file_info

    def get_file(self, path: str) -> FileInfo | None:
        """Get a file by path."""
        return self.files.get(path)

    def remove_file(self, path: str) -> bool:
        """Remove a file from the filesystem."""
        if path in self.files:
            del self.files[path]
            return True
        return False

    def list_files(self) -> list[str]:
        """List all file paths."""
        return list(self.files.keys())

    def update_file_content(self, path: str, content: str) -> bool:
        """Update file content."""
        if path in self.files:
            self.files[path].update_content(content)
            return True
        return False

    model_config = ConfigDict(json_schema_extra={})


class PlanningState(BaseModel):
    """State for planning operations."""

    todos: list[Todo] = Field(default_factory=list, description="List of todos")
    active_plan: str | None = Field(None, description="Active plan identifier")
    planning_context: dict[str, Any] = Field(
        default_factory=dict, description="Planning context"
    )

    def add_todo(self, todo: Todo) -> None:
        """Add a todo to the planning state."""
        self.todos.append(todo)

    def get_todo_by_id(self, todo_id: str) -> Todo | None:
        """Get a todo by ID."""
        for todo in self.todos:
            if todo.id == todo_id:
                return todo
        return None

    def update_todo_status(self, todo_id: str, status: TaskStatus) -> bool:
        """Update todo status."""
        todo = self.get_todo_by_id(todo_id)
        if todo:
            todo.status = status
            todo.updated_at = datetime.now()
            return True
        return False

    def get_todos_by_status(self, status: TaskStatus) -> list[Todo]:
        """Get todos by status."""
        return [todo for todo in self.todos if todo.status == status]

    def get_pending_todos(self) -> list[Todo]:
        """Get pending todos."""
        return self.get_todos_by_status(TaskStatus.PENDING)

    def get_in_progress_todos(self) -> list[Todo]:
        """Get in-progress todos."""
        return self.get_todos_by_status(TaskStatus.IN_PROGRESS)

    def get_completed_todos(self) -> list[Todo]:
        """Get completed todos."""
        return self.get_todos_by_status(TaskStatus.COMPLETED)

    model_config = ConfigDict(json_schema_extra={})


class DeepAgentState(BaseModel):
    """Main state for DeepAgent operations."""

    session_id: str = Field(..., description="Session identifier")
    todos: list[Todo] = Field(default_factory=list, description="List of todos")
    files: dict[str, FileInfo] = Field(
        default_factory=dict, description="Files in the filesystem"
    )
    current_directory: str = Field("/", description="Current working directory")
    active_tasks: list[str] = Field(default_factory=list, description="Active task IDs")
    completed_tasks: list[str] = Field(
        default_factory=list, description="Completed task IDs"
    )
    conversation_history: list[dict[str, Any]] = Field(
        default_factory=list, description="Conversation history"
    )
    shared_state: dict[str, Any] = Field(
        default_factory=dict, description="Shared state between agents"
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict, description="Additional metadata"
    )
    created_at: datetime = Field(
        default_factory=datetime.now, description="Creation timestamp"
    )
    updated_at: datetime | None = Field(None, description="Last update timestamp")

    def add_todo(self, todo: Todo) -> None:
        """Add a todo to the state."""
        self.todos.append(todo)
        self.updated_at = datetime.now()

    def update_todo_status(self, todo_id: str, status: TaskStatus) -> bool:
        """Update todo status."""
        for todo in self.todos:
            if todo.id == todo_id:
                todo.status = status
                todo.updated_at = datetime.now()
                self.updated_at = datetime.now()
                return True
        return False

    def add_file(self, file_info: FileInfo) -> None:
        """Add a file to the state."""
        self.files[file_info.path] = file_info
        self.updated_at = datetime.now()

    def get_file(self, path: str) -> FileInfo | None:
        """Get a file by path."""
        return self.files.get(path)

    def update_file_content(self, path: str, content: str) -> bool:
        """Update file content."""
        if path in self.files:
            self.files[path].update_content(content)
            self.updated_at = datetime.now()
            return True
        return False

    def add_to_conversation(self, role: str, content: str, **kwargs) -> None:
        """Add to conversation history."""
        self.conversation_history.append(
            {
                "role": role,
                "content": content,
                "timestamp": datetime.now().isoformat(),
                **kwargs,
            }
        )
        self.updated_at = datetime.now()

    def get_planning_state(self) -> PlanningState:
        """Get planning state from the main state."""
        return PlanningState(
            todos=self.todos, planning_context=self.shared_state.get("planning", {})
        )

    def get_filesystem_state(self) -> FilesystemState:
        """Get filesystem state from the main state."""
        return FilesystemState(
            files=self.files, current_directory=self.current_directory
        )

    def get_agent_context(self) -> AgentContext:
        """Get agent context from the main state."""
        return AgentContext(
            session_id=self.session_id,
            conversation_history=self.conversation_history,
            shared_state=self.shared_state,
            active_tasks=self.active_tasks,
            completed_tasks=self.completed_tasks,
        )

    model_config = ConfigDict(json_schema_extra={})


# State reducer functions for merging state updates
def merge_filesystem_state(
    current: dict[str, FileInfo], update: dict[str, FileInfo]
) -> dict[str, FileInfo]:
    """Merge filesystem state updates."""
    result = current.copy()
    result.update(update)
    return result


def merge_todos_state(current: list[Todo], update: list[Todo]) -> list[Todo]:
    """Merge todos state updates."""
    # Create a map of existing todos by ID
    todo_map = {todo.id: todo for todo in current}

    # Update or add todos from the update
    for todo in update:
        todo_map[todo.id] = todo

    return list(todo_map.values())


def merge_conversation_history(
    current: list[dict[str, Any]], update: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    """Merge conversation history updates."""
    return current + update


# Factory functions
def create_todo(
    content: str, priority: int = 0, tags: list[str] | None = None, **kwargs
) -> Todo:
    """Create a Todo with default values."""
    import uuid

    return Todo(
        id=str(uuid.uuid4()),
        content=content,
        priority=priority,
        tags=tags or [],
        **kwargs,
    )


def create_file_info(path: str, content: str = "", **kwargs) -> FileInfo:
    """Create a FileInfo with default values."""
    return FileInfo(
        path=path, content=content, size=len(content.encode("utf-8")), **kwargs
    )


def create_deep_agent_state(session_id: str, **kwargs) -> DeepAgentState:
    """Create a DeepAgentState with default values."""
    return DeepAgentState(session_id=session_id, **kwargs)
