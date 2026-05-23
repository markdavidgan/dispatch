"""Git ingest — read commits from local repos mounted at /repos/<slug>."""
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from core.db import Database

SOURCE = "git"


async def _get_cursor(db: Database, slug: str) -> str | None:
    async with db.cursor() as cur:
        await cur.execute(
            "SELECT cursor FROM cursors WHERE project_slug=? AND source=?",
            (slug, SOURCE),
        )
        row = await cur.fetchone()
    return row[0] if row else None


async def _set_cursor(db: Database, slug: str, value: str) -> None:
    now = datetime.now(timezone.utc).isoformat()
    async with db.cursor() as cur:
        await cur.execute(
            """INSERT INTO cursors (project_slug, source, cursor, updated_at)
               VALUES (?, ?, ?, ?)
               ON CONFLICT(project_slug, source) DO UPDATE SET
                   cursor = excluded.cursor,
                   updated_at = excluded.updated_at""",
            (slug, SOURCE, value, now),
        )


async def ingest_repo(db: Database, slug: str, path: Path) -> int:
    """Walk new commits since the last cursor; return number inserted."""
    last_sha = await _get_cursor(db, slug)
    rev_range = f"{last_sha}..HEAD" if last_sha else "HEAD"

    # %H sha | %cI iso commit date | %an author | %s subject
    fmt = "%H%x09%cI%x09%an%x09%s"
    result = subprocess.run(
        ["git", "-C", str(path), "log", "--no-merges", "--reverse",
         f"--pretty=format:{fmt}", rev_range],
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        # Empty range or other non-fatal: treat as no-op
        return 0

    lines = [l for l in result.stdout.splitlines() if l.strip()]
    if not lines:
        return 0

    now = datetime.now(timezone.utc).isoformat()
    inserted = 0
    last_seen_sha = None
    async with db.cursor() as cur:
        for line in lines:
            sha, when, author, subject = line.split("\t", 3)
            # Drop bot commits
            if author.lower() in ("dependabot[bot]", "renovate[bot]", "github-actions[bot]"):
                continue
            await cur.execute(
                """INSERT OR IGNORE INTO events
                   (project_slug, kind, external_id, title, author, occurred_at, ingested_at, url)
                   VALUES (?, 'commit', ?, ?, ?, ?, ?, ?)""",
                (slug, sha, subject[:200], author, when, now, None),
            )
            inserted += cur.rowcount or 0
            last_seen_sha = sha

    if last_seen_sha:
        await _set_cursor(db, slug, last_seen_sha)
    return inserted
