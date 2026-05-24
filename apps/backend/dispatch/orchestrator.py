"""Orchestrator — wires ingest → synthesis → publish → audio.

Each public coroutine is idempotent and logs to the `runs` table.
"""
from __future__ import annotations

import json
import logging
import os
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from core.db import Database
from dispatch.registry.loader import load_yaml
from dispatch.ingest import git as git_ingest, github as github_ingest
from dispatch.synthesis.bullets import derive_bullet, derive_active_count
from dispatch.synthesis.prompt import (
    build_article_prompt,
    build_lead_prompt,
    build_addendum_prompt,
)
from dispatch.synthesis.schema import ArticleFiling, LeadFiling, AddendumFiling
from dispatch.synthesis.synthesizer import select_primary
from dispatch.synthesis.kimi import KimiCLISynthesizer
from dispatch.synthesis.anthropic import AnthropicSynthesizer
from dispatch.synthesis.critic import single_pass, two_pass
from dispatch.synthesis.brief_lint import lint_lead
from dispatch.synthesis.mention_extraction import extract_mentions, record_mentions
from dispatch.publish.snapshot import publish_snapshot
from dispatch.audio import generate_brief_audio
from dispatch.publish.r2 import upload_bytes

log = logging.getLogger(__name__)

SETTINGS_PATH = Path(__file__).parent / "projects.yml"
REPOS_ROOT = Path("/repos")


# ------------------------------------------------------------------
# Runs logging
# ------------------------------------------------------------------
async def _log_run(
    db: Database,
    job: str,
    status: str,
    events_added: int = 0,
    error: str | None = None,
    started_at: str | None = None,
) -> None:
    finished_at = datetime.now(timezone.utc).isoformat()
    started = started_at or finished_at
    async with db.cursor() as cur:
        await cur.execute(
            "INSERT INTO runs (job, status, started_at, finished_at, events_added, error) VALUES (?, ?, ?, ?, ?, ?)",
            (job, status, started, finished_at, events_added, error),
        )


# ------------------------------------------------------------------
# Ingest
# ------------------------------------------------------------------
async def run_ingest_git(db: Database) -> int:
    """Ingest commits from all local repos. Returns total events inserted."""
    projects = load_yaml(SETTINGS_PATH)
    total = 0
    failed = 0
    for p in projects["projects"]:
        if not p.get("local_path"):
            continue
        path = Path(p["local_path"])
        if not path.exists():
            log.warning("git ingest: path missing %s", path)
            failed += 1
            continue
        try:
            n = await git_ingest.ingest_repo(db, p["slug"], path)
            total += n
            log.info("git ingest: %s +%d", p["slug"], n)
        except Exception as e:
            failed += 1
            log.exception("git ingest failed for %s", p["slug"])
    status = "ok" if failed == 0 else ("partial" if total > 0 else "error")
    await _log_run(db, "ingest:git", status, events_added=total)
    return total


async def run_ingest_github(db: Database) -> int:
    """Ingest GitHub activity for all projects with a github repo."""
    projects = load_yaml(SETTINGS_PATH)
    total = 0
    failed = 0
    for p in projects["projects"]:
        repo = p.get("github")
        if not repo:
            continue
        try:
            n = await github_ingest.ingest_repo(db, p["slug"], repo)
            total += n
            log.info("github ingest: %s +%d", p["slug"], n)
        except Exception as e:
            failed += 1
            log.exception("github ingest failed for %s", p["slug"])
    status = "ok" if failed == 0 else ("partial" if total > 0 else "error")
    await _log_run(db, "ingest:github", status, events_added=total)
    return total


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------
async def _events_for_window(db: Database, covers_from: str, covers_until: str) -> dict[str, list[dict]]:
    """Fetch events grouped by project for the synthesis window."""
    async with db.cursor() as cur:
        await cur.execute(
            """SELECT project_slug, kind, external_id, title, author, occurred_at, url
               FROM events
               WHERE occurred_at >= ? AND occurred_at <= ?
               ORDER BY occurred_at DESC""",
            (covers_from, covers_until),
        )
        rows = await cur.fetchall()

    by_project: dict[str, list[dict]] = {}
    for row in rows:
        slug = row[0]
        by_project.setdefault(slug, []).append({
            "project_slug": slug,
            "kind": row[1],
            "external_id": row[2],
            "title": row[3],
            "author": row[4],
            "occurred_at": row[5],
            "url": row[6],
        })
    return by_project


