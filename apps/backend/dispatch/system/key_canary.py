"""Master-key validation via a canary stored in the database.

On first boot: write an encrypted canary.
On subsequent boots: decrypt the existing canary; if it fails, refuse to boot.
This prevents the silent failure mode where a wrong key would encrypt new
settings while old settings remain unreadable.
"""
from __future__ import annotations

import logging

from core.db import Database
from dispatch.crypto import Crypto

log = logging.getLogger(__name__)
CANARY_KEY = "key_canary"
CANARY_PLAINTEXT = "dispatch-canary-v1"


async def validate_or_create(db: Database, crypto: Crypto) -> None:
    """Validate the master key against the DB canary, or create one on first boot."""
    async with db.cursor() as cur:
        await cur.execute(
            "SELECT value FROM system WHERE key = ?", (CANARY_KEY,)
        )
        row = await cur.fetchone()

    if row is None:
        # First boot — write the canary
        encrypted = crypto.encrypt(CANARY_PLAINTEXT)
        from datetime import datetime, timezone
        now = datetime.now(timezone.utc).isoformat()
        async with db.cursor() as cur:
            await cur.execute(
                "INSERT INTO system (key, value, updated_at) VALUES (?, ?, ?)",
                (CANARY_KEY, encrypted, now),
            )
        log.info("key_canary: created on first boot")
        return

    try:
        decrypted = crypto.decrypt(row[0])
    except Exception as exc:
        raise RuntimeError(
            "MASTER_KEY_MISMATCH: settings in this database were encrypted with "
            "a different DISPATCH_MASTER_KEY. If you have the old key, set "
            "DISPATCH_MASTER_KEY_OLD=<old> and DISPATCH_MASTER_KEY=<new>, then "
            "hit POST /api/admin/system/rotate-key. If you intentionally want "
            "to start fresh, delete or rename the database file."
        ) from exc

    if decrypted != CANARY_PLAINTEXT:
        raise RuntimeError(
            "MASTER_KEY_MISMATCH: canary decryption succeeded but payload "
            "does not match expected value. The database may be corrupted."
        )

    log.debug("key_canary: validated")
