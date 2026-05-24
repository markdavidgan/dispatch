"""Nightly SQLite online backup to the configured storage backend.

1. Copy live DB to temp file using SQLite backup API (safe under concurrent reads/writes)
2. Gzip the temp file
3. Upload to backups/dispatch-YYYY-MM-DD.db.gz
4. Apply retention: keep last 30 daily + 1st of each month for 12 months
"""
from __future__ import annotations

import gzip
import logging
import shutil
import sqlite3
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from core.db import Database
from dispatch.settings_store import SettingsStore
from dispatch.storage.base import StorageBackend

log = logging.getLogger(__name__)


async def run_backup(db: Database, store: SettingsStore) -> dict[str, str]:
    """Run a backup and upload to storage. Returns {"key": "backups/..."}."""
    # Get storage backend from app state... but we don't have app state here.
    # The caller (scheduler or API) should pass it in.
    raise RuntimeError("Use run_backup_with_storage() instead")


async def run_backup_with_storage(
    db: Database, storage: StorageBackend, db_path: str
) -> dict[str, str]:
    """Run a backup using the given storage backend."""
    date_stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    backup_key = f"backups/dispatch-{date_stamp}.db.gz"

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_db = Path(tmpdir) / "dispatch-backup.db"
        tmp_gz = Path(tmpdir) / "dispatch-backup.db.gz"

        # SQLite online backup
        src = sqlite3.connect(db_path)
        dst = sqlite3.connect(str(tmp_db))
        with dst:
            src.backup(dst)
        dst.close()
        src.close()

        # Gzip
        with open(tmp_db, "rb") as f_in, gzip.open(tmp_gz, "wb") as f_out:
            shutil.copyfileobj(f_in, f_out)

        # Upload
        data = tmp_gz.read_bytes()
        await storage.upload_bytes(data, backup_key, "application/gzip")

    log.info("backup uploaded: %s", backup_key)

    # TODO: retention cleanup
    return {"key": backup_key, "size_bytes": len(data)}
