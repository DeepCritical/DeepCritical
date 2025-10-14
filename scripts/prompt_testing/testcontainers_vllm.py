"""
VLLM Testcontainers integration for DeepCritical prompt testing.

This module provides VLLM container management and reasoning parsing
for testing prompts with actual LLM inference, fully configurable through Hydra.
"""

import json
import logging
import re
import time
from pathlib import Path
from typing import Any, TypedDict

from omegaconf import DictConfig


class ReasoningData(TypedDict):
    """Type definition for reasoning data extracted from LLM responses."""

    has_reasoning: bool
    reasoning_steps: list[str]
    tool_calls: list[dict[str, Any]]
    final_answer: str
    reasoning_format: str


# Try to import VLLM container, but handle gracefully if not available
try:
    from testcontainers.core.container import DockerContainer

    class VLLMContainer(DockerContainer):
        """Custom VLLM container implementation using testcontainers core."""

        def __init__(
            self,
            image: str = "vllm/vllm-openai:latest",
            model: str = "TinyLlama/TinyLlama-1.1B-Chat-v1.0",
            host_port: int = 8000,
            container_port: int = 8000,
            **kwargs,
        ):
            super().__init__(image, **kwargs)
            self.model = model
            self.host_port = host_port
            self.container_port = container_port

            # Configure container
            self.with_exposed_ports(self.container_port)
            self.with_env("VLLM_MODEL", model)
            self.with_env("VLLM_HOST", "0.0.0.0")
            self.with_env("VLLM_PORT", str(container_port))

        def get_connection_url(self) -> str:
            """Get the connection URL for the VLLM server."""
            try:
                host = self.get_container_host_ip()
                port = self.get_exposed_port(self.container_port)
                return f"http://{host}:{port}"
            except Exception:
                # Return a mock URL if container is not actually running
                return f"http://localhost:{self.container_port}"

    VLLM_AVAILABLE = True

except ImportError:
    VLLM_AVAILABLE = False

    # Create a mock VLLMContainer for when testcontainers is not available
    class VLLMContainer:
        def __init__(self, *args, **kwargs):
            msg = "testcontainers is not available. Please install it with: pip install testcontainers"
            raise ImportError(msg)


# Set up logging for test artifacts
log_dir = Path("test_artifacts")
log_dir.mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(log_dir / "vllm_prompt_tests.log"),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger(__name__)


