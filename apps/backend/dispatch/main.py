"""Dispatch collector — FastAPI entry point."""
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from starlette.responses import Response

from core import logging as core_logging
from core.config import get_settings
from core.db import Database
from dispatch import schema_init
from dispatch.crypto import Crypto
from dispatch.settings_store import SettingsStore
from dispatch.system.key_canary import validate_or_create
from dispatch.registry.loader import load_yaml, sync_to_db
from dispatch.scheduler import start_jobs, stop_jobs

# API routers
from dispatch.api import health as health_router
from dispatch.api import live as live_router
from dispatch.api import brief as brief_router
from dispatch.api import projects as projects_router
from dispatch.api import podcast as podcast_router
from dispatch.api import briefings as briefings_router
from dispatch.api import snapshot as snapshot_router
from dispatch.api import audio as audio_router
from dispatch.api import tts as tts_router
from dispatch.api import sitemap as sitemap_router
from dispatch.api.admin import settings as admin_settings_router
from dispatch.api.admin import projects as admin_projects_router
from dispatch.api.admin import schedules as admin_schedules_router
from dispatch.api.admin import runs as admin_runs_router
from dispatch.api.admin import system as admin_system_router
from dispatch.api.admin import briefings as admin_briefings_router
from dispatch.api.admin import podcasts as admin_podcasts_router
from dispatch.api import proxy as proxy_router

core_logging.configure()
settings = get_settings()

if not settings.master_key:
    raise RuntimeError(
        "DISPATCH_MASTER_KEY is required. Set it in your environment "
        "(see README → Key Management). "
        "This key encrypts all settings at rest."
    )

crypto = Crypto(settings.master_key)
db = Database(settings.db_path)


@asynccontextmanager
async def lifespan(app: FastAPI):
    await db.connect()
    await schema_init.apply(db)

    # Validate master key against DB canary (or create on first boot)
    await validate_or_create(db, crypto)

    # Settings store
    store = SettingsStore(db, crypto)
    await store.bootstrap_defaults()
    app.state.settings_store = store
    app.state.crypto = crypto

    # Storage backend
    from dispatch.storage import get_storage_backend
    from dispatch.storage.local import LocalStorage
    try:
        storage = await get_storage_backend(db, crypto)
        app.state.storage_backend = storage
    except Exception:
        # If storage is not configured yet (first boot), use local fallback
        storage = LocalStorage("./dispatch-media")
        app.state.storage_backend = storage

    # Wire the legacy R2 module to delegate to the storage backend
    from dispatch.publish import r2 as r2_compat
    r2_compat.set_storage_backend(storage)

    # Projects bootstrap from YAML (optional — can be disabled once DB registry is populated)
    projects_yml = Path(__file__).parent / "projects.yml"
    bootstrap_env = Path(__file__).parent.parent / ".env"
    # Only bootstrap from YAML if projects table is empty
    async with db.cursor() as cur:
        await cur.execute("SELECT COUNT(*) FROM projects")
        row = await cur.fetchone()
    if (not row or row[0] == 0) and projects_yml.exists():
        await sync_to_db(db, load_yaml(projects_yml))

    app.state.db = db
    await start_jobs(db)
    yield
    stop_jobs()
    await db.close()


app = FastAPI(title="Dispatch Collector", version="0.1.0", lifespan=lifespan)

# CORS — origins from DB settings, with dev defaults
@app.middleware("http")
async def cors_middleware(request, call_next):
    origin = request.headers.get("origin", "")
    allowed = ["http://localhost:5173", "http://127.0.0.1:5173"]
    if settings.cors_origins:
        allowed.extend([o.strip() for o in settings.cors_origins.split(",") if o.strip()])
    if hasattr(request.app.state, "settings_store"):
        try:
            configured = await request.app.state.settings_store.web_allowed_origins()
            allowed.extend(configured)
        except Exception:
            pass

    if request.method == "OPTIONS":
        response = Response(status_code=204)
    else:
        response = await call_next(request)

    if origin in allowed:
        response.headers["access-control-allow-origin"] = origin
        response.headers["access-control-allow-credentials"] = "true"
        response.headers["access-control-allow-methods"] = "GET, POST, PUT, PATCH, DELETE, OPTIONS"
        response.headers["access-control-allow-headers"] = "content-type, authorization, x-requested-with"
    return response


# Health stays at root (used by Docker healthcheck + Caddy)
app.include_router(health_router.router)
app.include_router(sitemap_router.router)

# All other public + admin routers live under /api
app.include_router(live_router.router, prefix="/api")
app.include_router(brief_router.router, prefix="/api")
app.include_router(projects_router.router, prefix="/api")
app.include_router(podcast_router.router, prefix="/api")
app.include_router(briefings_router.router, prefix="/api")
app.include_router(snapshot_router.router, prefix="/api")
app.include_router(audio_router.router, prefix="/api")

app.include_router(admin_settings_router.router, prefix="/api")
app.include_router(admin_projects_router.router, prefix="/api")
app.include_router(admin_schedules_router.router, prefix="/api")
app.include_router(admin_runs_router.router, prefix="/api")
app.include_router(admin_system_router.router, prefix="/api")
app.include_router(admin_briefings_router.router, prefix="/api")
app.include_router(admin_podcasts_router.router, prefix="/api")

app.include_router(proxy_router.router, prefix="/api")
