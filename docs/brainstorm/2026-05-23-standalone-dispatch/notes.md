# Dispatch — Standalone Extraction Brainstorm

> **⚠️ Superseded.** This document is preserved for original context. The decisions in §2 (built-in authentication) and §10/Key Decision #3 (Next.js frontend) have been replaced by the [operational-gaps follow-up](../2026-05-23-dispatch-operational-gaps/notes.md):
> - **No app-layer authentication.** Perimeter-trusting only (Cloudflare Access, Tailscale, Caddy basic auth, Authelia).
> - **Frontend is a Vite SPA** + React Router, not Next.js.
>
> Read the operational-gaps document first for current source of truth.

## Date
2026-05-23

## Context
Extract the Dispatch app from the `marklab` monorepo into a standalone, self-hosted product at `github.com:markdavidgan/dispatch`. Each deployed instance is independent: it watches a user-configurable registry of GitHub repos, synthesizes daily briefings + audio, and produces weekly podcasts. All configuration (repo registry, API keys, credentials) happens through the frontend admin UI.

---

## What We Keep (Exact)

### Visual Design
- **100% identical** — no design changes. The editorial/newsroom aesthetic (paper `#f9f7f2`, ink `#0b0b0e`, signal red `#ff2a2a`) is the product's identity.
- Same typography: Inter Tight (400–800) + JetBrains Mono.
- Same layout: asymmetric 8fr/3fr grid, fixed left ticker rail, sticky header with on-air dot.
- Same motion: CSS keyframe animations with `prefers-reduced-motion` respect.
- Same components: Masthead, LeadHero, Numeral, ProjectList, AudioPlayer, FilingTicker, etc.

### Backend Architecture (Preserve Where Possible)
- FastAPI + Uvicorn (ASGI)
- SQLite (WAL mode) — no PostgreSQL, no Redis, no message queue
- APScheduler in-process cron
- Pydantic v2 for settings and schemas
- Same synthesis pipeline: two-pass (Article → Lead), deterministic bullets, brief lint, optional critic
- Same audio pipeline: Google Chirp 3 HD TTS → ffmpeg concat → loudnorm → -16 LUFS
- Same podcast pipeline: Jinja2 → NotebookLM → DASH → MP3 → RSS
- Same publish pipeline: HMAC-signed JSON snapshot

---

## What Changes (Architectural Shifts)

### 1. Project Registry: YAML → Frontend-Driven DB

**Current:** `projects.yml` is hand-edited, loaded at startup, synced to DB.

**New:** Frontend admin panel provides CRUD for the registry. Each project entry:
- `slug` — unique identifier
- `display_name` — override or auto-resolved
- `github_repo` — `owner/repo` format
- `status` — active / held / archived
- `kind` — app / tool / service / meta / agents / site
- `summary` — optional description
- `podcast_config` — optional podcast settings (title, description, cron, cover art URL)

**API additions:**
- `GET /api/admin/projects` — list all projects
- `POST /api/admin/projects` — create project
- `PATCH /api/admin/projects/{slug}` — update project
- `DELETE /api/admin/projects/{slug}` — archive/delete project
- `POST /api/admin/projects/reorder` — change display order

**DB migration:** Add `sort_order` and `created_at` to `projects` table. Drop `local_path` (no longer needed — see §3).

### 2. Authentication: Cloudflare Access → Perimeter-Trusting (Superseded)

> **Update:** This section was replaced by the operational-gaps follow-up. The app does **not** implement built-in authentication. Instead, it trusts its deployment perimeter (Cloudflare Access, Tailscale, Caddy basic auth, Authelia). See the [operational-gaps brainstorm](../2026-05-23-dispatch-operational-gaps/notes.md) for the resolved design.

**Original idea (kept for context):** Built-in password-based auth with bcrypt + JWT sessions.

**Why it changed:** Perimeter auth is simpler, has no users/sessions tables, and works identically across all deployment shapes (all-in-one Docker, split Vercel+backend, Tailscale, etc.). Route prefixes (`/admin/*` and `/api/admin/*` vs public paths) let the perimeter apply policy.

### 3. Ingest: Local Git + GitHub API → GitHub API Only (with Daily Full Pull)

**Current:** Two ingest sources:
- `ingest/git.py` — local repos at `/repos/<slug>`, SHA cursor
- `ingest/github.py` — GitHub REST API, `updated_at` cursor

**New:** Single ingest source — GitHub API only. But enhanced:

#### 3a. Daily Full Repo Pull
Each day, for every configured repo:
1. **List all branches** via `GET /repos/{owner}/{repo}/branches`
2. **For each branch:** fetch commits since last check via `GET /repos/{owner}/{repo}/commits?sha={branch}`
3. **Deduplicate** commits across branches (same SHA = same commit)
4. **Store** as `commit` events with `branch` metadata in `meta` JSON

This replaces the local `git log` ingest and gives complete visibility into all active development branches.

#### 3b. Enhanced GitHub Ingest
Keep the existing GitHub API ingest for PRs, issues, releases — but extend it:
- **PRs:** include draft status, review count, mergeable status
- **Issues:** include labels, assignees, comments count
- **Releases:** include prerelease flag, asset count
- **Commits:** new endpoint for branch-aware commit ingest (§3a)

**New event kinds:**
- `commit` (now from GitHub API, not local git)
- `pr_opened`, `pr_merged`, `pr_closed`, `pr_draft_changed`
- `issue_opened`, `issue_closed`, `issue_reopened`
- `release_published`

**Cursor strategy:** Per-project, per-source cursors remain. For commits, cursor is `last_checked_at` timestamp + per-branch `last_sha`.

### 4. Storage: Hardcoded R2 → Configurable Storage Backend

**Current:** Cloudflare R2 is hardcoded everywhere (`publish/r2.py`). Audio and snapshots uploaded to R2. Frontend fetches snapshot directly from R2 REST API.

**New:** Pluggable storage backend configured via frontend admin:

**Supported backends:**
1. **Cloudflare R2** (default, for migration compatibility) — uses S3-compatible SDK
2. **AWS S3 / S3-compatible** (MinIO, Wasabi, etc.)
3. **Local filesystem** (for self-hosting without cloud storage)

**Configuration stored in DB:**
```sql
CREATE TABLE settings (
  key TEXT PRIMARY KEY,
  value TEXT NOT NULL,
  updated_at TEXT NOT NULL
);

-- Keys:
-- storage.provider = "r2" | "s3" | "local"
-- storage.endpoint = "..."
-- storage.bucket = "..."
-- storage.region = "..."
-- storage.access_key_id = "..."
-- storage.secret_access_key = "..." (encrypted at rest)
-- storage.public_base_url = "..."
```

**Frontend changes:**
- Snapshot fetched from backend API (`/api/snapshot`) instead of directly from R2
- Audio proxied through backend (`/api/audio/{key}`) instead of Next.js API route hitting R2 directly
- This removes all Cloudflare-specific env vars from the frontend — only `DISPATCH_API_URL` needed

### 5. AI Provider Keys: Env Vars → Frontend-Configurable

**Current:** `KIMI_OAUTH_JSON`, `ANTHROPIC_API_KEY`, `DISPATCH_AI_PROVIDER` are env vars.

**New:** Stored encrypted in DB, configurable via frontend admin Settings page.

```sql
-- settings keys:
-- ai.provider = "kimi" | "anthropic" | "openai"
-- ai.kimi_oauth_json = "..." (encrypted)
-- ai.anthropic_api_key = "..." (encrypted)
-- ai.model = "..."
-- ai.critique_enabled = "1" | "0"
```

**Encryption:** Use Fernet symmetric encryption with a master key from `DISPATCH_MASTER_KEY` env var. This is the ONE env var that remains required.

### 6. TTS Configuration: Env Vars → Frontend-Configurable

**Current:** `GCP_TTS_VOICE`, `GOOGLE_APPLICATION_CREDENTIALS`, `CARTESIA_API_KEY` are env vars.

**New:** Stored in `settings` table, configurable via frontend.

```
tts.provider = "google" | "cartesia" | "elevenlabs"
tts.google_credentials_json = "..." (encrypted)
tts.voice = "en-US-Chirp3-HD-Leda"
tts.cartesia_api_key = "..." (encrypted)
```

### 7. GitHub Token: Env Var → Per-Repo or Global in Frontend

**Current:** Single `GITHUB_TOKEN` env var.

**New:** Can be configured per-repo or globally:
- Global token: used for all repos unless overridden
- Per-repo token: for private repos or different organizations
- Stored encrypted in `settings` or `projects` table

```
github.global_token = "..." (encrypted)
-- OR per-project:
-- projects.github_token = "..." (encrypted, nullable)
```

### 8. Frontend: Read-Only → Read-Write Admin