class VLLMPromptTester:
    """VLLM-based prompt tester with reasoning parsing, configurable through Hydra."""

    def __init__(
        self,
        config: DictConfig | None = None,
        model_name: str | None = None,
        container_timeout: int | None = None,
        max_tokens: int | None = None,
        temperature: float | None = None,
    ):
        """Initialize VLLM prompt tester with Hydra configuration.

        Args:
            config: Hydra configuration object containing VLLM test settings
            model_name: Override model name from config
            container_timeout: Override container timeout from config
            max_tokens: Override max tokens from config
            temperature: Override temperature from config
        """
        # Check if VLLM is available
        if not VLLM_AVAILABLE:
            logger.warning("testcontainers not available, using mock mode for testing")

        # Use provided config or create default
        if config is None:
            from pathlib import Path

            from hydra import compose, initialize_config_dir

            config_dir = Path("configs")
            if config_dir.exists():
                try:
                    with initialize_config_dir(
                        config_dir=str(config_dir), version_base=None
                    ):
                        config = compose(
                            config_name="vllm_tests",
                            overrides=[
                                "model=local_model",
                                "performance=balanced",
                                "testing=comprehensive",
                                "output=structured",
                            ],
                        )
                except Exception as e:
                    logger.warning("Could not load Hydra config, using defaults: %s", e)
                    config = self._create_default_config()

        self.config = config
        self.vllm_available = VLLM_AVAILABLE

        # Also check if Docker is actually available for runtime
        self.docker_available = self._check_docker_availability()

        # Extract configuration values with overrides
        vllm_config = config.get("vllm_tests", {}) if config else {}
        model_config = config.get("model", {}) if config else {}
        performance_config = config.get("performance", {}) if config else {}

        # Apply configuration with overrides
        self.model_name = model_name or model_config.get(
            "name", "TinyLlama/TinyLlama-1.1B-Chat-v1.0"
        )
        self.container_timeout = container_timeout or performance_config.get(
            "max_container_startup_time", 120
        )
        self.max_tokens = max_tokens or model_config.get("generation", {}).get(
            "max_tokens", 256
        )
        self.temperature = temperature or model_config.get("generation", {}).get(
            "temperature", 0.7
        )

        # Container and artifact settings
        self.container: VLLMContainer | None = None
        artifacts_config = vllm_config.get("artifacts", {})
        self.artifacts_dir = Path(
            artifacts_config.get("base_directory", "test_artifacts/vllm_tests")
        )
        self.artifacts_dir.mkdir(parents=True, exist_ok=True)

        # Performance monitoring
        monitoring_config = vllm_config.get("monitoring", {})
        self.enable_monitoring = monitoring_config.get("enabled", True)
        self.max_execution_time_per_module = monitoring_config.get(
            "max_execution_time_per_module", 300
        )

        # Error handling
        error_config = vllm_config.get("error_handling", {})
        self.graceful_degradation = error_config.get("graceful_degradation", True)
        self.continue_on_module_failure = error_config.get(
            "continue_on_module_failure", True
        )
        self.retry_failed_prompts = error_config.get("retry_failed_prompts", True)
        self.max_retries_per_prompt = error_config.get("max_retries_per_prompt", 2)

        logger.info(
            "VLLMPromptTester initialized with model: %s, VLLM available: %s, Docker available: %s",
            self.model_name,
            self.vllm_available,
            self.docker_available,
        )

    def _check_docker_availability(self) -> bool:
        """Check if Docker is available and running."""
        try:
            import docker

            client = docker.from_env()
            # Try to ping the Docker daemon
            client.ping()
            return True
        except Exception:
            return False

    def _create_default_config(self) -> DictConfig:
        """Create default configuration when Hydra config is not available."""
        from omegaconf import OmegaConf

        default_config = {
            "vllm_tests": {
                "enabled": True,
                "run_in_ci": False,
                "execution_strategy": "sequential",
                "max_concurrent_tests": 1,
                "artifacts": {
                    "enabled": True,
                    "base_directory": "test_artifacts/vllm_tests",
                    "save_individual_results": True,
                    "save_module_summaries": True,
                    "save_global_summary": True,
                },
                "monitoring": {
                    "enabled": True,
                    "track_execution_times": True,
                    "track_memory_usage": True,
                    "max_execution_time_per_module": 300,
                },
                "error_handling": {
                    "graceful_degradation": True,
                    "continue_on_module_failure": True,
                    "retry_failed_prompts": True,
                    "max_retries_per_prompt": 2,
                },
            },
            "model": {
                "name": "TinyLlama/TinyLlama-1.1B-Chat-v1.0",
                "generation": {
                    "max_tokens": 256,
                    "temperature": 0.7,
                },
            },
            "performance": {
                "max_container_startup_time": 120,
            },
        }

        return OmegaConf.create(default_config)

    def __enter__(self):
        """Context manager entry."""
        self.start_container()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.stop_container()

    def start_container(self):
        """Start VLLM container with configuration-based settings."""
        if not self.vllm_available or not self.docker_available:
            if not self.vllm_available:
                logger.info("testcontainers not available, using mock mode")
            else:
                logger.info("Docker not available, using mock mode")
            return

        logger.info("Starting VLLM container with model: %s", self.model_name)

        # Get container configuration from config
        model_config = self.config.get("model", {})
        container_config = model_config.get("container", {})
        server_config = model_config.get("server", {})
        generation_config = model_config.get("generation", {})

        # Create VLLM container with configuration
        self.container = VLLMContainer(
            image=container_config.get("image", "vllm/vllm-openai:latest"),
            model=self.model_name,
            host_port=server_config.get("port", 8000),
            container_port=server_config.get("port", 8000),
            environment={
                "VLLM_MODEL": self.model_name,
                "VLLM_HOST": server_config.get("host", "0.0.0.0"),
                "VLLM_PORT": str(server_config.get("port", 8000)),
                "VLLM_MAX_TOKENS": str(
                    generation_config.get("max_tokens", self.max_tokens)
                ),
                "VLLM_TEMPERATURE": str(
                    generation_config.get("temperature", self.temperature)
                ),
                # Additional environment variables from config
                **container_config.get("environment", {}),
            },
        )

        # Set resource limits if configured
        resources = container_config.get("resources", {})
        if resources.get("cpu_limit"):
            self.container.with_cpu_limit(resources["cpu_limit"])
        if resources.get("memory_limit"):
            self.container.with_memory_limit(resources["memory_limit"])

        # Start the container
        logger.info("Starting container with timeout: %ds", self.container_timeout)
        self.container.start()

        # Wait for container to be ready with configured timeout
        self._wait_for_ready(self.container_timeout)

        logger.info("VLLM container started at %s", self.container.get_connection_url())

    def stop_container(self):
        """Stop VLLM container."""
        if self.container:
            logger.info("Stopping VLLM container")
            self.container.stop()
            self.container = None

    def _wait_for_ready(self, timeout: int | None = None):
        """Wait for VLLM container to be ready."""
        import requests

        # Use configured timeout or default
        health_check_config = (
            self.config.get("model", {}).get("server", {}).get("health_check", {})
        )
        check_timeout = timeout or health_check_config.get("timeout_seconds", 5)
        max_retries = health_check_config.get("max_retries", 3)
        interval = health_check_config.get("interval_seconds", 10)

        start_time = time.time()
        url = f"{self.container.get_connection_url()}{health_check_config.get('endpoint', '/health')}"

        retry_count = 0
        timeout_seconds = timeout or 300  # Default 5 minutes
        while time.time() - start_time < timeout_seconds and retry_count < max_retries:
            try:
                response = requests.get(url, timeout=check_timeout)
                if response.status_code == 200:
                    logger.info("VLLM container is ready")
                    return
            except Exception as e:
                logger.debug("Health check failed (attempt %d): %s", retry_count + 1, e)
                retry_count += 1
                if retry_count < max_retries:
                    time.sleep(interval)

        total_time = time.time() - start_time
        msg = f"VLLM container not ready after {total_time:.1f} seconds (timeout: {timeout}s)"
        raise TimeoutError(msg)

    def _validate_prompt_structure(self, prompt: str, prompt_name: str):
        """Validate that a prompt has proper structure using configuration."""
        # Check for basic prompt structure
        if not isinstance(prompt, str):
            msg = f"Prompt {prompt_name} is not a string"
            raise ValueError(msg)

        if not prompt.strip():
            msg = f"Prompt {prompt_name} is empty"
            raise ValueError(msg)

        # Check for common prompt patterns if validation is strict
        validation_config = self.config.get("testing", {}).get("validation", {})
        if validation_config.get("validate_prompt_structure", True):
            # Check for instructions or role definition
            has_instructions = any(
                pattern in prompt.lower()
                for pattern in [
                    "you are",
                    "your role",
                    "please",
                    "instructions:",
                    "task:",
                ]
            )

            # Most prompts should have some form of instructions
            if not has_instructions and len(prompt) > 50:
                logger.warning(
                    "Prompt %s might be missing clear instructions", prompt_name
                )

    def _validate_response_structure(self, response: str, prompt_name: str):
        """Validate that a response has proper structure using configuration."""
        # Check for basic response structure
        if not isinstance(response, str):
            msg = f"Response for prompt {prompt_name} is not a string"
            raise ValueError(msg)

        validation_config = self.config.get("testing", {}).get("validation", {})
        assertions_config = self.config.get("testing", {}).get("assertions", {})

        # Check minimum response length
        min_length = assertions_config.get("min_response_length", 10)
        if len(response.strip()) < min_length:
            logger.warning(
                "Response for prompt %s is shorter than expected: %d chars",
                prompt_name,
                len(response),
            )

        # Check for empty response
        if not response.strip():
            msg = f"Empty response for prompt {prompt_name}"
            raise ValueError(msg)

        # Check for response quality indicators
        if validation_config.get("validate_response_content", True):
            # Check for coherent response (basic heuristic)
            if len(response.split()) < 3 and len(response) > 20:
                logger.warning(
                    "Response for prompt %s might be too short or fragmented",
                    prompt_name,
                )

    def test_prompt(
        self,
        prompt: str,
        prompt_name: str,
        dummy_data: dict[str, Any],
        **generation_kwargs,
    ) -> dict[str, Any]:
        """Test a prompt with VLLM and parse reasoning using configuration.

        Args:
            prompt: The prompt template to test
            prompt_name: Name of the prompt for logging
            dummy_data: Dummy data to substitute in prompt
            **generation_kwargs: Additional generation parameters

        Returns:
            Dictionary containing test results and parsed reasoning
        """
        start_time = time.time()

        # Format prompt with dummy data
        try:
            formatted_prompt = prompt.format(**dummy_data)
        except KeyError as e:
            logger.warning("Missing placeholder in prompt %s: %s", prompt_name, e)
            # Use the prompt as-is if formatting fails
            formatted_prompt = prompt

        logger.info("Testing prompt: %s", prompt_name)

        # Get generation configuration
        generation_config = self.config.get("model", {}).get("generation", {})
        test_config = self.config.get("testing", {})
        validation_config = test_config.get("validation", {})

        # Validate prompt if enabled
        if validation_config.get("validate_prompt_structure", True):
            self._validate_prompt_structure(prompt, prompt_name)

        # Merge configuration with provided kwargs
        final_generation_kwargs = {
            "max_tokens": generation_kwargs.get("max_tokens", self.max_tokens),
            "temperature": generation_kwargs.get("temperature", self.temperature),
            "top_p": generation_config.get("top_p", 0.9),
            "frequency_penalty": generation_config.get("frequency_penalty", 0.0),
            "presence_penalty": generation_config.get("presence_penalty", 0.0),
        }

        # Generate response using VLLM with retry logic
        response = None
        for attempt in range(self.max_retries_per_prompt + 1):
            try:
                response = self._generate_response(
                    formatted_prompt, **final_generation_kwargs
                )
                break  # Success, exit retry loop

            except Exception as e:
                if attempt < self.max_retries_per_prompt and self.retry_failed_prompts:
                    logger.warning(
                        "Attempt %d failed for prompt %s: %s",
                        attempt + 1,
                        prompt_name,
                        e,
                    )
                    if self.graceful_degradation:
                        time.sleep(1)  # Brief delay before retry
                        continue
                else:
                    logger.exception("All retries failed for prompt %s", prompt_name)
                    raise

        if response is None:
            msg = f"Failed to generate response for prompt {prompt_name}"
            raise RuntimeError(msg)

        # Parse reasoning from response
        reasoning_data = self._parse_reasoning(response)

        # Validate response if enabled
        if validation_config.get("validate_response_structure", True):
            self._validate_response_structure(response, prompt_name)

        # Calculate execution time
        execution_time = time.time() - start_time

        # Create test result with full configuration context
        result = {
            "prompt_name": prompt_name,
            "original_prompt": prompt,
            "formatted_prompt": formatted_prompt,
            "dummy_data": dummy_data,
            "generated_response": response,
            "reasoning": reasoning_data,
            "success": True,
            "timestamp": time.time(),
            "execution_time": execution_time,
            "model_used": self.model_name,
            "generation_config": final_generation_kwargs,
            # Configuration metadata
            "config_source": (
                "hydra" if hasattr(self.config, "_metadata") else "default"
            ),
            "test_config_version": getattr(self.config, "_metadata", {}).get(
                "version", "unknown"
            ),
        }

        # Save artifact if enabled
        artifacts_config = self.config.get("vllm_tests", {}).get("artifacts", {})
        if artifacts_config.get("save_individual_results", True):
            self._save_artifact(result)

        return result

    def _generate_response(self, prompt: str, **kwargs) -> str:
        """Generate response using VLLM or mock response when not available."""
        import requests

        if not self.vllm_available:
            # Return mock response when VLLM is not available
            logger.info("VLLM not available, returning mock response")
            return self._generate_mock_response(prompt)

        if not self.container:
            msg = "VLLM container not started"
            raise RuntimeError(msg)

        # Default generation parameters
        gen_params = {
            "model": self.model_name,
            "prompt": prompt,
            "max_tokens": kwargs.get("max_tokens", self.max_tokens),
            "temperature": kwargs.get("temperature", self.temperature),
            "top_p": kwargs.get("top_p", 0.9),
            "frequency_penalty": kwargs.get("frequency_penalty", 0.0),
            "presence_penalty": kwargs.get("presence_penalty", 0.0),
        }

        url = f"{self.container.get_connection_url()}/v1/completions"

        response = requests.post(
            url,
            json=gen_params,
            headers={"Content-Type": "application/json"},
            timeout=60,
        )

        response.raise_for_status()

        result = response.json()
        return result["choices"][0]["text"].strip()

    def _generate_mock_response(self, prompt: str) -> str:
        """Generate a mock response for testing when VLLM is not available."""
        import random

        # Simple mock responses based on prompt content
        prompt_lower = prompt.lower()

        if "hello" in prompt_lower or "hi" in prompt_lower:
            return "Hello! I'm a mock AI assistant. How can I help you today?"
        if "what is" in prompt_lower:
            return "Based on the mock analysis, this appears to be a question about something. The mock system suggests that the answer involves understanding the fundamental concepts and applying them in practice."
        if "how" in prompt_lower:
            return "This is a mock response to a 'how' question. The mock system suggests following these steps: 1) Understand the problem, 2) Gather information, 3) Apply the solution, 4) Verify the results."
        if "why" in prompt_lower:
            return "This is a mock response to a 'why' question. The mock reasoning suggests that this happens because of underlying principles and mechanisms that can be explained through careful analysis."
        # Generic mock response
        responses = [
            "This is a mock response generated for testing purposes. The system is working correctly but using simulated data.",
            "Mock AI response: I understand your query and I'm processing it with mock data. The result suggests a comprehensive approach is needed.",
            "Testing mode: This response is generated as a placeholder. In a real scenario, this would contain actual AI-generated content based on the prompt.",
            "Mock analysis complete. The system has processed your request and generated this placeholder response for testing validation.",
        ]
        return random.choice(responses)

    def _parse_reasoning(self, response: str) -> ReasoningData:
        """Parse reasoning and tool calls from response.

        This implements basic reasoning parsing based on VLLM reasoning outputs.
        """
        reasoning_data: ReasoningData = {
            "has_reasoning": False,
            "reasoning_steps": [],
            "tool_calls": [],
            "final_answer": response,
            "reasoning_format": "unknown",
        }

        # Look for reasoning markers (common patterns)
        reasoning_patterns = [
            # OpenAI-style reasoning
            r"<thinking>(.*?)</thinking>",
            # Anthropic-style reasoning
            r"<reasoning>(.*?)</reasoning>",
            # Generic thinking patterns
            r"(?:^|\n)(?:Step \d+:|First,|Next,|Then,|Because|Therefore|However|Moreover)(.*?)(?:\n|$)",
        ]

        for pattern in reasoning_patterns:
            matches = re.findall(pattern, response, re.DOTALL | re.IGNORECASE)
            if matches:
                reasoning_data["has_reasoning"] = True
                reasoning_data["reasoning_steps"] = [match.strip() for match in matches]
                reasoning_data["reasoning_format"] = "structured"
                break

        # Look for tool calls (common patterns)
        tool_call_patterns = [
            r"Tool:\s*(\w+)\s*\((.*?)\)",
            r"Function:\s*(\w+)\s*\((.*?)\)",
            r"Call:\s*(\w+)\s*\((.*?)\)",
        ]

        for pattern in tool_call_patterns:
            matches = re.findall(pattern, response, re.IGNORECASE)
            if matches:
                for tool_name, params in matches:
                    reasoning_data["tool_calls"].append(
                        {
                            "tool_name": tool_name.strip(),
                            "parameters": params.strip(),
                            "confidence": 0.8,  # Default confidence
                        }
                    )

        if reasoning_data["tool_calls"]:
            reasoning_data["reasoning_format"] = "tool_calls"

        # Extract final answer (remove reasoning parts)
        if reasoning_data["has_reasoning"]:
            # Remove reasoning sections from final answer
            final_answer = response
            for step in reasoning_data["reasoning_steps"]:  # type: ignore
                final_answer = final_answer.replace(step, "").strip()

            # Clean up extra whitespace
            final_answer = re.sub(r"\n\s*\n\s*\n", "\n\n", final_answer)
            reasoning_data["final_answer"] = final_answer.strip()

        return reasoning_data

    def _save_artifact(self, result: dict[str, Any]):
        """Save test result as artifact."""
        timestamp = int(result.get("timestamp", time.time()))
        filename = f"{result['prompt_name']}_{timestamp}.json"

        artifact_path = self.artifacts_dir / filename

        with open(artifact_path, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2, ensure_ascii=False)

        logger.info("Saved artifact: %s", artifact_path)

    def batch_test_prompts(
        self, prompts: list[tuple[str, str, dict[str, Any]]], **generation_kwargs
    ) -> list[dict[str, Any]]:
        """Test multiple prompts in batch.

        Args:
            prompts: List of (prompt_name, prompt_template, dummy_data) tuples
            **generation_kwargs: Additional generation parameters

        Returns:
            List of test results
        """
        results = []

        for prompt_name, prompt_template, dummy_data in prompts:
            result = self.test_prompt(
                prompt_template, prompt_name, dummy_data, **generation_kwargs
            )
            results.append(result)

        return results

    def get_container_info(self) -> dict[str, Any]:
        """Get information about the VLLM container."""
        if not self.vllm_available or not self.docker_available:
            reason = (
                "testcontainers not available"
                if not self.vllm_available
                else "Docker not available"
            )
            return {
                "status": "mock_mode",
                "model": self.model_name,
                "note": f"{reason}, using mock responses",
            }

        if not self.container:
            return {"status": "not_started"}

        return {
            "status": "running",
            "model": self.model_name,
            "connection_url": self.container.get_connection_url(),
            "container_id": getattr(self.container, "_container", {}).get(
                "Id", "unknown"
            )[:12],
        }


