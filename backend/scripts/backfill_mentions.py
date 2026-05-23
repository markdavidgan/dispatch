"""One-time backfill: re-extract mentions from every snapshot archive
in R2 marklab-media/dispatch/snapshot-archive/*.json.

Run interactively:
    cd apps/backend/dispatch
    PYTHONPATH=.:.. python3 scripts/backfill_mentions.py

Safe to re-run — each per-date extraction REPLACES the row set.
"""
import asyncio
import json
import sys

from core.db import Database
from dispatch.publish.r2 import list_objects, download_bytes
from dispatch.publish.snapshot import _normalize_snapshot
from dispatch.synthesis.mention_extraction import extract_mentions, record_mentions


ARCHIVE_PREFIX = "dispatch/snapshot-archive/"
DB_PATH = "/data/dispatch.db"


async def main():
    db = Database(DB_PATH)
    await db.connect()
    async with db.cursor() as cur:
        await cur.execute(
            "SELECT slug, display_name FROM projects WHERE status IN ('active','held','archived')"
        )
        projects = {row[0]: row[1] for row in await cur.fetchall()}

    result = await list_objects(prefix=ARCHIVE_PREFIX, limit=1000)
    # Cloudflare v4 list-objects can return `result` as either:
    #   • a dict  {"objects": [...], "truncated": bool}  (newer)
    #   • a list  [{...}, {...}]                          (older)
    # publish/r2.list_objects() unwraps the outer envelope; either shape
    # may arrive depending on bucket/API version. Normalize.
    objects = result if isinstance(result, list) else result.get("objects", [])
    print(f"found {len(objects)} archived snapshots", file=sys.stderr)

    # Object key field is `key` in current Cloudflare R2 API; older
    # responses used `name`. Support both.
    def _obj_key(o: dict) -> str:
        return o.get("key") or o.get("name") or ""

    for obj in sorted(objects, key=_obj_key):
        key = _obj_key(obj)
        if not key:
            continue
        date = key.rsplit("/", 1)[-1].removesuffix(".json")
        try:
            data = await download_bytes(key)
            snapshot = _normalize_snapshot(json.loads(data))
        except Exception as exc:
            print(f"  {date}: failed to fetch/parse: {exc}", file=sys.stderr)
            continue

        if not snapshot or "brief" not in snapshot:
            print(f"  {date}: no brief in snapshot", file=sys.stderr)
            continue

        brief = snapshot["brief"]
        text = (brief.get("lead_body") or "") + "\n\n" + "\n\n".join(
            a.get("body", "") for a in (brief.get("addendums") or [])
        )
        mentions = extract_mentions(text, projects)
        await record_mentions(db, briefing_date=date, mentions=mentions)
        print(f"  {date}: {len(mentions)} mentions", file=sys.stderr)

    await db.close()


if __name__ == "__main__":
    asyncio.run(main())
