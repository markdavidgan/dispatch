"""Branch-aware GitHub commit ingest.

Lists all branches for a repo, then fetches commits since the last check
for each branch. Deduplicates across branches (same SHA = same commit).
"""
from __future__ import annotations

import os
from datetime import datetime, timezone

import httpx

from core.db import Database

API = "https://api.github.com"
SOURCE = "github:commits"


def _client() -> httpx.AsyncClient:
    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        raise RuntimeError("GITHUB_TOKEN not set")
    return httpx.AsyncClient(
        base_url=API,
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        },
        timeout=30.0,
    )


async def _get_cursor(db: Database, slug: str, source: str) -> str | None:
    async with db.cursor() as cur:
        await cur.execute(
            "SELECT cursor FROM cursors WHERE project_slug=? AND source=?",
            (slug, source),
        )
        row = await cur.fetchone()
    return row[0] if row else None


async def _set_cursor(db: Database, slug: str, source: str, value: str) -> None:
    now = datetime.now(timezone.utc).isoformat()
    async with db.cursor() as cur:
        await cur.execute(
            """INSERT INTO cursors (project_slug, source, cursor, updated_at)
               VALUES (?, ?, ?, ?)
               ON CONFLICT(project_slug, source) DO UPDATE SET
                   cursor = excluded.cursor,
                   updated_at = excluded.updated_at""",
            (slug, source, value, now),
        )


async def _insert_event(cur, slug, kind, ext_id, title, author, url, when, body=None, meta=None):
    now = datetime.now(timezone.utc).isoformat()
    import json
    await cur.execute(
        """INSERT OR IGNORE INTO events
           (project_slug, kind, external_id, title, author, url, occurred_at, ingested_at, body, meta)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (slug, kind, str(ext_id), title[:200] if title else None,
         author, url, when, now, body, json.dumps(meta) if meta else None),
    )
    return cur.rowcount or 0


async def ingest_commits(db: Database, slug: str, repo: str) -> int:
    """Fetch commits from all active branches. Returns events inserted."""
    inserted = 0
    cursor_val = await _get_cursor(db, slug, SOURCE)
    since = cursor_val or "1970-01-01T00:00:00Z"
    latest_seen = since

    async with _client() as gh, db.cursor() as cur:
        # List branches
        r = await gh.get(f"/repos/{repo}/branches", params={"per_page": 100})
        r.raise_for_status()
        branches = r.json()

        seen_shas: set[str] = set()

        for branch in branches:
            branch_name = branch["name"]
            # Fetch commits for this branch since last check
            r = await gh.get(
                f"/repos/{repo}/commits",
                params={"sha": branch_name, "since": since, "per_page": 100},
            )
            r.raise_for_status()
            commits = r.json()

            for commit in commits:
                sha = commit["sha"]
                if sha in seen_shas:
                    continue
                seen_shas.add(sha)

                commit_time = commit["commit"]["committer"]["date"]
                inserted += await _insert_event(
                    cur, slug, "commit", sha,
                    commit["commit"]["message"].split("\n")[0],
                    commit["commit"]["author"]["name"],
                    commit["html_url"],
                    commit_time,
                    meta={"branch": branch_name, "sha": sha},
                )
                if commit_time > latest_seen:
                    latest_seen = commit_time

    await _set_cursor(db, slug, SOURCE, latest_seen)
    return inserted
