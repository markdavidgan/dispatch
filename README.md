# Dispatch

A standalone daily editorial brief generator for software projects. Each deployed instance watches a configurable registry of GitHub repositories, synthesizes daily reports with audio narration, and produces weekly podcasts.

## Architecture

- **Frontend:** Vite SPA + React 19 + Tailwind CSS v4 + React Router — static build, deployed anywhere (Vercel, CDN, or served from the same origin)
- **Backend:** FastAPI + Python 3.12 + SQLite (WAL mode) — self-hosted via Docker
- **Scheduler:** In-process APScheduler (no Redis, no Celery)
- **Storage:** Pluggable backends — Cloudflare R2, AWS S3, or local filesystem
- **AI Synthesis:** Configurable providers (Kimi, Anthropic, OpenAI)
- **TTS:** Google Cloud Chirp 3 HD, Cartesia, or ElevenLabs

## Repository Structure

```
dispatch/
├── apps/
│   ├── frontend/      # Vite SPA (static build)
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

The stack:
- `dispatch-backend` — FastAPI on internal port 10060 (not published)
- `dispatch-frontend` — Caddy serving the Vite SPA + reverse-proxying `/api/*` and `/health` to the backend

By default the frontend is exposed at `http://localhost:8080`. Override with `DISPATCH_HTTP_PORT=80`.

Visit:
- http://localhost:8080/ → SPA
- http://localhost:8080/health → backend health
- http://localhost:8080/api/projects → backend API

### Frontend dev

```bash
cd apps/frontend
npm install
npm run dev
```

The dev server runs on `http://localhost:5173`. Vite proxies `/api/*` and `/health` to `http://127.0.0.1:10060`, so run the backend (above) alongside it.

## Key Management

The single required env var is `DISPATCH_MASTER_KEY`. This key encrypts every credential the app holds at rest (AI provider keys, TTS credentials, GitHub tokens, storage credentials, NotebookLM session).

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

Perimeter recipes for Cloudflare Access, Tailscale, Caddy basic auth, and Authelia live in `docs/operations/perimeter-recipes.md`.

## Development Status

This project was extracted from the [marklab](https://github.com/markdavidgan/marklab) homelab monorepo. See `docs/brainstorm/2026-05-23-standalone-dispatch/` for the architecture brainstorm and migration plan.

## License

MIT
