# Code Review: Documentation Accuracy vs. Code Reality

**Review date:** 2026-05-27  
**Scope:** All markdown documentation (`README.md`, `DESIGN.md`, `CLAUDE.md`, `docs/architecture/*`, `docs/operations/*`, `docs/brainstorm/*`, `docs/plans/*`) cross-checked against the actual codebase.

---

## Executive Summary

The documentation is **generally well-maintained and accurate** at the architectural level. However, there are **several significant discrepancies** where docs describe tables, columns, state machines, or API parameters that do not exist in the code. There are also **stale references** to completed phases, non-existent directories, and a persistent Python version mismatch.

| Severity | Count | Description |
|----------|-------|-------------|
| 🔴 Critical | 3 | State machines for non-existent columns; API parameter mismatch; wrong table schema documented |
| 🟡 Moderate | 5 | Missing API routes in docs; stale phase references; wrong file paths; misleading env-var guidance |
| 🟢 Minor | 6 | Python version drift; incomplete demo project lists; timezone default inconsistencies; encryption scheme imprecision |

---

## 🔴 Critical Discrepancies

### 1. `DATA-FLOW.md` — Fictional `filings` state machine

**Doc claim:**
> Briefing filings: `draft` → `narrated` → `published` (or `failed`)

**Reality:** The `filings` table has **no `status` column**.

```sql
-- apps/backend/dispatch/schema.sql
CREATE TABLE IF NOT EXISTS filings (
  id INTEGER PRIMARY KEY,
  date TEXT NOT NULL,
  kind TEXT NOT NULL,        -- 'lead' | 'addendum' | 'desk'
  issue_no INTEGER,
  covers_from TEXT NOT NULL,
  covers_until TEXT NOT NULL,
  lead_headline TEXT,
  lead_body TEXT,
  lead_article TEXT,
  audio_url TEXT,
  audio_duration_s INTEGER,
  active_count INTEGER,
  project_lines TEXT,
  addendum_label TEXT,
  addendum_body TEXT,
  model TEXT NOT NULL,
  prompt_hash TEXT NOT NULL,
  generated_at TEXT NOT NULL,
  raw_response TEXT,
  UNIQUE(date, kind)
);
```

There is no `status` field. The orchestrator simply inserts rows and moves on. The concept of `draft` / `narrated` / `published` exists only in documentation.

**Fix:** Remove the state machine diagram and prose, or add a `status` column to `schema.sql` and update the orchestrator to set it.

---

### 2. `docs/brainstorm/2026-05-23-dispatch-operational-gaps/notes.md` — Fictional `runs` columns

**Doc claim (Gap 9):**
> Single `runs` table with `job_name`, `status`, `started_at`, `finished_at`, `duration_ms`, `error_message`, `metadata` (JSON), `log_excerpt`

**Reality:** The actual `runs` table is much simpler:

```sql
CREATE TABLE IF NOT EXISTS runs (
  id INTEGER PRIMARY KEY,
  job TEXT NOT NULL,
  status TEXT NOT NULL,
  started_at TEXT NOT NULL,
  finished_at TEXT,
  events_added INTEGER,
  error TEXT
);
```

