"""
Workflow Middleware utilities for DeepCritical agent interaction design patterns.

This module vendors in the middleware system from the _workflows directory, providing
middleware pipeline management, execution control, and observability functionality
with minimal external dependencies.
"""

from __future__ import annotations

import inspect
from abc import ABC, abstractmethod
from collections.abc import Awaitable, Callable, MutableSequence
from enum import Enum
from typing import Any, ClassVar, Generic, TypeAlias, TypeVar

__all__ = [
    "AgentMiddleware",
    "AgentMiddlewareCallable",
    "AgentMiddlewarePipeline",
    "AgentMiddlewares",
    "AgentRunContext",
    "BaseMiddlewarePipeline",
    "ChatContext",
    "ChatMiddleware",
    "ChatMiddlewareCallable",
    "ChatMiddlewarePipeline",
    "FunctionInvocationContext",
    "FunctionMiddleware",
    "FunctionMiddlewareCallable",
    "FunctionMiddlewarePipeline",
    "Middleware",
    "MiddlewareType",
    "MiddlewareWrapper",
    "agent_middleware",
    "categorize_middleware",
    "chat_middleware",
    "create_function_middleware_pipeline",
    "function_middleware",
    "use_agent_middleware",
    "use_chat_middleware",
]


TAgent = TypeVar("TAgent")
TChatClient = TypeVar("TChatClient")
TContext = TypeVar("TContext")


class MiddlewareType(str, Enum):
    """Enum representing the type of middleware."""

    AGENT = "agent"
    FUNCTION = "function"
    CHAT = "chat"


class AgentRunContext:
    """Context object for agent middleware invocations."""

    INJECTABLE: ClassVar[set[str]] = {"agent", "result"}

    def __init__(
        self,
        agent: Any,
        messages: list[Any],
        is_streaming: bool = False,
        metadata: dict[str, Any] | None = None,
        result: Any = None,
        terminate: bool = False,
        kwargs: dict[str, Any] | None = None,
    ) -> None:
        """Initialize the AgentRunContext."""
        self.agent = agent
        self.messages = messages
        self.is_streaming = is_streaming
        self.metadata = metadata if metadata is not None else {}
        self.result = result
        self.terminate = terminate
        self.kwargs = kwargs if kwargs is not None else {}


class FunctionInvocationContext:
    """Context object for function middleware invocations."""

    INJECTABLE: ClassVar[set[str]] = {"function", "arguments", "result"}

    def __init__(
        self,
        function: Any,
        arguments: Any,
        metadata: dict[str, Any] | None = None,
        result: Any = None,
        terminate: bool = False,
        kwargs: dict[str, Any] | None = None,
    ) -> None:
        """Initialize the FunctionInvocationContext."""
        self.function = function
        self.arguments = arguments
        self.metadata = metadata if metadata is not None else {}
        self.result = result
        self.terminate = terminate
        self.kwargs = kwargs if kwargs is not None else {}


class ChatContext:
    """Context object for chat middleware invocations."""

    INJECTABLE: ClassVar[set[str]] = {"chat_client", "result"}

    def __init__(
        self,
        chat_client: Any,
        messages: MutableSequence[Any],
        chat_options: Any,
        is_streaming: bool = False,
        metadata: dict[str, Any] | None = None,
        result: Any = None,
        terminate: bool = False,
        kwargs: dict[str, Any] | None = None,
    ) -> None:
        """Initialize the ChatContext."""
        self.chat_client = chat_client
        self.messages = messages
        self.chat_options = chat_options
        self.is_streaming = is_streaming
        self.metadata = metadata if metadata is not None else {}
        self.result = result
        self.terminate = terminate
        self.kwargs = kwargs if kwargs is not None else {}


class AgentMiddleware(ABC):
    """Abstract base class for agent middleware."""

    @abstractmethod
    async def process(
        self,
        context: AgentRunContext,
        next: Callable[[AgentRunContext], Awaitable[None]],
    ) -> None:
        """Process an agent invocation."""
        ...


class FunctionMiddleware(ABC):
    """Abstract base class for function middleware."""

    @abstractmethod
    async def process(
        self,
        context: FunctionInvocationContext,
        next: Callable[[FunctionInvocationContext], Awaitable[None]],
    ) -> None:
        """Process a function invocation."""
        ...


class ChatMiddleware(ABC):
    """Abstract base class for chat middleware."""

    @abstractmethod
    async def process(
        self,
        context: ChatContext,
        next: Callable[[ChatContext], Awaitable[None]],
    ) -> None:
        """Process a chat client request."""
        ...


