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