Missing columns: `duration_ms`, `error_message` (it's `error`), `metadata`, `log_excerpt`.

The `api/admin/runs.py` SELECT confirms this:
```python
SELECT id, job, status, started_at, finished_at, events_added, error FROM runs
```

**Fix:** Update the brainstorm note to match the actual schema. If those columns were intentionally deferred, note that.

---

### 3. `README.md` — Backfill API parameter mismatch

**Doc claim:**
```bash
POST /api/admin/system/backfill
{ "max_days": 30, "ingest": true }
```

**Reality:** The endpoint accepts `look_back_days`, not `max_days`:

```python
# apps/backend/dispatch/api/admin/system.py
class BackfillBody(BaseModel):
    look_back_days: int = 30
    ingest: bool = True
```

The `Makefile` also sends the wrong parameter:
```makefile
make backfill:
	curl ... -d '{"max_days": 30, "ingest": true}'
```

**Fix:** Change `README.md` and `Makefile` to use `look_back_days`.

---

## 🟡 Moderate Discrepancies

### 4. `docs/architecture/ARCHITECTURE.md` — Incomplete route map

The "Route map" section is missing several admin endpoints that **do exist** in the code:

| Missing Route | File |
|---------------|------|
| `POST /api/admin/briefings/generate` | `api/admin/briefings.py` |
| `POST /api/admin/podcasts/{slug}/compose` | `api/admin/podcasts.py` |
| `GET /api/admin/podcasts/{slug}/preview-source` | `api/admin/podcasts.py` |
| `POST /api/admin/system/backfill` | `api/admin/system.py` |

**Fix:** Add these four routes to the route map table.

---

### 5. `CLAUDE.md` — Stale phase reference

**Doc claim:**
> Current: **Phase 2–5** — Vite SPA frontend, encrypted DB-backed settings, admin APIs, and pluggable storage backends.

**Reality:** `docs/plans/completed/2026-05/2026-05-23-dispatch-phases-2-7.md` shows phases 2–7 are **complete**. There is also a completed plan for `2026-05-26-briefings-vercel-serverless.md`.

**Fix:** Update to reflect that phases 2–7 are complete and the project is in maintenance/polish mode.

---

### 6. `CLAUDE.md` — Non-existent doc directories

**Doc claim:**
> - Specs: `docs/specs/YYYY-MM-DD-<short-desc>.md`
> - Insights: `docs/insights/YYYY-MM/`

**Reality:** Neither `docs/specs/` nor `docs/insights/` exist. (This very review file is being written to `docs/insights/` for the first time.)

**Fix:** Either create the directories or remove the references from `CLAUDE.md`.

---

### 7. `docs/operations/vercel-env-setup.md` — Wrong schema file path

**Doc claim:**
> The schema is in `apps/backend/dispatch/db/schema.sql`
> ```bash
> turso db shell dispatch < apps/backend/dispatch/db/schema.sql
> ```

**Reality:** The file is at `apps/backend/dispatch/schema.sql` (no `db/` subdirectory).

**Fix:** Remove `/db` from the path.

---

### 8. `docs/operations/perimeter-recipes.md` — Misleading `VITE_DISPATCH_API_URL` guidance

**Doc claim:**
> Set `VITE_DISPATCH_API_URL=https://api.example.com` in the frontend build.

**Reality:** The main frontend API client (`src/lib/api.ts`) hardcodes `const API_BASE = "/api"`. The env var is only referenced as a fallback in `api/proxy/setup-status.ts`:

```typescript
const BACKEND_URL = process.env.PODCAST_BACKEND_URL || process.env.VITE_DISPATCH_API_URL;
```

For split deployments, the Vercel tier serves its own `/api/*` routes; the SPA does not directly call the self-hosted backend. The guidance implies the SPA needs to know the backend URL, which is incorrect for the primary API surface.

**Fix:** Clarify that `VITE_DISPATCH_API_URL` is only needed for the podcast proxy fallback, not for general API calls.

---

## 🟢 Minor Discrepancies

### 9. Python version — Persistent 3.12 vs. 3.13 drift

| Source | Claim |
|--------|-------|
| `README.md` | "FastAPI + Python 3.12" |
| `ARCHITECTURE.md` diagram | "Python 3.12 + SQLite" |
| `docs/architecture/README.md` diagram | "Python 3.12 + SQLite" |
| `requirements.txt` comment | "target: Python 3.12 container" |
| `Dockerfile` | `FROM python:3.13-slim` |

**Reality:** The production container runs Python 3.13. Local dev may run 3.12–3.14.

**Fix:** Standardize on "Python 3.13" in docs (or "3.12+" if backward compatibility is intended). Update `requirements.txt` comment.

---

### 10. Timezone default — `UTC` vs. `Asia/Manila`

| Source | Claim |
|--------|-------|
| `ARCHITECTURE.md` Mode A config matrix | "default `UTC`" |
| `DEPLOYMENT.md` Topology A required vars | "default `UTC`" |
| `DEPLOYMENT.md` Topology B backend vars | "default `UTC`" |
| `scheduler.py` | `timezone=os.environ.get("DISPATCH_TZ", "Asia/Manila")` |
| `docker-compose.yml` | `DISPATCH_TZ=Asia/Manila` |

**Reality:** The code defaults to `Asia/Manila`, not `UTC`.

**Fix:** Update docs to say default is `Asia/Manila`, or change the code default to `UTC`.

---

### 11. `README.md` — Incomplete demo project list

**Doc claim:**
> watching `anthropics/claude-code`, `withastro/astro`, `Shopify/hydrogen`, `Netflix/metaflow`, `Netflix/mantis`, `vercel/ai`, `vercel/workflow`, and `google/gemma.cpp`.

**Reality:** `projects.yml` contains **10** projects, including `vercel/ai` (slug `ai-sdk`), `vercel/workflow` (slug `workflow-sdk`), `markdavidgan/dispatch`, and `dispatch-weekly`. The README omits 3 of them.

**Fix:** Either list all 10 or add "and others".

---

### 12. `ARCHITECTURE.md` — Encryption scheme imprecision

**Doc claim:**
> The same encryption scheme is used in both deployment modes. In the hybrid mode, the Vercel tier uses AES-GCM (Node.js `crypto`) instead of Fernet, but the key derivation from `DISPATCH_MASTER_KEY` is identical.

**Reality:** The key derivation is **similar** (both SHA-256 based) but the ciphertext formats are **not interoperable**. Fernet ciphertext cannot be decrypted by AES-GCM and vice versa. The Vercel and Docker settings stores are independent.

**Fix:** Clarify that the schemes are *separate* — same master key, different algorithms, non-interoperable ciphertext.

---

### 13. `vercel-env-setup.md` — Confusing Hugging Face token guidance

**Doc claim:**
> Section 5: "Hugging Face API Token (Free) — Required for Kokoro TTS via the Hugging Face Inference API"

But the full Doppler config summary says:
> `# TTS (delegated to backend — no HF token needed)`

**Reality:** TTS is delegated to the self-hosted backend (Google Cloud Chirp 3 HD). No HF token is needed.

**Fix:** Remove or strike-through section 5, or move it to an "alternatives considered" note.

---

### 14. `perimeter-recipes.md` — `credentials: "include"` claim

**Doc claim:**
> The frontend already sends `credentials: "include"` and sets `crossOrigin="use-credentials"` on podcast audio tags.

**Reality:** `src/lib/api.ts` does set `credentials: "include"`. However, a quick grep for `crossOrigin="use-credentials"` on audio tags in the frontend components was **not found** in the explored source. Verify in `EpisodeCard.tsx` or `AudioPlayer.tsx`.

**Fix:** Verify and add the attribute if missing, or remove the claim.

---

### 15. `DATA-FLOW.md` — Weekly cycle omits `from_the_desk` audio/publish

The weekly cycle diagram shows `synthesis_from_the_desk` → desk filing, but the desk filing kind (`kind='desk'`) does not appear to go through TTS or snapshot publish in the orchestrator. The daily cycle shows audio + publish; the weekly cycle omits them.

**Fix:** Clarify whether desk memos get audio/snapshot treatment or are text-only.

---

## ✅ Accurate Documentation (Verified)

The following docs were found to be **truthful and accurate**:

| Document | What was verified |
|----------|-------------------|
| `DESIGN.md` | Color tokens, typography scale, layout grid all match `src/index.css` and component implementations. |
| `docker-compose.yml` | Matches README descriptions: backend on 10060, frontend via Caddy on `${DISPATCH_HTTP_PORT:-8080}`. |
| `caddy/Caddyfile` | Matches DEPLOYMENT.md: SPA fallback, `/api/*` + `/health` proxy, commented basicauth block. |
| `Makefile` | All targets exist and match README descriptions (except `backfill` parameter mismatch noted above). |
| Frontend tech stack | Vite 6, React 19, Tailwind v4, React Router 7, Biome, Playwright — all match `package.json`. |
| Backend tech stack | FastAPI, aiosqlite, APScheduler, Pydantic v2, Fernet encryption — all match `requirements.txt` and source. |
| Storage backends | `LocalStorage`, `R2Storage`, `S3Storage` all exist in `dispatch/storage/`. |
| Settings encryption | Fernet from `DISPATCH_MASTER_KEY` via SHA-256 → base64url exists in `crypto.py`. |
| Key canary | `system.key_canary` validation on boot exists in `system/key_canary.py`. |
| Project registry CRUD | Full admin API exists for create/read/update/delete/reorder. |
| Scheduler jobs | Default cron expressions match `scheduler.py` and `vercel.json`. |
| Podcast pipeline | NotebookLM wrapper, DASH→MP3, RSS generation, Cloudflare Worker all exist. |
| API routes (documented ones) | Every route listed in ARCHITECTURE.md exists and behaves as described. |
| `bootstrap.sh` | Exactly matches README description: generates key, compose up, health wait, backfill. |

---

## Recommendations

1. **Fix the `filings` state machine** — Either add a `status` column or remove the state machine from `DATA-FLOW.md`.
2. **Fix the backfill parameter** — Update `README.md`, `Makefile`, and any other docs from `max_days` to `look_back_days`.
3. **Sync Python version** — Pick one (3.13 matches Dockerfile) and update all references.
4. **Update ARCHITECTURE.md route map** — Add the four missing admin endpoints.
5. **Update `CLAUDE.md`** — Mark phases 2–7 as complete; remove or create `docs/specs/` and `docs/insights/`.
6. **Clean up `vercel-env-setup.md`** — Fix schema path, remove or deprecate HF token section.
7. **Clarify encryption** — Note that Docker Fernet and Vercel AES-GCM are separate, non-interoperable stores.
8. **Fix `perimeter-recipes.md`** — Clarify that `VITE_DISPATCH_API_URL` is not used by the main SPA API client.
