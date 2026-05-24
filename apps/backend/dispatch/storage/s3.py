"""S3-compatible storage backend (R2, AWS S3, MinIO, Wasabi, etc.).

Uses aiobotocore for async S3 operations.
"""
from __future__ import annotations

import logging
from typing import Any

from dispatch.storage.base import StorageBackend

log = logging.getLogger(__name__)


class S3Storage(StorageBackend):
    """S3-compatible storage backend."""

    def __init__(
        self,
        endpoint_url: str,
        bucket: str,
        access_key_id: str,
        secret_access_key: str,
        region: str = "auto",
        public_base_url: str = "",
    ) -> None:
        self.endpoint_url = endpoint_url.rstrip("/")
        self.bucket = bucket
        self.access_key_id = access_key_id
        self.secret_access_key = secret_access_key
        self.region = region
        self.public_base_url = public_base_url.rstrip("/") if public_base_url else ""
        self._session = None

    def _get_session(self):
        if self._session is None:
            try:
                import aiobotocore.session
            except ImportError as exc:
                raise RuntimeError(
                    "aiobotocore is required for S3/R2 storage. "
                    "Install it with: pip install aiobotocore"
                ) from exc
            self._session = aiobotocore.session.AioSession()
        return self._session

    async def _client(self):
        session = self._get_session()
        return session.create_client(
            "s3",
            region_name=self.region,
            endpoint_url=self.endpoint_url,
            aws_access_key_id=self.access_key_id,
            aws_secret_access_key=self.secret_access_key,
        )

    async def upload_bytes(
        self, data: bytes, key: str, content_type: str = "application/octet-stream"
    ) -> str:
        async with await self._client() as client:
            await client.put_object(
                Bucket=self.bucket,
                Key=key,
                Body=data,
                ContentType=content_type,
            )
        log.info("s3 upload: %s", key)
        if self.public_base_url:
            return f"{self.public_base_url}/{key}"
        return f"{self.endpoint_url}/{self.bucket}/{key}"

    async def download_bytes(self, key: str) -> bytes:
        async with await self._client() as client:
            resp = await client.get_object(Bucket=self.bucket, Key=key)
            async with resp["Body"] as stream:
                return await stream.read()

    async def delete_object(self, key: str) -> bool:
        async with await self._client() as client:
            await client.delete_object(Bucket=self.bucket, Key=key)
        log.info("s3 delete: %s", key)
        return True

    async def list_objects(
        self, prefix: str = "", limit: int = 1000, cursor: str = ""
    ) -> dict[str, Any]:
        kwargs: dict[str, Any] = {
            "Bucket": self.bucket,
            "MaxKeys": limit,
            "Prefix": prefix,
        }
        if cursor:
            kwargs["ContinuationToken"] = cursor
        async with await self._client() as client:
            resp = await client.list_objects_v2(**kwargs)
        objects = [
            {
                "name": obj["Key"],
                "size": obj["Size"],
                "uploaded": obj["LastModified"].isoformat(),
            }
            for obj in resp.get("Contents", [])
        ]
        return {
            "objects": objects,
            "truncated": resp.get("IsTruncated", False),
            "cursor": resp.get("NextContinuationToken", ""),
        }

    async def audio_url(self, key: str, ttl_seconds: int = 3600) -> str | None:
        async with await self._client() as client:
            url = await client.generate_presigned_url(
                "get_object",
                Params={"Bucket": self.bucket, "Key": key},
                ExpiresIn=ttl_seconds,
            )
        return url

    async def local_path(self, key: str) -> str | None:
        return None
