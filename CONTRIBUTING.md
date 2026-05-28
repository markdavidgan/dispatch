# Contributing to Dispatch

Dispatch is **maintainer-curated**. The project is open-source so you can inspect, fork, and self-host it freely, but the core architecture and product direction are driven by the maintainer.

## What we welcome

- **Bug reports** — crashes, broken ingest pipelines, incorrect brief generation, UI glitches
- **Corrections** — outdated documentation, unsafe deployment advice, typos
- **Feature requests** — open an issue to discuss before writing code. See the project principles below.
- **Forks** — feel free to fork and adapt for your own team or homelab workflow

## What is maintainer-curated

- **Core architecture** — the single-admin, perimeter-trusting auth model, SQLite + APScheduler stack, and editorial design invariants are intentionally opinionated and change slowly.
- **New integrations** — new AI providers, TTS engines, or storage backends need alignment with the existing pluggable-adapter pattern.
- **UI/UX direction** — the editorial design system in `DESIGN.md` is treated as immutable; framework changes are fine, the look is not.

## How to report

Open a [GitHub Issue](https://github.com/markdavidgan/dispatch/issues). Include:

- The specific component (frontend, backend, ingest, podcast, admin UI)
- What you expected vs. what happened
- Steps to reproduce (for bugs)
- Your deployment mode (Docker all-in-one, hybrid/Vercel, or local dev)
- Relevant logs or screenshots

## How to contribute code

1. **Open an issue first** for anything beyond a trivial fix. This avoids wasted effort on changes that may not align with the project direction.
2. **One logical change per PR.** Do not bundle unrelated fixes.
3. **Include tests.** Backend changes should include pytest coverage. Frontend changes should not break existing Playwright e2e tests.
4. **Update docs.** If your change affects deployment, configuration, or behavior, update the relevant doc in `docs/`.
5. **Keep the Makefile green.** Run `make test`, `make typecheck`, and `make build` before opening a PR. There are 4 pre-existing backend test failures in `test_from_the_desk.py` and frontend lint issues being cleaned up — do not add new ones.

## Development setup

```bash
make install   # venv + pip install backend, npm install frontend
make dev       # backend (uvicorn --reload) + frontend (vite) together
make test      # backend pytest suite
make lint      # frontend Biome
make typecheck # frontend TypeScript
make build     # production SPA build
```

## For maintainers

Release workflow is documented in `docs/operations/releasing.md` (to be created). CI must pass before merge.
