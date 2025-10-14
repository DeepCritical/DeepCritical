import asyncio
from collections.abc import Callable
from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from DeepResearch.src.utils.workflow_middleware import (
    AgentMiddleware,
    AgentMiddlewarePipeline,
    AgentRunContext,
    ChatContext,
    ChatMiddleware,
    ChatMiddlewarePipeline,
    FunctionInvocationContext,
    FunctionMiddleware,
    FunctionMiddlewarePipeline,
    MiddlewareType,
    MiddlewareWrapper,
    _determine_middleware_type,
    agent_middleware,
    categorize_middleware,
    chat_middleware,
    function_middleware,
    use_agent_middleware,
    use_chat_middleware,
)


class TestWorkflowMiddleware:
    @pytest.fixture
    def mock_agent_class(self) -> type:
        """Create a mock agent class for testing."""

        class MockAgent:
            def __init__(self) -> None:
                self.middleware: Any = None

            async def run(
                self,
                messages: Any = None,
                *,
                thread: Any = None,
                **kwargs: Any,
            ) -> Any:
                return {"status": "original_run", "messages": messages}

            async def run_stream(
                self,
                messages: Any = None,
                *,
                thread: Any = None,
                **kwargs: Any,
            ) -> Any:
                yield {"status": "original_run_stream"}

            def _normalize_messages(self, messages: Any) -> Any:
                return messages or []

        return MockAgent

    @pytest.fixture
    def mock_chat_client_class(self) -> type:
        """Create a mock chat client class for testing."""

        class MockChatClient:
            def __init__(self) -> None:
                self.middleware: Any = None

            async def get_response(self, messages: Any, **kwargs: Any) -> Any:
                return {"status": "original_response", "messages": messages}

            async def get_streaming_response(self, messages: Any, **kwargs: Any) -> Any:
                yield {"status": "original_stream_response"}

            def prepare_messages(self, messages: Any, chat_options: Any) -> Any:
                return messages or []

        return MockChatClient

    @pytest.mark.asyncio
    async def test_middleware_initialization(self) -> None:
        # Test AgentRunContext initialization
        agent_context = AgentRunContext(
            agent="agentX", messages=[1, 2, 3], result="res"
        )
        assert agent_context.agent == "agentX"
        assert agent_context.messages == [1, 2, 3]
        assert agent_context.result == "res"
        assert agent_context.metadata == {}
        assert not agent_context.terminate

        # Test FunctionInvocationContext initialization
        function_context = FunctionInvocationContext(
            function=lambda x: x, arguments=(1, 2), result=None
        )
        assert callable(function_context.function)
        assert function_context.arguments == (1, 2)
        assert function_context.result is None
        assert function_context.metadata == {}
        assert not function_context.terminate

        # Test ChatContext initialization
        chat_context = ChatContext(chat_client="clientX", messages=[], chat_options={})
        assert chat_context.chat_client == "clientX"
        assert chat_context.messages == []
        assert chat_context.chat_options == {}
        assert chat_context.result is None
        assert not chat_context.terminate

        # Test MiddlewareWrapper wraps a coroutine function properly
        async def dummy_middleware(ctx, next_func: Callable) -> None:
            ctx.result = "middleware_run"
            await next_func(ctx)

        wrapper = MiddlewareWrapper(dummy_middleware)
        assert asyncio.iscoroutinefunction(wrapper.process)

        # Test decorators attach proper MiddlewareType
        @agent_middleware
        async def agent_fn(ctx: AgentRunContext, next_fn: Callable) -> None:
            await next_fn(ctx)

        @function_middleware
        async def function_fn(
            ctx: FunctionInvocationContext, next_fn: Callable
        ) -> None:
            await next_fn(ctx)

        @chat_middleware
        async def chat_fn(ctx: ChatContext, next_fn: Callable) -> None:
            await next_fn(ctx)

        assert getattr(agent_fn, "_middleware_type", None) == MiddlewareType.AGENT
        assert getattr(function_fn, "_middleware_type", None) == MiddlewareType.FUNCTION
        assert getattr(chat_fn, "_middleware_type", None) == MiddlewareType.CHAT

    @pytest.mark.asyncio
    async def test_middleware_execution(self) -> None:
        # Agent middleware execution
        agent_context = AgentRunContext(agent="agentX", messages=["msg1"])

        async def final_agent_handler(ctx: AgentRunContext) -> str:
            return "final_agent_result"

        async def agent_mw(ctx: AgentRunContext, next_fn: Callable) -> None:
            ctx.messages.append("middleware_run")
            await next_fn(ctx)
            ctx.result = "agent_done"

        pipeline = AgentMiddlewarePipeline([agent_mw])
        result = await pipeline.execute(
            "agentX", ["msg1"], agent_context, final_agent_handler
        )
        assert result == "agent_done"
        assert agent_context.messages[-1] == "middleware_run"

        # Function middleware execution
        function_context = FunctionInvocationContext(
            function=lambda x: x, arguments=[1]
        )

        async def final_function_handler(ctx: FunctionInvocationContext) -> str:
            return "final_function_result"

        async def function_mw(
            ctx: FunctionInvocationContext, next_fn: Callable
        ) -> None:
            ctx.arguments.append(2)
            await next_fn(ctx)
            ctx.result = "function_done"

        function_pipeline = FunctionMiddlewarePipeline([function_mw])
        result_func = await function_pipeline.execute(
            lambda x: x, [1], function_context, final_function_handler
        )
        assert result_func == "function_done"
        assert function_context.arguments[-1] == 2

        # Chat middleware execution
        chat_context = ChatContext(
            chat_client="clientX", messages=["hi"], chat_options={}
        )

        async def final_chat_handler(ctx: ChatContext) -> str:
            return "final_chat_result"

        async def chat_mw(ctx: ChatContext, next_fn: Callable) -> None:
            ctx.messages.append("chat_middleware")
            await next_fn(ctx)
            ctx.result = "chat_done"

        chat_pipeline = ChatMiddlewarePipeline([chat_mw])
        result_chat = await chat_pipeline.execute(
            "clientX", ["hi"], {}, chat_context, final_chat_handler
        )
        assert result_chat == "chat_done"
        assert chat_context.messages[-1] == "chat_middleware"

        # Test MiddlewareWrapper integration
        async def wrapper_fn(ctx, next_fn: Callable) -> None:
            ctx.result = "wrapped"
            await next_fn(ctx)

        wrapper = MiddlewareWrapper(wrapper_fn)
        test_context = AgentRunContext(agent="agentY", messages=[])

        async def dummy_final(ctx: AgentRunContext) -> str:
            return "done"

        handler_chain = wrapper.process(test_context, dummy_final)
        await handler_chain
        assert test_context.result == "wrapped"

    @pytest.mark.asyncio
    async def test_middleware_pipeline(self) -> None:
        # Test has_middlewares property

        agent_pipeline = AgentMiddlewarePipeline()
        assert not agent_pipeline.has_middlewares

        async def dummy_agent_mw(ctx, next_fn):
            await next_fn(ctx)

        agent_pipeline._register_middleware(dummy_agent_mw)
        assert agent_pipeline.has_middlewares

        # Test _register_middleware_with_wrapper auto-wrapping
        class CustomAgentMiddleware:
            async def process(self, ctx, next_fn):
                ctx.result = "custom_done"
                await next_fn(ctx)

        wrapped_pipeline = AgentMiddlewarePipeline()
        wrapped_pipeline._register_middleware_with_wrapper(
            CustomAgentMiddleware(), CustomAgentMiddleware
        )
        wrapped_pipeline._register_middleware_with_wrapper(
            dummy_agent_mw, CustomAgentMiddleware
        )

        test_context = AgentRunContext(agent="agentZ", messages=[])

        async def final_handler(ctx):
            return "final_result"

        result = await wrapped_pipeline.execute(
            "agentZ", [], test_context, final_handler
        )
        assert result in ["custom_done", "final_result"]

        # Function pipeline registration
        function_pipeline = FunctionMiddlewarePipeline()

        async def dummy_func_mw(ctx, next_fn):
            await next_fn(ctx)
            ctx.result = "func_done"

        function_pipeline._register_middleware(dummy_func_mw)
        assert function_pipeline.has_middlewares

        func_context = FunctionInvocationContext(function=lambda x: x, arguments=[1])
        result_func = await function_pipeline.execute(
            lambda x: x, [1], func_context, lambda ctx: asyncio.sleep(0)
        )
        assert result_func == "func_done"

        # Chat pipeline registration and terminate handling
        chat_pipeline = ChatMiddlewarePipeline()

        async def chat_mw(ctx, next_fn):
            ctx.terminate = True
            ctx.result = "terminated"
            await next_fn(ctx)

        chat_pipeline._register_middleware(chat_mw)
        assert chat_pipeline.has_middlewares

        chat_context = ChatContext(chat_client="clientZ", messages=[], chat_options={})

        async def chat_final(ctx):
            return "should_not_run"

        result_chat = await chat_pipeline.execute(
            "clientZ", [], {}, chat_context, chat_final
        )
        assert result_chat == "terminated"
        assert chat_context.terminate

    @pytest.mark.asyncio
    async def test_middleware_error_handling(self) -> None:
        # Agent pipeline exception handling
        agent_pipeline = AgentMiddlewarePipeline()

        async def faulty_agent_mw(ctx, next_fn):
            raise ValueError("agent error")

        agent_pipeline._register_middleware(faulty_agent_mw)
        context = AgentRunContext(agent="agentX", messages=[])

        with pytest.raises(ValueError, match="agent error") as excinfo:
            await agent_pipeline.execute("agentX", [], context, lambda ctx: "final")
        assert str(excinfo.value) == "agent error"

        # Function pipeline exception handling
        func_pipeline = FunctionMiddlewarePipeline()

        async def faulty_func_mw(ctx, next_fn):
            raise RuntimeError("function error")

        func_pipeline._register_middleware(faulty_func_mw)
        func_context = FunctionInvocationContext(function=lambda x: x, arguments=[1])

        with pytest.raises(RuntimeError) as excinfo2:
            await func_pipeline.execute(
                lambda x: x, [1], func_context, lambda ctx: "final"
            )
        assert str(excinfo2.value) == "function error"

        # Chat pipeline exception handling
        chat_pipeline = ChatMiddlewarePipeline()

        async def faulty_chat_mw(ctx, next_fn):
            raise KeyError("chat error")

        chat_pipeline._register_middleware(faulty_chat_mw)
        chat_context = ChatContext(chat_client="clientX", messages=[], chat_options={})

        with pytest.raises(KeyError) as excinfo3:
            await chat_pipeline.execute(
                "clientX", [], {}, chat_context, lambda ctx: "final"
            )
        assert str(excinfo3.value) == "'chat error'"

    """Unit tests for middleware decorator functions."""

    @pytest.mark.asyncio
    async def test_middleware_decorators_comprehensive(
        self, mock_agent_class: type, mock_chat_client_class: type
    ) -> None:
        """Comprehensive test covering all middleware decorator functionality."""
        # Test use_agent_middleware decorator returns class
        decorated_agent_class = use_agent_middleware(mock_agent_class)
        assert decorated_agent_class is mock_agent_class
        assert hasattr(decorated_agent_class, "run")
        assert hasattr(decorated_agent_class, "run_stream")

        # Test agent.run without middleware
        agent = decorated_agent_class()
        messages = [{"role": "user", "content": "test"}]
        result = await agent.run(messages, thread="thread_1")
        assert result == {"status": "original_run", "messages": messages}

        # Test agent.run with agent-level middleware
        mock_middleware = MagicMock()
        mock_pipeline = MagicMock()
        mock_pipeline.has_middlewares = True

        with patch(
            "DeepResearch.src.utils.workflow_middleware._build_middleware_pipelines"
        ) as mock_build_pipelines:
            mock_build_pipelines.return_value = (
                mock_pipeline,
                MagicMock(has_middlewares=False),
                [],
            )
            mock_pipeline.execute = AsyncMock(
                return_value={"status": "with_middleware"}
            )

            agent.middleware = mock_middleware
            result = await agent.run([{"role": "user"}], thread="thread_1")
            assert result == {"status": "with_middleware"}
            mock_build_pipelines.assert_called_once()

        # Test agent.run with run-level middleware
        mock_pipeline = MagicMock()
        mock_pipeline.has_middlewares = False

        with patch(
            "DeepResearch.src.utils.workflow_middleware._build_middleware_pipelines"
        ) as mock_build_pipelines:
            mock_build_pipelines.return_value = (
                mock_pipeline,
                MagicMock(has_middlewares=False),
                ["chat_middleware"],
            )

            agent = decorated_agent_class()
            result = await agent.run(
                messages, thread="thread_1", middleware="run_middleware"
            )
            assert result["messages"] == messages
            mock_build_pipelines.assert_called_once_with(None, "run_middleware")

        # Test agent.run returns None when middleware result is falsy
        mock_pipeline = MagicMock()
        mock_pipeline.has_middlewares = True
        mock_pipeline.execute = AsyncMock(return_value=None)

        with patch(
            "DeepResearch.src.utils.workflow_middleware._build_middleware_pipelines"
        ) as mock_build_pipelines:
            mock_build_pipelines.return_value = (
                mock_pipeline,
                MagicMock(has_middlewares=False),
                [],
            )

            agent = decorated_agent_class()
            agent.middleware = MagicMock()
            result = await agent.run([{"role": "user"}], thread="thread_1")
            assert result is None

        # Test agent.run_stream without middleware
        agent = decorated_agent_class()
        stream = agent.run_stream(messages, thread="thread_1")
        results = []
        async for item in stream:
            results.append(item)
        assert len(results) == 1
        assert results[0] == {"status": "original_run_stream"}

        # Test agent.run_stream with middleware
        mock_middleware = MagicMock()
        mock_pipeline = MagicMock()
        mock_pipeline.has_middlewares = True
        mock_pipeline.execute = AsyncMock(return_value={"status": "stream_with_mw"})

        with patch(
            "DeepResearch.src.utils.workflow_middleware._build_middleware_pipelines"
        ) as mock_build_pipelines:
            mock_build_pipelines.return_value = (
                mock_pipeline,
                MagicMock(has_middlewares=False),
                [],
            )

            agent = decorated_agent_class()
            agent.middleware = mock_middleware
            stream = agent.run_stream([{"role": "user"}], thread="thread_1")
            results = []
            async for item in stream:
                results.append(item)
            assert len(results) == 1
            assert results[0] == {"status": "stream_with_mw"}

        # Test use_chat_middleware decorator returns class
        decorated_chat_class = use_chat_middleware(mock_chat_client_class)
        assert decorated_chat_class is mock_chat_client_class
        assert hasattr(decorated_chat_class, "get_response")
        assert hasattr(decorated_chat_class, "get_streaming_response")

        # Test get_response without middleware
        client = decorated_chat_class()
        messages = [{"role": "user", "content": "hello"}]
        result = await client.get_response(messages)
        assert result == {"status": "original_response", "messages": messages}

        # Test get_response with instance-level middleware
        mock_middleware = MagicMock()
        mock_pipeline = MagicMock()
        mock_pipeline.execute = AsyncMock(return_value={"status": "with_middleware"})

        with patch(
            "DeepResearch.src.utils.workflow_middleware.categorize_middleware"
        ) as mock_categorize:
            mock_categorize.return_value = {
                "chat": [mock_middleware],
                "function": [],
            }

            with patch(
                "DeepResearch.src.utils.workflow_middleware.ChatMiddlewarePipeline"
            ) as mock_pipeline_class:
                mock_pipeline_class.return_value = mock_pipeline

                client = decorated_chat_class()
                client.middleware = mock_middleware
                result = await client.get_response(
                    [{"role": "user", "content": "test"}]
                )
                assert result == {"status": "with_middleware"}
                mock_categorize.assert_called_once()
                mock_pipeline.execute.assert_called_once()

        # Test get_response with call-level middleware
        call_middleware = MagicMock()

        with patch(
            "DeepResearch.src.utils.workflow_middleware.categorize_middleware"
        ) as mock_categorize:
            mock_categorize.return_value = {
                "chat": [call_middleware],
                "function": [],
            }

            with patch(
                "DeepResearch.src.utils.workflow_middleware.ChatMiddlewarePipeline"
            ) as mock_pipeline_class:
                mock_pipeline = MagicMock()
                mock_pipeline.execute = AsyncMock(return_value={"status": "result"})
                mock_pipeline_class.return_value = mock_pipeline

                client = decorated_chat_class()
                result = await client.get_response(
                    [{"role": "user"}], middleware=call_middleware
                )
                assert result == {"status": "result"}

        # Test get_response with function middleware pipeline
        function_middleware = [MagicMock()]

        with patch(
            "DeepResearch.src.utils.workflow_middleware.categorize_middleware"
        ) as mock_categorize:
            mock_categorize.return_value = {
                "chat": [],
                "function": function_middleware,
            }

            with patch(
                "DeepResearch.src.utils.workflow_middleware.FunctionMiddlewarePipeline"
            ) as mock_func_pipeline:
                client = decorated_chat_class()
                await client.get_response([{"role": "user"}])
                mock_func_pipeline.assert_called_once_with(function_middleware)

        # Test get_streaming_response without middleware
        client = decorated_chat_class()
        messages = [{"role": "user", "content": "hello"}]
        stream = client.get_streaming_response(messages)
        results = []
        async for item in stream:
            results.append(item)
        assert len(results) == 1
        assert results[0] == {"status": "original_stream_response"}

        # Test get_streaming_response with middleware
        mock_middleware = [MagicMock()]

        with patch(
            "DeepResearch.src.utils.workflow_middleware._merge_and_filter_chat_middleware"
        ) as mock_merge:
            mock_merge.return_value = mock_middleware

            with patch(
                "DeepResearch.src.utils.workflow_middleware.ChatMiddlewarePipeline"
            ) as mock_pipeline_class:
                mock_pipeline = MagicMock()
                mock_pipeline.execute = AsyncMock(
                    return_value={"status": "stream_result"}
                )
                mock_pipeline_class.return_value = mock_pipeline

                client = decorated_chat_class()
                client.middleware = mock_middleware
                stream = client.get_streaming_response(
                    [{"role": "user"}], middleware=mock_middleware
                )
                results = []
                async for item in stream:
                    results.append(item)
                assert len(results) == 1
                assert results[0] == {"status": "stream_result"}

        # Test get_streaming_response with empty middleware
        with patch(
            "DeepResearch.src.utils.workflow_middleware._merge_and_filter_chat_middleware"
        ) as mock_merge:
            mock_merge.return_value = []

            client = decorated_chat_class()
            stream = client.get_streaming_response([{"role": "user"}])
            results = []
            async for item in stream:
                results.append(item)
            assert len(results) == 1
            assert results[0] == {"status": "original_stream_response"}

        # Test middleware kwarg is properly popped
        with patch(
            "DeepResearch.src.utils.workflow_middleware.categorize_middleware"
        ) as mock_categorize:
            mock_categorize.return_value = {"chat": [], "function": []}

            client = decorated_chat_class()
            result = await client.get_response(
                [{"role": "user"}], middleware=MagicMock(), extra_kwarg="value"
            )
            assert result["status"] == "original_response"

    @pytest.mark.asyncio
    async def test_all_cases_determine_middleware_type(self):
        # ----- Agent middleware -----
        async def agent_annotated(ctx: AgentRunContext, next_fn):
            pass

        agent_annotated._middleware_type = MiddlewareType.AGENT  # type: ignore
        assert _determine_middleware_type(agent_annotated) == MiddlewareType.AGENT

        async def agent_only_decorator(ctx, next_fn):
            pass

        agent_only_decorator._middleware_type = MiddlewareType.AGENT  # type: ignore
        assert _determine_middleware_type(agent_only_decorator) == MiddlewareType.AGENT

        # ----- Function middleware -----
        async def func_annotated(ctx: FunctionInvocationContext, next_fn):
            pass

        func_annotated._middleware_type = MiddlewareType.FUNCTION  # type: ignore
        assert _determine_middleware_type(func_annotated) == MiddlewareType.FUNCTION

        async def func_only_decorator(ctx, next_fn):
            pass

        func_only_decorator._middleware_type = MiddlewareType.FUNCTION  # type: ignore
        assert (
            _determine_middleware_type(func_only_decorator) == MiddlewareType.FUNCTION
        )

        # ----- Chat middleware -----
        async def chat_annotated(ctx: ChatContext, next_fn):
            pass

        chat_annotated._middleware_type = MiddlewareType.CHAT  # type: ignore
        assert _determine_middleware_type(chat_annotated) == MiddlewareType.CHAT

        async def chat_only_decorator(ctx, next_fn):
            pass

        chat_only_decorator._middleware_type = MiddlewareType.CHAT  # type: ignore
        assert _determine_middleware_type(chat_only_decorator) == MiddlewareType.CHAT

        # ----- Both decorator and annotation match -----
        async def both_match(ctx: AgentRunContext, next_fn):
            pass

        both_match._middleware_type = MiddlewareType.AGENT  # type: ignore
        assert _determine_middleware_type(both_match) == MiddlewareType.AGENT

        # ----- Too few parameters -----
        async def too_few_params(ctx):
            pass

        with pytest.raises(
            ValueError,
            match="Cannot determine middleware type for function too_few_params",
        ):
            _determine_middleware_type(too_few_params)

        # ----- No type info at all -----
        async def no_type_info(a, b):
            pass

        with pytest.raises(ValueError, match="Cannot determine middleware type"):
            _determine_middleware_type(no_type_info)

    @pytest.mark.asyncio
    async def test_all_cases_categorize_middleware(self):
        # ----- Helper callables with type annotations -----
        async def agent_annotated(ctx: AgentRunContext, next_fn):
            pass

        async def func_annotated(ctx: FunctionInvocationContext, next_fn):
            pass

        async def chat_annotated(ctx: ChatContext, next_fn):
            pass

        # Dynamically set _middleware_type for decorator testing
        agent_annotated._middleware_type = MiddlewareType.AGENT  # type: ignore
        func_annotated._middleware_type = MiddlewareType.FUNCTION  # type: ignore
        chat_annotated._middleware_type = MiddlewareType.CHAT  # type: ignore

        # ----- Callable with conflict (should raise ValueError on _determine_middleware_type) -----
        async def conflict(ctx: AgentRunContext, next_fn):
            pass

        conflict._middleware_type = MiddlewareType.FUNCTION  # type: ignore

        # ----- Unknown type object -----
        unknown_obj = SimpleNamespace(name="unknown")

        # ----- Middleware class instances -----

        class DummyAgentMiddleware(AgentMiddleware):
            async def process(self, context, next_fn):
                return await next_fn(context)

        class DummyFunctionMiddleware(FunctionMiddleware):
            async def process(self, context, next_fn):
                return await next_fn(context)

        class DummyChatMiddleware(ChatMiddleware):
            async def process(self, context, next_fn):
                return await next_fn(context)

        agent_instance = DummyAgentMiddleware()
        func_instance = DummyFunctionMiddleware()
        chat_instance = DummyChatMiddleware()

        # ----- Multiple sources: list and single item, None -----
        source1 = [agent_annotated, func_instance, None]
        source2 = chat_annotated

        # ----- Test categorization -----
        # First, handle conflict: _determine_middleware_type will raise for conflict
        with pytest.raises(ValueError, match="Middleware type mismatch"):
            categorize_middleware(conflict)

        # Now full categorization without conflict
        result = categorize_middleware(
            source1, source2, [agent_instance, unknown_obj, chat_instance]
        )

        # ----- Assertions -----
        # Agent category
        assert agent_annotated in result["agent"]
        assert agent_instance in result["agent"]
        assert unknown_obj in result["agent"]  # fallback for unknown type

        # Function category
        assert func_instance in result["function"]

        # Chat category
        assert chat_annotated in result["chat"]
        assert chat_instance in result["chat"]
