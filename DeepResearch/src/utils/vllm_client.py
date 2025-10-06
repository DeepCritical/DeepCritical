"""
Comprehensive VLLM client with OpenAI API compatibility for Pydantic AI agents.

This module provides a complete VLLM client that can be used as a custom agent
in Pydantic AI, supporting all VLLM features while maintaining OpenAI API compatibility.
"""

from __future__ import annotations

import asyncio
import json
import time
from typing import Any, Dict, List, Optional, Union, AsyncGenerator
import aiohttp
from pydantic import BaseModel, Field
from ..datatypes.vllm_dataclass import (
    # Core configurations
    VllmConfig,
    ModelConfig,
    CacheConfig,
    ParallelConfig,
    SchedulerConfig,
    DeviceConfig,
    ObservabilityConfig,
    ChatCompletionRequest,
    ChatCompletionResponse,
    ChatCompletionChoice,
    ChatMessage,
    CompletionRequest,
    CompletionResponse,
    CompletionChoice,
    EmbeddingRequest,
    EmbeddingResponse,
    EmbeddingData,
    UsageStats,
    ModelInfo,
    ModelListResponse,
    HealthCheck,
    BatchRequest,
    BatchResponse,
    # Sampling parameters
    QuantizationMethod,
)
from ..datatypes.rag import VLLMConfig as RAGVLLMConfig


class VLLMClientError(Exception):
    """Base exception for VLLM client errors."""

    pass


class VLLMConnectionError(VLLMClientError):
    """Connection-related errors."""

    pass


class VLLMAPIError(VLLMClientError):
    """API-related errors."""

    pass


