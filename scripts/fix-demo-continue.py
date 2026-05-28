#!/usr/bin/env python3
"""
Continue fix-demo.py after timeout.
Skips wipe — just synthesizes remaining dates + audio + publish + podcast.
"""
from __future__ import annotations

import asyncio
import logging
from datetime import date
from pathlib import Path

from core.db import Database
from dispatch import orchestrator
from dispatch.podcast.registry import enabled_podcasts
from dispatch.podcast import intake
from dispatch.storage import get_storage_backend
from dispatch.crypto import Crypto
from core.config import get_settings
from dispatch.publish import r2 as r2_compat

logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger(__name__)

DB_PATH = "/data/dispatch.db"

REMAINING_DATES = [
    date(2026, 5, 22), date(2026, 5, 23), date(2026, 5, 24),
    date(2026, 5, 25), date(2026, 5, 26), date(2026, 5, 27),
]

PODCAST_WEEK_START = date(2026, 5, 13)


async def main():
    db = Database(DB_PATH)
    await db.connect()

    crypto = Crypto(get_settings().master_key)
    storage = await get_storage_backend(db, crypto)
    r2_compat.set_storage_backend(storage)
    log.info("[storage] backend=%s wired", storage.__class__.__name__)

    # 1. Synthesize remaining dates
    log.info("=== Synthesizing remaining %d dates ===", len(REMAINING_DATES))
    for d in REMAINING_DATES:
        result = await orchestrator.run_synthesis_lead(db, target_date=d)
        if result.get("skipped"):
            log.info("  ⚠ %s — skipped (%s)", d.isoformat(), result.get("reason"))
        else:
            log.info("  ✓ %s — issue #%s", d.isoformat(), result.get("issue_no"))

    # 2. Audio for ALL dates that have leads
    log.info("=== Generating audio ===")
    async with db.cursor() as cur:
        await cur.execute("SELECT date FROM filings WHERE kind='lead' ORDER BY date")
        dates_with_leads = [row[0] for row in await cur.fetchall()]

    log.info("  %d dates to process", len(dates_with_leads))
    for d in dates_with_leads:
        try:
            await orchestrator.run_audio(db, kind="lead", target_date=d)
            log.info("  ✓ audio: %s", d)
        except Exception as e:
            log.error("  ✗ audio %s: %s", d, e)

    # 3. Publish
    log.info("=== Publishing snapshot ===")
    try:
        await orchestrator.run_publish(db)
        log.info("  ✓ published")
    except Exception as e:
        log.error("  ✗ publish: %s", e)

    # 4. Podcast
    log.info("=== Podcast ===")
    podcasts = enabled_podcasts(Path("/app/dispatch/projects.yml"))
    if podcasts:
        try:
            ep_id = await intake.run_episode(db, podcasts[0], PODCAST_WEEK_START)
            if ep_id:
                log.info("  ✓ episode: %s (~4h NotebookLM)", ep_id)
            else:
                log.info("  ⚠ episode skipped")
        except Exception as e:
            log.error("  ✗ podcast: %s", e)

    await db.close()
    log.info("=== Done ===")


if __name__ == "__main__":
    asyncio.run(main())
