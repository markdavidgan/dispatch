import subprocess
import pytest
from pathlib import Path
from core.db import Database
from dispatch import schema_init
from dispatch.registry.loader import sync_to_db
from dispatch.ingest.git import ingest_repo


def _init_repo(path: Path):
    subprocess.run(["git", "init", "-q", "-b", "main", str(path)], check=True)
    subprocess.run(["git", "-C", str(path), "config", "user.email", "t@t.com"], check=True)
    subprocess.run(["git", "-C", str(path), "config", "user.name", "t"], check=True)


def _commit(path: Path, message: str):
    (path / "f.txt").write_text(message)
    subprocess.run(["git", "-C", str(path), "add", "-A"], check=True)
    subprocess.run(["git", "-C", str(path), "commit", "-q", "-m", message], check=True)


@pytest.mark.asyncio
async def test_ingest_writes_commits_and_advances_cursor(tmp_path):
    repo = tmp_path / "agos"
    _init_repo(repo)
    _commit(repo, "feat: first")
    _commit(repo, "fix: second")

    db = Database(str(tmp_path / "t.db"))
    await db.connect()
    await schema_init.apply(db)
    await sync_to_db(db, {"projects": [
        {"slug": "agos", "display_name": "Agos", "status": "active", "kind": "app",
         "local_path": str(repo)},
    ]})

    n = await ingest_repo(db, slug="agos", path=repo)
    assert n == 2

    async with db.cursor() as cur:
        await cur.execute("SELECT kind, title FROM events ORDER BY occurred_at")
        rows = await cur.fetchall()
    assert all(r[0] == "commit" for r in rows)
    titles = [r[1] for r in rows]
    assert "feat: first" in titles
    assert "fix: second" in titles

    # Second call ingests nothing (cursor advanced)
    n2 = await ingest_repo(db, slug="agos", path=repo)
    assert n2 == 0

    # Third commit picked up incrementally
    _commit(repo, "chore: third")
    n3 = await ingest_repo(db, slug="agos", path=repo)
    assert n3 == 1
    await db.close()
