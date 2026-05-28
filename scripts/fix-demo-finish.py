#!/usr/bin/env python3
"""
Finish fix-demo after rate-limit pause.
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

REMAINING = [date(2026, 5, 26), date(2026, 5, 27)]
PODCAST_WEEK_START = date(2026, 5, 13)


async def main():
    db = Database(DB_PATH)
    await db.connect()

    crypto = Crypto(get_settings().master_key)
    storage = await get_storage_backend(db, crypto)
    r2_compat.set_storage_backend(storage)

    # 1. Synthesize remaining dates with delay to avoid rate limits
    for d in REMAINING:
        await asyncio.sleep(5)
        result = await orchestrator.run_synthesis_lead(db, target_date=d)
        if result.get("skipped"):
            log.info("  ⚠ %s — skipped (%s)", d.isoformat(), result.get("reason"))
        else:
            log.info("  ✓ %s — issue #%s", d.isoformat(), result.get("issue_no"))

    # 2. Audio for ALL leads
    async with db.cursor() as cur:
        await cur.execute("SELECT date FROM filings WHERE kind='lead' ORDER BY date")
        dates = [row[0] for row in await cur.fetchall()]

    log.info("=== Generating audio for %d dates ===", len(dates))
    for d in dates:
        try:
            await orchestrator.run_audio(db, kind="lead", target_date=d)
            log.info("  ✓ audio: %s", d)
        except Exception as e:
            log.error("  ✗ audio %s: %s", d, e)

    # 3. Publish
    log.info("=== Publishing ===")
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
                log.info("  ✓ episode: %s", ep_id)
            else:
                log.info("  ⚠ skipped")
        except Exception as e:
            log.error("  ✗ podcast: %s", e)

    await db.close()
    log.info("=== Done ===")


if __name__ == "__main__":
    asyncio.run(main())
