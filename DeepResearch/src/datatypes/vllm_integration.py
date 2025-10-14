"""
VLLM integration for local model hosting in DeepCritical RAG workflows.

This module provides concrete implementations for VLLM-based embedding and LLM providers,
enabling local model hosting for RAG operations.
"""

from __future__ import annotations

import asyncio
import json
from typing import TYPE_CHECKING, Any

import aiohttp
from pydantic import BaseModel, ConfigDict, Field

from .rag import (
    EmbeddingModelType,
    Embeddings,
    EmbeddingsConfig,
    LLMModelType,
    LLMProvider,
    VLLMConfig,
)

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator


class VLLMEmbeddings(Embeddings):
    """VLLM-based embedding provider."""

    def __init__(self, config: EmbeddingsConfig):
        super().__init__(config)
        self.base_url = f"http://{config.base_url or 'localhost:8000'}"
        self.session: aiohttp.ClientSession | None = None

    async def __aenter__(self):
        """Async context manager entry."""
        self.session = aiohttp.ClientSession()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.session:
            await self.session.close()

    async def _make_request(
        self, endpoint: str, payload: dict[str, Any]
    ) -> dict[str, Any]:
        """Make HTTP request to VLLM server."""
        if not self.session:
            self.session = aiohttp.ClientSession()

        url = f"{self.base_url}/v1/{endpoint}"
        headers = {
            "Content-Type": "application/json",
            "Authorization": (
                f"Bearer {self.config.api_key}" if self.config.api_key else ""
            ),
        }

        async with self.session.post(url, json=payload, headers=headers) as response:
            response.raise_for_status()
            return await response.json()

    async def vectorize_documents(
        self, document_chunks: list[str]
    ) -> list[list[float]]:
        """Generate document embeddings for a list of chunks."""
        if not document_chunks:
            return []

        # Batch processing for efficiency
        embeddings = []
        batch_size = self.config.batch_size

        for i in range(0, len(document_chunks), batch_size):
            batch = document_chunks[i : i + batch_size]

            payload = {
                "input": batch,
                "model": self.config.model_name,
                "encoding_format": "float",
            }

            try:
                response = await self._make_request("embeddings", payload)
                batch_embeddings = [item["embedding"] for item in response["data"]]
                embeddings.extend(batch_embeddings)
            except Exception as e:
                msg = f"Failed to generate embeddings for batch {i // batch_size}: {e}"
                raise RuntimeError(msg)

        return embeddings

    async def vectorize_query(self, text: str) -> list[float]:
        """Generate embeddings for the query string."""
        embeddings = await self.vectorize_documents([text])
        return embeddings[0] if embeddings else []

    def vectorize_documents_sync(self, document_chunks: list[str]) -> list[list[float]]:
        """Synchronous version of vectorize_documents()."""
        return asyncio.run(self.vectorize_documents(document_chunks))

    def vectorize_query_sync(self, text: str) -> list[float]:
        """Synchronous version of vectorize_query()."""
        return asyncio.run(self.vectorize_query(text))


