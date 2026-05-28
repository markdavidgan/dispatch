#!/usr/bin/env python3
"""
Demo backfill script.

Generates historical daily briefings and a podcast episode so the static
demo has a rich, realistic history.

Usage (inside the backend container):
    python3 /app/scripts/backfill-demo.py

Or from host via docker exec:
    docker exec dispatch-backend python3 /app/scripts/backfill-demo.py
"""
import asyncio
import logging
from datetime import date, timedelta

from core.db import Database
from dispatch import orchestrator
from dispatch.podcast.registry import enabled_podcasts, PodcastConfig
from dispatch.podcast import intake

logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger(__name__)

DB_PATH = "/data/dispatch.db"

# Dates to backfill with lead briefings
# May 13-19: source material for the older podcast episode
# May 21-25: recent history for the demo (plus existing May 26-27 = 7 days)
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

# Podcast week to generate
PODCAST_WEEK_START = date(2026, 5, 13)


async def backfill_briefing(db: Database, target_date: date):
    """Generate lead briefing + audio + publish for one date."""
    log.info("▶ %s — synthesis", target_date.isoformat())
    try:
        result = await orchestrator.run_synthesis_lead(db, target_date=target_date)
        if result.get("skipped"):
            log.info("  ⚠ skipped: %s", result.get("reason"))
            return
        log.info("  ✓ lead generated")
    except Exception as e:
        log.error("  ✗ synthesis failed: %s", e)
        return

    # Audio (optional — non-fatal)
    try:
        await orchestrator.run_audio(db, kind="lead", target_date=target_date.isoformat())
        log.info("  ✓ audio generated")
    except Exception as e:
        log.warning("  ⚠ audio skipped: %s", e)

    # Publish snapshot
    try:
        await orchestrator.run_publish(db)
        log.info("  ✓ published")
    except Exception as e:
        log.warning("  ⚠ publish failed: %s", e)


async def backfill_podcast(db: Database, week_start: date):
    """Generate one podcast episode for the given week."""
    log.info("▶ Podcast — week of %s", week_start.isoformat())

    projects_yml = __import__("pathlib").Path("/app/dispatch/projects.yml")
    podcasts = enabled_podcasts(projects_yml)
    if not podcasts:
        log.warning("  ⚠ no podcasts enabled in projects.yml")
        return

    podcast: PodcastConfig = podcasts[0]

    try:
        episode_id = await intake.run_episode(db, podcast, week_start)
        if episode_id:
            log.info("  ✓ episode started: %s", episode_id)
            log.info("  ⏳ NotebookLM will take ~4 hours to generate audio")
        else:
            log.info("  ⚠ episode skipped (already exists or missing config)")
    except Exception as e:
        log.error("  ✗ podcast failed: %s", e)


async def main():
    db = Database(DB_PATH)
    await db.connect()

    log.info("=== Backfilling %d daily briefings ===", len(BRIEFING_DATES))
    for d in BRIEFING_DATES:
        await backfill_briefing(db, d)

    log.info("=== Backfilling podcast ===")
    await backfill_podcast(db, PODCAST_WEEK_START)

    await db.close()
    log.info("=== Done ===")


if __name__ == "__main__":
    asyncio.run(main())
