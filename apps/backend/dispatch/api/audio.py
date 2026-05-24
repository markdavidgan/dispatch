"""Audio endpoint — serves audio files via redirect or direct streaming.

For remote storage (R2/S3): returns 302 to presigned URL.
For local storage: returns FileResponse with Range support.
"""
from __future__ import annotations

import logging

from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import FileResponse, RedirectResponse

router = APIRouter(prefix="/audio")
log = logging.getLogger(__name__)

# Allowed key prefixes to prevent directory traversal / unauthorized access
ALLOWED_PREFIXES = ("dispatch/audio/", "podcast/")


@router.get("/{key:path}")
async def get_audio(request: Request, key: str):
    """Serve an audio file."""
    if not any(key.startswith(p) for p in ALLOWED_PREFIXES):
        raise HTTPException(status_code=403, detail="Invalid audio key")

    storage = request.app.state.storage_backend
    presigned = await storage.audio_url(key)
    if presigned:
        return RedirectResponse(url=presigned)

    local = await storage.local_path(key)
    if local:
        return FileResponse(local, media_type="audio/mpeg", filename=key.split("/")[-1])

    raise HTTPException(status_code=404, detail="Audio not found")