# Pure function type definitions for convenience
AgentMiddlewareCallable = Callable[
    [AgentRunContext, Callable[[AgentRunContext], Awaitable[None]]], Awaitable[None]
]

FunctionMiddlewareCallable = Callable[
    [FunctionInvocationContext, Callable[[FunctionInvocationContext], Awaitable[None]]],
    Awaitable[None],
]

ChatMiddlewareCallable = Callable[
    [ChatContext, Callable[[ChatContext], Awaitable[None]]], Awaitable[None]
]

# Type alias for all middleware types
Middleware: TypeAlias = (
    AgentMiddleware
    | AgentMiddlewareCallable
    | FunctionMiddleware
    | FunctionMiddlewareCallable
    | ChatMiddleware
    | ChatMiddlewareCallable
)
AgentMiddlewares: TypeAlias = AgentMiddleware | AgentMiddlewareCallable


class MiddlewareWrapper(Generic[TContext]):
    """Generic wrapper to convert pure functions into middleware protocol objects."""

    def __init__(
        self,
        func: Callable[
            [TContext, Callable[[TContext], Awaitable[None]]], Awaitable[None]
        ],
    ) -> None:
        self.func = func

    async def process(
        self, context: TContext, next: Callable[[TContext], Awaitable[None]]
    ) -> None:
        await self.func(context, next)


class BaseMiddlewarePipeline(ABC):
    """Base class for middleware pipeline execution."""

    def __init__(self) -> None:
        """Initialize the base middleware pipeline."""
        self._middlewares: list[Any] = []

    @abstractmethod
    def _register_middleware(self, middleware: Any) -> None:
        """Register a middleware item."""
        ...

    @property
    def has_middlewares(self) -> bool:
        """Check if there are any middlewares registered."""
        return bool(self._middlewares)

    def _register_middleware_with_wrapper(
        self,
        middleware: Any,
        expected_type: type,
    ) -> None:
        """Generic middleware registration with automatic wrapping."""
        if isinstance(middleware, expected_type):
            self._middlewares.append(middleware)
        elif callable(middleware):
            self._middlewares.append(MiddlewareWrapper(middleware))

    def _create_handler_chain(
        self,
        final_handler: Callable[[Any], Awaitable[Any]],
        result_container: dict[str, Any],
        result_key: str = "result",
    ) -> Callable[[Any], Awaitable[None]]:
        """Create a chain of middleware handlers."""

        def create_next_handler(index: int) -> Callable[[Any], Awaitable[None]]:
            if index >= len(self._middlewares):

                async def final_wrapper(c: Any) -> None:
                    # Execute actual handler and populate context for observability
                    result = await final_handler(c)
                    result_container[result_key] = result
                    c.result = result

                return final_wrapper

            middleware = self._middlewares[index]
            next_handler = create_next_handler(index + 1)

            async def current_handler(c: Any) -> None:
                await middleware.process(c, next_handler)

            return current_handler

        return create_next_handler(0)


class AgentMiddlewarePipeline(BaseMiddlewarePipeline):
    """Executes agent middleware in a chain."""

    def __init__(
        self, middlewares: list[AgentMiddleware | AgentMiddlewareCallable] | None = None
    ):
        """Initialize the agent middleware pipeline."""
        super().__init__()
        self._middlewares: list[AgentMiddleware] = []

        if middlewares:
            for middleware in middlewares:
                self._register_middleware(middleware)

    def _register_middleware(
        self, middleware: AgentMiddleware | AgentMiddlewareCallable
    ) -> None:
        """Register an agent middleware item."""
        self._register_middleware_with_wrapper(middleware, AgentMiddleware)

    async def execute(
        self,
        agent: Any,
        messages: list[Any],
        context: AgentRunContext,
        final_handler: Callable[[AgentRunContext], Awaitable[Any]],
    ) -> Any:
        """Execute the agent middleware pipeline for non-streaming."""
        # Update context with agent and messages
        context.agent = agent
        context.messages = messages
        context.is_streaming = False

        if not self._middlewares:
            return await final_handler(context)

        # Store the final result
        result_container: dict[str, Any] = {"result": None}

        # Custom final handler that handles termination and result override
        async def agent_final_handler(c: AgentRunContext) -> Any:
            # If terminate was set, return the result (which might be None)
            if c.terminate:
                if c.result is not None:
                    return c.result
                return None
            # Execute actual handler and populate context for observability
            return await final_handler(c)

        first_handler = self._create_handler_chain(
            agent_final_handler, result_container, "result"
        )
        await first_handler(context)

        # Return the result from result container or overridden result
        if context.result is not None:
            return context.result

        # If no result was set (next() not called), return empty result
        return result_container.get("result")


