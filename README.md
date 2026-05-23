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

### Prerequisites

- Node.js 20+ and pnpm (for frontend)
- Python 3.13+ and uv/pip (for backend)
- Docker and Docker Compose (for self-hosting)
- ffmpeg (for audio processing)

### Frontend

```bash
cd apps/frontend
pnpm install
pnpm dev
```

### Backend

```bash
cd apps/backend
pip install -r dispatch/requirements.txt
DISPATCH_MASTER_KEY=changeme uvicorn dispatch.main:app --reload
```

### Docker Compose

```bash
docker compose up -d
```

## Configuration

All configuration is managed through the frontend admin UI:

1. Run the setup wizard at `/setup` on first boot
2. Configure GitHub token(s) for repo monitoring
3. Configure AI provider credentials
4. Configure TTS provider credentials
5. Configure storage backend credentials
6. Add projects to the registry via `/admin/projects`

The only required environment variable is `DISPATCH_MASTER_KEY` — used to encrypt secrets at rest.

## Development Status

This project was extracted from the [marklab](https://github.com/markdavidgan/marklab) homelab monorepo. See `docs/brainstorm/2026-05-23-standalone-dispatch/` for the architecture brainstorm and migration plan.

## License

MIT
