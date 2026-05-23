# Dispatch — Operational Gaps Brainstorm (Follow-up)

## Date
2026-05-23

## Context
Follow-up to `docs/brainstorm/2026-05-23-standalone-dispatch/notes.md`. That brainstorm produced a strong "what we keep / what we change" north star but was thin on operational and security-critical edges. This session resolves those gaps so a spec can be written.

## Frame-Setting Decisions (Made This Session)

These decisions are upstream of every gap below and override or refine the original brainstorm:

1. **Audience: single-admin self-hosted.** Two private instances for the author (personal + revamplabs), plus a public showcase repo for others to self-host. No multi-tenancy, no in-app RBAC.
2. **Deployment-agnostic.** The repo supports two shapes without forking:
   - **All-in-one:** frontend + backend in one `docker-compose.yml`, served from one origin via a Caddy/Nginx reverse proxy. Closest-to-zero setup, ideal for showcase reviewers.
   - **Split:** static frontend on Vercel + backend self-hosted (the author's pattern). Both sit behind a shared perimeter (e.g., `*.markdavidgan.com` proxied through Cloudflare) so a single cookie covers both.
3. **Frontend: Vite + React 19 + Tailwind v4 + React Router.** Replaces the Next.js 15 choice from the prior brainstorm. The reader pages are a JSON-snapshot viewer and the admin pages are perimeter-gated — neither needs SSR. Vite gives instant client-side navigation, no SSR cold-starts, and a faster dev loop. The editorial design tokens (`DESIGN.md`) and component shapes carry over verbatim; only the framework shell changes.
4. **No app-layer authentication.** The app trusts its deployment perimeter (Cloudflare Access, Tailscale, Caddy basic auth, Authelia, etc.). No login page, no `users` / `sessions` tables, no JWT, no bcrypt, no refresh-token flow. Route prefixes (`/admin/*`, `/api/admin/*` vs public reader paths) let the perimeter apply policy. This supersedes §2 of the prior brainstorm.

---

## Resolved Gaps

### Gap 1 — Setup wizard sequencing

**Resolution.** Wizard lives at `/setup`. First-boot detection: backend exposes `GET /api/admin/setup-status` → `{ ai: bool, tts: bool, github: bool, storage: bool, has_projects: bool }`. Frontend redirects to `/setup` when any required-for-action setting is unconfigured AND the user attempts an action that requires it (or on first visit if `storage` and `ai` are both empty).

Wizard step order, all independently skippable, all re-enterable from `/admin/settings`:

1. **Storage backend** — defaults to **local filesystem** with a path on the mounted volume. Zero external credentials required to complete the wizard. Operator can swap to R2/S3 later.
2. **AI provider** — Kimi / Anthropic / OpenAI + key. Skipping → soft banner "Synthesis disabled — configure an AI provider to generate briefings."
3. **TTS provider** — Google / Cartesia / ElevenLabs + key. Skipping → soft banner "Audio narration disabled."
4. **GitHub token** — global token. Skipping → soft banner "Ingest disabled — add a GitHub token to monitor repositories." Per-repo token override available later via project edit.
5. **First project** — optional from the wizard; admin can add later via `/admin/projects`.

There is **no user creation step.** Anyone reaching `/setup` past the perimeter is implicitly the admin. See Gap 3.

**Acceptance.** A fresh container with only `DISPATCH_MASTER_KEY` set can boot, complete the wizard using local filesystem storage + a single AI provider key, add one project, and produce a first briefing on the next ingest tick — with no other env vars.

---

### Gap 2 — `DISPATCH_MASTER_KEY` lifecycle

**Resolution.** One env var. Mandatory. The app refuses to boot without it, with an explicit error referencing the key-management section of the README.

**Canary validation.** On startup, the app checks for `settings.system.key_canary`:

- **If absent** (first ever boot for this DB): write `settings.system.key_canary = fernet_encrypt(master_key, "dispatch-canary-v1")` and proceed.
- **If present**: attempt decryption with the current `DISPATCH_MASTER_KEY`. On failure, refuse to boot with `MASTER_KEY_MISMATCH: settings in this database were encrypted with a different key`. On success, proceed.

This prevents the silent failure mode where a wrong key would encrypt new settings with one key while old settings remain unreadable.

**JWT signing key.** Not needed. The no-app-auth decision (Gap 3 / frame decision #4) eliminates JWTs from the app entirely.

**Rotation.** Admin endpoint `POST /api/admin/system/rotate-key`. Operator-driven flow:

1. Operator generates a new key, sets both env vars on next start: `DISPATCH_MASTER_KEY_OLD=<old>` and `DISPATCH_MASTER_KEY=<new>`.
2. Operator hits the endpoint. Backend decrypts every value in `settings` with the old key, re-encrypts with the new key, rewrites the canary, returns a count of rotated values.
3. Operator restarts with only `DISPATCH_MASTER_KEY=<new>` set. Next boot validates the new canary.

**Backup.** Explicitly the operator's responsibility, not Dispatch's. README "Key Management" section states verbatim: *"If you lose `DISPATCH_MASTER_KEY`, all encrypted settings (AI keys, TTS credentials, GitHub tokens, storage credentials, NotebookLM session) are unrecoverable. You will need to re-enter them via /admin/settings. Briefings, audio, snapshots, and projects are unaffected. Back up this key in a password manager."*

---

### Gap 3 — Cross-origin authentication

**Resolution.** App-layer auth is removed entirely (frame decision #4). What's left at the app layer is only CORS.

**CORS surface.** Backend reads `settings.web.allowed_origins` (JSON array). Configured via admin Settings page. Defaults:

- Dev: `["http://localhost:5173"]`
- Production all-in-one: `[]` (same-origin, CORS not needed)
- Production split: operator adds their Vercel domain(s) here

**Operator perimeter recipes.** Shipped in `docs/operations/perimeter-recipes.md`. Each recipe is copy-pasteable:

- **Cloudflare Access (author's pattern).** Both frontend and backend share an apex domain (`*.markdavidgan.com`). One CF Access application policy gates the apex with the operator's email allowlist. Cookie set at `.markdavidgan.com` covers all subdomains — Vercel frontend can `fetch(backend, { credentials: "include" })` and CF transparently authenticates.
- **Tailscale Funnel.** Backend exposed via Tailscale; only devices in the operator's tailnet reach it. Frontend either also on Tailscale or fully public.
- **Caddy basic auth (all-in-one default).** Repo ships a `caddy/Caddyfile` with a commented `basicauth` block matched against both `/admin/*` (SPA UI) and `/api/admin/*` (admin API). Both prefixes must be gated together — gating only the UI leaves the API open. Operator uncomments, runs `caddy hash-password`, fills it in.
- **Authelia.** Reverse-proxy-style config; gates `/admin/*` with forward auth.

**Invariant the backend code must enforce.** No code path in the backend checks "is this caller authenticated" or "is this caller an admin." Admin-only logic is gated by route prefix at the FastAPI router level — `/api/admin/*` routes are mounted on a separate router so the perimeter can apply different policy to them. The app's only job is to expose the prefixes clearly.

---

### Gap 4 — Audio (and large-asset) delivery

**Resolution.** No proxying of multi-MB MP3s through the backend twice.

- **R2 / S3 backends:** `GET /api/audio/{key}` returns `302` to a pre-signed URL with 1-hour TTL. The reader's `<audio>` tag follows the redirect transparently and gets bytes directly from storage with native HTTP Range support for seeking.
- **Local filesystem backend:** `GET /api/audio/{key}` streams the file directly via Starlette's `FileResponse`, which handles Range requests for seeking. The backend is the storage host, so there is no double hop to avoid.

Same URL from the frontend's perspective in both modes (`/api/audio/{key}`). The storage backend's interface exposes `audio_url(key, ttl) → str`:

- R2/S3 implementation returns an externally-presigned URL (used as the `302` target).
- Local-fs implementation returns `None`, signaling the endpoint to fall through to `FileResponse` instead of redirecting.

Snapshots are small JSON and stay served directly from `GET /api/snapshot` — no redirect.

---

### Gap 5 — GitHub rate-limit math

**Resolution.** Documented budget + defensive logging. No quota issue at expected scale.

Authenticated single-token quota: **5,000 req/hr.**

Estimated load per instance (20 active repos):
- Routine ingest every 15 min: per repo, 1 PRs page + 1 issues page + 1 releases page (all with `?since=` cursor) ≈ 3 reqs → 60 req/cycle → **240 req/hr**.
- Daily branch-aware commit pull: per repo, 1 branch-list + ~5 active branches × 1 commits-since page ≈ 6 reqs → **120 req/day** total, negligible.
- Total ≈ 245 req/hr at peak. **~5% of quota.** Comfortable.

Defensive measures:
- After every batch, log `X-RateLimit-Remaining` to the `runs.metadata` JSON.
- If remaining < 500, skip non-essential branches (everything except default) for the rest of the hour.
- On `403 X-RateLimit-Remaining: 0`, mark the run `failed_quota`, surface in `/admin/runs`, retry on next schedule.

Per-repo token override (already in the prior brainstorm) handles private repos in different orgs and shards quota across tokens if needed.

---

### Gap 6 — Snapshot privacy

**Resolution.** Public by default. The snapshot **is** the editorial brief; broadcasting it is the product premise.

- `GET /api/snapshot` requires no app-layer auth.
- HMAC signature (existing pattern preserved) is for tamper-evidence, not access control.
- An operator who wants a fully private instance simply puts the public paths behind the same perimeter that already gates `/admin/*`.
- A `settings.snapshot.public = "1"` toggle is reserved for a hypothetical future "app-level private mode" but is **not implemented in MVP**. (If the operator wants private, they use the perimeter — this is consistent with frame decision #4.)

---

### Gap 7 — NotebookLM failure semantics

**Resolution.** Pre-flight probe + categorized failure handling + no stale republish.

Before every weekly podcast run, the orchestrator calls a lightweight `notebooklm.ping()`. Three outcomes:

| Outcome | Action |
|---|---|
| **OK** | Proceed with podcast generation. |
| **Transient** (network / 5xx) | Retry 3× with exponential backoff (1s, 4s, 16s). If still failing, write `runs(job_name="publish_podcast", status="failed_transient")` and retry on next schedule. |
| **Auth** (401 / 403) | Write `runs(... status="failed_auth")`, set `settings.podcast.notebooklm_status = "expired"`, surface a persistent banner in `/admin` with a link to Settings → Podcast → "Re-authenticate". **Do not republish a stale episode.** |

The RSS feed stays exactly as it was — the prior episode remains, this week is simply missing. Subscribers see no error.

Recovery: operator runs `notebooklm login` locally, pastes the new `storage_state.json` into the admin UI, clears the `notebooklm_status` flag implicitly, next scheduled run picks up normally.

---

### Gap 8 — `projects.yml` → DB migration

**Resolution.** Bootstrap on first boot only, then ignored.

- First boot: if `projects` table is empty **and** `DISPATCH_BOOTSTRAP_PROJECTS=/path/to/projects.yml` env var is set and the file exists, parse it and insert each project. Log the count.
- After first boot, the env var is ignored. DB is the sole source of truth. No file watching, no re-sync.
- For greenfield deployments, no `projects.yml` is needed — admin starts at `/setup`, lands on `/admin/projects` after, adds projects via UI.
- **Marklab → standalone migration.** Separate one-shot script `scripts/migrate-from-marklab.py` that takes paths to a marklab SQLite dump and `projects.yml`, copies projects + briefings + events into the standalone DB. Documented in `docs/operations/migrate-from-marklab.md`. Run once, manually.

---

### Gap 9 — Runs / job-execution data model

**Resolution.** Single `runs` table, indexed for the `/admin/runs` filter UI.

```sql
CREATE TABLE runs (
  id INTEGER PRIMARY KEY,
  job_name TEXT NOT NULL,         -- "ingest_github" | "synthesize_lead" | "publish_podcast" | "publish_snapshot" | "backup_db" | ...
  status TEXT NOT NULL,           -- "running" | "succeeded" | "failed" | "failed_transient" | "failed_auth" | "failed_quota" | "skipped"
  started_at TEXT NOT NULL,
  finished_at TEXT,
  duration_ms INTEGER,
  error_message TEXT,
  metadata TEXT,                  -- JSON: { project_slug, event_count, rate_limit_remaining, ... }
  log_excerpt TEXT                -- last ~100 lines of structured log output for quick debug
);
CREATE INDEX idx_runs_job_started ON runs(job_name, started_at DESC);
CREATE INDEX idx_runs_status ON runs(status);
```

Retention: daily housekeeping job (Gap 10) prunes runs older than 30 days. Failed runs in the last 30 days always retained.

`/admin/runs` UI: filterable by job_name + status, sortable by started_at. Click → detail view shows full metadata JSON, log excerpt, and a link to the produced artifact (briefing slug, podcast episode, snapshot URL) parsed from metadata.

---

### Gap 10 — Backup / disaster recovery

**Resolution.** Nightly SQLite online-backup to the configured storage backend, plus a documented restore runbook.

**Backup job.** Runs daily at 03:00 (after housekeeping):

1. Open a fresh SQLite connection with `PRAGMA journal_mode=WAL` semantics intact.
2. Call SQLite's online backup API (`sqlite3_backup_init` / `sqlite3.Connection.backup` in Python) to copy the live DB into a temp file. Safe under concurrent reads/writes.
3. Gzip the temp file.
4. Upload to `backups/dispatch-YYYY-MM-DD.db.gz` via the configured storage backend.
5. Apply retention: keep last 30 daily backups + the 1st of each month for the last 12 months. Delete others.

**Storage objects (snapshots, audio, podcasts).** Rely on the storage backend's own versioning where available — R2 versioning, S3 versioning are operator-configurable. Local filesystem has no versioning; this is a documented limitation of the "demo" path. Operator can layer `restic` or `borg` over the local volume if they need protection.

**Master key.** Explicitly NOT backed up by Dispatch (re-stated for emphasis — see Gap 2).

**Restore runbook** in `docs/operations/restore.md`:

1. Download the latest `dispatch-YYYY-MM-DD.db.gz` from storage.
2. Gunzip into `dispatch.db`.
3. Stop the backend container, replace the SQLite file on the mounted volume.
4. Start with the **same** `DISPATCH_MASTER_KEY` that was active when the backup was taken (otherwise canary validation fails and the backend refuses to boot).
5. Verify by hitting `/api/admin/setup-status`.

---

## Updated Repository Touch Points

Relative to the original brainstorm's structure, the no-app-auth and Vite-SPA decisions delete or replace these:

**Deleted from `backend/dispatch/`:**
- `auth/password.py` — no bcrypt
- `auth/jwt.py` — no JWT
- `auth/middleware.py` — no auth dependency
- `api/auth.py` — no /login, /logout, /refresh
- `api/admin/users.py` — no users API

**Added to `backend/dispatch/`:**
- `system/key_canary.py` — first-boot canary write + validate
- `system/rotate_key.py` — rotation endpoint logic
- `system/backup.py` — nightly SQLite online backup job
- `api/admin/system.py` — `/api/admin/system/rotate-key`, `/api/admin/system/backup-now`

**Replaced `frontend/` (Next.js → Vite SPA):**
- `index.html`, `src/main.tsx`, `src/App.tsx` (Vite entry)
- `src/router.tsx` (React Router config; same route set as original brainstorm minus `/login` and `/setup`'s user-creation step)
- `src/lib/api.ts` (fetch wrapper that respects `VITE_DISPATCH_API_URL` build-time env, falls back to same-origin `/api`)
- Static build output to `dist/`; in all-in-one mode, Caddy serves `dist/` and proxies `/api/*` to the backend
- Tailwind v4 config + design tokens carry over verbatim from the Next.js extraction; React components ported one-for-one

**Added at repo root:**
- `caddy/Caddyfile` — default reverse-proxy config for all-in-one mode, with commented `basicauth` block on `/admin/*`
- `docs/operations/perimeter-recipes.md` — Cloudflare Access, Tailscale, Caddy basic auth, Authelia recipes
- `docs/operations/restore.md` — backup restore runbook
- `docs/operations/migrate-from-marklab.md` — one-shot migration script docs
- `scripts/migrate-from-marklab.py`

---

## Updated Phase Plan

The phase plan from the original brainstorm is amended:

- **Phase 2 (Auth + Admin Shell) is deleted.** Replaced by **Phase 2 (Frontend pivot + Perimeter recipes):** scaffold Vite SPA, port components from the Next.js extraction, write the perimeter recipes doc, ship the default Caddyfile.
- **Phase 3 (Frontend-Driven Configuration) is unchanged**, minus any auth-protection work. Admin routes are just routes under `/admin/*`; perimeter handles access.
- **Phase 6b (NotebookLM Session Management) gains:** the failure-categorization + admin banner from Gap 7.
- **New Phase 7b (Operations):** SQLite nightly backup + restore runbook + migration script.

---

## Open Questions Carried Forward

The original brainstorm's six open questions are resolved or reframed by this session:

1. **Multi-tenancy?** → Resolved. Frame decision #1: single-admin, no in-app multi-user. Perimeter handles identity.
2. **Branch-aware ingest scope?** → Resolved. Default branch + branches with commits in last 30 days, configurable per repo. Quota math in Gap 5 confirms this is well within budget.
3. **Podcast cover art?** → Resolved. Uploaded via admin UI to the storage backend, referenced by URL stored in `projects.podcast_config`.
4. **NotebookLM viability?** → Already resolved in the original brainstorm. This session adds failure semantics (Gap 7).
5. **Marklab migration?** → Resolved. One-shot script (Gap 8).
6. **Real-time updates?** → Not for MVP. Polling `/api/live` is sufficient. Unchanged.

No new open questions from this session.

---

## Cross-References

- Parent brainstorm: [`../2026-05-23-standalone-dispatch/notes.md`](../2026-05-23-standalone-dispatch/notes.md)
- Visual identity (immutable): [`../../../DESIGN.md`](../../../DESIGN.md)
- Next step: promote to `docs/specs/2026-05-23-standalone-dispatch.md`, then write `docs/plans/2026-05-23-standalone-dispatch.md`.