def create_dummy_data_for_prompt(
    prompt: str, config: DictConfig | None = None
) -> dict[str, Any]:
    """Create dummy data for a prompt based on its placeholders, configurable through Hydra.

    Args:
        prompt: The prompt template string
        config: Hydra configuration for customizing dummy data

    Returns:
        Dictionary of dummy data for the prompt
    """
    # Extract placeholders from prompt
    placeholders = set(re.findall(r"\{(\w+)\}", prompt))

    dummy_data = {}

    # Get dummy data configuration
    if config is None:
        from omegaconf import OmegaConf

        config = OmegaConf.create({"data_generation": {"strategy": "realistic"}})

    data_gen_config = config.get("data_generation", {})
    strategy = data_gen_config.get("strategy", "realistic")

    for placeholder in placeholders:
        # Create appropriate dummy data based on placeholder name and strategy
        if strategy == "realistic":
            dummy_data[placeholder] = _create_realistic_dummy_data(placeholder)
        elif strategy == "minimal":
            dummy_data[placeholder] = _create_minimal_dummy_data(placeholder)
        elif strategy == "comprehensive":
            dummy_data[placeholder] = _create_comprehensive_dummy_data(placeholder)
        else:
            dummy_data[placeholder] = f"dummy_{placeholder.lower()}"

    return dummy_data


