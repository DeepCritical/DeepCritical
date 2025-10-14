"""
Workflow Context utilities for DeepCritical agent interaction design patterns.

This module vendors in the workflow context system from the _workflows directory, providing
context management, type inference, and execution context functionality
with minimal external dependencies.
"""

from __future__ import annotations

import inspect
import logging
from types import UnionType
from typing import (
    TYPE_CHECKING,
    Any,
    Generic,
    TypeVar,
    Union,
    cast,
    get_args,
    get_origin,
)

if TYPE_CHECKING:
    from collections.abc import Callable

logger = logging.getLogger(__name__)

T_Out = TypeVar("T_Out")
T_W_Out = TypeVar("T_W_Out")


def infer_output_types_from_ctx_annotation(
    ctx_annotation: Any,
) -> tuple[list[type[Any]], list[type[Any]]]:
    """Infer message types and workflow output types from the WorkflowContext generic parameters."""
    # If no annotation or not parameterized, return empty lists
    try:
        origin = get_origin(ctx_annotation)
    except Exception:
        origin = None

    # If annotation is unsubscripted WorkflowContext, nothing to infer
    if origin is None:
        return [], []

    # Expecting WorkflowContext[T_Out, T_W_Out]
    if origin is not WorkflowContext:
        return [], []

    args = list(get_args(ctx_annotation))
    if not args:
        return [], []

    # WorkflowContext[T_Out] -> message_types from T_Out, no workflow output types
    if len(args) == 1:
        t = args[0]
        t_origin = get_origin(t)
        if t is Any:
            return [cast("type[Any]", Any)], []

        if t_origin in (Union, UnionType):
            message_types = [arg for arg in get_args(t) if arg is not Any]
            return message_types, []

        return [t], []

    # WorkflowContext[T_Out, T_W_Out] -> message_types from T_Out, workflow_output_types from T_W_Out
    t_out, t_w_out = args[:2]  # Take first two args in case there are more

    # Process T_Out for message_types
    message_types = []
    t_out_origin = get_origin(t_out)
    if t_out is Any:
        message_types = [cast("type[Any]", Any)]
    elif t_out is not type(None):  # Avoid None type
        if t_out_origin in (Union, UnionType):
            message_types = [arg for arg in get_args(t_out) if arg is not Any]
        else:
            message_types = [t_out]

    # Process T_W_Out for workflow_output_types
    workflow_output_types = []
    t_w_out_origin = get_origin(t_w_out)
    if t_w_out is Any:
        workflow_output_types = [cast("type[Any]", Any)]
    elif t_w_out is not type(None):  # Avoid None type
        if t_w_out_origin in (Union, UnionType):
            workflow_output_types = [arg for arg in get_args(t_w_out) if arg is not Any]
        else:
            workflow_output_types = [t_w_out]

    return message_types, workflow_output_types


def _is_workflow_context_type(annotation: Any) -> bool:
    """Check if an annotation represents WorkflowContext, WorkflowContext[T], or WorkflowContext[T, U]."""
    origin = get_origin(annotation)
    if origin is WorkflowContext:
        return True
    # Also handle the case where the raw class is used
    return annotation is WorkflowContext


def validate_workflow_context_annotation(
    annotation: Any,
    parameter_name: str,
    context_description: str,
) -> tuple[list[type[Any]], list[type[Any]]]:
    """Validate a WorkflowContext annotation and return inferred types."""
    if annotation == inspect.Parameter.empty:
        msg = (
            f"{context_description} {parameter_name} must have a WorkflowContext, "
            f"WorkflowContext[T] or WorkflowContext[T, U] type annotation, "
            f"where T is output message type and U is workflow output type"
        )
        raise ValueError(msg)

    if not _is_workflow_context_type(annotation):
        msg = (
            f"{context_description} {parameter_name} must be annotated as "
            f"WorkflowContext, WorkflowContext[T], or WorkflowContext[T, U], "
            f"got {annotation}"
        )
        raise ValueError(msg)

    # Validate type arguments for WorkflowContext[T] or WorkflowContext[T, U]
    type_args = get_args(annotation)

    if len(type_args) > 2:
        msg = (
            f"{context_description} {parameter_name} must have at most 2 type arguments, "
            "WorkflowContext, WorkflowContext[T], or WorkflowContext[T, U], "
            f"got {len(type_args)} arguments"
        )
        raise ValueError(msg)

    if type_args:
        # Helper function to check if a value is a valid type annotation
        def _is_type_like(x: Any) -> bool:
            """Check if a value is a type-like entity (class, type, or typing construct)."""
            return isinstance(x, type) or get_origin(x) is not None

        for i, type_arg in enumerate(type_args):
            param_description = "T_Out" if i == 0 else "T_W_Out"

            # Allow Any explicitly
            if type_arg is Any:
                continue

            # Check if it's a union type and validate each member
            union_origin = get_origin(type_arg)
            if union_origin in (Union, UnionType):
                union_members = get_args(type_arg)
                invalid_members = [
                    m for m in union_members if not _is_type_like(m) and m is not Any
                ]
                if invalid_members:
                    msg = (
                        f"{context_description} {parameter_name} {param_description} "
                        f"contains invalid type entries: {invalid_members}. "
                        f"Use proper types or typing generics"
                    )
                    raise ValueError(msg)
            # Check if it's a valid type
            elif not _is_type_like(type_arg):
                msg = (
                    f"{context_description} {parameter_name} {param_description} "
                    f"contains invalid type entry: {type_arg}. "
                    f"Use proper types or typing generics"
                )
                raise ValueError(msg)

    return infer_output_types_from_ctx_annotation(annotation)


