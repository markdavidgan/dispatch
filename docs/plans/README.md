# Plans

Active implementation plans live here, named `YYYY-MM-DD-<short-desc>.md`. On completion, move to `completed/YYYY-MM/`.

## Active

*(none)*

## Completed

- [2026-05-26 — Move Briefings Pipeline to Vercel Serverless](completed/2026-05/2026-05-26-briefings-vercel-serverless.md)
- [2026-05-23 — Dispatch Phase 1 Foundation](completed/2026-05/2026-05-23-dispatch-phase-1-foundation.md)

## Deployment Options

The repo supports three deployment topologies. Choose based on your needs:

| Topology | Best For | Docs |
|---|---|---|
| **Self-hosted (Docker Compose)** | Full product on your own hardware | `docker-compose.yml` + `README.md` |
| **Static Demo (Vercel)** | Zero-cost showcase with baked-in data | `npm run build:demo` + `vercel.demo.json` |
| **Cloud VPS (Oracle Cloud Free Tier)** | Full product on a free perpetual VM | `docs/operations/deploy-oracle-cloud.md` |
| **Cloud VPS (Fly.io)** | Full product on a managed container platform | `docs/operations/deploy-fly-io.md` |
