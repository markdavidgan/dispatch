"""DB-backed encrypted settings store.

Replaces environment-variable configuration with a queryable key/value store
where every value is encrypted at rest using Fernet + DISPATCH_MASTER_KEY.
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any

from core.db import Database
from dispatch.crypto import Crypto

log = logging.getLogger(__name__)

# Default schedules to populate on first boot
# Cron expressions are interpreted in the schedule's timezone.
# Default synthesis:lead is 1 AM UTC (GMT).
DEFAULT_SCHEDULES = [
    ("ingest:git", "*/15 * * * *", "UTC"),
    ("ingest:github", "*/30 * * * *", "UTC"),
    ("synthesis:lead", "0 1 * * *", "UTC"),
    ("housekeeping", "30 3 * * *", "UTC"),
    ("synthesis:from_the_desk", "0 23 * * 0", "UTC"),
]


class SettingsStore:
    """Encrypted settings backed by SQLite."""

    def __init__(self, db: Database, crypto: Crypto) -> None:
        self.db = db
        self.crypto = crypto

    # -- Core encrypted settings --

    async def get(self, key: str, default: str | None = None) -> str | None:
        """Get decrypted setting by key. Returns default if not found."""
        async with self.db.cursor() as cur:
            await cur.execute(
                "SELECT value FROM settings WHERE key = ?", (key,)
            )
            row = await cur.fetchone()
        if row is None:
            return default
        return self.crypto.decrypt(row[0])

    async def get_json(self, key: str, default: Any = None) -> Any:
        """Get setting and parse as JSON."""
        raw = await self.get(key)
        if raw is None:
            return default
        return json.loads(raw)

    async def set(self, key: str, value: str) -> None:
        """Encrypt and store a setting."""
        encrypted = self.crypto.encrypt(value)
        now = datetime.now(timezone.utc).isoformat()
        async with self.db.cursor() as cur:
            await cur.execute(
                """INSERT INTO settings (key, value, updated_at)
                   VALUES (?, ?, ?)
                   ON CONFLICT(key) DO UPDATE SET
                       value=excluded.value,
                       updated_at=excluded.updated_at""",
                (key, encrypted, now),
            )

    async def set_json(self, key: str, value: Any) -> None:
        """Store a JSON-serializable value."""
        await self.set(key, json.dumps(value))

    async def delete(self, key: str) -> None:
        async with self.db.cursor() as cur:
            await cur.execute("DELETE FROM settings WHERE key = ?", (key,))

    async def list_keys(self, prefix: str = "") -> list[str]:
        """List setting keys, optionally filtered by prefix."""
        async with self.db.cursor() as cur:
            if prefix:
                await cur.execute(
                    "SELECT key FROM settings WHERE key LIKE ? ORDER BY key",
                    (f"{prefix}%",),
                )
            else:
                await cur.execute("SELECT key FROM settings ORDER BY key")
            return [row[0] for row in await cur.fetchall()]

    async def all_decrypted(self, prefix: str = "") -> dict[str, str]:
        """Return all settings as a decrypted dict."""
        keys = await self.list_keys(prefix)
        result: dict[str, str] = {}
        for k in keys:
            val = await self.get(k)
            if val is not None:
                result[k] = val
        return result

    # -- Bootstrap --

    async def bootstrap_defaults(self) -> None:
        """Populate default schedules if the schedules table is empty."""
        async with self.db.cursor() as cur:
            await cur.execute("SELECT COUNT(*) FROM schedules")
            count = await cur.fetchone()
        if count and count[0] > 0:
            return

        now = datetime.now(timezone.utc).isoformat()
        async with self.db.cursor() as cur:
            for job_name, cron, tz in DEFAULT_SCHEDULES:
                await cur.execute(
                    """INSERT INTO schedules (job_name, cron_expression, timezone, is_enabled, last_run_at, next_run_at)
                       VALUES (?, ?, ?, 1, NULL, NULL)""",
                    (job_name, cron, tz),
                )
        log.info("settings_store: bootstrapped default schedules")

    # -- Convenience accessors for common settings --

    async def ai_provider(self) -> str:
        return await self.get("ai.provider", "anthropic") or "anthropic"

    async def ai_model(self) -> str:
        return await self.get("ai.model", "") or ""

    async def ai_critique_enabled(self) -> bool:
        return (await self.get("ai.critique_enabled", "0")) == "1"

    async def tts_provider(self) -> str:
        return await self.get("tts.provider", "google") or "google"

    async def tts_voice(self) -> str:
        return await self.get("tts.voice", "en-US-Chirp3-HD-Leda") or "en-US-Chirp3-HD-Leda"

    async def github_global_token(self) -> str | None:
        return await self.get("github.global_token")

    async def notebooklm_session(self) -> dict | None:
        return await self.get_json("podcast.notebooklm_session")

    async def notebooklm_status(self) -> str:
        return await self.get("podcast.notebooklm_status", "") or ""

    async def web_allowed_origins(self) -> list[str]:
        raw = await self.get("web.allowed_origins")
        if raw:
            return json.loads(raw)
        return []

    async def snapshot_public(self) -> bool:
        return (await self.get("snapshot.public", "1")) == "1"

    # -- CORS helper --

    async def cors_origins(self) -> list[str]:
        """Return CORS origins from settings, with sensible dev defaults."""
        origins = await self.web_allowed_origins()
        if not origins:
            # Dev default
            return ["http://localhost:5173", "http://127.0.0.1:5173"]
        return origins
