"""Weekly episode intake — runs the 7-step pipeline for one project."""
from __future__ import annotations

import logging
import os
import tempfile
import uuid
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from core.db import Database
from dispatch.podcast.registry import PodcastConfig
from dispatch.podcast import composer, notebooklm_wrapper, dash_to_mp3, audio_post, rss
from dispatch.publish import r2

log = logging.getLogger(__name__)


async def _log_job(db: Database, episode_id: str, step: str, status: str, detail: str | None = None):
    now = datetime.now(timezone.utc).isoformat()
    async with db.cursor() as cur:
        if status == "in_progress":
            await cur.execute(
                "INSERT INTO podcast_jobs(episode_id, step, status, started_at, detail) VALUES (?,?,?,?,?)",
                (episode_id, step, status, now, detail),
            )
        else:
            await cur.execute(
                "UPDATE podcast_jobs SET status=?, finished_at=?, detail=? "
                "WHERE episode_id=? AND step=? AND finished_at IS NULL",
                (status, now, detail, episode_id, step),
            )


async def _set_episode_status(db: Database, episode_id: str, status: str, error: str | None = None):
    async with db.cursor() as cur:
        if error:
            await cur.execute("UPDATE episodes SET status=?, error=? WHERE id=?",
                              (status, error, episode_id))
        else:
            await cur.execute("UPDATE episodes SET status=? WHERE id=?", (status, episode_id))


async def _next_episode_no(db: Database, project_slug: str) -> int:
    async with db.cursor() as cur:
        await cur.execute("SELECT COALESCE(MAX(episode_no),0) FROM episodes WHERE project_slug=?",
                          (project_slug,))
        row = await cur.fetchone()
    return (row[0] or 0) + 1


async def _project_display_name(db: Database, project_slug: str) -> str:
    async with db.cursor() as cur:
        await cur.execute("SELECT display_name FROM projects WHERE slug=?", (project_slug,))
        row = await cur.fetchone()
    return row[0] if row else project_slug


async def _notebooklm_session(db: Database) -> dict | None:
    """Read NotebookLM session from DB settings, or return None if not configured."""
    from dispatch.settings_store import SettingsStore
    from dispatch.crypto import Crypto
    from core.config import get_settings
    crypto = Crypto(get_settings().master_key)
    store = SettingsStore(db, crypto)
    return await store.notebooklm_session()


async def _probe_notebooklm(storage_state: dict | None) -> str:
    """Pre-flight probe. Returns 'ok', 'transient', or 'auth'.

    NotebookLMClient is an async context manager — listing notebooks
    requires an `async with` to initialize the underlying RPC channel.
    Reuses the wrapper's `_client()` so it goes through the same
    storage-state persistence path as the real compose calls.
    """
    try:
        client = await notebooklm_wrapper._client(storage_state)
        async with client:
            await client.notebooks.list()
        return "ok"
    except Exception as e:
        err = str(e).lower()
        if "401" in err or "403" in err or "unauthorized" in err:
            return "auth"
        log.warning("notebooklm probe failed (transient): %s", e)
        return "transient"


