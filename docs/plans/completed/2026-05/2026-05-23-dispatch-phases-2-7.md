# Dispatch — Phases 2–7 Master Implementation Plan

> **Status:** Complete. All phases implemented end to end.

## Phase 1: Foundation ✅
- Standalone backend boots cleanly
- `DISPATCH_MASTER_KEY` boot-gate
- `cf_access` removed
- pytest suite green
- Docker Compose smoke test passing

## Phase 2: Vite SPA Frontend + Perimeter Recipes ✅
- Replaced Next.js frontend with Vite + React 19 + Tailwind v4 + React Router
- Ported all public pages: `/`, `/briefings`, `/briefings/:date`, `/projects`, `/projects/:slug`, `/projects/archive`, `/podcasts`, `/podcasts/:slug`
- Ported all components: Masthead, Numeral, LeadHero, Addendum, ProjectList, AudioPlayer, RefreshButton, FilingTicker, EventStream, FromTheDesk, MentionedInBriefings, LeadArticle, SectionLabel, EpisodeCard, PodcastSubscribeBlock
- Added admin routes: `/admin`, `/admin/projects`, `/admin/settings`, `/admin/runs`
- Added `/setup` wizard
- Client-side data fetching via thin API client
- Created `caddy/Caddyfile` for all-in-one deployment
- Created `docs/operations/perimeter-recipes.md`

## Phase 3: Frontend-Driven Configuration ✅
- Added `settings` table (key/value, encrypted at rest with Fernet)
- Added `schedules` table (configurable cron)
- Added `system` table (key canary)
- Created `dispatch/crypto.py` (Fernet encryption)
- Created `dispatch/system/key_canary.py` (validate master key on boot)
- Created admin APIs: `/api/admin/settings`, `/api/admin/schedules`, `/api/admin/system/*`
- Settings store with convenience accessors for AI, TTS, GitHub, storage, web

## Phase 4: Project Registry CRUD ✅
- Enhanced `projects` table: `sort_order`, `created_at`, `summary`, `podcast_config`
- Admin API: `/api/admin/projects` (CRUD + reorder)
- Made `projects.yml` bootstrap conditional (only if DB is empty)
- Frontend `/admin/projects` page

## Phase 5: Storage Abstraction ✅
- Created pluggable storage backends: `LocalStorage`, `R2Storage`, `S3Storage`
- Created `/api/snapshot` serves snapshot JSON directly
- Created `/api/audio/{key}` serves audio (302 presigned URL or FileResponse)
- Updated `publish/r2.py` to delegate to storage backend when available
- Frontend fetches snapshot/audio through backend only

## Phase 6: Enhanced Ingest ✅
- Created `dispatch/ingest/github_commits.py` for branch-aware commit ingest
- Lists all branches, fetches commits per branch, deduplicates across branches
- New event kind: `commit` with branch metadata
- Wired into scheduler as `ingest_github_commits` job (hourly)

## Phase 6b: NotebookLM Session Management ✅
- DB-backed `notebooklm_session` encrypted setting
- Updated `notebooklm_wrapper.py` to accept inline storage_state JSON
- Pre-flight probe (`_probe_notebooklm`) — returns ok/transient/auth
- Graceful degradation in `podcast/intake.py`: skips episode if session missing/expired, logs status

## Phase 7: Polish + Deploy ✅
- Frontend builds successfully (`npm run build` → `dist/`)
- Backend tests all green (113 passed)
- Updated `docker-compose.yml` with frontend service (Caddy)
- Updated `README.md` with current architecture
- Created `docs/operations/perimeter-recipes.md`
- CORS middleware with configurable origins

## Acceptance
- [x] `git clone && cd apps/backend && pip install -r dispatch/requirements.txt && DISPATCH_MASTER_KEY=x uvicorn dispatch.main:app` works
- [x] `DISPATCH_MASTER_KEY=x docker compose up --build` works
- [x] `pytest` in `apps/backend/` returns all green
- [x] `npm run build` in `apps/frontend/` succeeds
- [x] No production code references to `cf_access`
- [x] Booting without `DISPATCH_MASTER_KEY` fails fast
- [x] README documents local-dev, Docker Compose, and key management
- [x] Admin APIs exist for settings, projects, schedules, runs, system