class VLLMClient(BaseModel):
    """Comprehensive VLLM client with OpenAI API compatibility."""

    base_url: str = Field("http://localhost:8000", description="VLLM server base URL")
    api_key: Optional[str] = Field(None, description="API key for authentication")
    timeout: float = Field(60.0, description="Request timeout in seconds")
    max_retries: int = Field(3, description="Maximum number of retries")
    retry_delay: float = Field(1.0, description="Delay between retries in seconds")

    # VLLM-specific configuration
    vllm_config: Optional[VllmConfig] = Field(None, description="VLLM configuration")

    class Config:
        arbitrary_types_allowed = True

    def __init__(self, **data):
        super().__init__(**data)
        self._session: Optional[aiohttp.ClientSession] = None

    async def __aenter__(self):
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()

    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create aiohttp session."""
        if self._session is None or self._session.closed:
            timeout = aiohttp.ClientTimeout(total=self.timeout)
            self._session = aiohttp.ClientSession(timeout=timeout)
        return self._session

    async def close(self):
        """Close the client session."""
        if self._session and not self._session.closed:
            await self._session.close()

    async def _make_request(
        self,
        method: str,
        endpoint: str,
        payload: Optional[Dict[str, Any]] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        """Make HTTP request to VLLM server with retry logic."""
        session = await self._get_session()
        url = f"{self.base_url}/v1/{endpoint}"

        headers = {"Content-Type": "application/json", **kwargs.get("headers", {})}

        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        for attempt in range(self.max_retries):
            try:
                async with session.request(
                    method, url, json=payload, headers=headers, **kwargs
                ) as response:
                    if response.status == 200:
                        return await response.json()
                    elif response.status == 429:  # Rate limited
                        if attempt < self.max_retries - 1:
                            await asyncio.sleep(self.retry_delay * (2**attempt))
                            continue
                    elif response.status >= 400:
                        error_data = (
                            await response.json() if response.content_length else {}
                        )
                        raise VLLMAPIError(
                            f"API Error {response.status}: {error_data.get('error', {}).get('message', 'Unknown error')}"
                        )

            except aiohttp.ClientError as e:
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(self.retry_delay * (2**attempt))
                    continue
                raise VLLMConnectionError(f"Connection error: {e}")

        raise VLLMConnectionError(f"Max retries ({self.max_retries}) exceeded")

    # ============================================================================
    # OpenAI-Compatible API Methods
    # ============================================================================

    async def chat_completions(
        self, request: ChatCompletionRequest
    ) -> ChatCompletionResponse:
        """Create chat completion (OpenAI-compatible)."""
        payload = request.model_dump(exclude_unset=True)

        response_data = await self._make_request("POST", "chat/completions", payload)

        # Convert to proper response format
        return ChatCompletionResponse(
            id=response_data["id"],
            object=response_data["object"],
            created=response_data["created"],
            model=response_data["model"],
            choices=[
                ChatCompletionChoice(
                    index=choice["index"],
                    message=ChatMessage(
                        role=choice["message"]["role"],
                        content=choice["message"]["content"],
                    ),
                    finish_reason=choice.get("finish_reason"),
                )
                for choice in response_data["choices"]
            ],
            usage=UsageStats(**response_data["usage"]),
        )

    async def completions(self, request: CompletionRequest) -> CompletionResponse:
        """Create completion (OpenAI-compatible)."""
        payload = request.model_dump(exclude_unset=True)

        response_data = await self._make_request("POST", "completions", payload)

        return CompletionResponse(
            id=response_data["id"],
            object=response_data["object"],
            created=response_data["created"],
            model=response_data["model"],
            choices=[
                CompletionChoice(
                    text=choice["text"],
                    index=choice["index"],
                    logprobs=choice.get("logprobs"),
                    finish_reason=choice.get("finish_reason"),
                )
                for choice in response_data["choices"]
            ],
            usage=UsageStats(**response_data["usage"]),
        )

    async def embeddings(self, request: EmbeddingRequest) -> EmbeddingResponse:
        """Create embeddings (OpenAI-compatible)."""
        payload = request.model_dump(exclude_unset=True)

        response_data = await self._make_request("POST", "embeddings", payload)

        return EmbeddingResponse(
            object=response_data["object"],
            data=[
                EmbeddingData(
                    object=item["object"],
                    embedding=item["embedding"],
                    index=item["index"],
                )
                for item in response_data["data"]
            ],
            model=response_data["model"],
            usage=UsageStats(**response_data["usage"]),
        )

    async def models(self) -> ModelListResponse:
        """List available models (OpenAI-compatible)."""
        response_data = await self._make_request("GET", "models")
        return ModelListResponse(**response_data)

    async def health(self) -> HealthCheck:
        """Get server health status."""
        response_data = await self._make_request("GET", "health")
        return HealthCheck(**response_data)

    # ============================================================================
    # VLLM-Specific API Methods
    # ============================================================================

    async def get_model_info(self, model_name: str) -> ModelInfo:
        """Get detailed information about a specific model."""
        response_data = await self._make_request("GET", f"models/{model_name}")
        return ModelInfo(**response_data)

    async def tokenize(self, text: str, model: str) -> Dict[str, Any]:
        """Tokenize text using the specified model."""
        payload = {"text": text, "model": model}
        return await self._make_request("POST", "tokenize", payload)

    async def detokenize(self, token_ids: List[int], model: str) -> Dict[str, Any]:
        """Detokenize token IDs using the specified model."""
        payload = {"tokens": token_ids, "model": model}
        return await self._make_request("POST", "detokenize", payload)

    async def get_metrics(self) -> Dict[str, Any]:
        """Get server metrics (VLLM-specific)."""
        return await self._make_request("GET", "metrics")

    async def batch_request(self, batch: BatchRequest) -> BatchResponse:
        """Process a batch of requests."""
        start_time = time.time()
        responses = []
        errors = []
        total_requests = len(batch.requests)
        successful_requests = 0

        for i, request in enumerate(batch.requests):
            try:
                if isinstance(request, ChatCompletionRequest):
                    response = await self.chat_completions(request)
                    responses.append(response)
                elif isinstance(request, CompletionRequest):
                    response = await self.completions(request)
                    responses.append(response)
                elif isinstance(request, EmbeddingRequest):
                    response = await self.embeddings(request)
                    responses.append(response)
                else:
                    errors.append(
                        {
                            "request_index": i,
                            "error": f"Unsupported request type: {type(request)}",
                        }
                    )
                    continue

                successful_requests += 1

            except Exception as e:
                errors.append({"request_index": i, "error": str(e)})

        processing_time = time.time() - start_time

        return BatchResponse(
            batch_id=batch.batch_id or f"batch_{int(time.time())}",
            responses=responses,
            errors=errors,
            total_requests=total_requests,
            successful_requests=successful_requests,
            failed_requests=len(errors),
            processing_time=processing_time,
        )

    # ============================================================================
    # Streaming Support
    # ============================================================================

    async def chat_completions_stream(
        self, request: ChatCompletionRequest
    ) -> AsyncGenerator[str, None]:
        """Stream chat completions."""
        payload = request.model_dump(exclude_unset=True)
        payload["stream"] = True

        session = await self._get_session()
        url = f"{self.base_url}/v1/chat/completions"

        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        async with session.post(url, json=payload, headers=headers) as response:
            response.raise_for_status()

            async for line in response.content:
                line = line.decode("utf-8").strip()
                if line.startswith("data: "):
                    data = line[6:]  # Remove 'data: ' prefix
                    if data == "[DONE]":
                        break
                    try:
                        chunk = json.loads(data)
                        if "choices" in chunk and len(chunk["choices"]) > 0:
                            delta = chunk["choices"][0].get("delta", {})
                            if "content" in delta:
                                yield delta["content"]
                    except json.JSONDecodeError:
                        continue

    async def completions_stream(
        self, request: CompletionRequest
    ) -> AsyncGenerator[str, None]:
        """Stream completions."""
        payload = request.model_dump(exclude_unset=True)
        payload["stream"] = True

        session = await self._get_session()
        url = f"{self.base_url}/v1/completions"

        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        async with session.post(url, json=payload, headers=headers) as response:
            response.raise_for_status()

            async for line in response.content:
                line = line.decode("utf-8").strip()
                if line.startswith("data: "):
                    data = line[6:]  # Remove 'data: ' prefix
                    if data == "[DONE]":
                        break
                    try:
                        chunk = json.loads(data)
                        if "choices" in chunk and len(chunk["choices"]) > 0:
                            if "text" in chunk["choices"][0]:
                                yield chunk["choices"][0]["text"]
                    except json.JSONDecodeError:
                        continue

    # ============================================================================
    # VLLM Configuration and Management
    # ============================================================================

    def with_config(self, config: VllmConfig) -> "VLLMClient":
        """Set VLLM configuration."""
        self.vllm_config = config
        return self

    def with_base_url(self, base_url: str) -> "VLLMClient":
        """Set base URL."""
        self.base_url = base_url
        return self

    def with_api_key(self, api_key: str) -> "VLLMClient":
        """Set API key."""
        self.api_key = api_key
        return self

    def with_timeout(self, timeout: float) -> "VLLMClient":
        """Set request timeout."""
        self.timeout = timeout
        return self

    @classmethod
    def from_config(
        cls, model_name: str, base_url: str = "http://localhost:8000", **kwargs
    ) -> "VLLMClient":
        """Create client from model configuration."""
        # Create basic VLLM config
        model_config = ModelConfig(model=model_name)
        cache_config = CacheConfig()
        parallel_config = ParallelConfig()
        scheduler_config = SchedulerConfig()
        device_config = DeviceConfig()
        observability_config = ObservabilityConfig()

        vllm_config = VllmConfig(
            model=model_config,
            cache=cache_config,
            parallel=parallel_config,
            scheduler=scheduler_config,
            device=device_config,
            observability=observability_config,
        )

        return cls(base_url=base_url, vllm_config=vllm_config, **kwargs)

    @classmethod
    def from_rag_config(cls, rag_config: RAGVLLMConfig) -> "VLLMClient":
        """Create client from RAG VLLM configuration."""
        return cls(
            base_url=f"http://{rag_config.host}:{rag_config.port}",
            api_key=rag_config.api_key,
            timeout=30.0,  # Default timeout
        )


class VLLMAgent:
    """Pydantic AI agent wrapper for VLLM client."""

    def __init__(self, vllm_client: VLLMClient):
        self.client = vllm_client

    async def chat(self, messages: List[Dict[str, str]], **kwargs) -> str:
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

    async def embed(self, texts: Union[str, List[str]], **kwargs) -> List[List[float]]:
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
        async def chat_completion(ctx, messages: List[Dict[str, str]], **kwargs) -> str:
            """Chat completion using VLLM."""
            return await ctx.deps.chat(messages, **kwargs)

        @agent.tool
        async def text_completion(ctx, prompt: str, **kwargs) -> str:
            """Text completion using VLLM."""
            return await ctx.deps.complete(prompt, **kwargs)

        @agent.tool
        async def generate_embeddings(
            ctx, texts: Union[str, List[str]], **kwargs
        ) -> List[List[float]]:
            """Generate embeddings using VLLM."""
            return await ctx.deps.embed(texts, **kwargs)

        return agent


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

    def with_base_url(self, base_url: str) -> "VLLMClientBuilder":
        """Set base URL."""
        self._config["base_url"] = base_url
        return self

    def with_api_key(self, api_key: str) -> "VLLMClientBuilder":
        """Set API key."""
        self._config["api_key"] = api_key
        return self

    def with_timeout(self, timeout: float) -> "VLLMClientBuilder":
        """Set timeout."""
        self._config["timeout"] = timeout
        return self

    def with_retries(
        self, max_retries: int, retry_delay: float = 1.0
    ) -> "VLLMClientBuilder":
        """Set retry configuration."""
        self._config["max_retries"] = max_retries
        self._config["retry_delay"] = retry_delay
        return self

    def with_vllm_config(self, config: VllmConfig) -> "VLLMClientBuilder":
        """Set VLLM configuration."""
        self._vllm_config = config
        return self

    def with_model_config(
        self,
        model: str,
        tokenizer: Optional[str] = None,
        trust_remote_code: bool = False,
        max_model_len: Optional[int] = None,
        quantization: Optional[QuantizationMethod] = None,
    ) -> "VLLMClientBuilder":
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
    ) -> "VLLMClientBuilder":
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
    ) -> "VLLMClientBuilder":
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
    api_key: Optional[str] = None,
    **kwargs,
) -> VLLMClient:
    """Create a VLLM client with sensible defaults."""
    return VLLMClient.from_config(
        model_name=model_name, base_url=base_url, api_key=api_key, **kwargs
    )


async def test_vllm_connection(client: VLLMClient) -> bool:
    """Test if VLLM server is accessible."""
    try:
        await client.health()
        return True
    except Exception:
        return False


async def list_vllm_models(client: VLLMClient) -> List[str]:
    """List available models on the VLLM server."""
    try:
        response = await client.models()
        return [model.id for model in response.data]
    except Exception:
        return []


# ============================================================================
# Example Usage and Factory Functions
# ============================================================================


async def example_basic_usage():
    """Example of basic VLLM client usage."""
    client = create_vllm_client("microsoft/DialoGPT-medium")

    # Test connection
    if await test_vllm_connection(client):
        print("VLLM server is accessible")

        # List models
        models = await list_vllm_models(client)
        print(f"Available models: {models}")

        # Chat completion
        chat_request = ChatCompletionRequest(
            model="microsoft/DialoGPT-medium",
            messages=[{"role": "user", "content": "Hello, how are you?"}],
            max_tokens=50,
            temperature=0.7,
        )

        response = await client.chat_completions(chat_request)
        print(f"Response: {response.choices[0].message.content}")

    await client.close()


async def example_streaming():
    """Example of streaming usage."""
    client = create_vllm_client("microsoft/DialoGPT-medium")

    chat_request = ChatCompletionRequest(
        model="microsoft/DialoGPT-medium",
        messages=[{"role": "user", "content": "Tell me a story"}],
        max_tokens=100,
        temperature=0.8,
        stream=True,
    )

    print("Streaming response: ", end="")
    async for chunk in client.chat_completions_stream(chat_request):
        print(chunk, end="", flush=True)
    print()

    await client.close()


async def example_embeddings():
    """Example of embedding usage."""
    client = create_vllm_client("sentence-transformers/all-MiniLM-L6-v2")

    embedding_request = EmbeddingRequest(
        model="sentence-transformers/all-MiniLM-L6-v2",
        input=["Hello world", "How are you?"],
    )

    response = await client.embeddings(embedding_request)
    print(f"Generated {len(response.data)} embeddings")
    print(f"First embedding dimension: {len(response.data[0].embedding)}")

    await client.close()


async def example_batch_processing():
    """Example of batch processing."""
    client = create_vllm_client("microsoft/DialoGPT-medium")

    requests = [
        ChatCompletionRequest(
            model="microsoft/DialoGPT-medium",
            messages=[{"role": "user", "content": f"Question {i}"}],
            max_tokens=20,
        )
        for i in range(3)
    ]

    batch_request = BatchRequest(requests=requests, max_retries=2)
    batch_response = await client.batch_request(batch_request)

    print(f"Processed {batch_response.total_requests} requests")
    print(f"Successful: {batch_response.successful_requests}")
    print(f"Failed: {batch_response.failed_requests}")
    print(f"Processing time: {batch_response.processing_time:.2f}s")

    await client.close()


if __name__ == "__main__":
    # Run examples
    print("Running VLLM client examples...")

    # Basic usage
    asyncio.run(example_basic_usage())

    # Streaming
    asyncio.run(example_streaming())

    # Embeddings
    asyncio.run(example_embeddings())

    # Batch processing
    asyncio.run(example_batch_processing())

    print("All examples completed!")