**Current pages (keep all):**
- `/` — Home (daily briefing)
- `/briefings` — Archive
- `/briefings/[date]` — Detail
- `/projects` — Registry
- `/projects/[slug]` — Detail
- `/projects/archive` — Archived
- `/podcasts` — Podcast index
- `/podcasts/[slug]` — Episodes

**New admin pages:**
- `/admin` — Dashboard (system status, last runs, quick stats)
- `/admin/projects` — Project registry CRUD
- `/admin/settings` — All configuration:
  - Storage backend credentials
  - AI provider credentials
  - TTS credentials
  - GitHub token(s)
  - Schedule configuration (cron expressions)
  - Podcast settings
- `/admin/runs` — Job execution log viewer
- `/admin/users` — User management (if multi-user)

**New public pages:**
- `/login` — Authentication page
- `/setup` — First-time setup wizard (creates admin user, configures storage + AI)

### 9. Scheduling: Hardcoded Cron → Configurable

**Current:** Schedules are hardcoded in `scheduler.py`:
- Git ingest: every 15 min
- GitHub ingest: every 30 min
- Lead synthesis: daily 02:00
- Housekeeping: daily 03:30
- From-the-desk: Sunday 23:00
- Podcast: per-project cron in YAML

**New:** Configurable via frontend, stored in DB.

```sql
CREATE TABLE schedules (
  id INTEGER PRIMARY KEY,
  job_name TEXT UNIQUE NOT NULL,
  cron_expression TEXT NOT NULL,
  is_enabled INTEGER NOT NULL DEFAULT 1,
  last_run_at TEXT,
  next_run_at TEXT
);
```

Default schedules populate on first run. Users can tweak cron expressions or disable jobs.

### 10. Deployment Architecture

**Two supported shapes:**

1. **All-in-one (Docker Compose):**
   - Caddy reverse proxy serves the static SPA (`dist/`) and proxies `/api/*` to the backend
   - Single origin — no CORS needed
   - Ships with a commented `basicauth` block in `caddy/Caddyfile` for perimeter gating

2. **Split (static frontend + self-hosted backend):**
   - Frontend: static build deployed to Vercel, CDN, or any static host
   - Backend: Docker container (`python:3.12-slim` + ffmpeg)
   - CORS origins configured via admin UI (`settings.web.allowed_origins`)

**Backend (Self-hosted):**
- Docker container with the same base image (`python:3.12-slim` + ffmpeg + git)
- SQLite volume mounted for persistence
- Only required env var: `DISPATCH_MASTER_KEY` (for settings encryption)
- Optional: `PORT`, `HOST`, `DB_PATH`
- Can run on: Render, Railway, Fly.io, VPS, homelab

**Communication:**
- Frontend → Backend: HTTPS API calls (no auth headers — identity is handled by the perimeter)
- Backend → GitHub: HTTPS API with configured token
- Backend → AI providers: HTTPS API with configured keys
- Backend → Storage: S3-compatible API with configured credentials

---

## Open Questions / Decisions Needed

1. **Multi-tenancy?** Is each instance truly single-tenant (one admin), or do we need multi-user with roles (admin / viewer)?
   - *Lean toward single-admin for MVP. Multi-user can be a future enhancement.*

2. **Branch-aware commit ingest — scope?** Do we fetch ALL branches or only "active" ones (default branch + branches with recent activity)?
   - *Lean toward: default branch + branches with commits in last 30 days. Configurable per repo.*

3. **Podcast cover art storage?** Currently stored as local paths in the repo. In standalone, should cover art be uploaded to the configured storage backend?
   - *Yes — upload to storage backend, reference by URL.*

4. **NotebookLM dependency?** The podcast pipeline uses NotebookLM via `notebooklm-py`, which reverse-engineers Google's web UI. It requires a Playwright `storage_state.json` with Google session cookies. **This is viable for standalone deployment** because `notebooklm-py` supports the `NOTEBOOKLM_AUTH_JSON` environment variable — the entire storage state can be passed as inline JSON. No browser needed in the container.

   Important clarification: NotebookLM does NOT replace the LLM for analysis. The LLM (Kimi/Claude) does the hard work of reading raw commits/PRs/issues and synthesizing them into coherent prose (headline, dek, article). NotebookLM only narrates the pre-digested weekly markdown source. The standalone product absolutely still needs an LLM for daily brief synthesis.

   **Containerization strategy for NotebookLM:**
   - User runs `notebooklm login` once on their local machine → captures `storage_state.json`
   - Pastes the JSON into the Dispatch admin UI → backend encrypts with Fernet → stores in DB
   - At podcast runtime: decrypt → set `NOTEBOOKLM_AUTH_JSON` → `notebooklm-py` reads it directly
   - `refresh_auth()` auto-refreshes short-lived tokens on each API call
   - When session eventually expires (weeks/months), admin UI shows "re-authenticate" alert

   **Containerization status:**
   - ✅ **Kimi HTTP API:** Stateless, already containerized via `kimi-cli` + OAuth env var
   - ✅ **GCP Chirp HD TTS:** Standard Google Cloud API, container-friendly
   - ✅ **NotebookLM:** Container-friendly via `NOTEBOOKLM_AUTH_JSON` — requires one-time manual session setup per deployed instance

