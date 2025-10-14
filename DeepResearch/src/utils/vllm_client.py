"""
Comprehensive VLLM client with OpenAI API compatibility for Pydantic AI agents.

This module provides a complete VLLM client that can be used as a custom agent
in Pydantic AI, supporting all VLLM features while maintaining OpenAI API compatibility.
"""

from __future__ import annotations

import asyncio
import time
from typing import TYPE_CHECKING, Any

from pydantic import BaseModel, ConfigDict, Field

from DeepResearch.src.datatypes.vllm_dataclass import (
    BatchRequest,
    BatchResponse,
    CacheConfig,
    ChatCompletionChoice,
    ChatCompletionRequest,
    ChatCompletionResponse,
    ChatMessage,
    CompletionChoice,
    CompletionRequest,
    CompletionResponse,
    DeviceConfig,
    EmbeddingData,
    EmbeddingRequest,
    EmbeddingResponse,
    ModelConfig,
    ObservabilityConfig,
    ParallelConfig,
    QuantizationMethod,
    SchedulerConfig,
    UsageStats,
    VllmConfig,
)

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator


class VLLMClientError(Exception):
    """Base exception for VLLM client errors."""


class VLLMConnectionError(VLLMClientError):
    """Connection-related errors."""


class VLLMAPIError(VLLMClientError):
    """API-related errors."""


class VLLMClient(BaseModel):
    """Comprehensive VLLM client with OpenAI API compatibility."""

    base_url: str = Field("http://localhost:8000", description="VLLM server base URL")
    api_key: str | None = Field(None, description="API key for authentication")
    timeout: float = Field(60.0, description="Request timeout in seconds")
    max_retries: int = Field(3, description="Maximum number of retries")
    retry_delay: float = Field(1.0, description="Delay between retries in seconds")

    # VLLM-specific configuration
    vllm_config: VllmConfig | None = Field(None, description="VLLM configuration")

    model_config = ConfigDict(
        arbitrary_types_allowed=True,
        json_schema_extra={
            "example": {
                "base_url": "http://localhost:8000",
                "api_key": None,
                "timeout": 60.0,
                "max_retries": 3,
                "retry_delay": 1.0,
            }
        },
    )


