#!/usr/bin/env python3
"""
Resume podcast episode 001 from poll/download step.
The artifact was already uploaded to NotebookLM; we just need to
poll until ready, then download/convert/normalize/upload/RSS.
"""
import asyncio
import logging
import tempfile
from pathlib import Path

from core.db import Database
from dispatch.podcast import notebooklm_wrapper, dash_to_mp3, audio_post, rss
from dispatch.podcast.registry import enabled_podcasts, load_podcasts
from dispatch.settings_store import SettingsStore
from dispatch.crypto import Crypto
from core.config import get_settings
from dispatch.publish import r2 as r2_compat
from dispatch.storage import get_storage_backend

logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger(__name__)

DB_PATH = "/data/dispatch.db"


async def main():
    db = Database(DB_PATH)
    await db.connect()

    crypto = Crypto(get_settings().master_key)
    storage = await get_storage_backend(db, crypto)
    r2_compat.set_storage_backend(storage)

    async with db.cursor() as cur:
        await cur.execute(
            "SELECT id, status, notebooklm_artifact_id, audio_key, project_slug, "
            "       episode_no, title, description, source_markdown "
            "FROM episodes WHERE week_start='2026-05-13'"
        )
        row = await cur.fetchone()

    if not row:
        log.error("No episode found for week of 2026-05-13")
        await db.close()
        return

    episode_id, status, artifact_id, audio_key, project_slug, episode_no, title, description, source_md = row
    log.info("Episode %s status=%s artifact=%s", episode_id, status, artifact_id)

    if status == "ready":
        log.info("Episode already ready — nothing to do")
        await db.close()
        return

    if not artifact_id:
        log.error("No artifact_id — cannot recover")
        await db.close()
        return

    podcasts = {p.project_slug: p for p in load_podcasts(Path("/app/dispatch/projects.yml"))}
    podcast = podcasts.get(project_slug)
    if not podcast:
        log.error("No podcast config for %s", project_slug)
        await db.close()
        return

    store = SettingsStore(db, crypto)
    nblm_session = await store.notebooklm_session()
    if not nblm_session:
        log.error("NotebookLM session not configured")
        await db.close()
        return

    try:
        with tempfile.TemporaryDirectory() as td:
            tdp = Path(td)
            dash_path = tdp / "audio.dash"
            interm = tdp / "audio.mp3"
            final = tdp / "final.mp3"

            # Poll + download (will wait up to 4h if not ready yet)
            log.info("Polling NotebookLM for artifact %s...", artifact_id)
            await notebooklm_wrapper.wait_and_download(
                notebook_title=podcast.title,
                artifact_id=artifact_id,
                dest=dash_path,
                storage_state=nblm_session,
            )
            log.info("Downloaded")

            # Convert
            await dash_to_mp3.convert(dash_path, interm)
            log.info("Converted dash→mp3")

            # Normalize
            await audio_post.normalize_loudness(interm, final)
            duration = await audio_post.probe_duration_seconds(final)
            size = final.stat().st_size
            log.info("Normalized (%ds, %d bytes)", duration, size)

            # Upload
            url = await storage.upload_bytes(final.read_bytes(), audio_key, "audio/mpeg")
            log.info("Uploaded → %s", url)

            # Update episode
            async with db.cursor() as cur:
                await cur.execute(
                    "UPDATE episodes SET audio_size_bytes=?, duration_seconds=?, "
                    "status='ready', error=NULL, published_at=? WHERE id=?",
                    (size, duration, __import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat(), episode_id)
                )
            log.info("Episode updated")

            # RSS
            await rss.regenerate(db, podcast)
            log.info("RSS regenerated")

    except Exception as e:
        log.error("Recovery failed: %s", e)
        async with db.cursor() as cur:
            await cur.execute(
                "UPDATE episodes SET status='failed', error=? WHERE id=?",
                (str(e)[:500], episode_id)
            )

    await db.close()
    log.info("Done")


if __name__ == "__main__":
    asyncio.run(main())
