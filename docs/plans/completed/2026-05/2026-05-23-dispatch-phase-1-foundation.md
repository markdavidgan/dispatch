# Dispatch — Phase 1 Foundation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the backend extraction actually runnable as a standalone, perimeter-trusting service — locally and via Docker Compose — so every subsequent phase has a working foundation to build on.

**Architecture:** Backend-only Phase. The Next.js frontend is left untouched and will be deleted-and-rebuilt as a Vite SPA in Phase 2. This phase strips the marklab-era Cloudflare Access dependency (per the no-app-auth decision in the operational-gaps brainstorm), sets up a clean local-dev workflow, verifies the existing pytest suite still passes, and confirms `docker compose up` produces a service responding on `/health` with no env vars beyond `DISPATCH_MASTER_KEY`.

**Tech Stack:** FastAPI 0.115.6, Uvicorn 0.32.1, Python 3.13 (container) / 3.12+ (local dev), SQLite (WAL) via aiosqlite, pytest 8.3.4 with `pytest-asyncio` in auto mode, Docker Compose v2.

**Scope explicitly excluded from this phase** (handled later):
- DB-backed encrypted settings, master-key canary, rotation (Phase 3)
- Pluggable storage backends (Phase 5) — R2 hardcoding stays for now
- Project registry CRUD via DB (Phase 4) — `projects.yml` bootstrap stays for now
- Branch-aware GitHub ingest (Phase 6)
- Vite SPA scaffold (Phase 2)
- Any production deployment

**Reference docs:**
- Brainstorm: `docs/brainstorm/2026-05-23-standalone-dispatch/notes.md`
- Operational gaps: `docs/brainstorm/2026-05-23-dispatch-operational-gaps/notes.md`
- Visual identity (frozen): `DESIGN.md`

---

## File Map

**Delete:**
- `apps/backend/core/cf_access.py`
- `apps/backend/core/tests/test_cf_access.py`

**Modify:**
- `apps/backend/dispatch/api/live.py` — remove cf_access dep
- `apps/backend/dispatch/api/brief.py` — remove cf_access dep
- `apps/backend/dispatch/api/projects.py` — remove cf_access dep
- `apps/backend/dispatch/api/podcast.py` — remove cf_access dep
- `apps/backend/dispatch/api/briefings.py` — remove docstring reference to cf_access
- `apps/backend/dispatch/api/health.py` — remove stale "Task 1.4" comment
- `apps/backend/dispatch/main.py` — accept `DISPATCH_MASTER_KEY` env (boot-gate only; encryption usage is Phase 3)
- `README.md` — local dev + docker quick-start

**Create:**
- `apps/backend/.env.example`
- `apps/backend/dispatch/tests/integration/test_boot.py` — smoke test that the app boots and `/health` responds
- `apps/backend/dispatch/tests/integration/test_no_cf_required.py` — protected routes don't 401 in standalone mode
- `apps/backend/dispatch/tests/integration/__init__.py`
- `docs/plans/README.md` — plan index (if missing)
- `CLAUDE.md` — repo-wide instructions for future agents

**Tools required on the executor's machine:** `python3.12+`, `pip` (or `uv`), `docker`, `docker compose` (v2), `curl`, `git`.

---

## Task 1 — Repository conventions doc

**Why:** Future agents (and the executor of this plan) need to know the doc-conventions, the visual-identity invariant, and the no-app-auth decision before they touch code. A `CLAUDE.md` at the repo root is the highest-priority context they get.

**Files:**
- Create: `CLAUDE.md`
- Create: `docs/plans/README.md`

- [ ] **Step 1.1: Create `docs/plans/README.md` as a plan index**

```markdown
# Plans

Active implementation plans live here, named `YYYY-MM-DD-<short-desc>.md`. On completion, move to `completed/YYYY-MM/`.

## Active

- [2026-05-23 — Dispatch Phase 1 Foundation](2026-05-23-dispatch-phase-1-foundation.md)

## Completed

_(none yet)_
```

- [ ] **Step 1.2: Create `CLAUDE.md` at repo root**

