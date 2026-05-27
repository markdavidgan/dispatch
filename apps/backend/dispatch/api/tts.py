"""TTS generation endpoint — delegates to Google Cloud TTS.

Called by the Vercel frontend to generate briefing audio.
Returns raw MP3 bytes.
"""
from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel

router = APIRouter(prefix="/tts")
log = logging.getLogger(__name__)


class TTSRequest(BaseModel):
    text: str
    voice: str | None = None


@router.post("/generate")
async def generate_tts(req: TTSRequest):
    """Generate MP3 audio from text."""
    try:
        from dispatch.audio import generate_brief_audio
        mp3_bytes, duration = await generate_brief_audio(req.text)
        return Response(
            content=mp3_bytes,
            media_type="audio/mpeg",
            headers={"X-Audio-Duration-S": str(duration)},
        )
    except Exception as e:
        log.error("tts generation failed: %s", e)
        raise HTTPException(status_code=503, detail=f"TTS generation failed: {e}")
