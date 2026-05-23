"""Shared audio post-processing — loudness normalization + duration probing."""
import asyncio
import json
from pathlib import Path

LUFS = "-16"
TRUEPEAK = "-1.5"


async def normalize_loudness(src: Path, dst: Path) -> None:
    """Run ffmpeg loudness normalization. -16 LUFS / -1.5 dBTP / 192kbps."""
    proc = await asyncio.create_subprocess_exec(
        "ffmpeg", "-y", "-i", str(src),
        "-af", f"loudnorm=I={LUFS}:TP={TRUEPEAK}:LRA=11",
        "-ar", "44100", "-b:a", "192k", str(dst),
        stdout=asyncio.subprocess.DEVNULL,
        stderr=asyncio.subprocess.PIPE,
    )
    _, err = await proc.communicate()
    if proc.returncode != 0:
        raise RuntimeError(f"loudnorm failed: {err.decode()[:500]}")


async def probe_duration_seconds(src: Path) -> int:
    proc = await asyncio.create_subprocess_exec(
        "ffprobe", "-v", "quiet", "-print_format", "json", "-show_format", str(src),
        stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
    )
    out, _ = await proc.communicate()
    data = json.loads(out.decode() or "{}")
    return int(float(data.get("format", {}).get("duration", "0")))