async def run_episode(db: Database, podcast: PodcastConfig, week_start: date) -> str | None:
    """Run the full pipeline. Returns episode_id, or None if skipped due to missing NotebookLM session."""
    # Guard against duplicate episodes for the same week
    async with db.cursor() as cur:
        await cur.execute(
            "SELECT id FROM episodes WHERE project_slug=? AND week_start=?",
            (podcast.project_slug, week_start.isoformat()),
        )
        if await cur.fetchone():
            log.info("episode already exists for %s week %s — skipping", podcast.project_slug, week_start)
            return None

    episode_id = str(uuid.uuid4())
    episode_no = await _next_episode_no(db, podcast.project_slug)
    project_display = await _project_display_name(db, podcast.project_slug)
    title = f"{podcast.title} — Week of {week_start.isoformat()}"
    now = datetime.now(timezone.utc).isoformat()
    audio_key = f"podcast/{podcast.project_slug}/episode-{episode_no:03d}-{week_start.isoformat()}.mp3"

    # Phase 6b: Check NotebookLM session before starting
    nblm_session = await _notebooklm_session(db)
    if nblm_session is None:
        log.warning("notebooklm session not configured — skipping podcast episode for %s", podcast.project_slug)
        await _set_episode_status(db, episode_id, "skipped")
        return None

    # Pre-flight probe
    probe = await _probe_notebooklm(nblm_session)
    if probe == "auth":
        log.error("notebooklm auth expired for %s", podcast.project_slug)
        await _set_episode_status(db, episode_id, "failed_auth")
        return None
    if probe == "transient":
        log.warning("notebooklm transient failure for %s — will retry on next schedule", podcast.project_slug)
        await _set_episode_status(db, episode_id, "failed_transient")
        return None

    async with db.cursor() as cur:
        await cur.execute(
            "INSERT INTO episodes(id, project_slug, episode_no, week_start, title, description, "
            " audio_key, audio_size_bytes, duration_seconds, generated_at, status) "
            "VALUES (?,?,?,?,?,?,?,?,?,?,?)",
            (episode_id, podcast.project_slug, episode_no, week_start.isoformat(),
             title, podcast.description, audio_key, 0, 0, now, "composing"),
        )

    try:
        # Step 1: compose
        await _log_job(db, episode_id, "compose", "in_progress")
        if podcast.project_slug == composer.DISPATCH_WEEKLY_SLUG:
            # Dispatch-wide cross-project digest: source is the week's
            # curated lead briefings, not raw events.
            source_md = await composer.compose_dispatch_weekly(
                db, week_start, podcast.compose_window_days, episode_no,
            )
        else:
            source_md = await composer.compose(
                db, podcast.project_slug, podcast.title, project_display,
                week_start, podcast.compose_window_days, episode_no,
            )
        async with db.cursor() as cur:
            await cur.execute("UPDATE episodes SET source_markdown=? WHERE id=?", (source_md, episode_id))
        await _log_job(db, episode_id, "compose", "ok")

        # Step 2: upload to NotebookLM + queue audio generation
        await _set_episode_status(db, episode_id, "awaiting_nblm")
        await _log_job(db, episode_id, "upload_nblm", "in_progress")
        source_title = f"Episode {episode_no} — Week of {week_start.isoformat()}"
        artifact_id = await notebooklm_wrapper.generate_audio_overview(
            notebook_title=podcast.title,
            source_text=source_md,
            source_title=source_title,
            storage_state=nblm_session,
        )
        async with db.cursor() as cur:
            await cur.execute("UPDATE episodes SET notebooklm_artifact_id=? WHERE id=?",
                              (artifact_id, episode_id))
        await _log_job(db, episode_id, "upload_nblm", "ok", detail=f"artifact_id={artifact_id}")

        # Step 3: poll + download
        await _log_job(db, episode_id, "poll_nblm", "in_progress")
        with tempfile.TemporaryDirectory() as td:
            tdp = Path(td)
            dash_path = tdp / "audio.dash"
            interm = tdp / "audio.mp3"
            final = tdp / "final.mp3"

            await notebooklm_wrapper.wait_and_download(
                notebook_title=podcast.title,
                artifact_id=artifact_id,
                dest=dash_path,
                storage_state=nblm_session,
            )
            await _log_job(db, episode_id, "poll_nblm", "ok")
            await _set_episode_status(db, episode_id, "downloading")

            # Step 4a: download (already done above)
            await _log_job(db, episode_id, "download", "ok")

            # Step 4b: dash → mp3
            await _log_job(db, episode_id, "convert", "in_progress")
            await dash_to_mp3.convert(dash_path, interm)
            await _log_job(db, episode_id, "convert", "ok")

            # Step 4c: loudness normalize
            await _log_job(db, episode_id, "normalize", "in_progress")
            await audio_post.normalize_loudness(interm, final)
            duration = await audio_post.probe_duration_seconds(final)
            size = final.stat().st_size
            await _log_job(db, episode_id, "normalize", "ok",
                           detail=f"duration={duration}s, size={size}")

            # Step 5: upload to storage
            await _log_job(db, episode_id, "upload", "in_progress")
            await r2.upload_bytes(final.read_bytes(), audio_key, "audio/mpeg")
            async with db.cursor() as cur:
                await cur.execute(
                    "UPDATE episodes SET audio_size_bytes=?, duration_seconds=?, status='ready' WHERE id=?",
                    (size, duration, episode_id),
                )
            await _log_job(db, episode_id, "upload", "ok")

        # Step 6: regenerate RSS
        await _log_job(db, episode_id, "rss", "in_progress")
        await rss.regenerate(db, podcast)
        async with db.cursor() as cur:
            await cur.execute("UPDATE episodes SET published_at=? WHERE id=?",
                              (datetime.now(timezone.utc).isoformat(), episode_id))
        await _log_job(db, episode_id, "rss", "ok")

    except Exception as e:
        log.exception("intake failed for episode %s", episode_id)
        await _set_episode_status(db, episode_id, "failed", error=str(e)[:500])
        async with db.cursor() as cur:
            await cur.execute(
                "UPDATE podcast_jobs SET status='error', finished_at=?, detail=? "
                "WHERE episode_id=? AND finished_at IS NULL",
                (datetime.now(timezone.utc).isoformat(), str(e)[:500], episode_id),
            )
        raise

    return episode_id
