import builtins
import traceback as _traceback
from contextvars import ContextVar

import pytest

from DeepResearch.src.utils.workflow_events import (
    AgentRunEvent,
    AgentRunUpdateEvent,
    ExecutorCompletedEvent,
    ExecutorEvent,
    ExecutorFailedEvent,
    ExecutorInvokedEvent,
    RequestInfoEvent,
    WorkflowErrorDetails,
    WorkflowErrorEvent,
    WorkflowEvent,
    WorkflowEventSource,
    WorkflowFailedEvent,
    WorkflowOutputEvent,
    WorkflowRunState,
    WorkflowStartedEvent,
    WorkflowStatusEvent,
    WorkflowWarningEvent,
    _framework_event_origin,
)


class TestWorkflowEvents:
    def test_event_creation(self) -> None:
        # Basic WorkflowEvent creation
        ev = WorkflowEvent(data="test")
        assert ev.data == "test"
        assert ev.origin in (
            WorkflowEventSource.EXECUTOR,
            WorkflowEventSource.FRAMEWORK,
        )
        assert isinstance(repr(ev), str)

        # All lifecycle and specialized events
        start_ev = WorkflowStartedEvent()
        assert isinstance(start_ev, WorkflowEvent)
        assert repr(start_ev)

        warn_ev = WorkflowWarningEvent("warning")
        assert warn_ev.data == "warning"
        assert "warning" in repr(warn_ev)

        err_ev = WorkflowErrorEvent(Exception("error"))
        assert isinstance(err_ev.data, Exception)
        assert "error" in repr(err_ev)

        status_ev = WorkflowStatusEvent(state=WorkflowRunState.STARTED, data={"key": 1})
        assert status_ev.state == WorkflowRunState.STARTED
        assert status_ev.data == {"key": 1}
        assert repr(status_ev)

        details = WorkflowErrorDetails("TypeError", "msg", "tb")
        fail_ev = WorkflowFailedEvent(details=details, data="failed")
        assert fail_ev.details.error_type == "TypeError"
        assert fail_ev.data == "failed"
        assert repr(fail_ev)

        req_ev = RequestInfoEvent("rid", "exec", str, "reqdata")
        assert req_ev.request_id == "rid"
        assert repr(req_ev)

        out_ev = WorkflowOutputEvent(data=123, source_executor_id="exec1")
        assert out_ev.source_executor_id == "exec1"
        assert repr(out_ev)

        executor_ev = ExecutorEvent(executor_id="exec2", data="execdata")
        assert executor_ev.executor_id == "exec2"
        assert repr(executor_ev)

        invoked_ev = ExecutorInvokedEvent(executor_id="exec3", data=None)
        assert repr(invoked_ev)

        completed_ev = ExecutorCompletedEvent(executor_id="exec4", data="done")
        assert repr(completed_ev)

        failed_ev = ExecutorFailedEvent(executor_id="exec5", details=details)
        assert failed_ev.details.message == "msg"
        assert repr(failed_ev)

        agent_update = AgentRunUpdateEvent(executor_id="agent1", data=["msg1"])
        assert repr(agent_update)

        agent_run = AgentRunEvent(executor_id="agent2", data={"final": True})
        assert repr(agent_run)

    def test_event_processing(self) -> None:
        # Default origin is EXECUTOR
        ev = WorkflowEvent()
        assert ev.origin == WorkflowEventSource.EXECUTOR

        # Switching to FRAMEWORK origin
        with _framework_event_origin():
            ev2 = WorkflowEvent()
            assert ev2.origin == WorkflowEventSource.FRAMEWORK

        # After context manager, origin resets to EXECUTOR
        ev3 = WorkflowEvent()
        assert ev3.origin == WorkflowEventSource.EXECUTOR

    def test_event_validation(self, monkeypatch) -> None:
        # Check enum members
        assert WorkflowRunState.STARTED.value == "STARTED"
        assert WorkflowEventSource.FRAMEWORK.value == "FRAMEWORK"

        # Test WorkflowErrorDetails from_exception
        try:
            raise ValueError("oops")
        except ValueError as exc:
            details = WorkflowErrorDetails.from_exception(exc, executor_id="execX")
            assert details.error_type == "ValueError"
            assert "oops" in details.message
            if details.traceback is not None:
                assert "ValueError" in details.traceback
            assert details.executor_id == "execX"

        # Test fallback if traceback.format_exception fails
        def broken_format(*args, **kwargs):
            raise RuntimeError("fail")

        monkeypatch.setattr(_traceback, "format_exception", broken_format)
        details2 = WorkflowErrorDetails.from_exception(ValueError("fail"))
        assert details2.traceback is None

    def test_event_error_handling(self) -> None:
        # Verify WorkflowFailedEvent holds details correctly
        details = WorkflowErrorDetails("KeyError", "key missing")
        fail_ev = WorkflowFailedEvent(details=details)
        assert fail_ev.details.error_type == "KeyError"
        assert repr(fail_ev)

        # ExecutorFailedEvent also holds WorkflowErrorDetails
        exec_fail = ExecutorFailedEvent(executor_id="execY", details=details)
        assert exec_fail.details.message == "key missing"
        assert repr(exec_fail)

        # Verify WorkflowWarningEvent __repr__ includes message
        warn_ev = WorkflowWarningEvent("warn here")
        assert "warn here" in repr(warn_ev)

        # Verify WorkflowErrorEvent __repr__ includes exception
        err_ev = WorkflowErrorEvent(Exception("some error"))
        assert "some error" in repr(err_ev)
