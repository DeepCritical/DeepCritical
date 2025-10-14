"""
Jupyter client for DeepCritical.

Adapted from AG2 jupyter client for communicating with Jupyter gateway servers.
"""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass
from types import TracebackType
from typing import Any

import requests
from requests.adapters import HTTPAdapter, Retry
from typing_extensions import Self

from DeepResearch.src.utils.jupyter.base import JupyterConnectionInfo


class JupyterClient:
    """A client for communicating with a Jupyter gateway server."""

    def __init__(self, connection_info: JupyterConnectionInfo):
        """Initialize the Jupyter client.

        Args:
            connection_info (JupyterConnectionInfo): Connection information
        """
        self._connection_info = connection_info
        self._session = requests.Session()
        retries = Retry(total=5, backoff_factor=0.1)
        self._session.mount("http://", HTTPAdapter(max_retries=retries))
        self._session.mount("https://", HTTPAdapter(max_retries=retries))

    def _get_headers(self) -> dict[str, str]:
        """Get headers for API requests."""
        headers = {"Content-Type": "application/json"}
        if self._connection_info.token is not None:
            headers["Authorization"] = f"token {self._connection_info.token}"
        return headers

    def _get_api_base_url(self) -> str:
        """Get the base URL for API requests."""
        protocol = "https" if self._connection_info.use_https else "http"
        port = f":{self._connection_info.port}" if self._connection_info.port else ""
        return f"{protocol}://{self._connection_info.host}{port}"

    def list_kernel_specs(self) -> dict[str, Any]:
        """List available kernel specifications."""
        response = self._session.get(
            f"{self._get_api_base_url()}/api/kernelspecs", headers=self._get_headers()
        )
        response.raise_for_status()
        return response.json()

    def list_kernels(self) -> list[dict[str, Any]]:
        """List running kernels."""
        response = self._session.get(
            f"{self._get_api_base_url()}/api/kernels", headers=self._get_headers()
        )
        response.raise_for_status()
        return response.json()

    def start_kernel(self, kernel_spec_name: str) -> str:
        """Start a new kernel.

        Args:
            kernel_spec_name (str): Name of the kernel spec to start

        Returns:
            str: ID of the started kernel
        """
        response = self._session.post(
            f"{self._get_api_base_url()}/api/kernels",
            headers=self._get_headers(),
            json={"name": kernel_spec_name},
        )
        response.raise_for_status()
        return response.json()["id"]

    def delete_kernel(self, kernel_id: str) -> None:
        """Delete a kernel."""
        response = self._session.delete(
            f"{self._get_api_base_url()}/api/kernels/{kernel_id}",
            headers=self._get_headers(),
        )
        response.raise_for_status()

    def restart_kernel(self, kernel_id: str) -> None:
        """Restart a kernel."""
        response = self._session.post(
            f"{self._get_api_base_url()}/api/kernels/{kernel_id}/restart",
            headers=self._get_headers(),
        )
        response.raise_for_status()

    def execute_code(
        self, kernel_id: str, code: str, timeout: int = 30
    ) -> dict[str, Any]:
        """Execute code in a kernel.

        Args:
            kernel_id: ID of the kernel to execute in
            code: Code to execute
            timeout: Execution timeout in seconds

        Returns:
            Dictionary containing execution results
        """
        # For a full implementation, this would use WebSocket connections
        # This is a simplified version that uses HTTP endpoints where available

        # This is a simplified implementation - in practice, you'd need WebSocket
        # connections for full Jupyter protocol support
        raise NotImplementedError(
            "Full Jupyter execution requires WebSocket support. "
            "Use DockerCommandLineCodeExecutor for containerized execution instead."
        )


class JupyterKernelClient:
    """Client for communicating with a specific Jupyter kernel via WebSocket."""

    def __init__(self, websocket_connection):
        """Initialize the kernel client.

        Args:
            websocket_connection: WebSocket connection to the kernel
        """
        self._ws = websocket_connection
        self._msg_id = 0

    def _send_message(self, msg_type: str, content: dict[str, Any]) -> str:
        """Send a message to the kernel."""
        msg_id = str(uuid.uuid4())
        message = {
            "header": {
                "msg_id": msg_id,
                "msg_type": msg_type,
                "session": str(uuid.uuid4()),
                "username": "deepcritical",
                "version": "5.0",
            },
            "parent_header": {},
            "metadata": {},
            "content": content,
        }

        self._ws.send(json.dumps(message))
        return msg_id

    def execute_code(self, code: str, timeout: int = 30) -> dict[str, Any]:
        """Execute code in the kernel.

        Args:
            code: Code to execute
            timeout: Execution timeout in seconds

        Returns:
            Execution results
        """
        msg_id = self._send_message(
            "execute_request",
            {
                "code": code,
                "silent": False,
                "store_history": True,
                "user_expressions": {},
                "allow_stdin": False,
            },
        )

        # In a full implementation, this would collect responses
        # For now, return a placeholder
        return {
            "msg_id": msg_id,
            "status": "ok",
            "execution_count": 1,
            "outputs": [],
        }

    def __enter__(self) -> Self:
        """Context manager entry."""
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        """Context manager exit."""
        if hasattr(self, "_ws"):
            self._ws.close()
