"""Compose source markdown for NotebookLM from a project's week of events."""
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import jinja2
from core.db import Database

TEMPLATE_PATH = Path(__file__).parent / "templates" / "source.md.j2"


async def compose(
    db: Database,
    project_slug: str,
    podcast_title: str,
    project_display_name: str,
    week_start: date,
    window_days: int = 7,
    episode_no: int = 1,
) -> str:
    """Return composed markdown for one weekly source."""
    week_end = week_start + timedelta(days=window_days)
    frm = datetime.combine(week_start, datetime.min.time(), tzinfo=timezone.utc).isoformat()
    until = datetime.combine(week_end, datetime.min.time(), tzinfo=timezone.utc).isoformat()

    async with db.cursor() as cur:
        await cur.execute(
            "SELECT kind, title, author, occurred_at "
            "FROM events WHERE project_slug=? AND occurred_at>=? AND occurred_at<? "
            "ORDER BY occurred_at",
            (project_slug, frm, until),
        )
        events = await cur.fetchall()

    # Group by day
    by_day: dict[date, list[dict]] = {}
    for kind, title, author, occurred in events:
        d = datetime.fromisoformat(occurred.replace("Z", "+00:00")).date()
        if (author or "").lower() in ("dependabot[bot]", "renovate[bot]", "github-actions[bot]"):
            continue
        by_day.setdefault(d, []).append({
            "kind": kind, "title": (title or "")[:120], "author": author,
        })

    # All 7 days, even if empty (NotebookLM gets context)
    days = []
    for i in range(window_days):
        d = week_start + timedelta(days=i)
        days.append({
            "date": d.isoformat(),
            "label": d.strftime("%A"),
            "events": by_day.get(d, []),
        })

    env = jinja2.Environment(loader=jinja2.FileSystemLoader(TEMPLATE_PATH.parent),
                             trim_blocks=True, lstrip_blocks=True)
    tpl = env.get_template(TEMPLATE_PATH.name)
    return tpl.render(
        podcast_title=podcast_title,
        project_display_name=project_display_name,
        week_start_label=week_start.strftime("%B %-d, %Y"),
        week_end_label=(week_start + timedelta(days=window_days - 1)).strftime("%B %-d, %Y"),
        days=days,
        episode_count=f"Episode {episode_no}",
    )
