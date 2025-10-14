import asyncio
from collections.abc import Callable

import pytest

from DeepResearch.src.utils.workflow_middleware import (
    AgentMiddlewarePipeline,
    AgentRunContext,
    ChatContext,
    ChatMiddlewarePipeline,
    FunctionInvocationContext,
    FunctionMiddlewarePipeline,
    MiddlewareType,
    MiddlewareWrapper,
    agent_middleware,
    chat_middleware,
    function_middleware,
)


class TestWorkflowMiddleware:
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
            raise ValueError("agent error")  # ...

        agent_pipeline._register_middleware(faulty_agent_mw)
        context = AgentRunContext(agent="agentX", messages=[])

        with pytest.raises(ValueError, match="agent error") as excinfo:
            await agent_pipeline.execute("agentX", [], context, lambda ctx: "final")
        assert str(excinfo.value) == "agent error"  # ...

        # Function pipeline exception handling
        func_pipeline = FunctionMiddlewarePipeline()

        async def faulty_func_mw(ctx, next_fn):
            raise RuntimeError("function error")  # ...

        func_pipeline._register_middleware(faulty_func_mw)
        func_context = FunctionInvocationContext(function=lambda x: x, arguments=[1])

        with pytest.raises(RuntimeError) as excinfo2:
            await func_pipeline.execute(
                lambda x: x, [1], func_context, lambda ctx: "final"
            )
        assert str(excinfo2.value) == "function error"  # ...

        # Chat pipeline exception handling
        chat_pipeline = ChatMiddlewarePipeline()

        async def faulty_chat_mw(ctx, next_fn):
            raise KeyError("chat error")  # ...

        chat_pipeline._register_middleware(faulty_chat_mw)
        chat_context = ChatContext(chat_client="clientX", messages=[], chat_options={})

        with pytest.raises(KeyError) as excinfo3:
            await chat_pipeline.execute(
                "clientX", [], {}, chat_context, lambda ctx: "final"
            )
        assert str(excinfo3.value) == "'chat error'"  # ...
