"""Cartesia TTS client — async, chunked, ffmpeg-normalized.

Reuses patterns proven in aether-focus:
  - voice: Ava (sonic-3)
  - chunk at sentence boundaries, 4000 chars max
  - ffmpeg concat + loudnorm normalization
"""
from __future__ import annotations

import asyncio
import logging
import os
import re
import subprocess
import tempfile
from pathlib import Path

import httpx

log = logging.getLogger(__name__)

BASE_URL = "https://api.cartesia.ai"
VOICE_ID = "9a0cd2ab-32eb-4f1e-9d7f-f1029c17c71c"  # Ava
MODEL = "sonic-3-2026-01-12"
MAX_CHARS = 4000
OUTPUT_FMT = {"container": "mp3", "sample_rate": 44100, "encoding": "mp3"}


def _chunk_text(text: str, max_chars: int = MAX_CHARS) -> list[str]:
    sentences = re.split(r"(?<=[.!?])\s+", text)
    chunks: list[str] = []
    current = ""
    for sent in sentences:
        if len(current) + len(sent) + 1 > max_chars:
            if current:
                chunks.append(current.strip())
            current = sent
        else:
            current = current + " " + sent if current else sent
    if current:
        chunks.append(current.strip())
    return chunks


async def _generate_chunk(client: httpx.AsyncClient, text: str, out_path: Path) -> None:
    api_key = os.environ.get("CARTESIA_API_KEY")
    if not api_key:
        raise RuntimeError("CARTESIA_API_KEY not set")

    payload = {
        "model_id": MODEL,
        "transcript": text,
        "voice": {"mode": "id", "id": VOICE_ID},
        "output_format": OUTPUT_FMT,
        "language": "en",
    }
    r = await client.post(
        f"{BASE_URL}/tts/bytes",
        headers={
            "X-API-Key": api_key,
            "Cartesia-Version": "2024-06-10",
            "Content-Type": "application/json",
        },
        json=payload,
        timeout=60.0,
    )
    r.raise_for_status()
    out_path.write_bytes(r.content)


def _concat_chunks(chunk_paths: list[Path], out_path: Path) -> None:
    list_file = out_path.with_suffix(".list")
    with open(list_file, "w") as f:
        for p in chunk_paths:
            f.write(f"file '{p.absolute()}'\n")
    cmd = [
        "ffmpeg", "-y", "-f", "concat", "-safe", "0",
        "-i", str(list_file), "-c", "copy", str(out_path),
    ]
    subprocess.run(cmd, capture_output=True, check=True)
    list_file.unlink(missing_ok=True)


def _estimate_duration(text: str) -> int:
    """Rough estimate: ~150 words/min ≈ 2.5 chars/sec."""
    return max(1, int(len(text) / 2.5))


async def generate_brief_audio(text: str) -> tuple[bytes, int]:
    """Generate normalized MP3 bytes from *text*.

    Returns (mp3_bytes, estimated_duration_seconds).
    """
    chunks = _chunk_text(text)
    log.info("cartesia: %d chunks for %d chars", len(chunks), len(text))

    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        chunk_paths: list[Path] = []

        async with httpx.AsyncClient() as client:
            for i, chunk in enumerate(chunks, 1):
                cp = tmp / f"chunk_{i:03d}.mp3"
                await _generate_chunk(client, chunk, cp)
                chunk_paths.append(cp)

        raw = tmp / "combined.mp3"
        _concat_chunks(chunk_paths, raw)

        normalized = tmp / "normalized.mp3"
        from dispatch.podcast.audio_post import normalize_loudness
        await normalize_loudness(raw, normalized)

        data = normalized.read_bytes()

    duration = _estimate_duration(text)
    log.info("cartesia: done — %d bytes, ~%ds est", len(data), duration)
    return data, duration
