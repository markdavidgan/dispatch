# Dispatch — Agent Instructions

Dispatch is the standalone extraction of a daily-brief / podcast app from the marklab monorepo. Goals: deployable anywhere (homelab Docker, Vercel-frontend + self-hosted-backend, etc.), single-admin per instance, perimeter-trusting (no app-layer auth).

## Doc conventions

- Plans: `docs/plans/YYYY-MM-DD-<short-desc>.md` → archive to `docs/plans/completed/YYYY-MM/` on completion.
- Brainstorms: `docs/brainstorm/YYYY-MM-DD-<short-desc>/` (folder with `notes.md`).
- Specs: `docs/specs/YYYY-MM-DD-<short-desc>.md`.
- Insights: `docs/insights/YYYY-MM/`.

Do NOT write planning docs to `docs/superpowers/`, `.superpowers/`, or repo root.

## Architecture invariants

- **No app-layer authentication.** The backend trusts its deployment perimeter (Cloudflare Access, Tailscale, Caddy basic auth, Authelia). No login page, no users table, no JWT in the app. Admin-only logic is (or will be) gated by route prefix: `/api/admin/*` for operator-only endpoints, public reader paths (`/`, `/briefings/*`, `/podcasts/*`, `/api/snapshot`) for everyone. The current Phase-1 router layout still uses the marklab-era prefixes (`/live`, `/brief`, `/projects`, `/podcasts`); the `/api/admin/*` split is introduced incrementally across Phases 2-4.
- **Editorial design is immutable.** See `DESIGN.md`. Framework can change; the look cannot.
- **Single required env var.** `DISPATCH_MASTER_KEY` (encrypts settings at rest, used from Phase 3 onward). Every other credential lives in the DB, configured via admin UI.

## Phase ordering

Each phase has its own plan in `docs/plans/`. Do not jump ahead. Current: **Phase 1 — Foundation** (see plan).

## When in doubt

Read `docs/brainstorm/2026-05-23-dispatch-operational-gaps/notes.md` first — it is the current source of truth and supersedes the original brainstorm on authentication and frontend framework. Then read `docs/brainstorm/2026-05-23-standalone-dispatch/notes.md` for original context (note: its §2 auth design and Next.js choice have been replaced).