class FunctionMiddlewarePipeline(BaseMiddlewarePipeline):
    """Executes function middleware in a chain."""

    def __init__(
        self,
        middlewares: (
            list[FunctionMiddleware | FunctionMiddlewareCallable] | None
        ) = None,
    ):
        """Initialize the function middleware pipeline."""
        super().__init__()
        self._middlewares: list[FunctionMiddleware] = []

        if middlewares:
            for middleware in middlewares:
                self._register_middleware(middleware)

    def _register_middleware(
        self, middleware: FunctionMiddleware | FunctionMiddlewareCallable
    ) -> None:
        """Register a function middleware item."""
        self._register_middleware_with_wrapper(middleware, FunctionMiddleware)

    async def execute(
        self,
        function: Any,
        arguments: Any,
        context: FunctionInvocationContext,
        final_handler: Callable[[FunctionInvocationContext], Awaitable[Any]],
    ) -> Any:
        """Execute the function middleware pipeline."""
        # Update context with function and arguments
        context.function = function
        context.arguments = arguments

        if not self._middlewares:
            return await final_handler(context)

        # Store the final result
        result_container: dict[str, Any] = {"result": None}

        # Custom final handler that handles pre-existing results
        async def function_final_handler(c: FunctionInvocationContext) -> Any:
            # If terminate was set, skip execution and return the result (which might be None)
            if c.terminate:
                return c.result
            # Execute actual handler and populate context for observability
            return await final_handler(c)

        first_handler = self._create_handler_chain(
            function_final_handler, result_container, "result"
        )
        await first_handler(context)

        # Return the result from result container or overridden result
        if context.result is not None:
            return context.result
        return result_container["result"]


class ChatMiddlewarePipeline(BaseMiddlewarePipeline):
    """Executes chat middleware in a chain."""

    def __init__(
        self, middlewares: list[ChatMiddleware | ChatMiddlewareCallable] | None = None
    ):
        """Initialize the chat middleware pipeline."""
        super().__init__()
        self._middlewares: list[ChatMiddleware] = []

        if middlewares:
            for middleware in middlewares:
                self._register_middleware(middleware)

    def _register_middleware(
        self, middleware: ChatMiddleware | ChatMiddlewareCallable
    ) -> None:
        """Register a chat middleware item."""
        self._register_middleware_with_wrapper(middleware, ChatMiddleware)

    async def execute(
        self,
        chat_client: Any,
        messages: MutableSequence[Any],
        chat_options: Any,
        context: ChatContext,
        final_handler: Callable[[ChatContext], Awaitable[Any]],
        **kwargs: Any,
    ) -> Any:
        """Execute the chat middleware pipeline."""
        # Update context with chat client, messages, and options
        context.chat_client = chat_client
        context.messages = messages
        context.chat_options = chat_options

        if not self._middlewares:
            return await final_handler(context)

        # Store the final result
        result_container: dict[str, Any] = {"result": None}

        # Custom final handler that handles pre-existing results
        async def chat_final_handler(c: ChatContext) -> Any:
            # If terminate was set, skip execution and return the result (which might be None)
            if c.terminate:
                return c.result
            # Execute actual handler and populate context for observability
            return await final_handler(c)

        first_handler = self._create_handler_chain(
            chat_final_handler, result_container, "result"
        )
        await first_handler(context)

        # Return the result from result container or overridden result
        if context.result is not None:
            return context.result
        return result_container["result"]


