"""
VLLM-powered Pydantic AI agent for DeepCritical.

This module provides a complete VLLM agent implementation that can be used
with Pydantic AI's CLI and agent system.
"""

from __future__ import annotations

import asyncio
from typing import Any

from DeepResearch.src.datatypes.vllm_agent import VLLMAgentConfig, VLLMAgentDependencies
from DeepResearch.src.datatypes.vllm_dataclass import (
    ChatCompletionRequest,
    CompletionRequest,
    EmbeddingRequest,
    QuantizationMethod,
    VllmConfig,
)
from DeepResearch.src.utils.vllm_client import (
    VLLMAgent as VLLMClientWrapper,
)
from DeepResearch.src.utils.vllm_client import (
    VLLMClient,
)


def _generation_kwargs(
    kwargs: dict[str, Any],
    *,
    max_tokens: int,
    temperature: float,
    top_p: float,
) -> dict[str, Any]:
    """Merge configured generation defaults with caller overrides."""
    extra = dict(kwargs)
    return {
        "max_tokens": extra.pop("max_tokens", max_tokens),
        "temperature": extra.pop("temperature", temperature),
        "top_p": extra.pop("top_p", top_p),
        **extra,
    }


class VLLMAgent:
    """VLLM-powered agent for Pydantic AI."""

    def __init__(self, config: VLLMAgentConfig):
        self.config = config
        vllm_client_instance = VLLMClient(**config.client_config)
        self.client = VLLMClientWrapper(vllm_client_instance)
        self.dependencies = VLLMAgentDependencies(
            vllm_client=vllm_client_instance,  # Pass base client, not wrapper
            default_model=config.default_model,
            embedding_model=config.embedding_model,
        )

    async def initialize(self):
        """Initialize the VLLM agent."""
        # Test connection
        await self.client.health()

    async def close(self) -> None:
        """Release VLLM client resources."""
        await self.client.close()

    async def chat(
        self, messages: list[dict[str, str]], model: str | None = None, **kwargs
    ) -> str:
        """Chat with the VLLM model."""
        model = model or self.config.default_model

        request = ChatCompletionRequest(
            model=model,
            messages=messages,
            **_generation_kwargs(
                kwargs,
                max_tokens=self.config.max_tokens,
                temperature=self.config.temperature,
                top_p=self.config.top_p,
            ),
        )

        response = await self.client.chat_completions(request)
        return response.choices[0].message.content or ""

    async def complete(self, prompt: str, model: str | None = None, **kwargs) -> str:
        """Complete text with the VLLM model."""
        model = model or self.config.default_model

        request = CompletionRequest(
            model=model,
            prompt=prompt,
            **_generation_kwargs(
                kwargs,
                max_tokens=self.config.max_tokens,
                temperature=self.config.temperature,
                top_p=self.config.top_p,
            ),
        )

        response = await self.client.completions(request)
        return response.choices[0].text

    async def embed(
        self, texts: str | list[str], model: str | None = None, **kwargs
    ) -> list[list[float]]:
        """Generate embeddings for texts."""
        if isinstance(texts, str):
            texts = [texts]

        embedding_model = (
            model or self.config.embedding_model or self.config.default_model
        )

        request = EmbeddingRequest(model=embedding_model, input=texts, **kwargs)

        response = await self.client.embeddings(request)
        return [item.embedding for item in response.data]

    async def chat_stream(
        self, messages: list[dict[str, str]], model: str | None = None, **kwargs
    ) -> str:
        """Stream chat completion."""
        model = model or self.config.default_model

        extra = _generation_kwargs(
            kwargs,
            max_tokens=self.config.max_tokens,
            temperature=self.config.temperature,
            top_p=self.config.top_p,
        )
        extra["stream"] = True

        request = ChatCompletionRequest(
            model=model,
            messages=messages,
            **extra,
        )

        full_response = ""
        async for chunk in self.client.chat_completions_stream(request):
            # Extract content from chunk dict
            if isinstance(chunk, dict) and "choices" in chunk:
                delta_content = chunk["choices"][0].get("delta", {}).get("content", "")
                full_response += delta_content
        return full_response

    def to_pydantic_ai_agent(self):
        """Convert to Pydantic AI agent."""
        from pydantic_ai import Agent

        from DeepResearch.src.prompts.vllm_agent import VLLMAgentPrompts

        agent = Agent(
            "vllm-agent",
            deps_type=VLLMAgentDependencies,
            system_prompt=VLLMAgentPrompts.get_system_prompt(),
        )

        # Chat completion tool
        @agent.tool
        async def chat_completion(
            ctx, messages: list[dict[str, str]], model: str | None = None, **kwargs
        ) -> str:
            """Chat with the VLLM model."""
            response = await ctx.deps.vllm_client.chat_completions(
                ChatCompletionRequest(
                    model=model or ctx.deps.default_model,
                    messages=messages,
                    **kwargs,
                )
            )
            return response.choices[0].message.content or ""

        # Text completion tool
        @agent.tool
        async def text_completion(
            ctx, prompt: str, model: str | None = None, **kwargs
        ) -> str:
            """Complete text with the VLLM model."""
            response = await ctx.deps.vllm_client.completions(
                CompletionRequest(
                    model=model or ctx.deps.default_model,
                    prompt=prompt,
                    **kwargs,
                )
            )
            return response.choices[0].text

        # Embedding generation tool
        @agent.tool
        async def generate_embeddings(
            ctx, texts: str | list[str], model: str | None = None, **kwargs
        ) -> list[list[float]]:
            """Generate embeddings using VLLM."""
            if isinstance(texts, str):
                texts = [texts]

            embedding_model = (
                model or ctx.deps.embedding_model or ctx.deps.default_model
            )

            response = await ctx.deps.vllm_client.embeddings(
                EmbeddingRequest(model=embedding_model, input=texts, **kwargs)
            )
            return [item.embedding for item in response.data]

        # Model information tool
        @agent.tool
        async def get_model_info(ctx, model_name: str) -> dict[str, Any]:
            """Get information about a specific model."""
            client = VLLMClientWrapper(ctx.deps.vllm_client)
            response = await client.models()
            for item in response.get("data", []):
                if item.get("id") == model_name:
                    return dict(item)
            msg = f"Model not found: {model_name}"
            raise ValueError(msg)

        # List models tool
        @agent.tool
        async def list_models(ctx) -> list[str]:
            """List available models."""
            response = await VLLMClientWrapper(ctx.deps.vllm_client).models()
            return [item["id"] for item in response.get("data", []) if "id" in item]

        # Tokenization tools
        @agent.tool
        async def tokenize(ctx, text: str, model: str | None = None) -> dict[str, Any]:
            """Tokenize text."""
            selected_model = model or ctx.deps.default_model
            client = VLLMClientWrapper(ctx.deps.vllm_client)
            if client._use_http():
                return await client._http_request(
                    "POST",
                    "/tokenize",
                    {"model": selected_model, "prompt": text},
                )
            tokens = text.split()
            return {
                "model": selected_model,
                "tokens": list(range(len(tokens))),
                "token_texts": tokens,
            }

        @agent.tool
        async def detokenize(
            ctx, token_ids: list[int], model: str | None = None
        ) -> dict[str, Any]:
            """Detokenize token IDs."""
            selected_model = model or ctx.deps.default_model
            client = VLLMClientWrapper(ctx.deps.vllm_client)
            if client._use_http():
                return await client._http_request(
                    "POST",
                    "/detokenize",
                    {"model": selected_model, "tokens": token_ids},
                )
            return {
                "model": selected_model,
                "tokens": token_ids,
                "text": " ".join(str(token_id) for token_id in token_ids),
            }

        # Health check tool
        @agent.tool
        async def health_check(ctx) -> dict[str, Any]:
            """Check server health."""
            return await VLLMClientWrapper(ctx.deps.vllm_client).health()

        return agent


