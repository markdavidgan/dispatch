"""Pluggable storage backend interface.

Backends: local filesystem, R2 (S3-compatible), S3.
The backend is selected via settings.storage.provider and configured
via settings.storage.* keys.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class StorageBackend(ABC):
    """Abstract storage backend."""

    @abstractmethod
    async def upload_bytes(
        self, data: bytes, key: str, content_type: str = "application/octet-stream"
    ) -> str:
        """Upload data. Returns a URL suitable for public access (if public) or
        a reference URL that the backend's audio_url() can turn into a presigned URL."""

    @abstractmethod
    async def download_bytes(self, key: str) -> bytes:
        """Download object bytes."""

    @abstractmethod
    async def delete_object(self, key: str) -> bool:
        """Delete object. Returns True if deleted or already absent."""

    @abstractmethod
    async def list_objects(
        self, prefix: str = "", limit: int = 1000, cursor: str = ""
    ) -> dict[str, Any]:
        """List objects. Returns a dict with at least {"objects": [...]}."""

    @abstractmethod
    async def audio_url(self, key: str, ttl_seconds: int = 3600) -> str | None:
        """Return a presigned/public URL for audio streaming, or None if the
        backend serves files directly (e.g. local filesystem)."""

    @abstractmethod
    async def local_path(self, key: str) -> str | None:
        """Return an absolute filesystem path for the key, or None if not
        applicable (remote backends). Used by FileResponse fallback."""