```markdown
# Dispatch — Agent Instructions

Dispatch is the standalone extraction of a daily-brief / podcast app from the marklab monorepo. Goals: deployable anywhere (homelab Docker, Vercel-frontend + self-hosted-backend, etc.), single-admin per instance, perimeter-trusting (no app-layer auth).

## Doc conventions

- Plans: `docs/plans/YYYY-MM-DD-<short-desc>.md` → archive to `docs/plans/completed/YYYY-MM/` on completion.
- Brainstorms: `docs/brainstorm/YYYY-MM-DD-<short-desc>/` (folder with `notes.md`).
- Specs: `docs/specs/YYYY-MM-DD-<short-desc>.md`.
- Insights: `docs/insights/YYYY-MM/`.

Do NOT write planning docs to `docs/superpowers/`, `.superpowers/`, or repo root.

## Architecture invariants

- **No app-layer authentication.** The backend trusts its deployment perimeter (Cloudflare Access, Tailscale, Caddy basic auth, Authelia). No login page, no users table, no JWT in the app. Admin-only logic is gated by route prefix: `/api/admin/*` is operator-perimeter-protected; public reader paths (`/`, `/briefings/*`, `/podcasts/*`, `/api/snapshot`) are open.
- **Editorial design is immutable.** See `DESIGN.md`. Framework can change; the look cannot.
- **Single required env var.** `DISPATCH_MASTER_KEY` (encrypts settings at rest, used from Phase 3 onward). Every other credential lives in the DB, configured via admin UI.

## Phase ordering

Each phase has its own plan in `docs/plans/`. Do not jump ahead. Current: **Phase 1 — Foundation** (see plan).

## When in doubt

Read `docs/brainstorm/2026-05-23-standalone-dispatch/notes.md` (north star) and `docs/brainstorm/2026-05-23-dispatch-operational-gaps/notes.md` (resolved gaps).
```

- [ ] **Step 1.3: Commit**

```bash
git add CLAUDE.md docs/plans/README.md
git commit -m "docs: add CLAUDE.md and plans index for standalone repo"
```

---

## Task 2 — Failing smoke test: app boots and `/health` responds

**Why:** Before changing any code, lock in a regression-proof signal that the app starts. TDD: write the test, watch it fail (or pass — either way the bar is set), then proceed.

**Files:**
- Create: `apps/backend/dispatch/tests/integration/__init__.py` (empty)
- Create: `apps/backend/dispatch/tests/integration/test_boot.py`

- [ ] **Step 2.1: Create the integration tests package marker**

```bash
mkdir -p apps/backend/dispatch/tests/integration
touch apps/backend/dispatch/tests/integration/__init__.py
```

- [ ] **Step 2.2: Write the boot smoke test**

Create `apps/backend/dispatch/tests/integration/test_boot.py`:

```python
"""Smoke test: the app boots, lifespan completes, /health responds.

Uses FastAPI's TestClient which drives the lifespan context manager
end-to-end (DB connect, schema apply, scheduler start, projects.yml sync).
"""
from pathlib import Path

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def tmp_db_env(tmp_path, monkeypatch):
    """Point the app at a tempdir SQLite file and disable APScheduler timing."""
    db_path = tmp_path / "dispatch.db"
    monkeypatch.setenv("DB_PATH", str(db_path))
    # Phase 1 introduces this as a boot-gate (no encryption use yet).
    monkeypatch.setenv("DISPATCH_MASTER_KEY", "test-key-not-secret")
    # Force a fresh Settings() — the singleton caches across tests otherwise.
    from core import config
    config.get_settings.cache_clear()
    yield db_path
    config.get_settings.cache_clear()


def test_app_boots_and_health_responds(tmp_db_env):
    from dispatch.main import app

    with TestClient(app) as client:
        resp = client.get("/health")
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "healthy"
        assert body["service"] == "dispatch-collector"
        assert body["db_ok"] is True
```

- [ ] **Step 2.3: Run it — expect failure (missing `DISPATCH_MASTER_KEY` gate not yet added) or success (if app already boots cleanly)**

```bash
cd apps/backend
pytest dispatch/tests/integration/test_boot.py -v
```

Either outcome is acceptable here — Task 4 explicitly adds the master-key gate, which will make this test the regression signal for Task 4. Note the result in the commit message below.

- [ ] **Step 2.4: Commit**

```bash
git add apps/backend/dispatch/tests/integration/
git commit -m "test: add boot smoke test (Phase 1 baseline)"
```

---

## Task 3 — Failing test: protected routes do not require CF Access

**Why:** The cf_access dependency makes `/live`, `/brief`, `/projects`, `/podcasts` 401 without Cloudflare headers. Standalone mode trusts the perimeter; the app must serve these routes to any caller that reaches it. Write the test first so we have a green signal after Task 4 removes the dependency.

**Files:**
- Create: `apps/backend/dispatch/tests/integration/test_no_cf_required.py`

- [ ] **Step 3.1: Write the test**

```python
"""Standalone mode trusts the deployment perimeter, not Cf-Access headers.

After Task 4 removes the cf_access dependency, GET /live (and the other
previously-protected routes) must respond 200 with no special headers.
"""
from fastapi.testclient import TestClient


def test_live_does_not_require_cf_headers(tmp_db_env):
    from dispatch.main import app

    with TestClient(app) as client:
        resp = client.get("/live")
        # Acceptable: 200 (empty event set returns {} or similar).
        # Unacceptable: 401 (the cf_access "credentials required" response).
        assert resp.status_code != 401, (
            "Standalone backend must not require Cf-Access headers. "
            "If you see 401, the cf_access dependency was not removed."
        )


def test_brief_post_does_not_require_cf_headers(tmp_db_env):
    from dispatch.main import app

    with TestClient(app) as client:
        # /brief endpoints are POST in the existing code; we don't care
        # about response shape here, only that auth doesn't block us.
        resp = client.post("/brief/refresh")
        assert resp.status_code != 401


def test_projects_does_not_require_cf_headers(tmp_db_env):
    from dispatch.main import app

    with TestClient(app) as client:
        resp = client.get("/projects")
        assert resp.status_code != 401


def test_podcasts_does_not_require_cf_headers(tmp_db_env):
    from dispatch.main import app

    with TestClient(app) as client:
        resp = client.get("/podcasts")
        assert resp.status_code != 401
```

Note: this test re-uses the `tmp_db_env` fixture from `test_boot.py`. Move that fixture into `apps/backend/dispatch/tests/integration/conftest.py` so both files share it.

- [ ] **Step 3.2: Extract the fixture into `conftest.py`**

Create `apps/backend/dispatch/tests/integration/conftest.py`:

```python
"""Shared fixtures for integration tests."""
import pytest


@pytest.fixture
def tmp_db_env(tmp_path, monkeypatch):
    """Point the app at a tempdir SQLite file and provide the boot-gate key."""
    db_path = tmp_path / "dispatch.db"
    monkeypatch.setenv("DB_PATH", str(db_path))
    monkeypatch.setenv("DISPATCH_MASTER_KEY", "test-key-not-secret")
    from core import config
    config.get_settings.cache_clear()
    yield db_path
    config.get_settings.cache_clear()
```

Then overwrite `apps/backend/dispatch/tests/integration/test_boot.py` with the deduplicated version (fixture is now auto-discovered from the sibling `conftest.py`):

```python
"""Smoke test: the app boots, lifespan completes, /health responds."""
from fastapi.testclient import TestClient


def test_app_boots_and_health_responds(tmp_db_env):
    from dispatch.main import app

    with TestClient(app) as client:
        resp = client.get("/health")
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "healthy"
        assert body["service"] == "dispatch-collector"
        assert body["db_ok"] is True
```

- [ ] **Step 3.3: Run the new tests — expect failure (401s)**

```bash
cd apps/backend
pytest dispatch/tests/integration/test_no_cf_required.py -v
```

Expected: 4 failures, each with the "Standalone backend must not require Cf-Access headers" assertion message OR an HTTP 401 in the response.

- [ ] **Step 3.4: Commit (red)**

```bash
git add apps/backend/dispatch/tests/integration/
git commit -m "test: assert standalone routes do not require Cf-Access (red)"
```

---

## Task 4 — Add `DISPATCH_MASTER_KEY` boot-gate to `main.py`

**Why:** Per the operational-gaps brainstorm (Gap 2), the master key is mandatory and the app must refuse to boot without it. Phase 1 introduces only the boot-gate — encryption usage (canary, settings encrypt/decrypt) lands in Phase 3. The gate now means later phases don't have to retrofit it.

**Files:**
- Modify: `apps/backend/dispatch/main.py`
- Modify: `apps/backend/core/config.py` — surface `master_key` on `Settings`

- [ ] **Step 4.1: Add `master_key` field to `Settings`**

Replace the full contents of `apps/backend/core/config.py` with:

```python
"""Shared configuration for Dispatch backend services.

Loads from environment via pydantic-settings.
"""
from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Common settings used by every service that imports this lib."""

    model_config = SettingsConfigDict(env_file=None, extra="ignore")

    host: str = "0.0.0.0"
    port: int = 10060
    db_path: str = "/data/dispatch.db"
    dispatch_tz: str = "Asia/Manila"
    # Mandatory: encrypts settings at rest from Phase 3 onward.
    # Phase 1 validates presence only; no encryption is performed yet.
    # validation_alias pins the env var name to DISPATCH_MASTER_KEY
    # instead of the pydantic-settings default of MASTER_KEY.
    master_key: str | None = Field(
        default=None,
        validation_alias="DISPATCH_MASTER_KEY",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
```

- [ ] **Step 4.2: Add the boot-gate to `main.py`**

In `apps/backend/dispatch/main.py`, after `settings = get_settings()`, add the gate. The relevant section becomes:

```python
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
```

- [ ] **Step 4.3: Run the boot smoke test — expect pass with key set, fail without**

```bash
cd apps/backend
# With key (via fixture) — should pass:
pytest dispatch/tests/integration/test_boot.py -v
# Without key — should error:
DISPATCH_MASTER_KEY= python -c "from dispatch.main import app" 2>&1 | grep -q "DISPATCH_MASTER_KEY is required" && echo OK
```

Expected: first command passes (1 passed); second prints `OK`.

- [ ] **Step 4.4: Commit**

```bash
git add apps/backend/core/config.py apps/backend/dispatch/main.py
git commit -m "feat(boot): require DISPATCH_MASTER_KEY env var"
```

---

## Task 5 — Remove `cf_access` from production routes

**Why:** No-app-auth decision. The dependency unconditionally 401s every request that doesn't carry CF headers. Standalone mode has no CF in front of it by default; the perimeter (if any) is the operator's choice.

**Files:**
- Modify: `apps/backend/dispatch/api/live.py`
- Modify: `apps/backend/dispatch/api/brief.py`
- Modify: `apps/backend/dispatch/api/projects.py`
- Modify: `apps/backend/dispatch/api/podcast.py`
- Modify: `apps/backend/dispatch/api/briefings.py` (docstring only)
- Modify: `apps/backend/dispatch/api/health.py` (comment only)

Each router file has the identical pattern:

```python
from core.cf_access import verify_cf_access
...
router = APIRouter(prefix="/<x>", dependencies=[Depends(verify_cf_access)])
```

→ becomes:

```python
# no cf_access import
...
router = APIRouter(prefix="/<x>")
```

If a file then has no other `Depends` usage, remove `, Depends` from the `from fastapi import ...` line as well.

- [ ] **Step 5.1: Edit `live.py`**

Open `apps/backend/dispatch/api/live.py`. Replace the top of the file:

```python
"""Live data endpoint — returns current project stats.

Protected by the deployment perimeter (e.g. Cloudflare Access, Tailscale,
reverse-proxy basic auth). No app-layer authentication. See CLAUDE.md.
"""
from fastapi import APIRouter, Request
from datetime import datetime, timezone

from core.db import Database

router = APIRouter(prefix="/live")
```

(Removed: `, Depends` from fastapi import; the `cf_access` import; the `dependencies=[...]` argument.)

- [ ] **Step 5.2: Edit `brief.py`**

In `apps/backend/dispatch/api/brief.py`:
- Delete the line `from core.cf_access import verify_cf_access`
- Change `router = APIRouter(prefix="/brief", dependencies=[Depends(verify_cf_access)])` → `router = APIRouter(prefix="/brief")`
- If the file has no other `Depends` usage, remove it from the `fastapi` import line.

- [ ] **Step 5.3: Edit `projects.py`**

Same pattern as Step 5.2 in `apps/backend/dispatch/api/projects.py`.

- [ ] **Step 5.4: Edit `podcast.py`**

Same pattern as Step 5.2 in `apps/backend/dispatch/api/podcast.py`.

- [ ] **Step 5.5: Edit `briefings.py` (docstring only)**

In `apps/backend/dispatch/api/briefings.py`, replace the docstring lines:

```
Both require CF Access (already enforced globally by the verify_cf_access
middleware — see core/cf_access.py).
```

with:

```
Both endpoints are perimeter-protected at the deployment layer
(Cloudflare Access, Tailscale, reverse-proxy auth — see CLAUDE.md).
```

- [ ] **Step 5.6: Edit `health.py` (comment only)**

In `apps/backend/dispatch/api/health.py`, replace the module docstring:

```python
"""Health endpoints. /health is public; others land in Task 1.4 behind CF Access."""
```

with:

```python
"""Health endpoint. Public; no auth dependency."""
```

- [ ] **Step 5.7: Delete `cf_access.py` and its test**

```bash
git rm apps/backend/core/cf_access.py apps/backend/core/tests/test_cf_access.py
```

- [ ] **Step 5.8: Verify no stragglers**

```bash
grep -rn "cf_access\|verify_cf_access\|Cf-Access" apps/backend/ --include="*.py"
```

Expected: zero output. If anything appears, edit those files to remove or rewrite the reference.

- [ ] **Step 5.9: Run the no-CF tests — expect green**

```bash
cd apps/backend
pytest dispatch/tests/integration/test_no_cf_required.py -v
```

Expected: 4 passed.

- [ ] **Step 5.10: Run the full test suite — expect green**

```bash
cd apps/backend
pytest
```

Expected: all tests pass. If any test that previously used cf_access fixtures fails, edit the test to drop the now-irrelevant headers/mocks.

- [ ] **Step 5.11: Commit**

```bash
git add -A apps/backend/
git commit -m "feat(auth): remove cf_access dependency; trust deployment perimeter"
```

---

## Task 6 — Local-dev workflow: `.env.example` and README quick-start

**Why:** A developer cloning the repo right now has no idea what env vars are required, how to run pytest, or how to start uvicorn. Document the minimum.

**Files:**
- Create: `apps/backend/.env.example`
- Modify: `README.md`

- [ ] **Step 6.0: Ensure `.env` and SQLite dev artifacts are git-ignored**

Check if `.gitignore` exists at the repo root. If it does and already contains `.env` and `*.db*` patterns, skip this step. Otherwise, append to (or create) `.gitignore`:

```gitignore
# Local env files — never commit
.env
.env.local
*.env.local

# SQLite dev artifacts
*.db
*.db-shm
*.db-wal

# Python venv
.venv/
__pycache__/
*.pyc
```

Commit if changed:

```bash
git add .gitignore
git commit -m "chore: gitignore .env files and local SQLite artifacts"
```

- [ ] **Step 6.1: Create `.env.example`**

`apps/backend/.env.example`:

```bash
# Required: mandatory boot-gate. From Phase 3 onward, encrypts settings at rest.
# Generate locally with: python -c "import secrets; print(secrets.token_urlsafe(32))"
DISPATCH_MASTER_KEY=

# Optional: defaults are sensible for local dev.
HOST=127.0.0.1
PORT=10060
DB_PATH=./dispatch.dev.db
DISPATCH_TZ=Asia/Manila

# --- The following will move to DB-backed settings in Phase 3. ---
# Until then, they remain env-driven to keep the existing pipelines working.

# AI synthesis (one of):
# KIMI_OAUTH_JSON=
# ANTHROPIC_API_KEY=
# DISPATCH_AI_PROVIDER=kimi

# Google Cloud TTS:
# GOOGLE_APPLICATION_CREDENTIALS=/absolute/path/to/gcp-sa.json
# GCP_TTS_VOICE=en-US-Chirp3-HD-Leda

# GitHub ingest:
# GITHUB_TOKEN=

# Cloudflare R2 (snapshot + audio storage — Phase 5 replaces this with pluggable storage):
# R2_ACCOUNT_ID=
# R2_ACCESS_KEY_ID=
# R2_SECRET_ACCESS_KEY=
# R2_BUCKET=
# R2_PUBLIC_BASE_URL=

# NotebookLM (podcast composition):
# NOTEBOOKLM_AUTH_JSON=
```

- [ ] **Step 6.2: Replace the relevant sections of `README.md`**

Open `README.md`. Replace the entire "Quick Start" section (the `### Frontend` / `### Backend` / `### Docker Compose` subsections) with:

```markdown
## Quick Start

### Local backend dev

```bash
cd apps/backend
cp .env.example .env
# Edit .env — at minimum set DISPATCH_MASTER_KEY.
python -m venv .venv && source .venv/bin/activate
pip install -r dispatch/requirements.txt
set -a && source .env && set +a
uvicorn dispatch.main:app --reload --host "$HOST" --port "$PORT"
```

Visit http://127.0.0.1:10060/health — expect `{"status": "healthy", ...}`.

### Backend tests

```bash
cd apps/backend
pytest
```

### Docker Compose (full stack)

```bash
export DISPATCH_MASTER_KEY=$(python -c "import secrets; print(secrets.token_urlsafe(32))")
docker compose up --build
```

Visit http://localhost:10060/health.

### Frontend

The frontend pivot to a Vite SPA is **Phase 2** of the standalone extraction. The existing `apps/frontend/` is the previous Next.js extraction and will be replaced. See `docs/plans/` for the active plan.
```

Also add a new section before "License":

```markdown
## Key Management

The single required env var is `DISPATCH_MASTER_KEY`. From Phase 3 onward this key encrypts every credential the app holds (AI provider keys, TTS credentials, GitHub tokens, storage credentials, NotebookLM session).

**If you lose this key, those encrypted settings are unrecoverable** and you will need to re-enter them via the admin UI. Briefings, audio, snapshots, and projects are unaffected. Back up the key in a password manager.

Generate one with:

```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

## Authentication

Dispatch does not implement application-level authentication. The backend trusts its deployment perimeter — Cloudflare Access, Tailscale, a reverse-proxy basic-auth block, Authelia, or any equivalent.

Route prefixes are designed so any perimeter can apply policy:
- `/admin/*` and `/api/admin/*` — operator-only; gate these in your perimeter.
- `/`, `/briefings/*`, `/podcasts/*`, `/api/snapshot` — public reader paths; gate them too if you want a fully private instance.

Recipes for the common perimeters land in `docs/operations/perimeter-recipes.md` (added in Phase 2).
```

- [ ] **Step 6.3: Verify the documented local-dev path works**

```bash
cd apps/backend
cp .env.example .env
# Edit .env: set DISPATCH_MASTER_KEY=test-local-dev-key
python -m venv .venv-phase1-check && source .venv-phase1-check/bin/activate
pip install -r dispatch/requirements.txt
set -a && source .env && set +a
uvicorn dispatch.main:app --port 10060 &
UVICORN_PID=$!
sleep 3
curl -fsS http://127.0.0.1:10060/health | grep -q '"status":"healthy"' && echo OK
kill $UVICORN_PID
deactivate
rm -rf .venv-phase1-check .env dispatch.dev.db dispatch.dev.db-shm dispatch.dev.db-wal
```

Expected output: `OK`.

- [ ] **Step 6.4: Commit**

```bash
git add apps/backend/.env.example README.md
git commit -m "docs: backend local-dev workflow, key management, perimeter auth note"
```

---

## Task 7 — Docker Compose smoke test

**Why:** The brainstorm promises `docker compose up` produces a working backend. Verify, then document the verified behavior in `README.md` already covered in Task 6. This task is purely a smoke run; no code changes if the build succeeds.

**Files:** none modified unless the build fails.

- [ ] **Step 7.1: Build the image**

```bash
cd /mnt/data/repos/markdavidgan/dispatch
export DISPATCH_MASTER_KEY=$(python -c "import secrets; print(secrets.token_urlsafe(32))")
docker compose build dispatch-backend
```

Expected: image builds without error. If a `COPY` fails because `dispatch/skills/` is missing, that's a Phase-1 finding — see Step 7.4.

- [ ] **Step 7.2: Start the service**

```bash
docker compose up -d dispatch-backend
sleep 5
docker compose ps
```

Expected: status `running` and (after ~30s for the healthcheck to fire) `healthy`.

- [ ] **Step 7.3: Hit `/health`**

```bash
curl -fsS http://localhost:10060/health
```

Expected output (whitespace may differ):
```json
{"status":"healthy","service":"dispatch-collector","version":"0.1.0","ts":"...","db_ok":true}
```

- [ ] **Step 7.4: If the build failed for missing files, fix the Dockerfile or .dockerignore**

Common Phase-1 issues and their fixes:

- **`COPY dispatch/skills /app/skills` fails** — check `apps/backend/dispatch/skills/` exists. If not, remove that COPY line.
- **`COPY core /app/core` fails** — check `apps/backend/core/` exists (it should).
- **kimi-cli install fails on python:3.13-slim** — pin to `python:3.12-slim` for now; the requirements pin Python 3.12. Note the change in the commit message.

Make any required edits to `apps/backend/Dockerfile` and re-run Steps 7.1–7.3.

- [ ] **Step 7.5: Tear down**

```bash
docker compose down -v
```

- [ ] **Step 7.6: Commit (only if changes were needed in 7.4)**

```bash
git add apps/backend/Dockerfile docker-compose.yml
git commit -m "fix(docker): <describe the specific fix>"
```

If no changes were needed, skip this step — the smoke test is a verification, not a code change.

---

## Task 8 — Sanity-check that startup still syncs `projects.yml`

**Why:** The brainstorm preserves `projects.yml` bootstrap for Phases 1–3 (DB-backed registry CRUD is Phase 4). The boot lifespan calls `sync_to_db(db, load_yaml(projects_yml))`. Verify it still works after the cf_access removal.

**Files:**
- Create: `apps/backend/dispatch/tests/integration/test_projects_yml_bootstrap.py`

- [ ] **Step 8.1: Write the test**

```python
"""On boot, projects.yml is parsed and synced into the projects table.

Phase 4 replaces this with DB-backed CRUD; until then, the existing
sync_to_db path is load-bearing.
"""
from fastapi.testclient import TestClient


def test_projects_yml_syncs_on_boot(tmp_db_env):
    from dispatch.main import app

    with TestClient(app) as client:
        # /projects is the public list route; after boot it should
        # return >= 1 project from projects.yml.
        resp = client.get("/projects")
        assert resp.status_code == 200
        body = resp.json()
        # The response shape is whatever the existing projects.py returns;
        # we only assert the bootstrap ran (non-empty).
        assert body, f"expected projects from projects.yml bootstrap, got: {body!r}"
```

- [ ] **Step 8.2: Run it**

```bash
cd apps/backend
pytest dispatch/tests/integration/test_projects_yml_bootstrap.py -v
```

Expected: pass. If it fails because `/projects` returns an unexpected shape, adjust the assertion to match what `dispatch/api/projects.py` actually returns (do not modify the route — Phase 4 will redesign it).

- [ ] **Step 8.3: Run the full integration suite + the existing pytest suite**

```bash
cd apps/backend
pytest
```

Expected: all green.

- [ ] **Step 8.4: Commit**

```bash
git add apps/backend/dispatch/tests/integration/test_projects_yml_bootstrap.py
git commit -m "test: assert projects.yml bootstrap still runs on boot"
```

---

## Task 9 — Phase 1 wrap-up and tag

**Why:** A clean checkpoint so Phase 2 has a known-good baseline.

**Files:** none beyond the tag.

- [ ] **Step 9.1: Run the full test suite one final time**

```bash
cd apps/backend
pytest -v
```

Expected: all passing.

- [ ] **Step 9.2: Verify a clean tree**

```bash
cd /mnt/data/repos/markdavidgan/dispatch
git status
```

Expected: `nothing to commit, working tree clean`.

- [ ] **Step 9.3: Move the plan to completed**

```bash
mkdir -p docs/plans/completed/2026-05
git mv docs/plans/2026-05-23-dispatch-phase-1-foundation.md docs/plans/completed/2026-05/
```

Edit `docs/plans/README.md`: move the Phase 1 line from Active to Completed.

```bash
git add docs/plans/README.md
git commit -m "docs(plans): archive Phase 1 foundation as completed"
```

- [ ] **Step 9.4: Tag the release**

```bash
git tag -a v0.1.0-phase1 -m "Phase 1: Foundation — standalone backend boots cleanly"
```

Phase 1 done. Next: write `docs/plans/<date>-dispatch-phase-2-frontend-pivot.md`.

---

## Acceptance Criteria

Phase 1 is complete when ALL of these are true:

- [ ] `git clone && cd apps/backend && pip install -r dispatch/requirements.txt && DISPATCH_MASTER_KEY=x uvicorn dispatch.main:app` works without further configuration and `/health` returns 200.
- [ ] `DISPATCH_MASTER_KEY=x docker compose up --build` works and `/health` returns 200 from `localhost:10060`.
- [ ] `pytest` in `apps/backend/` returns all green.
- [ ] `grep -rn "cf_access" apps/backend/ --include="*.py"` returns zero output.
- [ ] Booting without `DISPATCH_MASTER_KEY` fails fast with the documented error.
- [ ] `README.md` documents both local-dev and Docker Compose paths.
- [ ] `CLAUDE.md` exists with the no-app-auth + doc-conventions invariants.
- [ ] The plan is archived to `docs/plans/completed/2026-05/`.
- [ ] Tag `v0.1.0-phase1` exists.