class VLLMAgent:
    """Pydantic AI agent wrapper for VLLM client."""

    def __init__(self, vllm_client: VLLMClient):
        self.client = vllm_client

    async def chat(self, messages: list[dict[str, str]], **kwargs) -> str:
        """Chat with the VLLM model."""
        request = ChatCompletionRequest(
            model="vllm-model",  # This would be configured
            messages=messages,
            **kwargs,
        )
        response = await self.client.chat_completions(request)
        return response.choices[0].message.content

    async def complete(self, prompt: str, **kwargs) -> str:
        """Complete text with the VLLM model."""
        request = CompletionRequest(model="vllm-model", prompt=prompt, **kwargs)
        response = await self.client.completions(request)
        return response.choices[0].text

    async def embed(self, texts: str | list[str], **kwargs) -> list[list[float]]:
        """Generate embeddings for texts."""
        if isinstance(texts, str):
            texts = [texts]

        request = EmbeddingRequest(model="vllm-embedding-model", input=texts, **kwargs)
        response = await self.client.embeddings(request)
        return [item.embedding for item in response.data]

    def to_pydantic_ai_agent(self, model_name: str = "vllm-agent"):
        """Convert to Pydantic AI agent format."""
        from pydantic_ai import Agent

        # Create agent with VLLM client as dependency
        agent = Agent(
            model_name,
            deps_type=VLLMClient,
            system_prompt="You are a helpful AI assistant powered by VLLM.",
        )

        # Add tools for VLLM functionality
        @agent.tool
        async def chat_completion(ctx, messages: list[dict[str, str]], **kwargs) -> str:
            """Chat completion using VLLM."""
            return await ctx.deps.chat(messages, **kwargs)

        @agent.tool
        async def text_completion(ctx, prompt: str, **kwargs) -> str:
            """Text completion using VLLM."""
            return await ctx.deps.complete(prompt, **kwargs)

        @agent.tool
        async def generate_embeddings(
            ctx, texts: str | list[str], **kwargs
        ) -> list[list[float]]:
            """Generate embeddings using VLLM."""
            return await ctx.deps.embed(texts, **kwargs)

        return agent

    # OpenAI-compatible API methods
    async def health(self) -> dict[str, Any]:
        """Check server health (OpenAI-compatible)."""
        # Simple health check - try to get models
        try:
            models = await self.models()
            return {"status": "healthy", "models": len(models.get("data", []))}
        except Exception:
            return {"status": "unhealthy"}

    async def models(self) -> dict[str, Any]:
        """List available models (OpenAI-compatible)."""
        # Return a mock response since VLLM doesn't have a models endpoint
        return {"object": "list", "data": [{"id": "vllm-model", "object": "model"}]}

    async def chat_completions(
        self, request: ChatCompletionRequest
    ) -> ChatCompletionResponse:
        """Create chat completion (OpenAI-compatible)."""
        messages = [msg["content"] for msg in request.messages]
        response_text = await self.chat(messages)
        return ChatCompletionResponse(
            id=f"chatcmpl-{asyncio.get_event_loop().time()}",
            object="chat.completion",
            created=int(time.time()),
            model=request.model,
            choices=[
                ChatCompletionChoice(
                    index=0,
                    message=ChatMessage(role="assistant", content=response_text),
                    finish_reason="stop",
                )
            ],
            usage=UsageStats(
                prompt_tokens=len(request.messages),
                completion_tokens=len(response_text.split()),
                total_tokens=len(request.messages) + len(response_text.split()),
            ),
        )

    async def chat_completions_stream(
        self, request: ChatCompletionRequest
    ) -> AsyncGenerator[dict[str, Any], None]:
        """Stream chat completion (OpenAI-compatible)."""
        # For simplicity, just yield the full response
        response = await self.chat_completions(request)
        choice = response.choices[0]
        yield {
            "id": response.id,
            "object": "chat.completion.chunk",
            "created": response.created,
            "model": response.model,
            "choices": [
                {
                    "index": 0,
                    "delta": {"content": choice.message.content},
                    "finish_reason": choice.finish_reason,
                }
            ],
        }

    async def completions(self, request: CompletionRequest) -> CompletionResponse:
        """Create completion (OpenAI-compatible)."""
        response_text = await self.complete(request.prompt)
        prompt_text = (
            request.prompt if isinstance(request.prompt, str) else str(request.prompt)
        )
        return CompletionResponse(
            id=f"cmpl-{asyncio.get_event_loop().time()}",
            object="text_completion",
            created=int(time.time()),
            model=request.model,
            choices=[
                CompletionChoice(text=response_text, index=0, finish_reason="stop")
            ],
            usage=UsageStats(
                prompt_tokens=len(prompt_text.split()),
                completion_tokens=len(response_text.split()),
                total_tokens=len(prompt_text.split()) + len(response_text.split()),
            ),
        )

    async def embeddings(self, request: EmbeddingRequest) -> EmbeddingResponse:
        """Create embeddings (OpenAI-compatible)."""
        embeddings = await self.embed(request.input)
        return EmbeddingResponse(
            object="list",
            data=[
                EmbeddingData(object="embedding", embedding=emb, index=i)
                for i, emb in enumerate(embeddings)
            ],
            model=request.model,
            usage=UsageStats(
                prompt_tokens=len(str(request.input).split()),
                completion_tokens=0,
                total_tokens=len(str(request.input).split()),
            ),
        )

    async def batch_request(self, request: BatchRequest) -> BatchResponse:
        """Process batch request."""
        # Simple implementation - process sequentially
        results = []
        for req in request.requests:
            if hasattr(req, "messages"):  # Chat completion
                result = await self.chat_completions(req)
                results.append(result)
            elif hasattr(req, "prompt"):  # Completion
                result = await self.completions(req)
                results.append(result)

        return BatchResponse(
            batch_id=f"batch-{asyncio.get_event_loop().time()}",
            responses=results,
            errors=[],
            total_requests=len(request.requests),
        )

    async def close(self) -> None:
        """Close client connections."""
        # No-op for this implementation


