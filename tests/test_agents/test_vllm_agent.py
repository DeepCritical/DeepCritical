"""Tests for the DeepResearch VLLM agent wrapper."""

from __future__ import annotations

import asyncio
import time
from types import SimpleNamespace
from typing import Any

import pytest

from DeepResearch.src.agents import vllm_agent as vllm_agent_module
from DeepResearch.src.agents.vllm_agent import (
    VLLMAgent,
    create_advanced_vllm_agent,
    create_vllm_agent,
)
from DeepResearch.src.datatypes.vllm_agent import VLLMAgentConfig
from DeepResearch.src.datatypes.vllm_dataclass import (
    ChatCompletionChoice,
    ChatCompletionRequest,
    ChatCompletionResponse,
    ChatMessage,
    CompletionChoice,
    CompletionRequest,
    CompletionResponse,
    EmbeddingData,
    EmbeddingRequest,
    EmbeddingResponse,
    QuantizationMethod,
    UsageStats,
)


def _usage() -> UsageStats:
    return UsageStats(prompt_tokens=1, completion_tokens=1, total_tokens=2)


def _chat_response(text: str = "chat response", model: str = "test-model"):
    return ChatCompletionResponse(
        id="chatcmpl-test",
        created=1,
        model=model,
        choices=[
            ChatCompletionChoice(
                index=0,
                message=ChatMessage(role="assistant", content=text),
                finish_reason="stop",
            )
        ],
        usage=_usage(),
    )


def _completion_response(text: str = "completion", model: str = "test-model"):
    return CompletionResponse(
        id="cmpl-test",
        created=1,
        model=model,
        choices=[CompletionChoice(index=0, text=text, finish_reason="stop")],
        usage=_usage(),
    )


def _embedding_response(vectors: list[list[float]], model: str = "embed-model"):
    return EmbeddingResponse(
        data=[
            EmbeddingData(object="embedding", embedding=vector, index=index)
            for index, vector in enumerate(vectors)
        ],
        model=model,
        usage=_usage(),
    )


class RecordingClient:
    def __init__(self, *, delay: float = 0.0):
        self.delay = delay
        self.health_calls = 0
        self.close_calls = 0
        self.chat_requests: list[ChatCompletionRequest] = []
        self.completion_requests: list[CompletionRequest] = []
        self.embedding_requests: list[EmbeddingRequest] = []
        self.stream_requests: list[ChatCompletionRequest] = []

    async def _maybe_delay(self) -> None:
        if self.delay:
            await asyncio.sleep(self.delay)

    async def health(self) -> dict[str, Any]:
        self.health_calls += 1
        return {"status": "healthy"}

    async def close(self) -> None:
        self.close_calls += 1

    async def chat_completions(
        self, request: ChatCompletionRequest
    ) -> ChatCompletionResponse:
        await self._maybe_delay()
        self.chat_requests.append(request)
        return _chat_response(model=request.model)

    async def completions(self, request: CompletionRequest) -> CompletionResponse:
        await self._maybe_delay()
        self.completion_requests.append(request)
        return _completion_response(model=request.model)

    async def embeddings(self, request: EmbeddingRequest) -> EmbeddingResponse:
        await self._maybe_delay()
        self.embedding_requests.append(request)
        texts = [request.input] if isinstance(request.input, str) else request.input
        vectors = [[float(index), 1.0] for index, _text in enumerate(texts)]
        return _embedding_response(vectors, model=request.model)

    async def chat_completions_stream(self, request: ChatCompletionRequest):
        self.stream_requests.append(request)
        for text in ("stream ", "response"):
            yield {
                "choices": [
                    {
                        "delta": {"content": text},
                        "finish_reason": None,
                    }
                ]
            }


class ErrorClient(RecordingClient):
    async def chat_completions(
        self, request: ChatCompletionRequest
    ) -> ChatCompletionResponse:
        raise RuntimeError("chat failed")

    async def completions(self, request: CompletionRequest) -> CompletionResponse:
        raise RuntimeError("completion failed")

    async def embeddings(self, request: EmbeddingRequest) -> EmbeddingResponse:
        raise RuntimeError("embedding failed")


