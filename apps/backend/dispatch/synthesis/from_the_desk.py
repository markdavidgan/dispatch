"""Weekly auto-summary per active+held project. Sunday 23:00 local.

Per spec §4.4: projects with <2 events in the window short-circuit to the
literal 'Quiet this week.' string — no LLM call. This saves cost and
avoids hallucinated filler when there's genuinely nothing to summarize.
"""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from typing import Iterable

from dispatch.synthesis.kimi import KimiCLISynthesizer

log = logging.getLogger(__name__)

_QUIET_FALLBACK = "Quiet this week."
_QUIET_THRESHOLD = 2


def _build_prompt(display_name: str, events: list[dict]) -> str:
    """Build a weekly-summary prompt for the given project and events."""
    lines = [f"Weekly summary for {display_name}", ""]
    for ev in events:
        kind = ev.get("kind", "event")
        title = ev.get("title", "")
        lines.append(f"- [{kind}] {title}")
    lines.append("")
    lines.append("Write a concise 2-3 sentence summary of this week's activity.")
    return "\n".join(lines)


async def generate_from_the_desk(
    *,
    project_slug: str,
    display_name: str,
    events: Iterable[dict],
) -> dict:
    """Return {body: str, generated_at: iso8601-utc}.

    Caller persists the result; this function is pure compute (one Kimi
    call OR the quiet fallback). See B5 for snapshot persistence.
    """
    event_list = list(events)
    now = datetime.now(timezone.utc).isoformat()

    if len(event_list) < _QUIET_THRESHOLD:
        return {"body": _QUIET_FALLBACK, "generated_at": now}

    prompt = _build_prompt(display_name, event_list)
    synth = KimiCLISynthesizer()
    try:
        body = await synth.generate(prompt)
    except Exception as exc:
        log.error("from_the_desk synthesis failed for %s: %s", project_slug, exc)
        raise
    return {"body": body.strip(), "generated_at": now}