def _create_realistic_dummy_data(placeholder: str) -> Any:
    """Create realistic dummy data for testing."""
    placeholder_lower = placeholder.lower()

    if "query" in placeholder_lower:
        return "What is the meaning of life?"
    if "context" in placeholder_lower:
        return "This is some context information for testing."
    if "code" in placeholder_lower:
        return "print('Hello, World!')"
    if "text" in placeholder_lower:
        return "This is sample text for testing."
    if "content" in placeholder_lower:
        return "Sample content for testing purposes."
    if "question" in placeholder_lower:
        return "What is machine learning?"
    if "answer" in placeholder_lower:
        return "Machine learning is a subset of AI."
    if "task" in placeholder_lower:
        return "Complete this research task."
    if "description" in placeholder_lower:
        return "A detailed description of the task."
    if "error" in placeholder_lower:
        return "An error occurred during processing."
    if "sequence" in placeholder_lower:
        return "Step 1: Analyze, Step 2: Process, Step 3: Complete"
    if "results" in placeholder_lower:
        return "Search results from web query."
    if "data" in placeholder_lower:
        return {"key": "value", "number": 42}
    if "examples" in placeholder_lower:
        return "Example 1, Example 2, Example 3"
    if "articles" in placeholder_lower:
        return "Article content for aggregation."
    if "topic" in placeholder_lower:
        return "artificial intelligence"
    if "problem" in placeholder_lower:
        return "Solve this complex problem."
    if "solution" in placeholder_lower:
        return "The solution involves multiple steps."
    if "system" in placeholder_lower:
        return "You are a helpful assistant."
    if "user" in placeholder_lower:
        return "Please help me with this task."
    if "current_time" in placeholder_lower:
        return "2024-01-01T12:00:00Z"
    if "current_date" in placeholder_lower:
        return "Mon, 01 Jan 2024 12:00:00 GMT"
    if "current_year" in placeholder_lower:
        return "2024"
    if "current_month" in placeholder_lower:
        return "1"
    if "language" in placeholder_lower:
        return "en"
    if "style" in placeholder_lower:
        return "formal"
    if "team_size" in placeholder_lower:
        return "5"
    if "available_vars" in placeholder_lower:
        return "numbers, threshold"
    if "knowledge" in placeholder_lower:
        return "General knowledge about the topic."
    if "knowledge_str" in placeholder_lower:
        return "String representation of knowledge."
    if "knowledge_items" in placeholder_lower:
        return "Item 1, Item 2, Item 3"
    if "serp_data" in placeholder_lower:
        return "Search engine results page data."
    if "workflow_description" in placeholder_lower:
        return "A comprehensive research workflow."
    if "coordination_strategy" in placeholder_lower:
        return "collaborative"
    if "agent_count" in placeholder_lower:
        return "3"
    if "max_rounds" in placeholder_lower:
        return "5"
    if "consensus_threshold" in placeholder_lower:
        return "0.8"
    if "task_description" in placeholder_lower:
        return "Complete the assigned task."
    if "workflow_type" in placeholder_lower:
        return "research"
    if "workflow_name" in placeholder_lower:
        return "test_workflow"
    if "input_data" in placeholder_lower:
        return {"test": "data"}
    if "evaluation_criteria" in placeholder_lower:
        return "quality, accuracy, completeness"
    if "selected_workflows" in placeholder_lower:
        return "workflow1, workflow2"
    if "name" in placeholder_lower:
        return "test_name"
    if "hypothesis" in placeholder_lower:
        return "Test hypothesis for validation."
    if "messages" in placeholder_lower:
        return [{"role": "user", "content": "Hello"}]
    if "model" in placeholder_lower:
        return "test-model"
    if "top_p" in placeholder_lower:
        return "0.9"
    if (
        "frequency_penalty" in placeholder_lower
        or "presence_penalty" in placeholder_lower
    ):
        return "0.0"
    if "texts" in placeholder_lower:
        return ["Text 1", "Text 2"]
    if "model_name" in placeholder_lower:
        return "test-model"
    if "token_ids" in placeholder_lower:
        return "[1, 2, 3, 4, 5]"
    if "server_url" in placeholder_lower:
        return "http://localhost:8000"
    if "timeout" in placeholder_lower:
        return "30"
    return f"dummy_{placeholder_lower}"


