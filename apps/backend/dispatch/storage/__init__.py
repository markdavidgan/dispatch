"""Storage backend factory.

Reads from DB settings to instantiate the correct backend.
"""
from __future__ import annotations

import logging
from typing import Any

from core.db import Database
from dispatch.crypto import Crypto
from dispatch.storage.base import StorageBackend
from dispatch.storage.local import LocalStorage
from dispatch.storage.r2 import R2Storage
from dispatch.storage.s3 import S3Storage

log = logging.getLogger(__name__)


async def get_storage_backend(db: Database, crypto: Crypto) -> StorageBackend:
    """Instantiate the configured storage backend from DB settings."""
    async with db.cursor() as cur:
        await cur.execute("SELECT key, value FROM settings WHERE key LIKE 'storage.%'")
        rows = {row[0]: row[1] for row in await cur.fetchall()}

    provider = rows.get("storage.provider", "local")

    if provider == "local":
        root = rows.get("storage.local_root", "./dispatch-media")
        return LocalStorage(root)

    # Decrypt credentials for remote backends
    def _get(key: str) -> str:
        val = rows.get(key, "")
        if val:
            return crypto.decrypt(val)
        return ""

    if provider == "r2":
        return R2Storage(
            account_id=_get("storage.r2_account_id"),
            bucket=_get("storage.r2_bucket") or "dispatch-media",
            access_key_id=_get("storage.r2_access_key_id"),
            secret_access_key=_get("storage.r2_secret_access_key"),
            public_base_url=_get("storage.r2_public_base_url"),
        )

    if provider == "s3":
        return S3Storage(
            endpoint_url=_get("storage.s3_endpoint"),
            bucket=_get("storage.s3_bucket") or "dispatch-media",
            access_key_id=_get("storage.s3_access_key_id"),
            secret_access_key=_get("storage.s3_secret_access_key"),
            region=_get("storage.s3_region") or "us-east-1",
            public_base_url=_get("storage.s3_public_base_url"),
        )

    raise RuntimeError(f"Unknown storage provider: {provider}")


async def get_storage_from_settings_dict(settings_dict: dict[str, str], crypto: Crypto) -> StorageBackend:
    """Instantiate from a flat dict (used during setup wizard before DB write)."""
    provider = settings_dict.get("storage.provider", "local")

    if provider == "local":
        root = settings_dict.get("storage.local_root", "/data/dispatch-media")
        return LocalStorage(root)

    def _get(key: str) -> str:
        val = settings_dict.get(key, "")
        if val and val.startswith("gAAAA"):  # Fernet prefix
            return crypto.decrypt(val)
        return val

    if provider == "r2":
        return R2Storage(
            account_id=_get("storage.r2_account_id"),
            bucket=_get("storage.r2_bucket") or "dispatch-media",
            access_key_id=_get("storage.r2_access_key_id"),
            secret_access_key=_get("storage.r2_secret_access_key"),
            public_base_url=_get("storage.r2_public_base_url"),
        )

    if provider == "s3":
        return S3Storage(
            endpoint_url=_get("storage.s3_endpoint"),
            bucket=_get("storage.s3_bucket") or "dispatch-media",
            access_key_id=_get("storage.s3_access_key_id"),
            secret_access_key=_get("storage.s3_secret_access_key"),
            region=_get("storage.s3_region") or "us-east-1",
            public_base_url=_get("storage.s3_public_base_url"),
        )

    raise RuntimeError(f"Unknown storage provider: {provider}")
