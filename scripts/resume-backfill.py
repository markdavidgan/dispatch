#!/usr/bin/env python3
"""
Resume the demo backfill after VS Code: crash.

Generates missing briefing audio, publishes the snapshot, and recovers the
podcast episode that failed on final upload (re-downloads from NotebookLM).

Usage (copy into the running backend container):
    docker cp scripts/resume-backfill.py dispatch-backend:/tmp/resume-backfill.py
    docker exec dispatch-backend python3 /tmp/resume-backfill.py
"""
from __future__ import annotations

import asyncio
import logging
import tempfile
from datetime import date, datetime, timezone
from pathlib import Path

from core.db import Database

# Wire the storage backend BEFORE importing modules that call r2.upload_bytes
from dispatch.publish import r2 as r2_compat
from dispatch.storage import get_storage_backend
from dispatch.crypto import Crypto
from core.config import get_settings

# Now safe to import orchestrator / podcast modules
from dispatch import orchestrator
from dispatch.podcast import notebooklm_wrapper, dash_to_mp3, audio_post, rss
from dispatch.podcast.registry import enabled_podcasts, load_podcasts
from dispatch.settings_store import SettingsStore

logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger(__name__)

DB_PATH = "/data/dispatch.db"

# Dates that the original backfill-demo.py targets
BRIEFING_DATES = [
    date(2026, 5, 13),
    date(2026, 5, 14),
    date(2026, 5, 15),
    date(2026, 5, 16),
    date(2026, 5, 17),
    date(2026, 5, 18),
    date(2026, 5, 19),
    date(2026, 5, 21),
    date(2026, 5, 22),
    date(2026, 5, 23),
    date(2026, 5, 24),
    date(2026, 5, 25),
]

PODCAST_WEEK_START = date(2026, 5, 13)
PROJECTS_YML = Path("/app/dispatch/projects.yml")


async def main():
    db = Database(DB_PATH)
    await db.connect()

    # Initialize storage exactly like the running FastAPI server does.
    # This is the piece that was missing when the script was run via
    # `docker exec` without the lifespan setup.
    crypto = Crypto(get_settings().master_key)
    storage = await get_storage_backend(db, crypto)
    r2_compat.set_storage_backend(storage)
    log.info("[storage] backend=%s wired", storage.__class__.__name__)

    # ------------------------------------------------------------------
    # 1. Briefings — audio for dates that are missing it
    # ------------------------------------------------------------------
    async with db.cursor() as cur:
        placeholders = ",".join("?" * len(BRIEFING_DATES))
        await cur.execute(
            f"SELECT date FROM filings WHERE kind='lead' AND audio_url IS NULL "
            f"AND date IN ({placeholders})",
            [d.isoformat() for d in BRIEFING_DATES],
        )
        missing_audio = [row[0] for row in await cur.fetchall()]

    if missing_audio:
        log.info("=== Missing audio for %d briefing dates ===", len(missing_audio))
        for d in missing_audio:
            log.info("▶ audio: %s", d)
            try:
                await orchestrator.run_audio(db, kind="lead", target_date=d)
                log.info("  ✓ audio done")
            except Exception as e:
                log.error("  ✗ audio failed: %s", e)
    else:
        log.info("=== All backfill dates already have audio ===")

    # Publish once after all audio is generated
    log.info("=== Publishing snapshot ===")
    try:
        await orchestrator.run_publish(db)
        log.info("  ✓ published")
    except Exception as e:
        log.error("  ✗ publish failed: %s", e)

    # ------------------------------------------------------------------
    # 2. Podcast — recover episode that failed on upload
    # ------------------------------------------------------------------
    log.info("=== Checking podcast episode ===")
    async with db.cursor() as cur:
        await cur.execute(
            "SELECT id, status, notebooklm_artifact_id, audio_key, "
            "       project_slug, episode_no, title, description, "
            "       audio_size_bytes, duration_seconds "
            "FROM episodes WHERE week_start=?",
            (PODCAST_WEEK_START.isoformat(),),
        )
        row = await cur.fetchone()

    if not row:
        log.info("No podcast episode found for week of %s", PODCAST_WEEK_START)
        # Fall back to running the normal backfill podcast step
        podcasts = enabled_podcasts(PROJECTS_YML)
        if podcasts:
            log.info("Starting fresh podcast episode...")
            from dispatch.podcast import intake
            try:
                ep_id = await intake.run_episode(db, podcasts[0], PODCAST_WEEK_START)
                log.info("  ✓ episode started: %s (NotebookLM ~4h)", ep_id)
            except Exception as e:
                log.error("  ✗ podcast failed: %s", e)
    else:
        (
            episode_id, status, artifact_id, audio_key,
            project_slug, episode_no, title, description,
            audio_size_bytes, duration_seconds,
        ) = row

        log.info(
            "Episode %s status=%s artifact=%s key=%s",
            episode_id, status, artifact_id, audio_key,
        )

        # If the audio file is already downloadable and episode looks healthy, skip
        try:
            await storage.download_bytes(audio_key)
            log.info("  ✓ audio file already exists in storage — nothing to do")
        except Exception:
            if not artifact_id:
                log.error(
                    "  ✗ audio missing and no NotebookLM artifact_id — "
                    "delete the episode row and re-run the backfill"
                )
            else:
                log.info("  ⏳ Re-downloading from NotebookLM and finishing upload...")
                await _recover_podcast_episode(
                    db, storage, episode_id, artifact_id, audio_key,
                    project_slug, episode_no, title, description,
                )

    await db.close()
    log.info("=== Done ===")