async def _project_input(db: Database, events_by_project: dict[str, list[dict]]) -> list[dict]:
    """Build project lines with deterministic bullets."""
    projects = load_yaml(SETTINGS_PATH)
    lines: list[dict] = []
    for p in projects["projects"]:
        if p.get("status") == "archived":
            continue
        evs = events_by_project.get(p["slug"], [])
        bullet = derive_bullet(p["status"], evs)
        stat_parts: list[str] = []
        commits = sum(1 for e in evs if e["kind"] == "commit")
        prs_opened = sum(1 for e in evs if e["kind"] == "pr_opened")
        prs_merged = sum(1 for e in evs if e["kind"] == "pr_merged")
        releases = sum(1 for e in evs if e["kind"] == "release")
        if commits:
            stat_parts.append(f"{commits} commit{'s' if commits != 1 else ''}")
        if prs_opened or prs_merged:
            pr_total = prs_opened + prs_merged
            stat_parts.append(f"{pr_total} PR{'s' if pr_total != 1 else ''}")
        if releases:
            stat_parts.append(f"{releases} release{'s' if releases != 1 else ''}")
        stat = " · ".join(stat_parts) if stat_parts else "Quiet"
        lines.append({
            "slug": p["slug"],
            "name": p["display_name"],
            "status": p["status"],
            "stat": stat,
            "bullet": bullet,
        })
    return lines


async def _refresh_mentions(db: Database, briefing_date: str) -> None:
    """Re-extract project mentions for *briefing_date* from the current
    lead + addendum bodies and replace the row set in `briefing_mentions`.

    Pure registry lookup; safe to call after every successful filing write.
    Idempotent — re-runs replace prior rows, so the addendum pass picks up
    any new project mentions on top of the already-filed lead.
    """
    async with db.cursor() as cur:
        await cur.execute(
            "SELECT slug, display_name FROM projects WHERE status != 'archived'"
        )
        project_rows = await cur.fetchall()
    projects = {row[0]: row[1] for row in project_rows}

    async with db.cursor() as cur:
        await cur.execute(
            "SELECT kind, lead_body, addendum_body FROM filings WHERE date = ? ORDER BY kind",
            (briefing_date,),
        )
        filing_rows = await cur.fetchall()

    parts: list[str] = []
    for kind, lead_body, addendum_body in filing_rows:
        if kind == "lead" and lead_body:
            parts.append(lead_body)
        if kind == "addendum" and addendum_body:
            parts.append(addendum_body)
    combined_text = "\n\n".join(parts)

    mentions = extract_mentions(combined_text, projects)
    await record_mentions(db, briefing_date=briefing_date, mentions=mentions)


async def _next_issue_no(db: Database) -> int:
    async with db.cursor() as cur:
        await cur.execute("SELECT COALESCE(MAX(issue_no), 0) + 1 FROM filings WHERE kind='lead'")
        row = await cur.fetchone()
    return row[0] or 1


# ------------------------------------------------------------------
# Synthesis
# ------------------------------------------------------------------
_USE_CRITIQUE = os.environ.get("DISPATCH_SYNTHESIS_CRITIQUE", "").lower() in ("1", "true", "yes")


async def _synthesize_with_fallback(
    prompt: str, schema: type, provider: str, db: Database | None = None
):
    """Try primary provider, fallback on failure. Returns (result, model_name).

    Uses single-pass by default (fast). Set DISPATCH_SYNTHESIS_CRITIQUE=1
    to enable the slower two-pass self-critique loop.

    Logs failures to the runs table if *db* is provided.
    """
    if provider == "kimi":
        primary = KimiCLISynthesizer()
        fallback = AnthropicSynthesizer()
    else:
        primary = AnthropicSynthesizer()
        fallback = KimiCLISynthesizer()

    synthesizers = [primary, fallback]
    pass_fn = two_pass if _USE_CRITIQUE else single_pass

    for synth in synthesizers:
        try:
            result = await pass_fn(synth, prompt, schema)
            return result, synth.name
        except Exception as e:
            log.warning("synthesizer %s failed: %s", synth.name, e)
            if db is not None:
                await _log_run(
                    db,
                    f"synthesis:{synth.name}",
                    "error",
                    error=str(e)[:500],
                )
            continue

    raise RuntimeError("Both synthesizers failed")


