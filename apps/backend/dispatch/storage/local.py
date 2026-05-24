"""Local filesystem storage backend.

Stores objects on the local filesystem under a configured root path.
Ideal for self-hosted deployments with no cloud storage.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from dispatch.storage.base import StorageBackend

log = logging.getLogger(__name__)


class LocalStorage(StorageBackend):
    """Local filesystem storage."""

    def __init__(self, root: str) -> None:
        self.root = Path(root).expanduser().resolve()
        self.root.mkdir(parents=True, exist_ok=True)

    def _path(self, key: str) -> Path:
        # Prevent directory traversal
        safe = key.replace("..", ".").lstrip("/")
        return self.root / safe

    async def upload_bytes(
        self, data: bytes, key: str, content_type: str = "application/octet-stream"
    ) -> str:
        path = self._path(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        log.info("local storage upload: %s", key)
        # Return a backend-relative URL; the API layer constructs the public URL
        return f"local://{key}"

    async def download_bytes(self, key: str) -> bytes:
        return self._path(key).read_bytes()

    async def delete_object(self, key: str) -> bool:
        path = self._path(key)
        if not path.exists():
            return True
        path.unlink()
        log.info("local storage delete: %s", key)
        return True

    async def list_objects(
        self, prefix: str = "", limit: int = 1000, cursor: str = ""
    ) -> dict[str, Any]:
        # Simple glob-based listing
        search_dir = self.root / prefix.lstrip("/") if prefix else self.root
        objects = []
        skip = int(cursor) if cursor else 0
        count = 0
        for p in sorted(search_dir.rglob("*")):
            if p.is_file():
                rel = p.relative_to(self.root).as_posix()
                if count >= skip + limit:
                    break
                if count >= skip:
                    objects.append({
                        "name": rel,
                        "size": p.stat().st_size,
                        "uploaded": datetime.fromtimestamp(
                            p.stat().st_mtime, tz=timezone.utc
                        ).isoformat(),
                    })
                count += 1
        return {"objects": objects, "truncated": False}

    async def audio_url(self, key: str, ttl_seconds: int = 3600) -> str | None:
        # Local filesystem serves directly via FileResponse; no presigned URL needed
        return None

    async def local_path(self, key: str) -> str | None:
        return str(self._path(key))
