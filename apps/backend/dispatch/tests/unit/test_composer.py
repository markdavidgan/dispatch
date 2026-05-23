import pytest
from datetime import date
from pathlib import Path

from core.db import Database
from dispatch import schema_init
from dispatch.registry.loader import sync_to_db
from dispatch.podcast.composer import compose


@pytest.mark.asyncio
async def test_compose_includes_events(tmp_path):
    db = Database(str(tmp_path / "t.db"))
    await db.connect()
    await schema_init.apply(db)
    await sync_to_db(db, {"projects": [
        {"slug": "agos", "display_name": "Agos", "status": "active", "kind": "app"},
    ]})
    async with db.cursor() as cur:
        await cur.execute(
            "INSERT INTO events(project_slug, kind, external_id, title, author, occurred_at, ingested_at) "
            "VALUES ('agos', 'commit', 'abc123', 'feat: cool thing', 'markdavidgan', "
            "'2026-05-05T10:00:00+00:00', '2026-05-05T10:00:00+00:00')"
        )

    md = await compose(
        db, project_slug="agos", podcast_title="Agos Dev",
        project_display_name="Agos", week_start=date(2026, 5, 4),
    )
    assert "Agos Dev" in md
    assert "feat: cool thing" in md
    assert "Tuesday" in md  # 2026-05-05 was a Tuesday
    await db.close()


@pytest.mark.asyncio
async def test_compose_handles_empty_week(tmp_path):
    db = Database(str(tmp_path / "t.db"))
    await db.connect()
    await schema_init.apply(db)
    await sync_to_db(db, {"projects": [
        {"slug": "agos", "display_name": "Agos", "status": "active", "kind": "app"},
    ]})
    md = await compose(db, "agos", "Agos Dev", "Agos", date(2026, 5, 4))
    assert "No notable activity." in md
    assert md.count("## Monday") + md.count("## Tuesday") + md.count("## Wednesday") + md.count("## Thursday") + md.count("## Friday") + md.count("## Saturday") + md.count("## Sunday") == 7  # 7 day headers
    await db.close()
