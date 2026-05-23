"""Live data endpoint — returns current project stats.

Protected by Cloudflare Access (service token or JWT)."""
from fastapi import APIRouter, Request, Depends
from datetime import datetime, timezone

from core.cf_access import verify_cf_access
from core.db import Database

router = APIRouter(prefix="/live", dependencies=[Depends(verify_cf_access)])


@router.get("")
async def live(request: Request) -> dict:
    db: Database = request.app.state.db

    # Aggregate live stats per project
    async with db.cursor() as cur:
        await cur.execute(
            """SELECT project_slug, kind, COUNT(*) as c
               FROM events
               WHERE occurred_at >= date('now', '-7 days')
               GROUP BY project_slug, kind"""
        )
        rows = await cur.fetchall()

    projects: dict[str, dict] = {}
    for slug, kind, count in rows:
        if slug not in projects:
            projects[slug] = {"open_prs": 0, "commits_7d": 0, "last_commit_at": None}
        if kind == "commit":
            projects[slug]["commits_7d"] += count
        elif kind in ("pr_opened",):
            projects[slug]["open_prs"] += count
        elif kind in ("pr_merged", "issue_closed"):
            # Subtract merged/closed from open count as a simple heuristic
            projects[slug]["open_prs"] -= count

    # Clamp open_prs to non-negative
    for slug in projects:
        projects[slug]["open_prs"] = max(0, projects[slug]["open_prs"])

    # Last commit per project
    async with db.cursor() as cur:
        await cur.execute(
            """SELECT project_slug, MAX(occurred_at) FROM events WHERE kind='commit' GROUP BY project_slug"""
        )
        for slug, last_at in await cur.fetchall():
            if slug not in projects:
                projects[slug] = {"open_prs": 0, "commits_7d": 0, "last_commit_at": last_at}
            else:
                projects[slug]["last_commit_at"] = last_at

    return {
        "as_of": datetime.now(timezone.utc).isoformat(),
        "projects": projects,
    }
