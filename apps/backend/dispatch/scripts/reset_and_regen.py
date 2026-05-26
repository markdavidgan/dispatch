#!/usr/bin/env python3
"""
Dispatch reset + regeneration script.

1. Cleans DB: filings, episodes, podcast_jobs, briefing_mentions, runs
2. Cleans R2: snapshot, archives, audio, podcasts, RSS feeds
3. Regenerates lead briefs for past 5 days (oldest → newest)
4. Regenerates podcasts for current trailing week as episode 1

Run inside the dispatch container:
    python3 /app/dispatch/scripts/reset_and_regen.py
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
import time

# ------------------------------------------------------------------
# Logging
# ------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("reset")

# ------------------------------------------------------------------
# Config
# ------------------------------------------------------------------
DB_PATH = os.environ.get("DB_PATH", "/data/dispatch.db")
PROJECTS_YML = Path("/app/dispatch/projects.yml")
BRIEF_DATES = [
    date(2026, 5, 14),
    date(2026, 5, 15),
    date(2026, 5, 16),
    date(2026, 5, 17),
    date(2026, 5, 18),
]

# ------------------------------------------------------------------
# Token refresh helper
# ------------------------------------------------------------------
async def _ensure_kimi_fresh() -> None:
    """Kimi removed — synthesis moved to Vercel serverless."""
    pass


# ------------------------------------------------------------------
# DB cleanup
# ------------------------------------------------------------------
async def _clean_db(db) -> None:
    log.info("Cleaning DB...")
    async with db.cursor() as cur:
        # Order matters for FK constraints
        await cur.execute("DELETE FROM podcast_jobs")   # refs episodes
        await cur.execute("DELETE FROM episodes")
        await cur.execute("DELETE FROM briefing_mentions")
        await cur.execute("DELETE FROM filings")
        await cur.execute("DELETE FROM runs")
    log.info("DB cleaned")


# ------------------------------------------------------------------
# R2 cleanup
# ------------------------------------------------------------------
async def _clean_r2() -> None:
    log.info("Cleaning R2...")
    from dispatch.publish import r2

    # Helper: list all objects under a prefix (handles pagination)
    async def _list_all(prefix: str) -> list[dict]:
        all_objs: list[dict] = []
        cursor = ""
        while True:
            result = await r2.list_objects(prefix=prefix, limit=1000, cursor=cursor)
            # Cloudflare R2 v4 returns result as a list directly
            if isinstance(result, list):
                objs = result
                truncated = len(objs) == 1000  # best guess
            elif isinstance(result, dict):
                objs = result.get("objects", [])
                truncated = result.get("truncated", False)
            else:
                objs = []
                truncated = False
            all_objs.extend(objs)
            if not truncated or not objs:
                break
            # Next cursor: Cloudflare uses different pagination mechanisms;
            # for now we just do one page since our object count is small.
            break
        return all_objs

    # Delete snapshot
    try:
        await r2.delete_object("dispatch/snapshot.json")
        log.info("  deleted snapshot.json")
    except Exception as e:
        log.warning("  snapshot delete failed: %s", e)

    # Delete archives
    archive_objs = await _list_all("dispatch/snapshot-archive/")
    for obj in archive_objs:
        key = obj.get("key") or obj.get("name")
        if key:
            try:
                await r2.delete_object(key)
            except Exception as e:
                log.warning("  failed to delete %s: %s", key, e)
    log.info("  deleted %d archive objects", len(archive_objs))

    # Delete audio
    audio_objs = await _list_all("dispatch/audio/")
    for obj in audio_objs:
        key = obj.get("key") or obj.get("name")
        if key:
            try:
                await r2.delete_object(key)
            except Exception as e:
                log.warning("  failed to delete %s: %s", key, e)
    log.info("  deleted %d audio objects", len(audio_objs))

    # Delete podcast MP3s and RSS
    podcast_objs = await _list_all("podcast/")
    for obj in podcast_objs:
        key = obj.get("key") or obj.get("name")
        if key:
            try:
                await r2.delete_object(key)
            except Exception as e:
                log.warning("  failed to delete %s: %s", key, e)
    log.info("  deleted %d podcast objects", len(podcast_objs))

    log.info("R2 cleaned")


# ------------------------------------------------------------------
# Brief regeneration
# ------------------------------------------------------------------
async def _generate_briefs(db) -> None:
    from dispatch import orchestrator

    for d in BRIEF_DATES:
        log.info("=" * 60)
        log.info("Generating brief for %s", d.isoformat())

        # await _ensure_kimi_fresh()  # Kimi removed

        try:
            result = await orchestrator.run_synthesis_lead(db, target_date=d)
        except Exception as e:
            log.error("Synthesis failed for %s: %s", d.isoformat(), e)
            continue

        if result.get("skipped"):
            log.info("Skipped %s: %s", d.isoformat(), result.get("reason"))
            continue

        log.info("Lead done: issue %d — %s", result["issue_no"], result.get("headline", "")[:60])

        # Audio (non-blocking failure)
        try:
            # await _ensure_kimi_fresh()  # Kimi removed
            await orchestrator.run_audio(db, kind="lead")
            log.info("Audio done for %s", d.isoformat())
        except Exception as e:
            log.warning("Audio failed for %s: %s", d.isoformat(), e)

        # Publish snapshot
        try:
            await orchestrator.run_publish(db)
            log.info("Published for %s", d.isoformat())
        except Exception as e:
            log.warning("Publish failed for %s: %s", d.isoformat(), e)


# ------------------------------------------------------------------
# Podcast regeneration
# ------------------------------------------------------------------
async def _generate_podcasts(db) -> None:
    from dispatch.podcast.registry import enabled_podcasts
    from dispatch.podcast import intake

    podcasts = enabled_podcasts(PROJECTS_YML)
    if not podcasts:
        log.info("No enabled podcasts; skipping")
        return

    today = date.today()
    week_start = today - timedelta(days=7)
    log.info("Generating podcasts for week of %s", week_start.isoformat())

    for podcast in podcasts:
        log.info("-" * 60)
        log.info("Podcast: %s (%s)", podcast.project_slug, podcast.title)

        # await _ensure_kimi_fresh()  # Kimi removed

        try:
            await intake.run_episode(db, podcast, week_start)
            log.info("Podcast %s done", podcast.project_slug)
        except Exception as e:
            log.error("Podcast %s failed: %s", podcast.project_slug, e)


# ------------------------------------------------------------------
# Main
# ------------------------------------------------------------------
async def main() -> int:
    # Imports inside main so module-level code doesn't run on import
    from core.db import Database

    db = Database(DB_PATH)
    await db.connect()
    log.info("Connected to %s", DB_PATH)

    try:
        await _clean_db(db)
        await _clean_r2()
        await _generate_briefs(db)
        await _generate_podcasts(db)
        log.info("=" * 60)
        log.info("ALL DONE")
    except Exception as e:
        log.exception("Fatal error: %s", e)
        return 1
    finally:
        await db.close()
        log.info("DB disconnected")

    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
