"""Backfill long-form `lead_article` for historical briefings.

For each lead filing missing `lead_article`, this script:
  1. Reconstructs the events window from the existing covers_from/until
  2. Runs the article-pass synthesis (Pass A only)
  3. Writes the article into filings.lead_article
  4. Regenerates the daily-brief audio so Ava reads the long form

Idempotent — re-running skips filings that already have an article unless
--force is passed.

Run inside the dispatch-collector container:
    docker exec -it dispatch-collector \\
        env PYTHONPATH=/app python3 /app/dispatch/scripts/backfill_articles.py
"""
import argparse
import asyncio
import json
import logging
import sys
from datetime import datetime, timezone

from core.db import Database
from dispatch.audio import generate_brief_audio
from dispatch.orchestrator import _project_input, _events_for_window
from dispatch.publish.r2 import upload_bytes
from dispatch.publish.snapshot import publish_snapshot
from dispatch.synthesis.prompt import build_article_prompt
from dispatch.synthesis.schema import ArticleFiling
from dispatch.synthesis.synthesizer import select_primary
from dispatch.synthesis.anthropic import AnthropicSynthesizer
from dispatch.synthesis.critic import two_pass
from dispatch.synthesis.kimi import KimiCLISynthesizer

DB_PATH = "/data/dispatch.db"
log = logging.getLogger("backfill_articles")


async def _synthesize_article(prompt: str) -> tuple[str, str]:
    provider = select_primary()
    primary = KimiCLISynthesizer() if provider == "kimi" else AnthropicSynthesizer()
    fallback = AnthropicSynthesizer() if provider == "kimi" else KimiCLISynthesizer()
    for synth in (primary, fallback):
        try:
            result: ArticleFiling = await two_pass(synth, prompt, ArticleFiling)
            return result.article.strip(), synth.name
        except Exception as exc:
            log.warning("article synth %s failed: %s", synth.name, exc)
    raise RuntimeError("Both synthesizers failed")


async def _backfill_one(db: Database, row: tuple, *, regen_audio: bool) -> None:
    date_local, issue_no, covers_from, covers_until = row
    log.info("backfilling %s (issue %s)", date_local, issue_no)

    events = await _events_for_window(db, covers_from, covers_until)
    projects = await _project_input(db, events)

    prompt, _ = build_article_prompt(
        issue_no=issue_no or 0,
        date_local=date_local,
        tz="Asia/Manila",
        covers_from=covers_from,
        covers_until=covers_until,
        projects_input=projects,
        events_by_project=events,
    )
    article, model = await _synthesize_article(prompt)
    log.info("  article: %d chars (model=%s)", len(article), model)

    async with db.cursor() as cur:
        await cur.execute(
            "UPDATE filings SET lead_article=? WHERE date=? AND kind='lead'",
            (article, date_local),
        )

    if regen_audio:
        async with db.cursor() as cur:
            await cur.execute(
                "SELECT lead_headline FROM filings WHERE date=? AND kind='lead'",
                (date_local,),
            )
            headline = (await cur.fetchone())[0] or ""
        text = f"{headline}. {article}"
        mp3, duration = await generate_brief_audio(text)
        r2_key = f"dispatch/audio/{date_local}-lead.mp3"
        url = await upload_bytes(mp3, r2_key, "audio/mpeg")
        log.info("  audio: %s (~%ds)", url, duration)


async def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--force", action="store_true",
                        help="re-synthesize even when lead_article is already set")
    parser.add_argument("--no-audio", action="store_true",
                        help="skip audio regeneration (article only)")
    parser.add_argument("--limit", type=int, default=10,
                        help="max filings to process this run (default 10)")
    parser.add_argument("--dates", help="comma-separated explicit dates to backfill")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    db = Database(DB_PATH)
    await db.connect()

    where = "kind='lead'"
    params: list = []
    if args.dates:
        dates = [d.strip() for d in args.dates.split(",") if d.strip()]
        placeholders = ",".join(["?"] * len(dates))
        where += f" AND date IN ({placeholders})"
        params.extend(dates)
    elif not args.force:
        where += " AND (lead_article IS NULL OR lead_article='')"

    async with db.cursor() as cur:
        await cur.execute(
            f"SELECT date, issue_no, covers_from, covers_until "
            f"FROM filings WHERE {where} ORDER BY date DESC LIMIT ?",
            (*params, args.limit),
        )
        rows = await cur.fetchall()

    if not rows:
        log.info("nothing to backfill")
        await db.close()
        return 0

    log.info("backfilling %d filings", len(rows))
    failures = 0
    for row in rows:
        try:
            await _backfill_one(db, row, regen_audio=not args.no_audio)
        except Exception:
            failures += 1
            log.exception("failed for %s", row[0])

    # Republish snapshot once at the end so the homepage reflects new audio
    # URLs / durations (R2 keys are stable but caches need a snapshot bump).
    if not args.no_audio:
        try:
            url, _ = await publish_snapshot(db)
            log.info("snapshot republished: %s", url)
        except Exception:
            log.exception("snapshot republish failed (article backfill still succeeded)")

    await db.close()
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
