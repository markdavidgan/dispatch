"""Async wrapper around notebooklm-py.

Normalizes the interface for intake.py. Each podcast project gets its own
notebook (created once, reused thereafter). Sources are added per-episode
and old sources are pruned to keep the notebook focused.
"""
from __future__ import annotations

import logging
import os
from pathlib import Path

from notebooklm import NotebookLMClient
from notebooklm.rpc.types import AudioFormat, AudioLength

log = logging.getLogger(__name__)

# Map environment to notebooklm-py storage path
_STORAGE_PATH = os.environ.get(
    "NOTEBOOKLM_SESSION_PATH",
    "/home/dispatch/.notebooklm/profiles/default/storage_state.json",
)


async def _client() -> NotebookLMClient:
    return await NotebookLMClient.from_storage(path=_STORAGE_PATH)


async def _get_or_create_notebook(client: NotebookLMClient, title: str) -> str:
    """Return notebook ID, creating if necessary."""
    notebooks = await client.notebooks.list()
    for nb in notebooks:
        if nb.title == title:
            log.info("notebooklm: using existing notebook %r (%s)", title, nb.id)
            return nb.id
    nb = await client.notebooks.create(title)
    log.info("notebooklm: created notebook %r (%s)", title, nb.id)
    return nb.id


async def _prune_old_sources(client: NotebookLMClient, notebook_id: str, keep: int = 8) -> None:
    """Keep only the *keep* most recent sources."""
    sources = await client.sources.list(notebook_id)
    if len(sources) <= keep:
        return
    # Sort by created_at descending (newest first)
    sources_sorted = sorted(sources, key=lambda s: s.created_at or "", reverse=True)
    for old in sources_sorted[keep:]:
        try:
            await client.sources.delete(notebook_id, old.id)
            log.info("notebooklm: pruned source %r", old.title)
        except Exception as e:
            log.warning("notebooklm: failed to prune source %r: %s", old.title, e)


async def generate_audio_overview(
    notebook_title: str,
    source_text: str,
    source_title: str,
    instructions: str | None = None,
    audio_format_str: str | None = None,
    audio_length_str: str | None = None,
) -> str:
    """Upload source, generate audio, return artifact_id (task_id).

    Raises RuntimeError on any failure.
    """
    async with await _client() as client:
        notebook_id = await _get_or_create_notebook(client, notebook_title)

        # Add source
        await client.sources.add_text(notebook_id, title=source_title, content=source_text)
        log.info("notebooklm: added source %r to %r", source_title, notebook_title)

        # Prune old sources
        await _prune_old_sources(client, notebook_id)

        # Map format/length strings to enums
        audio_format = None
        audio_length = None
        if audio_format_str:
            fmt_map = {
                "DEEP_DIVE": AudioFormat.DEEP_DIVE,
                "BRIEF": AudioFormat.BRIEF,
                "CRITIQUE": AudioFormat.CRITIQUE,
                "DEBATE": AudioFormat.DEBATE,
            }
            audio_format = fmt_map.get(audio_format_str.upper())
        if audio_length_str:
            len_map = {
                "SHORT": AudioLength.SHORT,
                "DEFAULT": AudioLength.DEFAULT,
                "LONG": AudioLength.LONG,
            }
            audio_length = len_map.get(audio_length_str.upper())

        # Generate audio overview
        result = await client.artifacts.generate_audio(
            notebook_id,
            instructions=instructions,
            audio_format=audio_format,
            audio_length=audio_length,
        )
        log.info("notebooklm: audio generation queued — task_id=%s status=%s", result.task_id, result.status)
        return result.task_id


async def wait_and_download(
    notebook_title: str,
    artifact_id: str,
    dest: Path,
    timeout_s: int = 4 * 3600,
    poll_interval_s: int = 60,
) -> None:
    """Poll until artifact is ready, then download to *dest*.

    Raises TimeoutError or RuntimeError on failure.
    """
    async with await _client() as client:
        notebook_id = await _get_or_create_notebook(client, notebook_title)

        # Wait for completion
        log.info("notebooklm: waiting for artifact %s (timeout=%ds)", artifact_id, timeout_s)
        try:
            artifact = await client.artifacts.wait_for_completion(
                notebook_id, artifact_id, timeout=timeout_s, poll_interval=poll_interval_s
            )
        except Exception as e:
            raise TimeoutError(f"NotebookLM artifact {artifact_id} did not complete: {e}")

        if artifact.status == "failed":
            raise RuntimeError(f"NotebookLM artifact {artifact_id} failed")

        # Download
        log.info("notebooklm: downloading artifact %s → %s", artifact_id, dest)
        await client.artifacts.download_audio(notebook_id, str(dest), artifact_id=artifact_id)
        log.info("notebooklm: downloaded %s (%d bytes)", dest, dest.stat().st_size)
