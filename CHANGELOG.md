# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Open-source contributor infrastructure: `LICENSE`, `CONTRIBUTING.md`, `CHANGELOG.md`, issue templates, PR template, and CI workflow.
- GitHub Sponsors and Ko-fi funding links.

## [0.2.0] - 2026-05-27

### Added
- Vite SPA frontend with React 19, Tailwind CSS v4, and React Router.
- Encrypted DB-backed settings (AES-GCM via `DISPATCH_MASTER_KEY`).
- Admin UI for projects, settings, and system operations.
- Pluggable storage: local filesystem, Cloudflare R2, or S3-compatible.
- Enhanced GitHub ingest with rate-limit awareness.
- Vercel serverless hybrid deployment mode.
- Weekly podcast composition via NotebookLM.
- Perimeter-auth recipes for Cloudflare Access, Tailscale, Caddy, and Authelia.

## [0.1.0] - 2026-05-23

### Added
- Initial release: FastAPI backend with SQLite (WAL mode) and APScheduler.
- Daily editorial brief generation with TTS narration (Google Cloud Chirp 3 HD).
- Docker all-in-one stack with Caddy reverse proxy.
- Single-admin, perimeter-trusting authentication model.