def _agent(config: VLLMAgentConfig | None = None) -> VLLMAgent:
    return VLLMAgent(
        config
        or VLLMAgentConfig(
            default_model="default-model",
            embedding_model="embedding-model",
            max_tokens=64,
            temperature=0.4,
            top_p=0.8,
        )
    )


def test_initialization_wires_config_and_dependencies() -> None:
    config = VLLMAgentConfig(
        client_config={"base_url": "http://vllm.test", "transport_mode": "simulate"},
        default_model="chat-model",
        embedding_model="embed-model",
    )

    agent = VLLMAgent(config)

    assert agent.config is config
    assert agent.dependencies.default_model == "chat-model"
    assert agent.dependencies.embedding_model == "embed-model"
    assert agent.dependencies.vllm_client.base_url == "http://vllm.test"
    assert agent.dependencies.vllm_client.transport_mode == "simulate"


@pytest.mark.asyncio
async def test_initialize_and_close_delegate_to_client() -> None:
    agent = _agent()
    client = RecordingClient()
    agent.client = client  # type: ignore[assignment]

    await agent.initialize()
    await agent.close()

    assert client.health_calls == 1
    assert client.close_calls == 1


@pytest.mark.asyncio
async def test_chat_uses_defaults_and_allows_generation_overrides() -> None:
    agent = _agent()
    client = RecordingClient()
    agent.client = client  # type: ignore[assignment]

    text = await agent.chat(
        [{"role": "user", "content": "hello"}],
        max_tokens=12,
        temperature=0.2,
        top_p=0.7,
        stop=["done"],
    )

    assert text == "chat response"
    request = client.chat_requests[0]
    assert request.model == "default-model"
    assert request.max_tokens == 12
    assert request.temperature == 0.2
    assert request.top_p == 0.7
    assert request.stop == ["done"]


@pytest.mark.asyncio
async def test_complete_uses_model_override_and_generation_overrides() -> None:
    agent = _agent()
    client = RecordingClient()
    agent.client = client  # type: ignore[assignment]

    text = await agent.complete(
        "The answer is",
        model="completion-model",
        max_tokens=24,
        temperature=0.1,
        top_p=0.5,
    )

    assert text == "completion"
    request = client.completion_requests[0]
    assert request.model == "completion-model"
    assert request.prompt == "The answer is"
    assert request.max_tokens == 24
    assert request.temperature == 0.1
    assert request.top_p == 0.5


@pytest.mark.asyncio
async def test_embed_normalizes_string_input_and_uses_embedding_model() -> None:
    agent = _agent()
    client = RecordingClient()
    agent.client = client  # type: ignore[assignment]

    embeddings = await agent.embed("hello")

    assert embeddings == [[0.0, 1.0]]
    request = client.embedding_requests[0]
    assert request.model == "embedding-model"
    assert request.input == ["hello"]


@pytest.mark.asyncio
async def test_chat_stream_forces_stream_and_combines_chunks() -> None:
    agent = _agent()
    client = RecordingClient()
    agent.client = client  # type: ignore[assignment]

    text = await agent.chat_stream(
        [{"role": "user", "content": "hello"}],
        stream=False,
        max_tokens=5,
    )

    assert text == "stream response"
    request = client.stream_requests[0]
    assert request.stream is True
    assert request.max_tokens == 5


@pytest.mark.asyncio
async def test_invalid_prompt_shape_raises_validation_error() -> None:
    agent = _agent()
    client = RecordingClient()
    agent.client = client  # type: ignore[assignment]

    with pytest.raises(Exception):
        await agent.chat("not a message list")  # type: ignore[arg-type]


@pytest.mark.asyncio
async def test_client_errors_propagate() -> None:
    agent = _agent()
    agent.client = ErrorClient()  # type: ignore[assignment]

    with pytest.raises(RuntimeError, match="chat failed"):
        await agent.chat([{"role": "user", "content": "hello"}])
    with pytest.raises(RuntimeError, match="completion failed"):
        await agent.complete("hello")
    with pytest.raises(RuntimeError, match="embedding failed"):
        await agent.embed(["hello"])