async def run_synthesis_lead(db: Database, target_date: date | None = None) -> dict:
    """Generate the morning lead filing. Returns the filing row as dict.

    If *target_date* is provided, synthesize for that date instead of yesterday.
    """
    tz = os.environ.get("DISPATCH_TZ", "Asia/Manila")
    if target_date is not None:
        date_local = target_date.isoformat()
    else:
        now = datetime.now(timezone.utc)
        # Covers "yesterday" in local tz: 00:00 to 23:59
        date_local = (now.astimezone() - timedelta(days=1)).strftime("%Y-%m-%d")
    covers_from = f"{date_local}T00:00:00+00:00"
    covers_until = f"{date_local}T23:59:59+00:00"

    events = await _events_for_window(db, covers_from, covers_until)

    # Quiet-day skip: if no project moved at all in the window, don't
    # file a briefing and don't burn an issue number. The next active
    # day picks up where this one would have been.
    if not any(events.values()):
        log.info("no events for %s; skipping briefing (issue number preserved)", date_local)
        await _log_run(db, "synthesis:lead", "skipped")
        return {"date": date_local, "skipped": True, "reason": "no events"}

    # Reuse the existing issue number if we're re-synthesizing the same
    # date (e.g. prompt change, post-incident regen). Allocating a fresh
    # number here would create gaps and confuse the index.
    async with db.cursor() as cur:
        await cur.execute(
            "SELECT issue_no FROM filings WHERE date=? AND kind='lead'",
            (date_local,),
        )
        existing = await cur.fetchone()
    issue_no = existing[0] if existing else await _next_issue_no(db)
    projects = await _project_input(db, events)
    active_count = derive_active_count(projects)
    provider = select_primary()

    # Pass A: long-form article (~500 words, Ava reads this aloud).
    article_prompt, article_hash = build_article_prompt(
        issue_no=issue_no,
        date_local=date_local,
        tz=tz,
        covers_from=covers_from,
        covers_until=covers_until,
        projects_input=projects,
        events_by_project=events,
    )
    article_result, _ = await _synthesize_with_fallback(
        article_prompt, ArticleFiling, provider, db
    )
    article_text = article_result.article.strip()

    # Pass B: structured filing (headline + dek summarizing the article +
    # project lines). Passing the article in as context anchors the dek so
    # it can't drift from the long-form prose.
    prompt, prompt_hash = build_lead_prompt(
        issue_no=issue_no,
        date_local=date_local,
        tz=tz,
        covers_from=covers_from,
        covers_until=covers_until,
        projects_input=projects,
        events_by_project=events,
        article=article_text,
        examples=None,
    )

    result, model_name = await _synthesize_with_fallback(prompt, LeadFiling, provider, db)

    # Enforce deterministic active_count
    computed_count = derive_active_count(projects)
    if result.active_count != computed_count:
        log.warning(
            "model active_count %s != computed %s; overriding",
            result.active_count,
            computed_count,
        )
        result.active_count = computed_count

    # Lint (non-blocking)
    warnings = lint_lead(result)
    if warnings:
        log.warning("brief lint warnings: %s", warnings)

    # Persist
    generated_at = datetime.now(timezone.utc).isoformat()
    async with db.cursor() as cur:
        await cur.execute(
            """INSERT INTO filings
               (date, kind, issue_no, covers_from, covers_until, lead_headline, lead_body, lead_article, active_count, project_lines, model, prompt_hash, generated_at, raw_response)
               VALUES (?, 'lead', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
               ON CONFLICT(date, kind) DO UPDATE SET
                   issue_no=excluded.issue_no,
                   covers_from=excluded.covers_from,
                   covers_until=excluded.covers_until,
                   lead_headline=excluded.lead_headline,
                   lead_body=excluded.lead_body,
                   lead_article=excluded.lead_article,
                   active_count=excluded.active_count,
                   project_lines=excluded.project_lines,
                   model=excluded.model,
                   prompt_hash=excluded.prompt_hash,
                   generated_at=excluded.generated_at,
                   raw_response=excluded.raw_response""",
            (
                date_local, issue_no, covers_from, covers_until,
                result.lead_headline, result.lead_body, article_text,
                int(result.active_count),
                json.dumps(result.model_dump(include={"project_lines"})["project_lines"]),
                model_name, prompt_hash, generated_at,
                result.model_dump_json(),
            ),
        )

    await _refresh_mentions(db, date_local)
    await _log_run(db, "synthesis:lead", "ok")
    log.info("synthesis lead done: issue %d via %s", issue_no, model_name)
    return {
        "date": date_local,
        "issue_no": issue_no,
        "headline": result.lead_headline,
        "body": result.lead_body,
        "model": model_name,
    }