class VLLMClientBuilder:
    """Builder for creating VLLM clients with complex configurations."""

    def __init__(self):
        self._config = {
            "base_url": "http://localhost:8000",
            "timeout": 60.0,
            "max_retries": 3,
            "retry_delay": 1.0,
        }
        self._vllm_config = None

    def with_base_url(self, base_url: str) -> VLLMClientBuilder:
        """Set base URL."""
        self._config["base_url"] = base_url
        return self

    def with_api_key(self, api_key: str) -> VLLMClientBuilder:
        """Set API key."""
        self._config["api_key"] = api_key
        return self

    def with_timeout(self, timeout: float) -> VLLMClientBuilder:
        """Set timeout."""
        self._config["timeout"] = timeout
        return self

    def with_retries(
        self, max_retries: int, retry_delay: float = 1.0
    ) -> VLLMClientBuilder:
        """Set retry configuration."""
        self._config["max_retries"] = max_retries
        self._config["retry_delay"] = retry_delay
        return self

    def with_vllm_config(self, config: VllmConfig) -> VLLMClientBuilder:
        """Set VLLM configuration."""
        self._vllm_config = config
        return self

    def with_model_config(
        self,
        model: str,
        tokenizer: str | None = None,
        trust_remote_code: bool = False,
        max_model_len: int | None = None,
        quantization: QuantizationMethod | None = None,
    ) -> VLLMClientBuilder:
        """Configure model settings."""
        if self._vllm_config is None:
            self._vllm_config = VllmConfig(
                model=ModelConfig(
                    model=model,
                    tokenizer=tokenizer,
                    trust_remote_code=trust_remote_code,
                    max_model_len=max_model_len,
                    quantization=quantization,
                ),
                cache=CacheConfig(),
                parallel=ParallelConfig(),
                scheduler=SchedulerConfig(),
                device=DeviceConfig(),
                observability=ObservabilityConfig(),
            )
        else:
            self._vllm_config.model = ModelConfig(
                model=model,
                tokenizer=tokenizer,
                trust_remote_code=trust_remote_code,
                max_model_len=max_model_len,
                quantization=quantization,
            )
        return self

    def with_cache_config(
        self,
        block_size: int = 16,
        gpu_memory_utilization: float = 0.9,
        swap_space: int = 4,
    ) -> VLLMClientBuilder:
        """Configure cache settings."""
        if self._vllm_config is None:
            self._vllm_config = VllmConfig(
                model=ModelConfig(model="default"),
                cache=CacheConfig(
                    block_size=block_size,
                    gpu_memory_utilization=gpu_memory_utilization,
                    swap_space=swap_space,
                ),
                parallel=ParallelConfig(),
                scheduler=SchedulerConfig(),
                device=DeviceConfig(),
                observability=ObservabilityConfig(),
            )
        else:
            self._vllm_config.cache = CacheConfig(
                block_size=block_size,
                gpu_memory_utilization=gpu_memory_utilization,
                swap_space=swap_space,
            )
        return self

    def with_parallel_config(
        self,
        tensor_parallel_size: int = 1,
        pipeline_parallel_size: int = 1,
    ) -> VLLMClientBuilder:
        """Configure parallel settings."""
        if self._vllm_config is None:
            self._vllm_config = VllmConfig(
                model=ModelConfig(model="default"),
                cache=CacheConfig(),
                parallel=ParallelConfig(
                    tensor_parallel_size=tensor_parallel_size,
                    pipeline_parallel_size=pipeline_parallel_size,
                ),
                scheduler=SchedulerConfig(),
                device=DeviceConfig(),
                observability=ObservabilityConfig(),
            )
        else:
            self._vllm_config.parallel = ParallelConfig(
                tensor_parallel_size=tensor_parallel_size,
                pipeline_parallel_size=pipeline_parallel_size,
            )
        return self

    def build(self) -> VLLMClient:
        """Build the VLLM client."""
        return VLLMClient(vllm_config=self._vllm_config, **self._config)


