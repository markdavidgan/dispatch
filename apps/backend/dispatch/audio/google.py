"""Google Cloud TTS client — async, chunked, ffmpeg-normalized.

Reuses patterns proven in scripts/generate-tts.py:
  - voice: Ava (Chirp 3 HD / en-US-Chirp3-HD-Leda)
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

from google.cloud import texttospeech

log = logging.getLogger(__name__)

VOICE_NAME = os.environ.get("GCP_TTS_VOICE", "en-US-Chirp3-HD-Leda")
LANGUAGE_CODE = os.environ.get("GCP_TTS_LANGUAGE_CODE", "en-US")
MAX_CHARS = 4000


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


def _synthesize_chunk(
    client: texttospeech.TextToSpeechClient,
    text: str,
    voice_params,
    audio_config,
    out_path: Path,
) -> None:
    input_text = texttospeech.SynthesisInput(text=text)
    response = client.synthesize_speech(
        input=input_text, voice=voice_params, audio_config=audio_config
    )
    out_path.write_bytes(response.audio_content)


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
    """Rough estimate: ~150 wpm at ~5 chars/word (incl. space) ≈ 12.5 chars/sec.
    Previously divided by 2.5 and overstated by ~5×."""
    return max(1, int(len(text) / 12.5))


async def generate_brief_audio(text: str) -> tuple[bytes, int]:
    """Generate normalized MP3 bytes from *text* using Google Chirp 3 HD (Ava).

    Returns (mp3_bytes, estimated_duration_seconds).
    """
    # Ensure GCP credentials are available
    creds_path = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
    if not creds_path:
        raise RuntimeError("GOOGLE_APPLICATION_CREDENTIALS not set")

    chunks = _chunk_text(text)
    log.info("google-tts: %d chunks for %d chars (voice=%s)", len(chunks), len(text), VOICE_NAME)

    client = texttospeech.TextToSpeechClient()
    voice = texttospeech.VoiceSelectionParams(
        language_code=LANGUAGE_CODE,
        name=VOICE_NAME,
    )
    audio_config = texttospeech.AudioConfig(
        audio_encoding=texttospeech.AudioEncoding.MP3,
        speaking_rate=1.0,
        pitch=0.0,
    )

    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        chunk_paths: list[Path] = []

        for i, chunk in enumerate(chunks, 1):
            cp = tmp / f"chunk_{i:03d}.mp3"
            # Google client is synchronous — offload to thread
            await asyncio.to_thread(
                _synthesize_chunk, client, chunk, voice, audio_config, cp
            )
            chunk_paths.append(cp)

        raw = tmp / "combined.mp3"
        _concat_chunks(chunk_paths, raw)

        normalized = tmp / "normalized.mp3"
        from dispatch.podcast.audio_post import normalize_loudness
        await normalize_loudness(raw, normalized)

        data = normalized.read_bytes()

    duration = _estimate_duration(text)
    log.info("google-tts: done — %d bytes, ~%ds est", len(data), duration)
    return data, duration
