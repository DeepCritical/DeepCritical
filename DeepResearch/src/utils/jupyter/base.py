"""
Base classes and protocols for Jupyter integration in DeepCritical.

Adapted from AG2 jupyter framework for use in DeepCritical's code execution system.
"""

from dataclasses import dataclass
from typing import Protocol, runtime_checkable


@dataclass
class JupyterConnectionInfo:
    """Connection information for Jupyter servers."""

    host: str
    """Host of the Jupyter gateway server"""
    use_https: bool
    """Whether to use HTTPS"""
    port: int | None = None
    """Port of the Jupyter gateway server. If None, the default port is used"""
    token: str | None = None
    """Token for authentication. If None, no token is used"""


@runtime_checkable
class JupyterConnectable(Protocol):
    """Protocol for Jupyter-connectable objects."""

    @property
    def connection_info(self) -> JupyterConnectionInfo:
        """Return the connection information for this connectable."""
