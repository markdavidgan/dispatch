"""Apply the dispatch schema at lifespan start. Idempotent."""
from pathlib import Path
from core.db import Database

SCHEMA_PATH = Path(__file__).parent / "schema.sql"


async def apply(db: Database) -> None:
    """Apply the schema. Idempotent — every CREATE uses IF NOT EXISTS."""
    # Migration: drop old stub episodes table if it lacks the new columns
    async with db.cursor() as cur:
        await cur.execute(
            "SELECT sql FROM sqlite_master WHERE type='table' AND name='episodes'"
        )
        row = await cur.fetchone()
        if row and "episode_no" not in row[0]:
            await cur.execute("DROP TABLE episodes")

    # Pre-script rename: the schema.sql CREATE TABLE statements use the
    # new (project_*) column names. On a pre-rename DB, IF NOT EXISTS is a
    # no-op, so we must rename the old columns BEFORE running the script
    # if we want the post-script state to actually match. The script's
    # CREATE INDEX statements then succeed against the renamed columns.
    await _rename_column_if_present(
        db, table="filings",
        old_col="bureau_lines", new_col="project_lines",
    )
    await _rename_column_if_present(
        db, table="briefing_mentions",
        old_col="bureau_slug", new_col="project_slug",
    )
    # Drop the stale old index that referenced the renamed column. After
    # RENAME COLUMN SQLite keeps the index pointing at the new column
    # name, so this is purely a cosmetic cleanup (the new
    # `briefing_mentions_project` index created by schema.sql below
    # covers the same query pattern).
    async with db.cursor() as cur:
        await cur.execute("DROP INDEX IF EXISTS briefing_mentions_bureau")

    sql = SCHEMA_PATH.read_text()
    assert db._conn is not None, "call connect() first"
    await db._conn.executescript(sql)

    # Migration: add from_the_desk columns if they don't exist yet,
    # and the long-form article column on filings (added 2026-05-17 —
    # see synthesis/article.py).
    for column_ddl in (
        "ALTER TABLE projects ADD COLUMN from_the_desk TEXT",
        "ALTER TABLE projects ADD COLUMN from_the_desk_generated_at TEXT",
        "ALTER TABLE filings ADD COLUMN lead_article TEXT",
        "ALTER TABLE filings ADD COLUMN audio_url TEXT",
        "ALTER TABLE filings ADD COLUMN audio_duration_s INTEGER",
    ):
        try:
            async with db.cursor() as cur:
                await cur.execute(column_ddl)
        except Exception as e:
            if "duplicate column" not in str(e).lower():
                raise


async def _rename_column_if_present(
    db: Database, *, table: str, old_col: str, new_col: str,
) -> None:
    """SQLite RENAME COLUMN, but only if the old column actually exists.

    Uses PRAGMA table_info to detect the current column set. Safe on a
    fresh DB (no `table` row yet → no-op) and on a partially-migrated DB
    (the new column is already present → no-op). Plan 3 (2026-05-18):
    bureau_lines → project_lines, bureau_slug → project_slug.
    """
    async with db.cursor() as cur:
        await cur.execute(f"PRAGMA table_info({table})")
        cols = {row[1] for row in await cur.fetchall()}
    if not cols:
        return  # table doesn't exist yet
    if old_col in cols and new_col not in cols:
        async with db.cursor() as cur:
            await cur.execute(
                f"ALTER TABLE {table} RENAME COLUMN {old_col} TO {new_col}"
            )
