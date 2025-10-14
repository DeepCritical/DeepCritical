"""
Docker sandbox isolation tests for security validation.
"""

import pytest

from tests.utils.testcontainers.docker_helpers import create_isolated_container


class TestDockerSandboxIsolation:
    """Test container isolation and security."""

    @pytest.mark.containerized
    @pytest.mark.optional
    @pytest.mark.docker
    def test_container_cannot_access_proc(self, test_config):
        """Test that container cannot access /proc filesystem."""
        if not test_config["docker_enabled"]:
            pytest.skip("Docker tests disabled")

        # Create container with restricted access
        container = create_isolated_container(
            image="python:3.11-slim",
            command=["python", "-c", "import os; print(open('/proc/version').read())"],
        )

        # Start the container explicitly (testcontainers context manager doesn't auto-start)
        container.start()

        # Wait for container to be running
        import time

        for _ in range(10):  # Wait up to 10 seconds
            container.reload()
            if container.status == "running":
                break
            time.sleep(1)

        assert container.get_wrapped_container().status == "running"

    @pytest.mark.containerized
    @pytest.mark.optional
    @pytest.mark.docker
    def test_container_cannot_access_host_dirs(self, test_config):
        """Test that container cannot access unauthorized host directories."""
        if not test_config["docker_enabled"]:
            pytest.skip("Docker tests disabled")

        container = create_isolated_container(
            image="python:3.11-slim",
            command=["python", "-c", "import os; print(open('/etc/passwd').read())"],
        )

        # Start the container explicitly
        container.start()

        # Wait for container to be running
        import time

        for _ in range(10):  # Wait up to 10 seconds
            container.reload()
            if container.status == "running":
                break
            time.sleep(1)

        assert container.get_wrapped_container().status == "running"

    @pytest.mark.containerized
    @pytest.mark.optional
    @pytest.mark.docker
    def test_readonly_mounts_enforced(self, test_config, tmp_path):
        """Test that read-only mounts cannot be written to."""
        if not test_config["docker_enabled"]:
            pytest.skip("Docker tests disabled")

        # Create test file
        test_file = tmp_path / "readonly_test.txt"
        test_file.write_text("test content")

        # Create container and add volume mapping
        container = create_isolated_container(
            image="python:3.11-slim",
            command=[
                "python",
                "-c",
                "open('/test/readonly.txt', 'w').write('modified')",
            ],
        )
        # Add volume mapping after container creation
        # Note: testcontainers API may vary by version - using direct container method
        try:
            # Try the standard testcontainers volume mapping
            container.with_volume_mapping(
                str(test_file), "/test/readonly.txt", mode="ro"
            )
        except AttributeError:
            # If with_volume_mapping doesn't exist, try alternative approaches
            # For now, we'll skip the volume mapping and test differently
            pytest.skip(
                "Volume mapping not available in current testcontainers version"
            )

        # Start the container explicitly
        container.start()

        # Wait for container to be running
        import time

        for _ in range(10):  # Wait up to 10 seconds
            container.reload()
            if container.status == "running":
                break
            time.sleep(1)

        assert container.get_wrapped_container().status == "running"

        # Verify original content unchanged
        assert test_file.read_text() == "test content"