5. **Migration from marklab?** Do we need a migration path for existing marklab dispatch data?
   - *Nice-to-have. Can be a script that exports SQLite + projects.yml and imports into standalone.*

6. **Real-time updates?** Should the frontend have WebSocket/SSE for live status (ingest running, synthesis in progress)?
   - *Not for MVP. Polling the `/api/live` endpoint is sufficient.*

---

## Repository Structure

```
dispatch/
├── backend/
│   ├── dispatch/               # Main Python package
│   │   ├── main.py             # FastAPI entry point
│   │   ├── orchestrator.py     # Core pipeline
│   │   ├── scheduler.py        # APScheduler wiring
│   │   ├── schema.sql          # SQLite DDL
│   │   ├── schema_init.py      # Schema application + migrations
│   │   ├── api/                # FastAPI routers
│   │   │   ├── health.py
│   │   │   ├── auth.py         # NEW: login, logout, refresh
│   │   │   ├── admin/          # NEW: admin APIs
│   │   │   │   ├── projects.py
│   │   │   │   ├── settings.py
│   │   │   │   ├── schedules.py
│   │   │   │   ├── users.py
│   │   │   │   └── runs.py
│   │   │   ├── live.py
│   │   │   ├── brief.py
│   │   │   ├── briefings.py
│   │   │   ├── projects.py     # Public project listing
│   │   │   ├── podcast.py
│   │   │   └── snapshot.py     # NEW: serves snapshot JSON
│   │   ├── ingest/
│   │   │   ├── github.py       # Enhanced: branch-aware commits
│   │   │   └── git.py          # DEPRECATED: remove (replaced by github.py)
│   │   ├── synthesis/
│   │   ├── publish/
│   │   ├── audio/
│   │   ├── podcast/
│   │   ├── registry/
│   │   ├── storage/            # NEW: pluggable storage backends
│   │   │   ├── base.py
│   │   │   ├── r2.py           # S3-compatible
│   │   │   ├── s3.py           # S3-compatible (general)
│   │   │   └── local.py
│   │   ├── auth/               # NEW: auth utilities
│   │   │   ├── password.py     # bcrypt hashing
│   │   │   ├── jwt.py          # token creation/validation
│   │   │   └── middleware.py   # FastAPI dependency
│   │   └── crypto.py           # NEW: Fernet encryption for secrets
│   ├── core/                   # Shared utilities (extracted from marklab)
│   ├── tests/
│   ├── Dockerfile
│   ├── entrypoint.sh
│   └── requirements.txt
├── frontend/
│   ├── index.html              # Vite entry
│   ├── src/
│   │   ├── main.tsx            # React root
│   │   ├── App.tsx             # Router outlet
│   │   ├── router.tsx          # React Router config
│   │   ├── globals.css         # Tailwind v4 + design tokens
│   │   ├── pages/              # Route pages
│   │   │   ├── Home.tsx
│   │   │   ├── Briefings.tsx
│   │   │   ├── BriefingDetail.tsx
│   │   │   ├── Projects.tsx
│   │   │   ├── ProjectDetail.tsx
│   │   │   ├── Podcasts.tsx
│   │   │   ├── PodcastDetail.tsx
│   │   │   ├── AdminDashboard.tsx
│   │   │   ├── AdminProjects.tsx
│   │   │   ├── AdminSettings.tsx
│   │   │   ├── AdminSchedules.tsx
│   │   │   ├── AdminRuns.tsx
│   │   │   └── Setup.tsx
│   │   ├── components/         # Shared React components
│   │   ├── lib/
│   │   │   ├── api.ts          # Thin fetch wrapper (VITE_DISPATCH_API_URL)
│   │   │   ├── snapshot.ts     # Fetch snapshot from backend
│   │   │   └── ...
│   │   └── public/
│   ├── package.json
│   ├── vite.config.ts
│   ├── tsconfig.json
│   └── playwright.config.ts
├── docker-compose.yml          # Standalone compose for self-hosting
├── README.md
└── docs/
    └── brainstorm/
        └── 2026-05-23-standalone-dispatch/
            └── notes.md         # This file
```

