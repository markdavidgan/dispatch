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
from dispatch.settings_store import SettingsStore
from dispatch.storage.r2 import R2Storage
from dispatch.storage.s3 import S3Storage

log = logging.getLogger(__name__)


async def get_storage_backend(db: Database, crypto: Crypto) -> StorageBackend:
    """Instantiate the configured storage backend from DB settings."""
    store = SettingsStore(db, crypto)
    provider = await store.get("storage.provider", "local") or "local"

    if provider == "local":
        root = await store.get("storage.local_root", "./dispatch-media") or "./dispatch-media"
        return LocalStorage(root)

    # Decrypt credentials for remote backends
    async def _get(key: str) -> str:
        val = await store.get(key, "")
        return val or ""

    if provider == "r2":
        return R2Storage(
            account_id=await _get("storage.r2_account_id"),
            bucket=await _get("storage.r2_bucket") or "dispatch-media",
            access_key_id=await _get("storage.r2_access_key_id"),
            secret_access_key=await _get("storage.r2_secret_access_key"),
            public_base_url=await _get("storage.r2_public_base_url"),
        )

    if provider == "s3":
        return S3Storage(
            endpoint_url=await _get("storage.s3_endpoint"),
            bucket=await _get("storage.s3_bucket") or "dispatch-media",
            access_key_id=await _get("storage.s3_access_key_id"),
            secret_access_key=await _get("storage.s3_secret_access_key"),
            region=await _get("storage.s3_region") or "us-east-1",
            public_base_url=await _get("storage.s3_public_base_url"),
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
