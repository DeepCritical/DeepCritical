"""Optional real-container smoke tests for the VLLM agent wrapper."""

from __future__ import annotations

import asyncio
import time

import pytest

from DeepResearch.src.agents.vllm_agent import create_vllm_agent


@pytest.mark.vllm
@pytest.mark.containerized
@pytest.mark.optional
def test_vllm_agent_talks_to_real_vllm_container() -> None:
    requests = pytest.importorskip("requests")

    try:
        from tests.utils.testcontainers.container_managers import VLLMContainer
    except Exception as exc:  # pragma: no cover - environment dependent
        pytest.skip(f"VLLM container helper is unavailable: {exc}")

    model_name = "TinyLlama/TinyLlama-1.1B-Chat-v1.0"
    container = VLLMContainer(model=model_name, ports={"8000": "8000"})

    try:
        try:
            container.start()
        except Exception as exc:  # pragma: no cover - environment dependent
            pytest.skip(f"Docker/VLLM container startup unavailable: {exc}")

        base_url = container.get_connection_url()
        deadline = time.time() + 180
        while time.time() < deadline:
            try:
                response = requests.get(f"{base_url}/health", timeout=5)
                if response.status_code == 200:
                    break
            except Exception:
                time.sleep(5)
        else:  # pragma: no cover - environment dependent
            pytest.skip("VLLM container did not become healthy in time")

        agent = create_vllm_agent(
            model_name=model_name,
            base_url=base_url,
            transport_mode="http",
            timeout=30,
            max_retries=0,
        )

        async def _exercise_agent() -> None:
            await agent.initialize()
            text = await agent.chat(
                [{"role": "user", "content": "Reply with a short greeting."}],
                max_tokens=16,
                temperature=0.0,
            )
            await agent.close()
            assert isinstance(text, str)
            assert text.strip()

        asyncio.run(_exercise_agent())
    finally:
        try:
            container.stop()
        except Exception:
            pass