class VLLMLLMProvider(LLMProvider):
    """VLLM-based LLM provider."""

    def __init__(self, config: VLLMConfig):
        super().__init__(config)
        self.base_url = f"http://{config.host}:{config.port}"
        self.session: aiohttp.ClientSession | None = None

    async def __aenter__(self):
        """Async context manager entry."""
        self.session = aiohttp.ClientSession()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.session:
            await self.session.close()

    async def _make_request(
        self, endpoint: str, payload: dict[str, Any]
    ) -> dict[str, Any]:
        """Make HTTP request to VLLM server."""
        if not self.session:
            self.session = aiohttp.ClientSession()

        url = f"{self.base_url}/v1/{endpoint}"
        headers = {
            "Content-Type": "application/json",
            "Authorization": (
                f"Bearer {self.config.api_key}" if self.config.api_key else ""
            ),
        }

        async with self.session.post(url, json=payload, headers=headers) as response:
            response.raise_for_status()
            return await response.json()

    async def generate(
        self, prompt: str, context: str | None = None, **kwargs: Any
    ) -> str:
        """Generate text using the LLM."""
        full_prompt = prompt
        if context:
            full_prompt = f"Context: {context}\n\n{prompt}"

        payload = {
            "model": self.config.model_name,
            "messages": [{"role": "user", "content": full_prompt}],
            "max_tokens": kwargs.get("max_tokens", self.config.max_tokens),
            "temperature": kwargs.get("temperature", self.config.temperature),
            "top_p": kwargs.get("top_p", self.config.top_p),
            "frequency_penalty": kwargs.get(
                "frequency_penalty", self.config.frequency_penalty
            ),
            "presence_penalty": kwargs.get(
                "presence_penalty", self.config.presence_penalty
            ),
            "stop": kwargs.get("stop", self.config.stop),
            "stream": False,
        }

        try:
            response = await self._make_request("chat/completions", payload)
            return response["choices"][0]["message"]["content"]
        except Exception as e:
            msg = f"Failed to generate text: {e}"
            raise RuntimeError(msg)

    async def generate_stream(
        self, prompt: str, context: str | None = None, **kwargs: Any
    ) -> AsyncGenerator[str, None]:
        """Generate streaming text using the LLM."""
        full_prompt = prompt
        if context:
            full_prompt = f"Context: {context}\n\n{prompt}"

        payload = {
            "model": self.config.model_name,
            "messages": [{"role": "user", "content": full_prompt}],
            "max_tokens": kwargs.get("max_tokens", self.config.max_tokens),
            "temperature": kwargs.get("temperature", self.config.temperature),
            "top_p": kwargs.get("top_p", self.config.top_p),
            "frequency_penalty": kwargs.get(
                "frequency_penalty", self.config.frequency_penalty
            ),
            "presence_penalty": kwargs.get(
                "presence_penalty", self.config.presence_penalty
            ),
            "stop": kwargs.get("stop", self.config.stop),
            "stream": True,
        }

        if not self.session:
            self.session = aiohttp.ClientSession()

        url = f"{self.base_url}/v1/chat/completions"
        headers = {
            "Content-Type": "application/json",
            "Authorization": (
                f"Bearer {self.config.api_key}" if self.config.api_key else ""
            ),
        }

        try:
            async with self.session.post(
                url, json=payload, headers=headers
            ) as response:
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
        except Exception as e:
            msg = f"Failed to generate streaming text: {e}"
            raise RuntimeError(msg)


class VLLMServerConfig(BaseModel):
    """Configuration for VLLM server deployment."""

    model_name: str = Field(..., description="Model name or path")
    host: str = Field("0.0.0.0", description="Server host")
    port: int = Field(8000, description="Server port")
    gpu_memory_utilization: float = Field(0.9, description="GPU memory utilization")
    max_model_len: int = Field(4096, description="Maximum model length")
    dtype: str = Field("auto", description="Data type for model")
    trust_remote_code: bool = Field(False, description="Trust remote code")
    download_dir: str | None = Field(None, description="Download directory for models")
    load_format: str = Field("auto", description="Model loading format")
    tensor_parallel_size: int = Field(1, description="Tensor parallel size")
    pipeline_parallel_size: int = Field(1, description="Pipeline parallel size")
    max_num_seqs: int = Field(256, description="Maximum number of sequences")
    max_num_batched_tokens: int = Field(8192, description="Maximum batched tokens")
    max_paddings: int = Field(256, description="Maximum paddings")
    disable_log_stats: bool = Field(False, description="Disable log statistics")
    revision: str | None = Field(None, description="Model revision")
    code_revision: str | None = Field(None, description="Code revision")
    tokenizer: str | None = Field(None, description="Tokenizer name")
    tokenizer_mode: str = Field("auto", description="Tokenizer mode")
    skip_tokenizer_init: bool = Field(
        False, description="Skip tokenizer initialization"
    )
    enforce_eager: bool = Field(False, description="Enforce eager execution")
    max_seq_len_to_capture: int = Field(
        8192, description="Max sequence length to capture"
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "model_name": "TinyLlama/TinyLlama-1.1B-Chat-v1.0",
                "host": "0.0.0.0",
                "port": 8000,
                "gpu_memory_utilization": 0.9,
                "max_model_len": 4096,
            }
        }
    )