async def _recover_podcast_episode(
    db, storage, episode_id, artifact_id, audio_key,
    project_slug, episode_no, title, description,
):
    podcasts = {p.project_slug: p for p in load_podcasts(PROJECTS_YML)}
    podcast = podcasts.get(project_slug)
    if not podcast:
        log.error("  ✗ no podcast config for slug %s", project_slug)
        return

    # NotebookLM session from DB settings
    store = SettingsStore(db, Crypto(get_settings().master_key))
    nblm_session = await store.notebooklm_session()
    if not nblm_session:
        log.error("  ✗ NotebookLM session not configured in /admin/settings")
        return

    try:
        with tempfile.TemporaryDirectory() as td:
            tdp = Path(td)
            dash_path = tdp / "audio.dash"
            interm = tdp / "audio.mp3"
            final = tdp / "final.mp3"

            # Re-download the already-generated audio from NotebookLM
            log.info("  ⏳ NotebookLM download (artifact %s)...", artifact_id)
            await notebooklm_wrapper.wait_and_download(
                notebook_title=podcast.title,
                artifact_id=artifact_id,
                dest=dash_path,
                storage_state=nblm_session,
            )
            log.info("  ✓ downloaded")

            # DASH → MP3
            await dash_to_mp3.convert(dash_path, interm)
            log.info("  ✓ converted")

            # Loudness normalize
            await audio_post.normalize_loudness(interm, final)
            duration = await audio_post.probe_duration_seconds(final)
            size = final.stat().st_size
            log.info("  ✓ normalized (%ds, %d bytes)", duration, size)

            # Upload to configured storage backend
            url = await storage.upload_bytes(final.read_bytes(), audio_key, "audio/mpeg")
            log.info("  ✓ uploaded → %s", url)

            # Update episode row
            async with db.cursor() as cur:
                await cur.execute(
                    "UPDATE episodes SET audio_size_bytes=?, duration_seconds=?, "
                    "status='ready', error=NULL, published_at=? WHERE id=?",
                    (size, duration, datetime.now(timezone.utc).isoformat(), episode_id),
                )
            log.info("  ✓ episode record updated")

            # Regenerate RSS feed
            await rss.regenerate(db, podcast)
            log.info("  ✓ RSS feed regenerated")

    except Exception as e:
        log.error("  ✗ podcast recovery failed: %s", e)
        log.error(
            "    If the NotebookLM artifact expired, delete this episode row "
            "and re-run the backfill (≈4 hour wait for regeneration)."
        )


if __name__ == "__main__":
    asyncio.run(main())
