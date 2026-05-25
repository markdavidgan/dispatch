#!/usr/bin/env bash
# Dispatch — one-command bring-up for a fresh clone.
#
#   curl + docker is all you need. This script:
#     1. Generates a DISPATCH_MASTER_KEY into .env if one doesn't exist
#     2. Builds and starts the docker compose stack
#     3. Waits for the backend to report healthy
#     4. Triggers an ingest + look-back synthesis backfill
#     5. Prints the URL and the next-steps for adding an AI provider key
#
# Idempotent — safe to re-run.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

ENV_FILE="$REPO_ROOT/.env"
HOST_PORT="${DISPATCH_HTTP_PORT:-8080}"
BASE_URL="http://localhost:${HOST_PORT}"

# Prefer docker; fall back to podman. Both expose a `compose` subcommand.
if command -v docker >/dev/null 2>&1; then
  COMPOSE_BIN="docker"
elif command -v podman >/dev/null 2>&1; then
  COMPOSE_BIN="podman"
else
  echo "Neither docker nor podman is installed; please install one." >&2
  exit 1
fi

color() { printf '\033[%sm%s\033[0m\n' "$1" "$2"; }
say()   { color "1;36" "▸ $*"; }
ok()    { color "1;32" "✓ $*"; }
warn()  { color "1;33" "! $*"; }

# ---------- 1. master key ----------
if [ -f "$ENV_FILE" ] && grep -q "^DISPATCH_MASTER_KEY=" "$ENV_FILE"; then
  ok ".env exists with DISPATCH_MASTER_KEY — reusing"
else
  if ! command -v python3 >/dev/null 2>&1; then
    echo "python3 is required to generate a master key" >&2
    exit 1
  fi
  KEY=$(python3 -c "import secrets; print(secrets.token_urlsafe(32))")
  printf "DISPATCH_MASTER_KEY=%s\n" "$KEY" >> "$ENV_FILE"
  ok "generated DISPATCH_MASTER_KEY into .env"
  warn "back this key up in a password manager — losing it makes encrypted settings unrecoverable"
fi

# ---------- 2. compose up ----------
say "building and starting compose stack (${COMPOSE_BIN} compose)"
"$COMPOSE_BIN" compose --env-file "$ENV_FILE" up -d --build

# ---------- 3. wait for health ----------
say "waiting for backend to be healthy at ${BASE_URL}/health"
for i in $(seq 1 60); do
  if curl -fsS "${BASE_URL}/health" >/dev/null 2>&1; then
    ok "backend is healthy"
    break
  fi
  sleep 2
  if [ "$i" = 60 ]; then
    warn "backend did not become healthy in 120s — check '${COMPOSE_BIN} compose logs dispatch-backend'"
    exit 1
  fi
done

# ---------- 4. backfill ----------
say "running initial backfill (ingest + look-back synthesis)"
BACKFILL_OUT=$(curl -fsS -X POST "${BASE_URL}/api/admin/system/backfill" \
  -H "Content-Type: application/json" \
  -d '{"max_days": 30, "ingest": true}' || true)
echo "$BACKFILL_OUT"

# ---------- 5. next steps ----------
echo
ok "Dispatch is up at ${BASE_URL}/"
echo
echo "Next steps:"
echo "  1. Open ${BASE_URL}/admin/settings and add an AI provider key (Kimi / Anthropic / OpenAI)"
echo "     to enable narrated brief generation."
echo "  2. Re-run the backfill from ${BASE_URL}/admin (or curl ${BASE_URL}/api/admin/system/backfill)"
echo "     once a key is configured — events ingested in step 4 will turn into briefs."
echo "  3. Edit apps/backend/dispatch/projects.yml or use ${BASE_URL}/admin/projects to add your own repos."
echo
