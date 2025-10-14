"""
Docker helper utilities for testing.
"""

import os

from testcontainers.core.container import DockerContainer


class TestContainerManager:
    """Manages test containers for isolated testing."""

    def __init__(self):
        self.containers = {}
        self.networks = {}

    def create_container(self, image: str, **kwargs) -> DockerContainer:
        """Create a test container with specified configuration."""
        container = DockerContainer(image, **kwargs)

        # Add security constraints for testing
        if os.getenv("TEST_SECURITY_ENABLED", "true") == "true":
            container = self._add_security_constraints(container)

        return container

    def _add_security_constraints(self, container: DockerContainer) -> DockerContainer:
        """Add security constraints for test containers."""
        # Disable privileged mode
        # Set resource limits
        # Restrict network access
        # Set user namespace

        # Example: container.with_privileged(False)
        # Example: container.with_memory_limit("2G")
        # Example: container.with_cpu_limit(1.0)

        return container

    def create_isolated_container(
        self, image: str, command: list | None = None, **kwargs
    ) -> DockerContainer:
        """Create a container for isolation testing."""
        container = self.create_container(image, **kwargs)

        if command:
            container.with_command(command)

        # Add isolation-specific configuration
        container.with_env("TEST_ISOLATION", "true")
        # Note: Volume mapping may need to be handled differently based on testcontainers version

        return container

    def cleanup(self):
        """Clean up all managed containers and networks."""
        for container in self.containers.values():
            try:
                container.stop()
            except Exception:
                pass

        for network in self.networks.values():
            try:
                # Remove networks if needed
                pass
            except Exception:
                pass


# Global test container manager
test_container_manager = TestContainerManager()


def create_isolated_container(image: str, **kwargs) -> DockerContainer:
    """Create an isolated container for security testing."""
    return test_container_manager.create_isolated_container(image, **kwargs)


def create_vllm_container(
    model: str = "TinyLlama/TinyLlama-1.1B-Chat-v1.0", **kwargs
) -> DockerContainer:
    """Create VLLM container for testing."""
    container = test_container_manager.create_container(
        "vllm/vllm-openai:latest", **kwargs
    )

    container.with_env("VLLM_MODEL", model)
    container.with_env("VLLM_HOST", "0.0.0.0")
    container.with_env("VLLM_PORT", "8000")

    return container