def _determine_middleware_type(middleware: Any) -> MiddlewareType:
    """Determine middleware type using decorator and/or parameter type annotation."""
    # Check for decorator marker
    decorator_type: MiddlewareType | None = getattr(
        middleware, "_middleware_type", None
    )

    # Check for parameter type annotation
    param_type: MiddlewareType | None = None
    try:
        sig = inspect.signature(middleware)
        params = list(sig.parameters.values())

        # Must have at least 2 parameters (context and next)
        if len(params) >= 2:
            first_param = params[0]
            if hasattr(first_param.annotation, "__name__"):
                annotation_name = first_param.annotation.__name__
                if annotation_name == "AgentRunContext":
                    param_type = MiddlewareType.AGENT
                elif annotation_name == "FunctionInvocationContext":
                    param_type = MiddlewareType.FUNCTION
                elif annotation_name == "ChatContext":
                    param_type = MiddlewareType.CHAT
        else:
            # Not enough parameters - can't be valid middleware
            msg = (
                f"Middleware function must have at least 2 parameters (context, next), "
                f"but {middleware.__name__} has {len(params)}"
            )
            raise ValueError(msg)
    except Exception:
        # Signature inspection failed - continue with other checks
        pass

    if decorator_type and param_type:
        # Both decorator and parameter type specified - they must match
        if decorator_type != param_type:
            msg = (
                f"Middleware type mismatch: decorator indicates '{decorator_type.value}' "
                f"but parameter type indicates '{param_type.value}' for function {middleware.__name__}"
            )
            raise ValueError(msg)
        return decorator_type

    if decorator_type:
        # Just decorator specified - rely on decorator
        return decorator_type

    if param_type:
        # Just parameter type specified - rely on types
        return param_type

    # Neither decorator nor parameter type specified - throw exception
    msg = (
        f"Cannot determine middleware type for function {middleware.__name__}. "
        f"Please either use @agent_middleware/@function_middleware/@chat_middleware decorators "
        f"or specify parameter types (AgentRunContext, FunctionInvocationContext, or ChatContext)."
    )
    raise ValueError(msg)


def agent_middleware(func: AgentMiddlewareCallable) -> AgentMiddlewareCallable:
    """Decorator to mark a function as agent middleware."""
    # Add marker attribute to identify this as agent middleware
    func._middleware_type = MiddlewareType.AGENT
    return func


def function_middleware(func: FunctionMiddlewareCallable) -> FunctionMiddlewareCallable:
    """Decorator to mark a function as function middleware."""
    # Add marker attribute to identify this as function middleware
    func._middleware_type = MiddlewareType.FUNCTION
    return func


def chat_middleware(func: ChatMiddlewareCallable) -> ChatMiddlewareCallable:
    """Decorator to mark a function as chat middleware."""
    # Add marker attribute to identify this as chat middleware
    func._middleware_type = MiddlewareType.CHAT
    return func


def categorize_middleware(
    *middleware_sources: Any | list[Any] | None,
) -> dict[str, list[Any]]:
    """Categorize middleware from multiple sources into agent, function, and chat types."""
    result: dict[str, list[Any]] = {"agent": [], "function": [], "chat": []}

    # Merge all middleware sources into a single list
    all_middleware: list[Any] = []
    for source in middleware_sources:
        if source:
            if isinstance(source, list):
                all_middleware.extend(source)
            else:
                all_middleware.append(source)

    # Categorize each middleware item
    for middleware in all_middleware:
        if isinstance(middleware, AgentMiddleware):
            result["agent"].append(middleware)
        elif isinstance(middleware, FunctionMiddleware):
            result["function"].append(middleware)
        elif isinstance(middleware, ChatMiddleware):
            result["chat"].append(middleware)
        elif callable(middleware):
            # Always call _determine_middleware_type to ensure proper validation
            middleware_type = _determine_middleware_type(middleware)
            if middleware_type == MiddlewareType.AGENT:
                result["agent"].append(middleware)
            elif middleware_type == MiddlewareType.FUNCTION:
                result["function"].append(middleware)
            elif middleware_type == MiddlewareType.CHAT:
                result["chat"].append(middleware)
        else:
            # Fallback to agent middleware for unknown types
            result["agent"].append(middleware)

    return result


def create_function_middleware_pipeline(
    *middleware_sources: list[Any] | None,
) -> FunctionMiddlewarePipeline | None:
    """Create a function middleware pipeline from multiple middleware sources."""
    middleware = categorize_middleware(*middleware_sources)
    function_middlewares = middleware["function"]
    return (
        FunctionMiddlewarePipeline(function_middlewares)
        if function_middlewares
        else None
    )