def create_vllm_agent(
    model_name: str = "TinyLlama/TinyLlama-1.1B-Chat-v1.0",
    base_url: str = "http://localhost:8000",
    api_key: str | None = None,
    embedding_model: str | None = None,
    **kwargs,
) -> VLLMAgent:
    """Create a VLLM agent with default configuration."""

    config = VLLMAgentConfig(
        client_config={"base_url": base_url, "api_key": api_key, **kwargs},
        default_model=model_name,
        embedding_model=embedding_model,
    )

    return VLLMAgent(config)


def create_advanced_vllm_agent(
    model_name: str = "TinyLlama/TinyLlama-1.1B-Chat-v1.0",
    base_url: str = "http://localhost:8000",
    quantization: QuantizationMethod | None = None,
    tensor_parallel_size: int = 1,
    gpu_memory_utilization: float = 0.9,
    **kwargs,
) -> VLLMAgent:
    """Create a VLLM agent with advanced configuration."""

    # Create VLLM configuration
    from DeepResearch.src.datatypes.vllm_dataclass import (
        CacheConfig,
        DeviceConfig,
        LoadConfig,
        ModelConfig,
        ObservabilityConfig,
        ParallelConfig,
        SchedulerConfig,
    )

    model_config = ModelConfig(
        model=model_name,
        quantization=quantization,
    )

    parallel_config = ParallelConfig(
        tensor_parallel_size=tensor_parallel_size,
    )

    cache_config = CacheConfig(
        gpu_memory_utilization=gpu_memory_utilization,
    )

    vllm_config = VllmConfig(
        model=model_config,
        cache=cache_config,
        load=LoadConfig(),
        parallel=parallel_config,
        scheduler=SchedulerConfig(),
        device=DeviceConfig(),
        observability=ObservabilityConfig(),
    )

    config = VLLMAgentConfig(
        client_config={"base_url": base_url, "vllm_config": vllm_config, **kwargs},
        default_model=model_name,
    )

    return VLLMAgent(config)


# ============================================================================
# Example Usage
# ============================================================================


async def example_vllm_agent():  # pragma: no cover
    """Example usage of VLLM agent."""

    # Create agent
    agent = create_vllm_agent(
        model_name="TinyLlama/TinyLlama-1.1B-Chat-v1.0",
        base_url="http://localhost:8000",
        temperature=0.8,
        max_tokens=100,
    )

    await agent.initialize()

    # Test chat
    messages = [{"role": "user", "content": "Hello! How are you today?"}]
    await agent.chat(messages)

    # Test completion
    prompt = "The future of AI is"
    await agent.complete(prompt)

    # Test embeddings (if embedding model is available)
    if agent.config.embedding_model:
        texts = ["Hello world", "AI is amazing"]
        await agent.embed(texts)


async def example_pydantic_ai_integration():  # pragma: no cover
    """Example of using VLLM agent with Pydantic AI."""

    # Create agent
    agent = create_vllm_agent(
        model_name="TinyLlama/TinyLlama-1.1B-Chat-v1.0",
        base_url="http://localhost:8000",
    )

    await agent.initialize()

    # Convert to Pydantic AI agent
    pydantic_agent = agent.to_pydantic_ai_agent()

    # Test with dependencies
    await pydantic_agent.run(
        "Tell me about artificial intelligence", deps=agent.dependencies
    )


if __name__ == "__main__":  # pragma: no cover
    # Run basic example
    asyncio.run(example_vllm_agent())

    # Run Pydantic AI integration example
    asyncio.run(example_pydantic_ai_integration())
