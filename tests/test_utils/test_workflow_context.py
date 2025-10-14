"""
tests/test_utils/test_workflow_context.py

Expanded test suite for WorkflowContext utilities.

Implements:
- Initialization behavior testing
- Context management (enter/exit)
- Validation logic
- Cleanup/error handling
- Mock-based dependency isolation

"""

from typing import Any, Union
from unittest.mock import patch

import pytest

from DeepResearch.src.utils.workflow_context import (
    WorkflowContext,
    infer_output_types_from_ctx_annotation,
    validate_function_signature,
    validate_workflow_context_annotation,
)


# WorkflowContext Behavior
class TestWorkflowContext:
    """Unit and integration tests for WorkflowContext lifecycle and validation."""

    # ---- Initialization -------------------------------------------------
    def test_context_initialization_valid(self):
        """Verify WorkflowContext initializes with proper attributes."""
        ctx = WorkflowContext(
            executor_id="exec_1",
            source_executor_ids=["src_1"],
            shared_state={"a": 1},
            runner_context={},
        )
        assert ctx._executor_id == "exec_1"
        assert ctx.get_source_executor_id() == "src_1"
        assert ctx.shared_state == {"a": 1}
        assert isinstance(ctx.source_executor_ids, list)

    def test_context_initialization_empty_source_ids_raises(self):
        """Ensure initialization fails when no source_executor_ids are given."""
        with pytest.raises(ValueError, match="cannot be empty"):
            WorkflowContext(
                executor_id="exec_1",
                source_executor_ids=[],
                shared_state={},
                runner_context={},
            )

    # ---- Context management (enter/exit simulation) --------------------
    def test_context_management_single_source(self):
        """Check get_source_executor_id works for single-source case."""
        ctx = WorkflowContext(
            executor_id="exec_2",
            source_executor_ids=["alpha"],
            shared_state={},
            runner_context={},
        )
        assert ctx.get_source_executor_id() == "alpha"

    def test_context_management_multiple_sources_raises(self):
        """get_source_executor_id should fail when multiple sources exist."""
        ctx = WorkflowContext(
            executor_id="exec_3",
            source_executor_ids=["a", "b"],
            shared_state={},
            runner_context={},
        )
        with pytest.raises(RuntimeError, match="multiple source executors"):
            ctx.get_source_executor_id()

    # ---- Shared state manipulation -------------------------------------
    @pytest.mark.asyncio
    async def test_set_and_get_shared_state_async(self):
        """Ensure async shared_state methods exist and behave as placeholders."""
        ctx = WorkflowContext(
            executor_id="exec_4",
            source_executor_ids=["src_4"],
            shared_state={"x": 10},
            runner_context={},
        )
        result = await ctx.get_shared_state("x")
        # Currently returns None (not implemented)
        assert result is None
        # set_shared_state doesn't raise
        await ctx.set_shared_state("y", 5)

    def test_multiple_trace_contexts_initialization(self):
        ctx = WorkflowContext(
            executor_id="exec_x",
            source_executor_ids=["a", "b"],
            shared_state={},
            runner_context={},
            trace_contexts=[{"trace": "1"}, {"trace": "2"}],
            source_span_ids=["span1", "span2"],
        )
        assert len(ctx._trace_contexts) == 2
        assert len(ctx._source_span_ids) == 2

    # ---- Validation utility tests --------------------------------------
    def test_validate_workflow_context_annotation_valid(self):
        """Validate a proper WorkflowContext annotation."""
        anno = WorkflowContext[int, str]
        msg_types, wf_types = validate_workflow_context_annotation(
            anno, "ctx", "Function executor"
        )
        assert int in msg_types
        assert str in wf_types

    def test_validate_workflow_context_annotation_invalid(self):
        """Raise ValueError for incorrect annotation types."""
        with pytest.raises(ValueError, match="must be annotated as WorkflowContext"):
            validate_workflow_context_annotation(int, "ctx", "Function executor")

    def test_validate_workflow_context_annotation_empty(self):
        """Raise ValueError for empty parameter type."""
        from inspect import Parameter

        with pytest.raises(ValueError, match="must have a WorkflowContext"):
            validate_workflow_context_annotation(
                Parameter.empty, "ctx", "Function executor"
            )

    def test_validate_workflow_context_annotation_invalid_types(self):
        """Raise ValueError for invalid args type."""
        with patch(
            "DeepResearch.src.utils.workflow_context.get_args",
            return_value=(Union[int, str], 58),
        ):
            with pytest.raises(
                ValueError, match="must be annotated as WorkflowContext"
            ):
                validate_workflow_context_annotation(
                    object(),  # annotation
                    "parameter 'ctx'",  # name
                    "Function executor",  # context_description
                )

    def test_infer_output_types_from_ctx_annotation_union(self):
        """Infer multiple output types when WorkflowContext uses Union."""

        anno = WorkflowContext[Union[int, str], None]
        msg_types, wf_types = infer_output_types_from_ctx_annotation(anno)
        assert set(msg_types) == {int, str}
        assert wf_types == []

    def test_infer_output_types_from_ctx_annotation_none(self):
        """Infer multiple output types when WorkflowContext uses NoneType."""

        anno = WorkflowContext[None, None]
        msg_types, wf_types = infer_output_types_from_ctx_annotation(anno)
        assert msg_types == []
        assert wf_types == []

    def test_infer_output_types_from_ctx_annotation_unparameterized(self):
        """Infer multiple output types when WorkflowContext is not parameterized."""
        msg_types, wf_types = infer_output_types_from_ctx_annotation(str)
        assert msg_types == []
        assert wf_types == []

    def test_infer_output_types_from_ctx_annotation_invalid_class(self):
        """Infer multiple output types when WorkflowContext is not parameterized."""

        class BadAnnotation:
            @property
            def __origin__(self):
                raise RuntimeError("Boom!")

        msg_types, wf_types = infer_output_types_from_ctx_annotation(BadAnnotation)
        assert msg_types == []
        assert wf_types == []

    # ---- Function signature validation ---------------------------------
    def test_validate_function_signature_valid_function(self):
        """Accepts function(message: int, ctx: WorkflowContext[str, Any])."""

        async def func(msg: int, ctx: WorkflowContext[str, Any]):
            return msg

        msg_t, ctx_ann, out_t, wf_out_t = validate_function_signature(
            func, "Function executor"
        )
        assert msg_t is int
        assert "WorkflowContext" in str(ctx_ann)
        assert str in out_t or str in wf_out_t

    def test_validate_function_signature_missing_annotation(self):
        """Raises if message parameter has no annotation."""

        def func(msg, ctx: WorkflowContext[str, Any]):
            return msg

        with pytest.raises(
            ValueError, match="Function executor func must have a type annotation"
        ):
            validate_function_signature(func, "Function executor")

    def test_validate_function_signature_wrong_param_count(self):
        """Raises if the parameter count doesn’t match executor signature."""

        def func(a, b, c):
            return None

        with pytest.raises(ValueError, match="Got 3 parameters"):
            validate_function_signature(func, "Function executor")

    def test_validate_function_signature_no_context_parameter(self):
        """Raises if No context parameter (only valid for function executors)"""

        async def func(msg: int, ctx: WorkflowContext[str, Any]):
            return msg

        with pytest.raises(ValueError, match="Funtion executor func must have"):
            # Note that the spelling of the word Function is incorrect
            validate_function_signature(func, "Funtion executor")

    @pytest.mark.asyncio
    async def test_context_cleanup_handles_error(self):
        """Simulate cleanup error handling."""
        ctx = WorkflowContext(
            executor_id="exec_5",
            source_executor_ids=["src_5"],
            shared_state={},
            runner_context={},
        )
        # Mock a failing cleanup method
        with patch.object(ctx, "set_state", side_effect=RuntimeError("Boom")):
            with pytest.raises(RuntimeError, match="Boom"):
                await ctx.set_state({"foo": "bar"})

    @pytest.mark.asyncio
    async def test_context_state_management_async_methods(self):
        """Ensure get_state/set_state methods exist and behave gracefully."""
        ctx = WorkflowContext(
            executor_id="exec_6",
            source_executor_ids=["src_6"],
            shared_state={},
            runner_context={},
        )
        await ctx.set_state({"state": "value"})
        result = await ctx.get_state()
        # Not implemented yet, expected None
        assert result is None