def _create_minimal_dummy_data(placeholder: str) -> Any:
    """Create minimal dummy data for quick testing."""
    placeholder_lower = placeholder.lower()

    if "data" in placeholder_lower or "content" in placeholder_lower:
        return {"key": "value"}
    if "list" in placeholder_lower or "items" in placeholder_lower:
        return ["item1", "item2"]
    if "text" in placeholder_lower or "description" in placeholder_lower:
        return f"Test {placeholder_lower}"
    if "number" in placeholder_lower or "count" in placeholder_lower:
        return 42
    if "boolean" in placeholder_lower or "flag" in placeholder_lower:
        return True
    return f"test_{placeholder_lower}"


def _create_comprehensive_dummy_data(placeholder: str) -> Any:
    """Create comprehensive dummy data for thorough testing."""
    placeholder_lower = placeholder.lower()

    if "query" in placeholder_lower:
        return "What is the fundamental nature of consciousness and how does it relate to quantum mechanics in biological systems?"
    if "context" in placeholder_lower:
        return "This analysis examines the intersection of quantum biology and consciousness studies, focusing on microtubule-based quantum computation theories and their implications for understanding subjective experience."
    if "code" in placeholder_lower:
        return '''
import numpy as np
import matplotlib.pyplot as plt

def quantum_consciousness_simulation(n_qubits=10, time_steps=100):
    """Simulate quantum consciousness model."""
    # Initialize quantum state
    state = np.random.rand(2**n_qubits) + 1j * np.random.rand(2**n_qubits)
    state = state / np.linalg.norm(state)

    # Simulate time evolution
    for t in range(time_steps):
        # Apply quantum operations
        state = quantum_gate_operation(state)

    return state

def quantum_gate_operation(state):
    """Apply quantum gate operations."""
    # Simplified quantum gate
    gate = np.array([[1, 0], [0, 1j]])
    return np.dot(gate, state[:2])

# Run simulation
result = quantum_consciousness_simulation()
print(f"Final quantum state norm: {np.linalg.norm(result)}")
'''
    if "text" in placeholder_lower:
        return "This is a comprehensive text sample for testing purposes, containing multiple sentences and demonstrating various linguistic patterns that might be encountered in real-world applications of natural language processing systems."
    if "data" in placeholder_lower:
        return {
            "research_findings": [
                {
                    "topic": "quantum_consciousness",
                    "confidence": 0.87,
                    "evidence": "experimental",
                },
                {
                    "topic": "microtubule_computation",
                    "confidence": 0.72,
                    "evidence": "theoretical",
                },
            ],
            "methodology": {
                "approach": "multi_modal_analysis",
                "tools": ["quantum_simulation", "consciousness_modeling"],
                "validation": "cross_domain_verification",
            },
            "conclusions": [
                "Consciousness may involve quantum processes",
                "Microtubules could serve as quantum computers",
                "Integration of physics and neuroscience needed",
            ],
        }
    if "examples" in placeholder_lower:
        return [
            "Quantum microtubule theory of consciousness",
            "Orchestrated objective reduction (Orch-OR)",
            "Penrose-Hameroff hypothesis",
            "Quantum effects in biological systems",
            "Consciousness and quantum mechanics",
        ]
    if "articles" in placeholder_lower:
        return [
            {
                "title": "Quantum Aspects of Consciousness",
                "authors": ["Penrose, R.", "Hameroff, S."],
                "journal": "Physics of Life Reviews",
                "year": 2014,
                "abstract": "Theoretical framework linking consciousness to quantum processes in microtubules.",
            },
            {
                "title": "Microtubules as Quantum Computers",
                "authors": ["Hameroff, S."],
                "journal": "Frontiers in Physics",
                "year": 2019,
                "abstract": "Exploration of microtubule-based quantum computation in neurons.",
            },
        ]
    return _create_realistic_dummy_data(placeholder)


