"""Pre-prompt event shaping — drop noise, truncate, group by project."""
from typing import Iterable

BOT_AUTHORS = {"dependabot[bot]", "renovate[bot]", "github-actions[bot]"}


def shape_events(events: Iterable[dict]) -> list[dict]:
    """Drop bots; truncate fields; sort by occurred_at."""
    keep = []
    for e in events:
        if (e.get("author") or "").lower() in BOT_AUTHORS:
            continue
        keep.append({
            "project_slug": e["project_slug"],
            "kind": e["kind"],
            "title": (e.get("title") or "")[:80],
            "url": e.get("url"),
            "occurred_at": e["occurred_at"],
        })
    return sorted(keep, key=lambda e: e["occurred_at"])


def group_by_project(events: list[dict]) -> dict[str, list[dict]]:
    out: dict[str, list[dict]] = {}
    for e in events:
        out.setdefault(e["project_slug"], []).append(e)
    return out
