"""
Network utilities for container testing.
"""

from testcontainers.core.network import Network


class NetworkManager:
    """Manages networks for container testing."""

    def __init__(self):
        self.networks: dict[str, Network] = {}

    def create_network(self, name: str, driver: str = "bridge") -> Network:
        """Create a new network."""
        network = Network()
        network.name = name
        self.networks[name] = network
        return network

    def get_network(self, name: str) -> Network | None:
        """Get a network by name."""
        return self.networks.get(name)

    def remove_network(self, name: str) -> None:
        """Remove a network."""
        if name in self.networks:
            try:
                self.networks[name].remove()
            except Exception:
                pass  # Ignore errors during cleanup
            finally:
                del self.networks[name]

    def cleanup(self) -> None:
        """Clean up all networks."""
        for name in list(self.networks.keys()):
            self.remove_network(name)


def create_isolated_network(name: str = "test_isolated") -> Network:
    """Create an isolated network for testing."""
    network = Network()
    network.name = name
    return network


def create_shared_network(name: str = "test_shared") -> Network:
    """Create a shared network for multi-container testing."""
    network = Network()
    network.name = name
    return network