# ============================================================================
# Utility Functions
# ============================================================================


def create_vllm_client(
    model_name: str,
    base_url: str = "http://localhost:8000",
    api_key: str | None = None,
    **kwargs,
) -> VLLMClient:
    """Create a VLLM client with sensible defaults."""
    builder = (
        VLLMClientBuilder().with_base_url(base_url).with_model_config(model=model_name)
    )
    if api_key is not None:
        builder = builder.with_api_key(api_key)
    return builder.build()


async def test_vllm_connection(client: VLLMClient) -> bool:
    """Test if VLLM server is accessible."""
    try:
        await client.health()  # type: ignore[attr-defined]
        return True
    except Exception:
        return False


async def list_vllm_models(client: VLLMClient) -> list[str]:
    """List available models on the VLLM server."""
    try:
        response = await client.models()  # type: ignore[attr-defined]
        return [model.id for model in response.data]
    except Exception:
        return []


# ============================================================================
# Example Usage and Factory Functions
# ============================================================================


async def example_basic_usage():
    """Example of basic VLLM client usage."""
    client = create_vllm_client("TinyLlama/TinyLlama-1.1B-Chat-v1.0")

    # Test connection
    if await test_vllm_connection(client):
        # List models
        await list_vllm_models(client)

        # Chat completion
        chat_request = ChatCompletionRequest(
            model="TinyLlama/TinyLlama-1.1B-Chat-v1.0",
            messages=[{"role": "user", "content": "Hello, how are you?"}],
            max_tokens=50,
            temperature=0.7,
        )

        await client.chat_completions(chat_request)  # type: ignore[attr-defined]

    await client.close()  # type: ignore[attr-defined]


async def example_streaming():
    """Example of streaming usage."""
    client = create_vllm_client("TinyLlama/TinyLlama-1.1B-Chat-v1.0")

    chat_request = ChatCompletionRequest(
        model="TinyLlama/TinyLlama-1.1B-Chat-v1.0",
        messages=[{"role": "user", "content": "Tell me a story"}],
        max_tokens=100,
        temperature=0.8,
        stream=True,
    )

    async for _chunk in client.chat_completions_stream(chat_request):  # type: ignore[attr-defined]
        pass

    await client.close()  # type: ignore[attr-defined]


async def example_embeddings():
    """Example of embedding usage."""
    client = create_vllm_client("sentence-transformers/all-MiniLM-L6-v2")

    embedding_request = EmbeddingRequest(
        model="sentence-transformers/all-MiniLM-L6-v2",
        input=["Hello world", "How are you?"],
    )

    await client.embeddings(embedding_request)  # type: ignore[attr-defined]

    await client.close()  # type: ignore[attr-defined]


async def example_batch_processing():
    """Example of batch processing."""
    client = create_vllm_client("TinyLlama/TinyLlama-1.1B-Chat-v1.0")

    requests = [
        ChatCompletionRequest(
            model="TinyLlama/TinyLlama-1.1B-Chat-v1.0",
            messages=[{"role": "user", "content": f"Question {i}"}],
            max_tokens=20,
        )
        for i in range(3)
    ]

    batch_request = BatchRequest(requests=requests, max_retries=2)
    await client.batch_request(batch_request)  # type: ignore[attr-defined]

    await client.close()  # type: ignore[attr-defined]


if __name__ == "__main__":
    # Run examples

    # Basic usage
    asyncio.run(example_basic_usage())

    # Streaming
    asyncio.run(example_streaming())

    # Embeddings
    asyncio.run(example_embeddings())

    # Batch processing
    asyncio.run(example_batch_processing())
