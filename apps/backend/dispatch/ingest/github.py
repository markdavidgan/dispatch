"""GitHub ingest — PRs (opened/merged), issues, releases.

Uses per-source cursors to avoid re-fetching unchanged data on every run.
"""
import os
from datetime import datetime, timezone
import httpx
from core.db import Database

API = "https://api.github.com"
SOURCE = "github"


def _client() -> httpx.AsyncClient:
    """GitHub HTTP client.

    GITHUB_TOKEN is optional. Without it, the unauthenticated GitHub REST
    API is used (60 requests/hour limit per IP). For continuous ingestion
    against more than a couple of repos, set a personal access token via
    the admin Settings page or the GITHUB_TOKEN environment variable.
    """
    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return httpx.AsyncClient(base_url=API, headers=headers, timeout=30.0)


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


async def _insert_event(cur, slug, kind, ext_id, title, author, url, when, body=None):
    now = datetime.now(timezone.utc).isoformat()
    await cur.execute(
        """INSERT OR IGNORE INTO events
           (project_slug, kind, external_id, title, author, url, occurred_at, ingested_at, body)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (slug, kind, str(ext_id), title[:200] if title else None,
         author, url, when, now, body),
    )
    return cur.rowcount or 0


async def ingest_repo(db: Database, slug: str, repo: str) -> int:
    """Pull PRs, issues, releases for one repo. Returns total events inserted."""
    inserted = 0
    latest_seen = "1970-01-01T00:00:00Z"
    cursor_val = await _get_cursor(db, slug, SOURCE)
    since = cursor_val or latest_seen

    async with _client() as gh, db.cursor() as cur:
        # PRs — capture both opened and merged states
        r = await gh.get(
            f"/repos/{repo}/pulls",
            params={"state": "all", "per_page": 50, "sort": "updated", "direction": "desc"},
        )
        r.raise_for_status()
        for pr in r.json():
            if pr["updated_at"] < since:
                continue
            inserted += await _insert_event(
                cur, slug, "pr_opened", pr["number"], pr["title"],
                pr["user"]["login"], pr["html_url"], pr["created_at"],
            )
            if pr.get("merged_at"):
                inserted += await _insert_event(
                    cur, slug, "pr_merged", pr["number"], pr["title"],
                    pr["user"]["login"], pr["html_url"], pr["merged_at"],
                )
            if pr["updated_at"] > latest_seen:
                latest_seen = pr["updated_at"]

        # Issues — exclude PRs (which also appear in /issues)
        r = await gh.get(
            f"/repos/{repo}/issues",
            params={"state": "all", "per_page": 50, "sort": "updated", "direction": "desc"},
        )
        r.raise_for_status()
        for iss in r.json():
            if "pull_request" in iss:
                continue
            if iss["updated_at"] < since:
                continue
            inserted += await _insert_event(
                cur, slug, "issue_opened", iss["number"], iss["title"],
                iss["user"]["login"], iss["html_url"], iss["created_at"],
            )
            if iss.get("closed_at"):
                inserted += await _insert_event(
                    cur, slug, "issue_closed", iss["number"], iss["title"],
                    iss["user"]["login"], iss["html_url"], iss["closed_at"],
                )
            if iss["updated_at"] > latest_seen:
                latest_seen = iss["updated_at"]

        # Releases
        r = await gh.get(
            f"/repos/{repo}/releases",
            params={"per_page": 20},
        )
        r.raise_for_status()
        for rel in r.json():
            if rel["published_at"] < since:
                continue
            inserted += await _insert_event(
                cur, slug, "release", rel["id"], rel["name"] or rel["tag_name"],
                rel["author"]["login"], rel["html_url"], rel["published_at"],
                body=rel.get("body"),
            )
            if rel["published_at"] > latest_seen:
                latest_seen = rel["published_at"]

    await _set_cursor(db, slug, SOURCE, latest_seen)
    return inserted