def validate_function_signature(
    func: Callable[..., Any], context_description: str
) -> tuple[type, Any, list[type[Any]], list[type[Any]]]:
    """Validate function signature for executor functions."""
    signature = inspect.signature(func)
    params = list(signature.parameters.values())

    # Determine expected parameter count based on context
    expected_counts: tuple[int, ...]
    if context_description.startswith("Function"):
        # Function executor: (message) or (message, ctx)
        expected_counts = (1, 2)
        param_description = "(message: T) or (message: T, ctx: WorkflowContext[U])"
    else:
        # Handler method: (self, message, ctx)
        expected_counts = (3,)
        param_description = "(self, message: T, ctx: WorkflowContext[U])"

    if len(params) not in expected_counts:
        msg = f"{context_description} {getattr(func, '__name__', 'function')} must have {param_description}. Got {len(params)} parameters."
        raise ValueError(msg)

    # Extract message parameter (index 0 for functions, index 1 for methods)
    message_param_idx = 0 if context_description.startswith("Function") else 1
    message_param = params[message_param_idx]

    # Check message parameter has type annotation
    if message_param.annotation == inspect.Parameter.empty:
        msg = f"{context_description} {getattr(func, '__name__', 'function')} must have a type annotation for the message parameter"
        raise ValueError(msg)

    message_type = message_param.annotation

    # Check if there's a context parameter
    ctx_param_idx = message_param_idx + 1
    if len(params) > ctx_param_idx:
        ctx_param = params[ctx_param_idx]
        output_types, workflow_output_types = validate_workflow_context_annotation(
            ctx_param.annotation, f"parameter '{ctx_param.name}'", context_description
        )
        ctx_annotation = ctx_param.annotation
    else:
        # No context parameter (only valid for function executors)
        if not context_description.startswith("Function"):
            msg = f"{context_description} {getattr(func, '__name__', 'function')} must have a WorkflowContext parameter"
            raise ValueError(msg)
        output_types, workflow_output_types = [], []
        ctx_annotation = None

    return message_type, ctx_annotation, output_types, workflow_output_types


class WorkflowContext(Generic[T_Out, T_W_Out]):
    """Execution context that enables executors to interact with workflows and other executors."""

    def __init__(
        self,
        executor_id: str,
        source_executor_ids: list[str],
        shared_state: Any,  # This would be SharedState in the full implementation
        runner_context: Any,  # This would be RunnerContext in the full implementation
        trace_contexts: list[dict[str, str]] | None = None,
        source_span_ids: list[str] | None = None,
    ):
        """Initialize the executor context with the given workflow context."""
        self._executor_id = executor_id
        self._source_executor_ids = source_executor_ids
        self._runner_context = runner_context
        self._shared_state = shared_state

        # Store trace contexts and source span IDs for linking (supporting multiple sources)
        self._trace_contexts = trace_contexts or []
        self._source_span_ids = source_span_ids or []

        if not self._source_executor_ids:
            msg = "source_executor_ids cannot be empty. At least one source executor ID is required."
            raise ValueError(msg)

    async def send_message(self, message: T_Out, target_id: str | None = None) -> None:
        """Send a message to the workflow context."""
        # This would be implemented with the actual message sending logic

    async def yield_output(self, output: T_W_Out) -> None:
        """Set the output of the workflow."""
        # This would be implemented with the actual output yielding logic

    async def add_event(self, event: Any) -> None:
        """Add an event to the workflow context."""
        # This would be implemented with the actual event adding logic

    async def get_shared_state(self, key: str) -> Any:
        """Get a value from the shared state."""
        # This would be implemented with the actual shared state access
        return None

    async def set_shared_state(self, key: str, value: Any) -> None:
        """Set a value in the shared state."""
        # This would be implemented with the actual shared state setting

    def get_source_executor_id(self) -> str:
        """Get the ID of the source executor that sent the message to this executor."""
        if len(self._source_executor_ids) > 1:
            msg = (
                "Cannot get source executor ID when there are multiple source executors. "
                "Access the full list via the source_executor_ids property instead."
            )
            raise RuntimeError(msg)
        return self._source_executor_ids[0]

    @property
    def source_executor_ids(self) -> list[str]:
        """Get the IDs of the source executors that sent messages to this executor."""
        return self._source_executor_ids

    @property
    def shared_state(self) -> Any:
        """Get the shared state."""
        return self._shared_state

    async def set_state(self, state: dict[str, Any]) -> None:
        """Persist this executors state into the checkpointable context."""
        # This would be implemented with the actual state persistence

    async def get_state(self) -> dict[str, Any] | None:
        """Retrieve previously persisted state for this executor, if any."""
        # This would be implemented with the actual state retrieval
        return None


# Export all workflow context components
__all__ = [
    "WorkflowContext",
    "_is_workflow_context_type",
    "infer_output_types_from_ctx_annotation",
    "validate_function_signature",
    "validate_workflow_context_annotation",
]
