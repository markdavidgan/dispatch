"""Post-synthesis pass: find project name mentions in the lead/addendum
body and record one row per mention to `briefing_mentions`.

Pure regex + registry lookup; no LLM call. Called from the orchestrator
immediately after a successful `synthesis:lead` or `synthesis:addendum`.
"""
from __future__ import annotations

import re
from typing import Iterable, Mapping

from core.db import Database


def _titleize_slug(slug: str) -> str:
    """Convert a kebab/underscore slug into a title-cased phrase."""
    tokens = re.split(r"[-_]+", slug)
    return " ".join(t[:1].upper() + t[1:] for t in tokens if t)


def _split_sentences(text: str) -> list[str]:
    """Split prose into sentences. Simple regex split on `. `, `! `, `? `
    boundaries; good enough for editorial prose. Preserves trailing
    punctuation on the sentence."""
    parts = re.split(r"(?<=[.!?])\s+", text.strip())
    return [p for p in parts if p]


def extract_mentions(
    text: str,
    projects: Mapping[str, str],
) -> list[dict]:
    """Return list of mention dicts: {project_slug, excerpt, position}.

    `projects` is a {slug -> display_name} map. Matches are case-insensitive
    against display_name. Each (sentence, project) pair records at most one
    mention; position increments across the whole text.

    When multiple display names match in the same sentence, the longest
    one wins — so 'Made with Aether' is preferred over the bare 'Aether'.
    """
    if not text or not projects:
        return []

    # Build (display_name, slug) list, longest display first.
    # Also include titleized-slug aliases so briefings that use the slug
    # form (e.g. "Bellegan" instead of "Belle Gan") are still matched.
    by_name = sorted(
        ((display, slug) for slug, display in projects.items()),
        key=lambda kv: -len(kv[0]),
    )
    seen_displays = {display.lower() for display, _ in by_name}
    for slug, display in projects.items():
        titleized = _titleize_slug(slug)
        if titleized.lower() not in seen_displays:
            by_name.append((titleized, slug))
    by_name.sort(key=lambda kv: -len(kv[0]))

    out: list[dict] = []
    pos = 0
    for sentence in _split_sentences(text):
        seen_in_sentence: set[str] = set()
        # Track which character spans have already been consumed by a
        # longer match so we don't also record the shorter sub-match.
        consumed_spans: list[tuple[int, int]] = []
        for display, slug in by_name:
            if slug in seen_in_sentence:
                continue
            # Word-boundary match prevents false positives like "AGOS"
            # matching inside "Pagos". `re.escape` handles display names
            # with regex metachars (e.g. "mark.id"). Lookarounds avoid
            # \b's quirks with non-word first/last chars in the display name.
            pattern = rf"(?<!\w){re.escape(display)}(?!\w)"
            m = re.search(pattern, sentence, re.IGNORECASE)
            if not m:
                continue
            span = (m.start(), m.end())
            if any(s <= span[0] < e or s < span[1] <= e for s, e in consumed_spans):
                continue
            out.append({
                "project_slug": slug,
                "excerpt": sentence,
                "position": pos,
            })
            seen_in_sentence.add(slug)
            consumed_spans.append(span)
            pos += 1
    return out


async def record_mentions(
    db: Database,
    briefing_date: str,
    mentions: Iterable[dict],
) -> None:
    """Replace all mentions for `briefing_date` with the given list.

    Idempotent: re-runs (e.g. addendum filed after lead) replace the row
    set on each call. Caller is responsible for passing the canonical
    combined-text mention set; mention_extraction at the orchestrator
    layer combines lead+addendum text before extracting.
    """
    async with db.cursor() as cur:
        await cur.execute(
            "DELETE FROM briefing_mentions WHERE briefing_date = ?",
            (briefing_date,),
        )
        rows = [
            (briefing_date, m["project_slug"], m["excerpt"], m["position"])
            for m in mentions
        ]
        if rows:
            await cur.executemany(
                "INSERT INTO briefing_mentions "
                "(briefing_date, project_slug, excerpt, position) VALUES (?, ?, ?, ?)",
                rows,
            )
