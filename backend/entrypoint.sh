#!/usr/bin/env bash
# apps/backend/dispatch/entrypoint.sh
# Hydrate Kimi OAuth credentials from $KIMI_OAUTH_JSON on every boot when
# the env var is set, then exec uvicorn. The dispatch-kimi volume persists
# kimi-code.json across restarts; we want a rotated token in Doppler to
# take effect on the next `compose restart`, not on the next image
# rebuild — so we always refresh from env when present.

set -euo pipefail

CREDS_DIR=/home/dispatch/.kimi/credentials
CREDS_FILE="$CREDS_DIR/kimi-code.json"

mkdir -p "$CREDS_DIR"

if [[ -n "${KIMI_OAUTH_JSON:-}" ]]; then
  TMP_NEW=$(mktemp)
  printf '%s' "$KIMI_OAUTH_JSON" > "$TMP_NEW"
  # Rewrite only when contents differ — avoids mtime churn on no-op restarts.
  if [[ ! -s "$CREDS_FILE" ]] || ! cmp -s "$TMP_NEW" "$CREDS_FILE"; then
    echo "[entrypoint] refreshing Kimi creds from KIMI_OAUTH_JSON"
    install -m 600 "$TMP_NEW" "$CREDS_FILE"
  fi
  rm -f "$TMP_NEW"
elif [[ ! -s "$CREDS_FILE" ]]; then
  echo "[entrypoint] WARNING: no Kimi creds available (synthesis will fail)" >&2
fi

cp /app/dispatch/kimi-config.toml /home/dispatch/.kimi/config.toml || true

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
