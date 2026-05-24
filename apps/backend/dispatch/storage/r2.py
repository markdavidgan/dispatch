"""Cloudflare R2 storage backend.

R2 is S3-compatible, so this is a thin wrapper around S3Storage that
uses the Cloudflare-specific endpoint format.
"""
from __future__ import annotations

from dispatch.storage.s3 import S3Storage


class R2Storage(S3Storage):
    """Cloudflare R2 via S3-compatible API."""

    def __init__(
        self,
        account_id: str,
        bucket: str,
        access_key_id: str,
        secret_access_key: str,
        public_base_url: str = "",
    ) -> None:
        endpoint = f"https://{account_id}.r2.cloudflarestorage.com"
        super().__init__(
            endpoint_url=endpoint,
            bucket=bucket,
            access_key_id=access_key_id,
            secret_access_key=secret_access_key,
            region="auto",
            public_base_url=public_base_url,
        )
