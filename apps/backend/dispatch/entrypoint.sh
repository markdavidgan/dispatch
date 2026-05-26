#!/usr/bin/env bash
# apps/backend/dispatch/entrypoint.sh
# Podcast-only backend — synthesis moved to Vercel serverless.
# NotebookLM session handling remains for podcast generation.

set -euo pipefail

# NotebookLM session is bind-mounted from host at /home/dispatch/.notebooklm
# In rootless Podman, the bind-mounted file may not be readable by the
# container user due to UID mapping. Copy it to a writable location.
NOTEBOOKLM_SRC="/home/dispatch/.notebooklm/profiles/default/storage_state.json"
NOTEBOOKLM_DST="/home/dispatch/.notebooklm_session.json"
if [[ -r "$NOTEBOOKLM_SRC" ]]; then
  cp "$NOTEBOOKLM_SRC" "$NOTEBOOKLM_DST"
  chmod 600 "$NOTEBOOKLM_DST"
  export NOTEBOOKLM_SESSION_PATH="$NOTEBOOKLM_DST"
  echo "[entrypoint] copied NotebookLM session → $NOTEBOOKLM_DST"
elif [[ -r "$NOTEBOOKLM_DST" ]]; then
  export NOTEBOOKLM_SESSION_PATH="$NOTEBOOKLM_DST"
  echo "[entrypoint] using cached NotebookLM session"
else
  echo "[entrypoint] WARNING: NotebookLM session not available (podcasts will fail)" >&2
fi

exec uvicorn dispatch.main:app --host "${HOST:-0.0.0.0}" --port "${PORT:-10060}"