---

## Phase Breakdown (Suggested)

### Phase 1: Foundation
- [ ] Clean extraction from marklab (done — source copied)
- [ ] Fix import paths (remove `apps.backend.` prefix, adjust `core` imports)
- [ ] Get backend running standalone with existing functionality
- [ ] Get frontend running standalone with existing functionality
- [ ] Docker Compose setup for local dev

### Phase 2: Frontend Pivot + Perimeter Recipes
- [ ] Scaffold `apps/frontend/` as Vite + React 19 + Tailwind v4 + React Router
- [ ] Port all components and pages from Next.js to React Router
- [ ] Add admin routes: `/admin`, `/admin/projects`, `/admin/settings`, `/admin/runs`
- [ ] Add `/setup` wizard
- [ ] Client-side data fetching via thin API client
- [ ] Delete old Next.js frontend code
- [ ] Write `docs/operations/perimeter-recipes.md`
- [ ] Write `caddy/Caddyfile`

### Phase 3: Frontend-Driven Configuration
- [ ] Add `settings` table + crypto layer
- [ ] Build Settings page (AI, TTS, GitHub, Storage)
- [ ] Migrate env-var config to DB-backed config
- [ ] Add `schedules` table + configurable cron UI

### Phase 4: Project Registry CRUD
- [ ] Add admin project CRUD API
- [ ] Build `/admin/projects` page
- [ ] Remove `projects.yml` dependency
- [ ] Update ingest to use DB registry

### Phase 5: Storage Abstraction
- [ ] Build pluggable storage backends
- [ ] Migrate snapshot + audio publishing
- [ ] Update frontend to fetch via backend API

### Phase 6: Enhanced Ingest
- [ ] Branch-aware GitHub commit ingest
- [ ] Daily full-repo pull
- [ ] Enhanced PR/issue metadata

### Phase 6b: NotebookLM Session Management
- [ ] Add `notebooklm_session` encrypted setting to DB
- [ ] Build admin UI for pasting/uploading `storage_state.json`
- [ ] Update `entrypoint.sh` to hydrate `NOTEBOOKLM_AUTH_JSON` from DB setting (not bind-mount)
- [ ] Graceful degradation when session is missing/expired (skip podcast job, alert admin)
- [ ] Test podcast pipeline end-to-end in Docker container without host bind-mounts

### Phase 7: Polish + Deploy
- [ ] E2E tests (Playwright)
- [ ] SQLite nightly backup job
- [ ] Restore runbook
- [ ] Migration script from marklab
- [ ] Documentation polish
- [ ] Docker image publish ready

---

## Key Technical Decisions (Made)

1. **SQLite stays.** No migration to PostgreSQL. The app is designed for single-instance, moderate data volume. SQLite + WAL is perfect.
2. **No Redis, no Celery, no message queue.** APScheduler in-process is sufficient and keeps the architecture minimal.
3. **Frontend is Vite SPA + React 19 + Tailwind v4 + React Router.** The editorial design (`DESIGN.md`) is sacred; only the framework shell changed from Next.js.
4. **Backend is FastAPI + Python 3.13.** No framework changes.
5. **No app-layer authentication.** The app trusts its deployment perimeter. No users table, no JWT, no bcrypt.
6. **Storage is pluggable but S3-compatible first.** R2, S3, MinIO all speak the same protocol. Local filesystem for dev/testing.
7. **Secrets are encrypted at rest with Fernet.** Master key from single env var. All other config lives in DB.

---

## Notes

- The existing `core/` module from marklab (`config.py`, `db.py`, `cf_access.py`, `logging.py`) is copied into the new repo. `cf_access.py` was removed in Phase 1 — the app is perimeter-trusting with no Cloudflare Access dependency.
- The existing `ingest/git.py` (local git log parsing) should be **removed** in Phase 6 since all ingest moves to GitHub API. The `local_path` field in `projects` should be dropped.
- The `kimi-config.toml` and `skills/creative-writing/` directory are Kimi-specific artifacts. Keep them for the synthesis pipeline but document that they're optional.
- The podcast cover art assets (`podcast/assets/`) should be moved to configurable URLs (uploaded via admin UI to storage backend) rather than baked into the container.
