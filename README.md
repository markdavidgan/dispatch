# Dispatch

A standalone daily editorial brief generator for software projects. Each deployed instance watches a configurable registry of GitHub repositories, synthesizes daily reports with audio narration, and produces weekly podcasts.

## Architecture

- **Frontend:** Next.js 15 + React 19 + Tailwind CSS v4 — deployed to Vercel
- **Backend:** FastAPI + Python 3.13 + SQLite (WAL mode) — self-hosted via Docker
- **Scheduler:** In-process APScheduler (no Redis, no Celery)
- **Storage:** Pluggable backends — Cloudflare R2, AWS S3, or local filesystem
- **AI Synthesis:** Configurable providers (Kimi, Anthropic, OpenAI)
- **TTS:** Google Cloud Chirp 3 HD, Cartesia, or ElevenLabs

## Repository Structure

```
dispatch/
├── apps/
│   ├── frontend/      # Next.js app (Vercel)
│   └── backend/       # FastAPI app (Docker)
├── docker-compose.yml # Self-hosting setup
└── docs/              # Brainstorm, specs, plans
```

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

## Development Status

This project was extracted from the [marklab](https://github.com/markdavidgan/marklab) homelab monorepo. See `docs/brainstorm/2026-05-23-standalone-dispatch/` for the architecture brainstorm and migration plan.

## License

MIT
