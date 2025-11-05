"""Minimal docker.errors stub."""

from __future__ import annotations


class DockerException(Exception):
    """Base docker exception."""


class ImageNotFound(DockerException):
    """Raised when a requested image is unavailable."""
