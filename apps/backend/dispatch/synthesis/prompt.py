"""Deterministic prompt assembly for the lead + addendum filings."""
import hashlib
import json

LEAD_SYSTEM = """\
You are writing for Dispatch, a private daily editorial brief for a
software engineer who runs a homelab and ships a handful of personal
projects. Apply the `creative-writing` skill at Technical/Journalistic
register (Ars Technica dial), dialed back toward Monocle restraint:
precise, calm, slightly dry. No hype, no "excited to announce", no
clichés. The reader is the engineer himself.
"""

ARTICLE_SYSTEM = """\
You are writing the daily briefing for Dispatch — a private editorial
for a software engineer who runs a homelab and ships a handful of
personal projects. Apply the `creative-writing` skill at
Technical/Journalistic register, Ars Technica dial dialed back toward
Monocle restraint. The reader is the engineer himself; he already
knows the projects exist, so don't re-introduce them. He listens to
this every morning, so it must be short.

## Length

Pick ONE of three modes based on the day's data — match length to
substance, never inflate.

**Digest (default — ~200 words, ~80 seconds aloud).** Two paragraphs.
Use this for ordinary days: feature work, bug fixes, refactors,
incremental progress. Lead with the most consequential movement; walk
the rest in priority order; stop. No closing flourish unless one is
genuinely visible in the data.

**Digest + explainer (~300 words max, ~2 minutes aloud).** Use this
ONLY when a genuinely new concept, technique, or idea shipped today —
something the reader would benefit from a one-paragraph plain-language
explanation of (e.g. "regime gating", "cross-venue divergence
detection", a new architectural pattern). Two short paragraphs of
digest plus one short paragraph that names the concept and explains
what it is and why it matters, in prose, without jargon stacking.
Do NOT trigger this mode for routine work, bug fixes, or restatements
of yesterday's concepts.

**Long-form (~700 words max, ~5 minutes aloud).** Use this when the
day is genuinely busy across several projects AND there's enough
distinct thematic material to support extended prose without padding.
Triggers roughly: four or more projects active, OR a single project
shipped a major release alongside related downstream activity, OR two
or more new concepts arrived the reader would benefit from being
walked through. Structure: open with the headline movement; devote a
focused paragraph to each of the day's distinct narrative threads
(typically 3–5); close with the quietest signal that still matters.
Each paragraph earns its place — if you can cut one without losing
information, cut it. Better a 350-word brief that's tight than a
700-word brief that wanders.

## Style

Cite specific events — "the WebSocket reconnection bug landed in the
trader app", "the threading-and-memory P6 slice merged" — not generic
"made progress". Narrative prose, not bullet points.

Hard rules: no exclamation marks, no second person, no "excited to
announce", no "leverage", no "in today's fast-paced", no bulleted
lists, no headings inside the prose. Sentence rhythm should vary —
don't write three same-shape sentences in a row.
"""

ADDENDUM_SYSTEM = """\
You are writing for Dispatch, a private daily editorial brief. This is
a rolling addendum — a short update filed after the morning lead.
Apply the `creative-writing` skill at Technical/Journalistic register,
Monocle restraint. Report only *new* movement since the lead below.
One or two sentences. Calm, precise, no hype.
"""


def build_article_prompt(
    *,
    issue_no: int,
    date_local: str,
    tz: str,
    covers_from: str,
    covers_until: str,
    projects_input: list[dict],
    events_by_project: dict[str, list[dict]],
) -> tuple[str, str]:
    """Returns (prompt_text, prompt_hash) for the long-form article pass."""

    lines: list[str] = []
    lines.append(ARTICLE_SYSTEM)
    lines.append("")
    lines.append("## Window")
    lines.append(f"- Issue No. {issue_no} — {date_local}")
    lines.append(f"- Covers: {covers_from} → {covers_until} ({tz})")
    lines.append("")
    name_by_slug = {p["slug"]: p["name"] for p in projects_input}
    lines.append("## Projects (input — for orientation)")
    for p in projects_input:
        lines.append(f"- {p['slug']} ({p['name']}) [{p['status']}] bullet={p['bullet']} stat={p['stat']!r}")
    lines.append("")
    lines.append("## Data")
    for slug, events in events_by_project.items():
        if not events:
            continue
        display_name = name_by_slug.get(slug, slug)
        lines.append(f"### {slug} ({display_name})")
        for e in events:
            t = e["occurred_at"].split("T", 1)[1][:5] if "T" in e["occurred_at"] else ""
            lines.append(f"- {t} {e['kind']:>11} {e['title']}")
        lines.append("")

    lines.append("## Output")
    lines.append("Return ONLY a JSON object — no prose around it, no code fences:")
    lines.append(json.dumps({
        "article": (
            "the briefing prose. ~200 words / 2 short paragraphs by default; "
            "up to ~300 words when a genuinely new concept shipped today; "
            "up to ~700 words / 3–5 focused paragraphs on busy multi-project "
            "days with distinct narrative threads (see system message). "
            "Paragraphs separated by blank lines."
        ),
    }, indent=2))

    text = "\n".join(lines)
    h = hashlib.sha256(text.encode()).hexdigest()[:16]
    return text, h


