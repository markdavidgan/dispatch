"""Convert a downloaded NotebookLM DASH audio file to MP3.

Patterned after the recent aether-focus fix
'fix(podcast): convert NotebookLM DASH audio to MP3 after download'.
"""
import asyncio
from pathlib import Path


async def convert(dash_path: Path, mp3_path: Path) -> None:
    proc = await asyncio.create_subprocess_exec(
        "ffmpeg", "-y", "-i", str(dash_path),
        "-vn",                      # no video
        "-c:a", "libmp3lame",
        "-b:a", "192k",
        "-ar", "44100",
        str(mp3_path),
        stdout=asyncio.subprocess.DEVNULL,
        stderr=asyncio.subprocess.PIPE,
    )
    _, err = await proc.communicate()
    if proc.returncode != 0:
        raise RuntimeError(f"dash→mp3 conversion failed: {err.decode()[:500]}")