class VLLMEmbeddingServerConfig(BaseModel):
    """Configuration for VLLM embedding server deployment."""

    model_name: str = Field(..., description="Embedding model name or path")
    host: str = Field("0.0.0.0", description="Server host")
    port: int = Field(8001, description="Server port")
    gpu_memory_utilization: float = Field(0.9, description="GPU memory utilization")
    max_model_len: int = Field(512, description="Maximum model length for embeddings")
    dtype: str = Field("auto", description="Data type for model")
    trust_remote_code: bool = Field(False, description="Trust remote code")
    download_dir: str | None = Field(None, description="Download directory for models")
    load_format: str = Field("auto", description="Model loading format")
    tensor_parallel_size: int = Field(1, description="Tensor parallel size")
    pipeline_parallel_size: int = Field(1, description="Pipeline parallel size")
    max_num_seqs: int = Field(256, description="Maximum number of sequences")
    max_num_batched_tokens: int = Field(8192, description="Maximum batched tokens")
    max_paddings: int = Field(256, description="Maximum paddings")
    disable_log_stats: bool = Field(False, description="Disable log statistics")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "model_name": "sentence-transformers/all-MiniLM-L6-v2",
                "host": "0.0.0.0",
                "port": 8001,
                "gpu_memory_utilization": 0.9,
                "max_model_len": 512,
            }
        }
    )


class VLLMDeployment(BaseModel):
    """VLLM deployment configuration and management."""

    llm_config: VLLMServerConfig = Field(..., description="LLM server configuration")
    embedding_config: VLLMEmbeddingServerConfig | None = Field(
        None, description="Embedding server configuration"
    )
    auto_start: bool = Field(True, description="Automatically start servers")
    health_check_interval: int = Field(
        30, description="Health check interval in seconds"
    )
    max_retries: int = Field(3, description="Maximum retry attempts for health checks")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "llm_config": {
                    "model_name": "TinyLlama/TinyLlama-1.1B-Chat-v1.0",
                    "port": 8000,
                },
                "embedding_config": {
                    "model_name": "sentence-transformers/all-MiniLM-L6-v2",
                    "port": 8001,
                },
                "auto_start": True,
            }
        }
    )

    async def start_llm_server(self) -> bool:
        """Start the LLM server."""
        # This would typically use subprocess or docker to start VLLM server
        # For now, we'll assume the server is already running
        return await self._check_server_health(
            f"http://{self.llm_config.host}:{self.llm_config.port}/health"
        )

    async def start_embedding_server(self) -> bool:
        """Start the embedding server."""
        if not self.embedding_config:
            return True

        return await self._check_server_health(
            f"http://{self.embedding_config.host}:{self.embedding_config.port}/health"
        )

    async def _check_server_health(self, url: str) -> bool:
        """Check if a server is healthy."""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=5) as response:
                    return response.status == 200
        except Exception:
            return False

    async def wait_for_servers(self) -> bool:
        """Wait for all servers to be ready."""
        if self.auto_start:
            llm_ready = await self.start_llm_server()
            embedding_ready = (
                await self.start_embedding_server() if self.embedding_config else True
            )

            retries = 0
            while (not llm_ready or not embedding_ready) and retries < self.max_retries:
                await asyncio.sleep(self.health_check_interval)
                llm_ready = await self._check_server_health(
                    f"http://{self.llm_config.host}:{self.llm_config.port}/health"
                )
                embedding_ready = (
                    await self._check_server_health(
                        f"http://{self.embedding_config.host}:{self.embedding_config.port}/health"
                    )
                    if self.embedding_config
                    else True
                )
                retries += 1

            return llm_ready and embedding_ready

        return True


class VLLMRAGSystem(BaseModel):
    """VLLM-based RAG system implementation."""

    deployment: VLLMDeployment = Field(..., description="VLLM deployment configuration")
    embeddings: VLLMEmbeddings | None = Field(
        None, description="VLLM embeddings provider"
    )
    llm: VLLMLLMProvider | None = Field(None, description="VLLM LLM provider")

    async def initialize(self) -> None:
        """Initialize the VLLM RAG system."""
        # Wait for servers to be ready
        await self.deployment.wait_for_servers()

        # Initialize embeddings if embedding server is configured
        if self.deployment.embedding_config:
            embedding_config = EmbeddingsConfig(
                model_type=EmbeddingModelType.CUSTOM,
                model_name=self.deployment.embedding_config.model_name,
                base_url=f"http://{self.deployment.embedding_config.host}:{self.deployment.embedding_config.port}",  # type: ignore
                num_dimensions=384,  # Default for sentence-transformers models
            )
            self.embeddings = VLLMEmbeddings(embedding_config)

        # Initialize LLM provider
        llm_config = VLLMConfig(
            model_type=LLMModelType.CUSTOM,
            model_name=self.deployment.llm_config.model_name,
            host=self.deployment.llm_config.host,
            port=self.deployment.llm_config.port,
        )
        self.llm = VLLMLLMProvider(llm_config)

    model_config = ConfigDict(arbitrary_types_allowed=True)