# Decorator for adding middleware support to agent classes
def use_agent_middleware(agent_class: type[TAgent]) -> type[TAgent]:
    """Class decorator that adds middleware support to an agent class."""
    # Store original methods
    original_run = agent_class.run
    original_run_stream = agent_class.run_stream

    async def middleware_enabled_run(
        self: Any,
        messages: Any = None,
        *,
        thread: Any = None,
        middleware: Any | list[Any] | None = None,
        **kwargs: Any,
    ) -> Any:
        """Middleware-enabled run method."""
        # Build fresh middleware pipelines from current middleware collection and run-level middleware
        agent_middleware = getattr(self, "middleware", None)

        agent_pipeline, function_pipeline, chat_middlewares = (
            _build_middleware_pipelines(agent_middleware, middleware)
        )

        # Add function middleware pipeline to kwargs if available
        if function_pipeline.has_middlewares:
            kwargs["_function_middleware_pipeline"] = function_pipeline

        # Pass chat middleware through kwargs for run-level application
        if chat_middlewares:
            kwargs["middleware"] = chat_middlewares

        normalized_messages = self._normalize_messages(messages)

        # Execute with middleware if available
        if agent_pipeline.has_middlewares:
            context = AgentRunContext(
                agent=self,
                messages=normalized_messages,
                is_streaming=False,
                kwargs=kwargs,
            )

            async def _execute_handler(ctx: AgentRunContext) -> Any:
                return await original_run(
                    self, ctx.messages, thread=thread, **ctx.kwargs
                )

            result = await agent_pipeline.execute(
                self,
                normalized_messages,
                context,
                _execute_handler,
            )

            return result if result else None

        # No middleware, execute directly
        return await original_run(self, normalized_messages, thread=thread, **kwargs)

    def middleware_enabled_run_stream(
        self: Any,
        messages: Any = None,
        *,
        thread: Any = None,
        middleware: Any | list[Any] | None = None,
        **kwargs: Any,
    ) -> Any:
        """Middleware-enabled run_stream method."""
        # Build fresh middleware pipelines from current middleware collection and run-level middleware
        agent_middleware = getattr(self, "middleware", None)
        agent_pipeline, function_pipeline, chat_middlewares = (
            _build_middleware_pipelines(agent_middleware, middleware)
        )

        # Add function middleware pipeline to kwargs if available
        if function_pipeline.has_middlewares:
            kwargs["_function_middleware_pipeline"] = function_pipeline

        # Pass chat middleware through kwargs for run-level application
        if chat_middlewares:
            kwargs["middleware"] = chat_middlewares

        normalized_messages = self._normalize_messages(messages)

        # Execute with middleware if available
        if agent_pipeline.has_middlewares:
            context = AgentRunContext(
                agent=self,
                messages=normalized_messages,
                is_streaming=True,
                kwargs=kwargs,
            )

            async def _execute_stream_handler(ctx: AgentRunContext) -> Any:
                async for update in original_run_stream(
                    self, ctx.messages, thread=thread, **ctx.kwargs
                ):
                    yield update

            async def _stream_generator() -> Any:
                result = await agent_pipeline.execute(
                    self,
                    normalized_messages,
                    context,
                    _execute_stream_handler,
                )
                yield result

            return _stream_generator()

        # No middleware, execute directly
        return original_run_stream(self, normalized_messages, thread=thread, **kwargs)

    agent_class.run = middleware_enabled_run
    agent_class.run_stream = middleware_enabled_run_stream

    return agent_class


