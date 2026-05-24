"""System admin API — setup status, key rotation, backup trigger."""
from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Request
from pydantic import BaseModel

from core.config import get_settings

router = APIRouter(prefix="/admin/system")
log = logging.getLogger(__name__)


class RotateKeyBody(BaseModel):
    old_key: str
    new_key: str


@router.get("/setup-status")
async def setup_status(request: Request) -> dict[str, Any]:
    """Returns configuration status for the setup wizard."""
    store = request.app.state.settings_store
    db = request.app.state.db

    # Check if storage is configured
    storage_provider = await store.get("storage.provider", "")
    has_storage = bool(storage_provider)

    # Check AI provider
    ai_provider = await store.get("ai.provider", "")
    has_ai = bool(ai_provider)

    # Check TTS
    tts_provider = await store.get("tts.provider", "")
    has_tts = bool(tts_provider)

    # Check GitHub token
    gh_token = await store.get("github.global_token", "")
    has_github = bool(gh_token)

    # Check projects
    async with db.cursor() as cur:
        await cur.execute("SELECT COUNT(*) FROM projects")
        row = await cur.fetchone()
    has_projects = (row[0] or 0) > 0

    return {
        "storage": has_storage,
        "ai": has_ai,
        "tts": has_tts,
        "github_token_present": has_github,
        "project_count": row[0] or 0,
        "storage_provider": storage_provider or None,
        "ai_provider": ai_provider or None,
    }


@router.post("/rotate-key")
async def rotate_key(request: Request, body: RotateKeyBody) -> dict[str, Any]:
    """Re-encrypt all settings with a new master key."""
    from dispatch.crypto import Crypto

    db = request.app.state.db
    old_crypto = Crypto(body.old_key)
    new_crypto = Crypto(body.new_key)

    async with db.cursor() as cur:
        await cur.execute("SELECT key, value FROM settings")
        rows = await cur.fetchall()

    rotated = 0
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc).isoformat()
    for key, encrypted in rows:
        try:
            plaintext = old_crypto.decrypt(encrypted)
            new_encrypted = new_crypto.encrypt(plaintext)
        except Exception as e:
            log.warning("rotate-key: failed to decrypt %s: %s", key, e)
            continue
        async with db.cursor() as cur:
            await cur.execute(
                "UPDATE settings SET value = ?, updated_at = ? WHERE key = ?",
                (new_encrypted, now, key),
            )
        rotated += 1

    # Update canary
    from dispatch.system.key_canary import CANARY_PLAINTEXT
    new_canary = new_crypto.encrypt(CANARY_PLAINTEXT)
    async with db.cursor() as cur:
        await cur.execute(
            "UPDATE system SET value = ?, updated_at = ? WHERE key = 'key_canary'",
            (new_canary, now),
        )

    return {"rotated": rotated, "total": len(rows)}


@router.post("/backup-now")
async def backup_now(request: Request) -> dict[str, Any]:
    """Trigger an immediate SQLite backup."""
    from dispatch.system.backup import run_backup

    db = request.app.state.db
    store = request.app.state.settings_store
    try:
        result = await run_backup(db, store)
        return {"status": "ok", "result": result}
    except Exception as e:
        log.exception("backup failed")
        return {"status": "error", "error": str(e)}