@pytest.mark.asyncio
async def test_concurrent_wrapper_calls_are_async_and_return_expected_values() -> None:
    agent = _agent()
    client = RecordingClient(delay=0.01)
    agent.client = client  # type: ignore[assignment]

    started = time.perf_counter()
    chat_text, completion_text, embeddings = await asyncio.gather(
        agent.chat([{"role": "user", "content": "hello"}]),
        agent.complete("hello"),
        agent.embed(["a", "b"]),
    )
    elapsed = time.perf_counter() - started

    assert chat_text == "chat response"
    assert completion_text == "completion"
    assert embeddings == [[0.0, 1.0], [1.0, 1.0]]
    assert elapsed < 0.2


def test_create_vllm_agent_preserves_basic_configuration() -> None:
    agent = create_vllm_agent(
        model_name="custom-model",
        base_url="http://127.0.0.1:8000",
        api_key="test-key",
        embedding_model="custom-embed",
        transport_mode="simulate",
        timeout=3.0,
    )

    assert agent.config.default_model == "custom-model"
    assert agent.config.embedding_model == "custom-embed"
    assert agent.dependencies.vllm_client.base_url == "http://127.0.0.1:8000"
    assert agent.dependencies.vllm_client.api_key == "test-key"
    assert agent.dependencies.vllm_client.timeout == 3.0


def test_create_advanced_vllm_agent_preserves_vllm_config() -> None:
    agent = create_advanced_vllm_agent(
        model_name="advanced-model",
        base_url="http://advanced.test",
        quantization=QuantizationMethod.AWQ,
        tensor_parallel_size=2,
        gpu_memory_utilization=0.5,
        transport_mode="simulate",
    )

    vllm_config = agent.dependencies.vllm_client.vllm_config
    assert agent.config.default_model == "advanced-model"
    assert agent.dependencies.vllm_client.base_url == "http://advanced.test"
    assert vllm_config is not None
    assert vllm_config.model.model == "advanced-model"
    assert vllm_config.model.quantization == QuantizationMethod.AWQ
    assert vllm_config.parallel.tensor_parallel_size == 2
    assert vllm_config.cache.gpu_memory_utilization == 0.5


class FakePydanticAgent:
    def __init__(self, *args: Any, **kwargs: Any):
        self.args = args
        self.kwargs = kwargs
        self.tools: dict[str, Any] = {}

    def tool(self, func):
        self.tools[func.__name__] = func
        return func


@pytest.mark.asyncio
async def test_pydantic_ai_tools_use_supported_client_paths(monkeypatch) -> None:
    monkeypatch.setattr("pydantic_ai.Agent", FakePydanticAgent)
    agent = create_vllm_agent(
        model_name="pydantic-model",
        embedding_model="pydantic-embed",
        transport_mode="simulate",
    )
    pydantic_agent = agent.to_pydantic_ai_agent()
    ctx = SimpleNamespace(deps=agent.dependencies)

    chat_text = await pydantic_agent.tools["chat_completion"](
        ctx,
        [{"role": "user", "content": "hello"}],
    )
    completion_text = await pydantic_agent.tools["text_completion"](ctx, "hello")
    embeddings = await pydantic_agent.tools["generate_embeddings"](ctx, "hello")
    model_ids = await pydantic_agent.tools["list_models"](ctx)
    model_info = await pydantic_agent.tools["get_model_info"](ctx, "vllm-model")
    tokens = await pydantic_agent.tools["tokenize"](ctx, "hello world")
    detokenized = await pydantic_agent.tools["detokenize"](ctx, [1, 2])
    health = await pydantic_agent.tools["health_check"](ctx)

    assert "[Simulated reply" in chat_text
    assert "[Simulated completion" in completion_text
    assert embeddings == [[0.0] * 384]
    assert model_ids == ["vllm-model"]
    assert model_info["id"] == "vllm-model"
    assert tokens["tokens"] == [0, 1]
    assert detokenized["text"] == "1 2"
    assert health["status"] == "healthy"


@pytest.mark.asyncio
async def test_pydantic_ai_model_info_reports_missing_model(monkeypatch) -> None:
    monkeypatch.setattr("pydantic_ai.Agent", FakePydanticAgent)
    agent = create_vllm_agent(transport_mode="simulate")
    pydantic_agent = agent.to_pydantic_ai_agent()
    ctx = SimpleNamespace(deps=agent.dependencies)

    with pytest.raises(ValueError, match="Model not found"):
        await pydantic_agent.tools["get_model_info"](ctx, "missing-model")
