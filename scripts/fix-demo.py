#!/usr/bin/env python3
"""
Fix the demo after removing dispatch from projects.yml.
- Wipes all filings, podcast episodes, jobs, mentions
- Wipes local media
- Re-synthesizes May 10-27 in chronological order (sequential issue numbers)
- Generates audio + publishes + podcast
"""
from __future__ import annotations

import asyncio
import logging
import shutil
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

DEMO_DATES = [
    date(2026, 5, 10), date(2026, 5, 11), date(2026, 5, 12),
    date(2026, 5, 13), date(2026, 5, 14), date(2026, 5, 15),
    date(2026, 5, 16), date(2026, 5, 17), date(2026, 5, 18),
    date(2026, 5, 19), date(2026, 5, 20), date(2026, 5, 21),
    date(2026, 5, 22), date(2026, 5, 23), date(2026, 5, 24),
    date(2026, 5, 25), date(2026, 5, 26), date(2026, 5, 27),
]

PODCAST_WEEK_START = date(2026, 5, 13)


async def main():
    db = Database(DB_PATH)
    await db.connect()

    # Wire storage backend
    crypto = Crypto(get_settings().master_key)
    storage = await get_storage_backend(db, crypto)
    r2_compat.set_storage_backend(storage)
    log.info("[storage] backend=%s wired", storage.__class__.__name__)

    # 1. Wipe everything
    log.info("=== Wiping filings, podcasts, mentions, media ===")
    async with db.cursor() as cur:
        await cur.execute("DELETE FROM filings")
        await cur.execute("DELETE FROM podcast_jobs")
        await cur.execute("DELETE FROM episodes")
        await cur.execute("DELETE FROM briefing_mentions")
    media_root = Path("/data/media")
    if media_root.exists():
        shutil.rmtree(media_root)
    log.info("  ✓ wiped")

    # 2. Re-synthesize in chronological order
    log.info("=== Re-synthesizing %d dates (chronological) ===", len(DEMO_DATES))
    synthesized = []
    for d in DEMO_DATES:
        result = await orchestrator.run_synthesis_lead(db, target_date=d)
        if result.get("skipped"):
            log.info("  ⚠ %s — skipped (%s)", d.isoformat(), result.get("reason"))
        else:
            log.info("  ✓ %s — issue #%s", d.isoformat(), result.get("issue_no"))
            synthesized.append(d.isoformat())

    # 3. Audio for all synthesized dates
    log.info("=== Generating audio ===")
    for d in synthesized:
        try:
            await orchestrator.run_audio(db, kind="lead", target_date=d)
            log.info("  ✓ audio: %s", d)
        except Exception as e:
            log.error("  ✗ audio %s: %s", d, e)

    # 4. Publish
    log.info("=== Publishing snapshot ===")
    try:
        await orchestrator.run_publish(db)
        log.info("  ✓ published")
    except Exception as e:
        log.error("  ✗ publish: %s", e)

    # 5. Podcast
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