def build_lead_prompt(
    *,
    issue_no: int,
    date_local: str,
    tz: str,
    covers_from: str,
    covers_until: str,
    projects_input: list[dict],
    events_by_project: dict[str, list[dict]],
    article: str | None = None,
    examples: list[dict] | None = None,
) -> tuple[str, str]:
    """Returns (prompt_text, prompt_hash).

    When *article* is provided, the dek must be a faithful summary of the
    article's lede — same facts, no new claims, no fabrication. This is
    the pass-B path in the article-first → dek-second two-pass.
    """

    lines: list[str] = []
    lines.append(LEAD_SYSTEM)
    lines.append("")
    lines.append("## Window")
    lines.append(f"- Issue No. {issue_no} — {date_local}")
    lines.append(f"- Covers: {covers_from} → {covers_until} ({tz})")
    lines.append("")
    name_by_slug = {p["slug"]: p["name"] for p in projects_input}
    lines.append("## Projects (input — bullet already computed)")
    for p in projects_input:
        lines.append(f"- {p['slug']} ({p['name']}) [{p['status']}] bullet={p['bullet']} stat={p['stat']!r}")
    lines.append("")
    if article:
        lines.append("## Article (already written — summarize, don't invent)")
        lines.append("The dek (`lead_body`) must compress this article's opening claim into")
        lines.append("2-3 sentences. The headline must reflect the article's central point.")
        lines.append("Do not introduce facts that are not in the article.")
        lines.append("")
        lines.append(article)
        lines.append("")
    lines.append("## Data")
    for slug, events in events_by_project.items():
        if not events:
            continue
        display_name = name_by_slug.get(slug, slug)
        lines.append(f"### {slug} ({display_name})")
        for e in events:
            t = e["occurred_at"].split("T", 1)[1][:5] if "T" in e["occurred_at"] else ""
            lines.append(f"- {t} {e['kind']:>11} {e['title']}")
        lines.append("")

    lines.append("## Output")
    lines.append("Return ONLY a JSON object matching this schema, no prose, no code fences:")
    lines.append(json.dumps({
        "lead_headline": "string, <=120 chars, sentence case",
        "lead_body": "string, 2-3 sentences, <=280 chars, narrative not bulleted",
        "active_count": "two-digit string like '03'",
        "project_lines": [
            {"slug": "<slug>", "name": "<display name>",
             "status": "active|held", "stat": "<short caps phrase>",
             "bullet": "red|amber|sand"}
        ],
    }, indent=2))

    if examples:
        lines.append("")
        lines.append("## Worked examples (style anchors)")
        for ex in examples:
            lines.append(json.dumps(ex))

    text = "\n".join(lines)
    h = hashlib.sha256(text.encode()).hexdigest()[:16]
    return text, h


def build_addendum_prompt(
    *,
    date_local: str,
    tz: str,
    lead_headline: str,
    lead_body: str,
    projects_input: list[dict],
    events_by_project: dict[str, list[dict]],
) -> tuple[str, str]:
    """Returns (prompt_text, prompt_hash) for a rolling addendum."""

    lines: list[str] = []
    lines.append(ADDENDUM_SYSTEM)
    lines.append("")
    lines.append("## Window")
    lines.append(f"- Date: {date_local} ({tz})")
    lines.append("- This addendum covers movement since the morning lead.")
    lines.append("")
    lines.append("## Morning lead (for context — do not repeat)")
    lines.append(f"Headline: {lead_headline}")
    lines.append(f"Body: {lead_body}")
    lines.append("")
    name_by_slug = {p["slug"]: p["name"] for p in projects_input}
    lines.append("## Projects (current state)")
    for p in projects_input:
        lines.append(f"- {p['slug']} ({p['name']}) [{p['status']}] bullet={p['bullet']} stat={p['stat']!r}")
    lines.append("")
    lines.append("## New data since lead")
    for slug, events in events_by_project.items():
        if not events:
            continue
        display_name = name_by_slug.get(slug, slug)
        lines.append(f"### {slug} ({display_name})")
        for e in events:
            t = e["occurred_at"].split("T", 1)[1][:5] if "T" in e["occurred_at"] else ""
            lines.append(f"- {t} {e['kind']:>11} {e['title']}")
        lines.append("")

    lines.append("## Output")
    lines.append("Return ONLY a JSON object, no prose, no code fences:")
    lines.append(json.dumps({
        "addendum_body": "string, 1-2 sentences, <=200 chars, only new movement",
    }, indent=2))

    text = "\n".join(lines)
    h = hashlib.sha256(text.encode()).hexdigest()[:16]
    return text, h