async def run_synthesis_addendum(db: Database) -> dict:
    """Generate a rolling addendum for today. Returns the filing row as dict."""
    tz = os.environ.get("DISPATCH_TZ", "Asia/Manila")
    now = datetime.now(timezone.utc)
    today = now.strftime("%Y-%m-%d")
    covers_from = f"{today}T00:00:00+00:00"
    covers_until = now.isoformat()

    # Fetch today's lead for context
    async with db.cursor() as cur:
        await cur.execute(
            "SELECT lead_headline, lead_body, active_count, project_lines FROM filings WHERE date=? AND kind='lead'",
            (today,),
        )
        lead_row = await cur.fetchone()

    if not lead_row:
        raise RuntimeError("No lead found for today — cannot addendum without lead")

    lead_headline, lead_body, lead_active_count, lead_project_lines_json = lead_row
    events = await _events_for_window(db, covers_from, covers_until)
    projects = await _project_input(db, events)

    prompt, prompt_hash = build_addendum_prompt(
        date_local=today,
        tz=tz,
        lead_headline=lead_headline or "",
        lead_body=lead_body or "",
        projects_input=projects,
        events_by_project=events,
    )

    provider = select_primary()
    result, model_name = await _synthesize_with_fallback(prompt, AddendumFiling, provider, db)

    generated_at = datetime.now(timezone.utc).isoformat()
    from dispatch.scheduler import get_lead_time
    lead_time = await get_lead_time(db)
    label = f"Filed since {lead_time} · {generated_at.split('T')[1][:5]}"
    async with db.cursor() as cur:
        await cur.execute(
            """INSERT INTO filings
               (date, kind, issue_no, covers_from, covers_until, addendum_label, addendum_body, active_count, project_lines, model, prompt_hash, generated_at, raw_response)
               VALUES (?, 'addendum', NULL, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
               ON CONFLICT(date, kind) DO UPDATE SET
                   covers_from=excluded.covers_from,
                   covers_until=excluded.covers_until,
                   addendum_label=excluded.addendum_label,
                   addendum_body=excluded.addendum_body,
                   active_count=excluded.active_count,
                   project_lines=excluded.project_lines,
                   model=excluded.model,
                   prompt_hash=excluded.prompt_hash,
                   generated_at=excluded.generated_at,
                   raw_response=excluded.raw_response""",
            (
                today, covers_from, covers_until, label, result.addendum_body,
                lead_active_count or 0,
                lead_project_lines_json or "[]",
                model_name, prompt_hash, generated_at,
                result.model_dump_json(),
            ),
        )

    await _refresh_mentions(db, today)
    await _log_run(db, "synthesis:addendum", "ok")
    log.info("synthesis addendum done via %s", model_name)
    return {
        "date": today,
        "label": label,
        "body": result.addendum_body,
        "model": model_name,
    }


# ------------------------------------------------------------------
# Publish + Audio
# ------------------------------------------------------------------
async def run_publish(db: Database) -> tuple[str, dict]:
    """Publish snapshot to R2. Returns (url, snapshot)."""
    started = datetime.now(timezone.utc).isoformat()
    url, snapshot = await publish_snapshot(db)
    await _log_run(db, "publish:snapshot", "ok", started_at=started)
    return url, snapshot


async def run_audio(db: Database, text: str | None = None, kind: str = "lead") -> dict:
    """Generate TTS audio for the brief, upload to R2, and persist the URL.

    Writes audio_url / audio_duration_s onto the matching filings row so
    publish_snapshot can emit them. Keyed by the filing's own `date`, not
    "now in UTC" — these can differ when the brief covers yesterday-local.
    """
    started = datetime.now(timezone.utc).isoformat()

    # Resolve the filing row we're generating audio for. We always work
    # against the most-recent filing of this kind so addendum refreshes
    # and lead generation both target the row that publish will read.
    async with db.cursor() as cur:
        await cur.execute(
            "SELECT date, lead_headline, lead_body, lead_article, addendum_label, addendum_body "
            "FROM filings WHERE kind=? ORDER BY date DESC, id DESC LIMIT 1",
            (kind,),
        )
        row = await cur.fetchone()
    if not row:
        raise RuntimeError(f"No {kind} filing to generate audio for")
    filing_date = row[0]

    if text is None:
        if kind == "lead":
            body = row[3] or row[2] or ""
            text = f"{row[1]}. {body}"
        else:  # addendum
            text = f"{row[4] or ''}. {row[5] or ''}"

    mp3_bytes, duration = await generate_brief_audio(text)
    r2_key = f"dispatch/audio/{filing_date}-{kind}.mp3"
    url = await upload_bytes(mp3_bytes, r2_key, "audio/mpeg")

    async with db.cursor() as cur:
        await cur.execute(
            "UPDATE filings SET audio_url=?, audio_duration_s=? WHERE date=? AND kind=?",
            (url, duration, filing_date, kind),
        )

    await _log_run(db, f"audio:generate:{kind}", "ok", started_at=started)
    log.info("audio done: %s (~%ds)", url, duration)
    return {"url": url, "duration": duration, "kind": kind}