def get_all_prompts_with_modules() -> list[tuple[str, str, str]]:
    """Get all prompts from all prompt modules.

    Returns:
        List of (module_name, prompt_name, prompt_content) tuples
    """
    import importlib

    prompts_dir = Path("DeepResearch/src/prompts")
    all_prompts = []

    # Get all Python files in prompts directory
    for py_file in prompts_dir.glob("*.py"):
        if py_file.name.startswith("__"):
            continue

        module_name = py_file.stem

        try:
            # Import the module
            module = importlib.import_module(f"DeepResearch.src.prompts.{module_name}")

            # Look for prompt dictionaries or classes
            for attr_name in dir(module):
                if attr_name.startswith("__"):
                    continue

                attr = getattr(module, attr_name)

                # Check if it's a prompt dictionary or class
                if isinstance(attr, dict) and attr_name.endswith("_PROMPTS"):
                    # Extract prompts from dictionary
                    for prompt_key, prompt_value in attr.items():
                        if isinstance(prompt_value, str):
                            all_prompts.append(
                                (module_name, f"{attr_name}.{prompt_key}", prompt_value)
                            )

                elif isinstance(attr, str) and (
                    "PROMPT" in attr_name or "SYSTEM" in attr_name
                ):
                    # Individual prompt strings
                    all_prompts.append((module_name, attr_name, attr))

                elif hasattr(attr, "PROMPTS") and isinstance(attr.PROMPTS, dict):
                    # Classes with PROMPTS attribute
                    for prompt_key, prompt_value in attr.PROMPTS.items():
                        if isinstance(prompt_value, str):
                            all_prompts.append(
                                (module_name, f"{attr_name}.{prompt_key}", prompt_value)
                            )

        except ImportError as e:
            logger.warning("Could not import module %s: %s", module_name, e)
            continue

    return all_prompts
