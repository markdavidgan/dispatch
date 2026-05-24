"""Cloudflare R2 REST client — upload, download, list, delete.

Uses the Cloudflare Global API Key (no S3 tokens).
Pattern proven in aether-focus/tools/podcast/scripts/upload_to_r2.py.

Delegates to the pluggable storage backend when one is configured via
app.state. Falls back to legacy direct R2 calls for backward compatibility.
"""
from __future__ import annotations

import logging
import os
from datetime import datetime, timezone
from typing import Any

import httpx

from dispatch.storage.base import StorageBackend

log = logging.getLogger(__name__)

# Module-level storage backend — set by main.py lifespan
_storage_backend: StorageBackend | None = None


def set_storage_backend(backend: StorageBackend | None) -> None:
    global _storage_backend
    _storage_backend = backend


def _credentials() -> tuple[str, str, str]:
    account = os.environ.get("CLOUDFLARE_ACCOUNT_ID", "")
    email = os.environ.get("CLOUDFLARE_EMAIL", "")
    key = os.environ.get("CLOUDFLARE_GLOBAL_API_KEY", "")
    if not all([account, email, key]):
        raise RuntimeError("Cloudflare credentials missing")
    return account, email, key


def _bucket() -> str:
    return os.environ.get("R2_BUCKET_NAME", "dispatch-media")


def _public_base() -> str:
    base = os.environ.get("R2_PUBLIC_BASE_URL", "")
    if base:
        return base.rstrip("/")
    # Fallback — construct from account id (may not match your R2 config)
    account = os.environ.get("CLOUDFLARE_ACCOUNT_ID", "")
    return f"https://{account}.r2.dev"


def _api_url(account: str, bucket: str, key: str = "") -> str:
    base = (
        f"https://api.cloudflare.com/client/v4/accounts/{account}"
        f"/r2/buckets/{bucket}/objects"
    )
    if key:
        return f"{base}/{key}"
    return base


async def upload_bytes(
    data: bytes,
    r2_key: str,
    content_type: str = "application/json",
) -> str:
    """Upload *data* to R2 at *r2_key*. Returns the public URL."""
    if _storage_backend is not None:
        return await _storage_backend.upload_bytes(data, r2_key, content_type)

    account, email, api_key = _credentials()
    bucket = _bucket()
    url = _api_url(account, bucket, r2_key)

    async with httpx.AsyncClient(timeout=120.0) as client:
        r = await client.put(
            url,
            headers={
                "X-Auth-Email": email,
                "X-Auth-Key": api_key,
                "Content-Type": content_type,
            },
            content=data,
        )
    r.raise_for_status()
    payload = r.json()
    if not payload.get("success"):
        raise RuntimeError(f"R2 upload failed: {payload.get('errors')}")

    public = f"{_public_base()}/{r2_key}"
    log.info("r2 upload: %s → %s", r2_key, public)
    return public


async def signed_url(r2_key: str, expires_in_seconds: int = 3600) -> str:
    """Return a pre-signed URL for *r2_key*.

    For MVP we use the public r2.dev URL directly since the bucket
    is configured for public read.
    """
    return f"{_public_base()}/{r2_key}"


async def download_bytes(r2_key: str) -> bytes:
    """Download an object from R2."""
    if _storage_backend is not None:
        return await _storage_backend.download_bytes(r2_key)

    account, email, api_key = _credentials()
    bucket = _bucket()
    url = _api_url(account, bucket, r2_key)

    async with httpx.AsyncClient(timeout=30.0) as client:
        r = await client.get(
            url,
            headers={"X-Auth-Email": email, "X-Auth-Key": api_key},
        )
    r.raise_for_status()
    return r.content


async def delete_object(r2_key: str) -> bool:
    """Delete an object from R2. Returns True if deleted (or already absent)."""
    if _storage_backend is not None:
        return await _storage_backend.delete_object(r2_key)

    account, email, api_key = _credentials()
    bucket = _bucket()
    url = _api_url(account, bucket, r2_key)

    async with httpx.AsyncClient(timeout=30.0) as client:
        r = await client.delete(
            url,
            headers={"X-Auth-Email": email, "X-Auth-Key": api_key},
        )
    if r.status_code == 404:
        log.debug("r2 delete: %s already absent", r2_key)
        return True
    r.raise_for_status()
    log.info("r2 delete: %s", r2_key)
    return True


async def list_objects(
    prefix: str = "",
    limit: int = 1000,
    cursor: str = "",
) -> dict[str, Any]:
    """List objects in the bucket. Returns the raw API result dict.

    Response shape (Cloudflare v4):
        {
            "result": {
                "objects": [
                    {"name": "...", "size": 123, "uploaded": "2026-01-01T00:00:00.000Z"}
                ],
                "truncated": false
            },
            "success": true
        }
    """
    if _storage_backend is not None:
        return await _storage_backend.list_objects(prefix, limit, cursor)

    account, email, api_key = _credentials()
    bucket = _bucket()
    url = _api_url(account, bucket)
    params: dict[str, str] = {"limit": str(limit)}
    if prefix:
        params["prefix"] = prefix
    if cursor:
        params["cursor"] = cursor

    async with httpx.AsyncClient(timeout=30.0) as client:
        r = await client.get(
            url,
            headers={"X-Auth-Email": email, "X-Auth-Key": api_key},
            params=params,
        )
    r.raise_for_status()
    payload = r.json()
    if not payload.get("success"):
        raise RuntimeError(f"R2 list failed: {payload.get('errors')}")
    return payload.get("result", {})
