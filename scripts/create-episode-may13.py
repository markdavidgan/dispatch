#!/usr/bin/env python3
"""Create podcast episode 001 for week of May 13, 2026."""
import asyncio
import logging
from datetime import date
from pathlib import Path

from core.db import Database
from dispatch.podcast.registry import enabled_podcasts
from dispatch.podcast import intake
from dispatch.storage import get_storage_backend
from dispatch.crypto import Crypto
from core.config import get_settings
from dispatch.publish import r2 as r2_compat

logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger(__name__)


async def main():
    db = Database("/data/dispatch.db")
    await db.connect()

    crypto = Crypto(get_settings().master_key)
    storage = await get_storage_backend(db, crypto)
    r2_compat.set_storage_backend(storage)

    podcasts = enabled_podcasts(Path("/app/dispatch/projects.yml"))
    if podcasts:
        ep_id = await intake.run_episode(db, podcasts[0], date(2026, 5, 13))
        if ep_id:
            log.info("Created episode: %s", ep_id)
        else:
            log.info("Episode skipped")
    else:
        log.error("No podcasts enabled")

    await db.close()


if __name__ == "__main__":
    asyncio.run(main())
