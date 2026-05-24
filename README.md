# Dispatch

> A standalone, self-hosted **daily editorial brief generator** for software projects.
> Each instance watches a configurable registry of GitHub repositories, synthesizes a
> daily report with audio narration, and produces weekly podcasts.

Dispatch is deliberately built as a **single-admin per instance, perimeter-trusting**
application — no users table, no login page, no JWTs. Authentication lives at the
deployment perimeter (Cloudflare Access, Tailscale, Caddy basic auth, Authelia, etc.).
The only required environment variable is `DISPATCH_MASTER_KEY`; every other credential
is configured through the admin UI and encrypted at rest.

---

## Architecture at a glance

| Layer       | Stack                                                                   |
| ----------- | ----------------------------------------------------------------------- |
| Frontend    | Vite + React 19 + Tailwind CSS v4 + React Router (static SPA build)     |
| Backend     | FastAPI + Python 3.12 + aiosqlite (SQLite in WAL mode)                  |
| Scheduler   | In-process APScheduler — no Redis, no Celery                            |
| Storage     | Pluggable: local filesystem, Cloudflare R2, or S3-compatible            |
| AI          | Configurable providers — Kimi, Anthropic, OpenAI                        |
| TTS         | Google Cloud Chirp 3 HD (extension points for Cartesia / ElevenLabs)    |
| Reverse proxy | Caddy (ships in `docker-compose.yml`); any HTTP proxy works           |
| Perimeter   | Deployment-layer auth — see `docs/operations/perimeter-recipes.md`      |

For full diagrams and a layer-by-layer walkthrough, see **[docs/architecture/](docs/architecture/)**.

---

## Documentation

| Doc                                                                  | What it covers                                                                  |
| -------------------------------------------------------------------- | ------------------------------------------------------------------------------- |
| [`docs/architecture/`](docs/architecture/)                           | System architecture, data flow, deployment patterns, interactive HTML diagram   |
| [`DESIGN.md`](DESIGN.md)                                             | The editorial design system (typography, palette, layout invariants)            |
| [`docs/operations/perimeter-recipes.md`](docs/operations/perimeter-recipes.md) | Concrete perimeter-auth recipes for Cloudflare Access, Tailscale, Caddy, Authelia |
| [`docs/brainstorm/`](docs/brainstorm/)                               | Architecture brainstorms (design history — useful context, not specification)   |

---

## Repository layout

```
dispatch/
├── apps/
│   ├── frontend/      # Vite SPA — static build
│   └── backend/       # FastAPI app — Docker, encrypted settings, pluggable storage
├── caddy/             # Default reverse-proxy config (used by docker-compose)
├── docker-compose.yml # All-in-one stack (backend + caddy-served SPA)
├── docs/              # Architecture, design, operations, brainstorms
├── CLAUDE.md          # Repository-level agent instructions (internal)
├── DESIGN.md          # Editorial design system
└── README.md          # You are here
```

---

## Quick start

### One-command bring-up (recommended)

```bash
./scripts/bootstrap.sh
```

That script generates a `DISPATCH_MASTER_KEY` into `.env` if you don't have one,
brings up the docker compose stack, waits for the backend to report healthy,
then triggers an ingest + look-back synthesis backfill against the three
example projects shipped in `apps/backend/dispatch/projects.yml`
(`anthropics/claude-code`, `withastro/astro`, and `markdavidgan/dispatch`).

Visit:

- `http://localhost:8080/` — SPA
- `http://localhost:8080/health` — backend health
- `http://localhost:8080/api/projects` — backend API

Override the host port with `DISPATCH_HTTP_PORT=80`.

> Note: brief *generation* requires an AI provider key (Kimi, Anthropic, or
> OpenAI). The bootstrap script ingests events and primes the catch-up loop,
> but the first narrated brief only appears once you add a provider key under
> `/admin/settings` and re-run the backfill from `/admin` (or hit
> `POST /api/admin/system/backfill`).

### Manual Docker bring-up

```bash
export DISPATCH_MASTER_KEY=$(python -c "import secrets; print(secrets.token_urlsafe(32))")
docker compose up --build
```

The stack is two services:

- `dispatch-backend` — FastAPI on **internal** port 10060 (not published).
- `dispatch-frontend` — Caddy serving the Vite SPA and reverse-proxying
  `/api/*` and `/health` to the backend.

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

Then `curl http://127.0.0.1:10060/health` → expect `{"status": "healthy", ...}`.

### Backend tests

```bash
cd apps/backend
pytest
```

### Local frontend dev

```bash
cd apps/frontend
npm install
npm run dev
```

The Vite dev server runs on `http://localhost:5173` and proxies `/api/*`
and `/health` to `http://127.0.0.1:10060`, so run the backend alongside it.

---

## Key management

The single required env var is `DISPATCH_MASTER_KEY`. This key encrypts every
credential the app holds at rest (AI provider keys, TTS credentials, GitHub
tokens, storage credentials, NotebookLM session).

**If you lose this key, the encrypted settings are unrecoverable** and you will
need to re-enter them via the admin UI. Briefings, audio, snapshots, and project
configuration are unaffected. Back the key up in a password manager.

Generate one with:

```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

To rotate, use the admin endpoint:

```
POST /api/admin/system/rotate-key
{ "old_key": "...", "new_key": "..." }
```

---

## Authentication model

Dispatch does **not** implement application-level authentication. The backend trusts
its deployment perimeter — Cloudflare Access, Tailscale, a reverse-proxy basic-auth
block, Authelia, or any equivalent.

Route prefixes are designed so any perimeter can apply policy:

- `/admin/*` and `/api/admin/*` — operator-only; **must** be gated.
- `/`, `/briefings/*`, `/podcasts/*`, `/api/snapshot` — public reader paths; gate
  these too if you want a fully private instance.

Recipes for the common perimeter patterns live in
[`docs/operations/perimeter-recipes.md`](docs/operations/perimeter-recipes.md).

---

## Configuring your own projects

The shipped `apps/backend/dispatch/projects.yml` registers three showcase
projects — `anthropics/claude-code`, `withastro/astro`, and this repository
(`markdavidgan/dispatch`) — so a fresh clone has something to summarize. After
your first boot, either:

- Edit `projects.yml` directly and restart, **or**
- Use the admin UI at `/admin/projects` to CRUD projects at runtime.

See the comments at the top of `projects.yml` for the full schema.

## Backfill and catch-up

The daily synthesis job follows a small priority chain:

1. If yesterday is uncovered and had activity, generate yesterday's brief.
2. Otherwise, find the oldest uncovered day with activity in the last 30 days
   and generate that one (catch-up).
3. Otherwise, skip (no work to do).

This means an instance that was offline for a week will catch up over the
following days, one brief per scheduler tick. To process the whole backlog
immediately (e.g. right after `bootstrap.sh`), hit:

```
POST /api/admin/system/backfill
{ "max_days": 30, "ingest": true }
```

The endpoint ingests fresh events, then loops the look-back synthesis until
every uncovered active day in the window has a brief (capped at `max_days`
iterations to prevent runaway).

---

## License

MIT
