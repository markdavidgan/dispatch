"""Load projects.yml and upsert into the projects table.

Called from dispatch.main lifespan at startup. Reapplies on SIGHUP
(future) — the upsert is idempotent.

Display names are resolved via `registry.resolve` (see that module's
docstring for the override → README H1 → titleize-with-acronyms chain).
"""
from datetime import datetime, timezone
from pathlib import Path
import yaml
from core.db import Database

from .resolve import load_acronyms, resolve_display_name

_ACRONYMS_PATH = Path(__file__).parent / "acronyms.yml"


def load_yaml(path: Path) -> dict:
    return yaml.safe_load(path.read_text())


async def sync_to_db(db: Database, data: dict) -> None:
    """Upsert each project from the YAML into the projects table."""
    now = datetime.now(timezone.utc).isoformat()
    acronyms = load_acronyms(_ACRONYMS_PATH)
    async with db.cursor() as cur:
        for p in data.get("projects", []):
            display_name = resolve_display_name(
                slug=p["slug"],
                override=p.get("display_name"),
                local_path=p.get("local_path"),
                acronyms=acronyms,
            )
            await cur.execute(
                """
                INSERT INTO projects (
                    slug, display_name, github_repo, local_path,
                    status, kind, color_hint, first_seen_at, last_seen_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(slug) DO UPDATE SET
                    display_name = excluded.display_name,
                    github_repo = excluded.github_repo,
                    local_path = excluded.local_path,
                    status = excluded.status,
                    kind = excluded.kind,
                    color_hint = excluded.color_hint,
                    last_seen_at = excluded.last_seen_at
                """,
                (
                    p["slug"],
                    display_name,
                    p.get("github"),
                    p.get("local_path"),
                    p["status"],
                    p.get("kind"),
                    p.get("color_hint"),
                    now,
                    now,
                ),
            )
