"""Dispatch collector — FastAPI entry point."""
from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI

from core import logging as core_logging
from core.config import get_settings
from core.db import Database
from dispatch import schema_init
from dispatch.api import health as health_router
from dispatch.api import live as live_router
from dispatch.api import brief as brief_router
from dispatch.api import projects as projects_router
from dispatch.api import podcast as podcast_router
from dispatch.api import briefings as briefings_router
from dispatch.registry.loader import load_yaml, sync_to_db
from dispatch.scheduler import start_jobs, stop_jobs

core_logging.configure()
settings = get_settings()

if not settings.master_key:
    raise RuntimeError(
        "DISPATCH_MASTER_KEY is required. Set it in your environment "
        "(see README → Key Management). "
        "From Phase 3 onward this key encrypts all settings at rest; "
        "Phase 1 enforces presence only."
    )

db = Database(settings.db_path)


@asynccontextmanager
async def lifespan(app: FastAPI):
    await db.connect()
    await schema_init.apply(db)
    projects_yml = Path(__file__).parent / "projects.yml"
    await sync_to_db(db, load_yaml(projects_yml))
    app.state.db = db
    start_jobs(db)
    yield
    stop_jobs()
    await db.close()


app = FastAPI(title="Dispatch Collector", version="0.1.0", lifespan=lifespan)
app.include_router(health_router.router)
app.include_router(live_router.router)
app.include_router(brief_router.router)
app.include_router(projects_router.router)
app.include_router(podcast_router.router)
app.include_router(briefings_router.router)