def use_chat_middleware(chat_client_class: type[TChatClient]) -> type[TChatClient]:
    """Class decorator that adds middleware support to a chat client class."""
    # Store original methods
    original_get_response = chat_client_class.get_response
    original_get_streaming_response = chat_client_class.get_streaming_response

    async def middleware_enabled_get_response(
        self: Any,
        messages: Any,
        **kwargs: Any,
    ) -> Any:
        """Middleware-enabled get_response method."""
        # Check if middleware is provided at call level or instance level
        call_middleware = kwargs.pop("middleware", None)
        instance_middleware = getattr(self, "middleware", None)

        # Merge all middleware and separate by type
        middleware = categorize_middleware(instance_middleware, call_middleware)
        chat_middleware_list = middleware["chat"]

        # Extract function middleware for the function invocation pipeline
        function_middleware_list = middleware["function"]

        # Pass function middleware to function invocation system if present
        if function_middleware_list:
            kwargs["_function_middleware_pipeline"] = FunctionMiddlewarePipeline(
                function_middleware_list
            )

        # If no chat middleware, use original method
        if not chat_middleware_list:
            return await original_get_response(self, messages, **kwargs)

        # Create pipeline and execute with middleware
        from DeepResearch.src.datatypes.agent_framework_options import ChatOptions

        # Extract chat_options or create default
        chat_options = kwargs.pop("chat_options", ChatOptions())

        pipeline = ChatMiddlewarePipeline(chat_middleware_list)
        context = ChatContext(
            chat_client=self,
            messages=self.prepare_messages(messages, chat_options),
            chat_options=chat_options,
            is_streaming=False,
            kwargs=kwargs,
        )

        async def final_handler(ctx: ChatContext) -> Any:
            return await original_get_response(
                self, list(ctx.messages), chat_options=ctx.chat_options, **ctx.kwargs
            )

        return await pipeline.execute(
            chat_client=self,
            messages=context.messages,
            chat_options=context.chat_options,
            context=context,
            final_handler=final_handler,
            **kwargs,
        )

    def middleware_enabled_get_streaming_response(
        self: Any,
        messages: Any,
        **kwargs: Any,
    ) -> Any:
        """Middleware-enabled get_streaming_response method."""

        async def _stream_generator() -> Any:
            # Check if middleware is provided at call level or instance level
            call_middleware = kwargs.pop("middleware", None)
            instance_middleware = getattr(self, "middleware", None)

            # Merge middleware from both sources, filtering for chat middleware only
            all_middleware: list[ChatMiddleware | ChatMiddlewareCallable] = (
                _merge_and_filter_chat_middleware(instance_middleware, call_middleware)
            )

            # If no middleware, use original method
            if not all_middleware:
                async for update in original_get_streaming_response(
                    self, messages, **kwargs
                ):
                    yield update
                return

            # Create pipeline and execute with middleware
            from DeepResearch.src.datatypes.agent_framework_options import ChatOptions

            # Extract chat_options or create default
            chat_options = kwargs.pop("chat_options", ChatOptions())

            pipeline = ChatMiddlewarePipeline(all_middleware)
            context = ChatContext(
                chat_client=self,
                messages=self.prepare_messages(messages, chat_options),
                chat_options=chat_options,
                is_streaming=True,
                kwargs=kwargs,
            )

            def final_handler(ctx: ChatContext) -> Any:
                return original_get_streaming_response(
                    self,
                    list(ctx.messages),
                    chat_options=ctx.chat_options,
                    **ctx.kwargs,
                )

            result = await pipeline.execute(
                chat_client=self,
                messages=context.messages,
                chat_options=context.chat_options,
                context=context,
                final_handler=final_handler,
                **kwargs,
            )
            yield result

        return _stream_generator()

    # Replace methods
    chat_client_class.get_response = middleware_enabled_get_response
    chat_client_class.get_streaming_response = middleware_enabled_get_streaming_response

    return chat_client_class


def _build_middleware_pipelines(
    agent_level_middlewares: Any | list[Any] | None,
    run_level_middlewares: Any | list[Any] | None = None,
) -> tuple[
    AgentMiddlewarePipeline,
    FunctionMiddlewarePipeline,
    list[ChatMiddleware | ChatMiddlewareCallable],
]:
    """Build fresh agent and function middleware pipelines from the provided middleware lists."""
    middleware = categorize_middleware(agent_level_middlewares, run_level_middlewares)

    return (
        AgentMiddlewarePipeline(middleware["agent"]),
        FunctionMiddlewarePipeline(middleware["function"]),
        middleware["chat"],
    )


def _merge_and_filter_chat_middleware(
    instance_middleware: Any | list[Any] | None,
    call_middleware: Any | list[Any] | None,
) -> list[ChatMiddleware | ChatMiddlewareCallable]:
    """Merge instance-level and call-level middleware, filtering for chat middleware only."""
    middleware = categorize_middleware(instance_middleware, call_middleware)
    return middleware["chat"]


# Export all middleware components
__all__ = [
    "AgentMiddleware",
    "AgentMiddlewareCallable",
    "AgentMiddlewarePipeline",
    "AgentMiddlewares",
    "AgentRunContext",
    "BaseMiddlewarePipeline",
    "ChatContext",
    "ChatMiddleware",
    "ChatMiddlewareCallable",
    "ChatMiddlewarePipeline",
    "FunctionInvocationContext",
    "FunctionMiddleware",
    "FunctionMiddlewareCallable",
    "FunctionMiddlewarePipeline",
    "Middleware",
    "MiddlewareType",
    "MiddlewareWrapper",
    "agent_middleware",
    "categorize_middleware",
    "chat_middleware",
    "create_function_middleware_pipeline",
    "function_middleware",
    "use_agent_middleware",
    "use_chat_middleware",
]
