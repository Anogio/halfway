#!/bin/zsh

set -euo pipefail
unsetopt BG_NICE 2>/dev/null || true

ROOT_DIR="$(cd "$(dirname "$0")/../.." && pwd)"
BACKEND_DIR="$ROOT_DIR/backend"
FRONTEND_DIR="$ROOT_DIR/frontend"

BACKEND_HOST="${E2E_BACKEND_HOST:-127.0.0.1}"
BACKEND_PORT="${E2E_BACKEND_PORT:-8000}"
FRONTEND_HOST="${E2E_FRONTEND_HOST:-127.0.0.1}"
FRONTEND_PORT="${E2E_FRONTEND_PORT:-3002}"
PLAYWRIGHT_BASE_URL="http://${FRONTEND_HOST}:${FRONTEND_PORT}"
BACKEND_URL="http://${BACKEND_HOST}:${BACKEND_PORT}"

backend_pid=""
frontend_pid=""

cleanup() {
  if [[ -n "$frontend_pid" ]]; then
    kill -TERM "$frontend_pid" >/dev/null 2>&1 || true
    wait "$frontend_pid" >/dev/null 2>&1 || true
  fi
  if [[ -n "$backend_pid" ]]; then
    kill -TERM "$backend_pid" >/dev/null 2>&1 || true
    wait "$backend_pid" >/dev/null 2>&1 || true
  fi
}

ensure_port_free() {
  local host="$1"
  local port="$2"
  local label="$3"

  if lsof -nP -iTCP:"$port" -sTCP:LISTEN 2>/dev/null | grep -F "${host}:${port}" >/dev/null; then
    echo "${label} port ${host}:${port} is already in use. Stop the competing process or override the port with E2E_${label}_PORT." >&2
    return 1
  fi
}

wait_for_url() {
  local url="$1"
  local label="$2"
  local max_attempts="${3:-120}"
  local attempt=1

  while (( attempt <= max_attempts )); do
    if curl -fsS "$url" >/dev/null 2>&1; then
      return 0
    fi
    sleep 1
    (( attempt += 1 ))
  done

  echo "Timed out waiting for ${label} at ${url}" >&2
  return 1
}

trap cleanup EXIT INT TERM

ensure_port_free "$BACKEND_HOST" "$BACKEND_PORT" "BACKEND"
ensure_port_free "$FRONTEND_HOST" "$FRONTEND_PORT" "FRONTEND"

cd "$BACKEND_DIR"
CORS_ALLOW_ORIGIN_REGEX="^http://${FRONTEND_HOST//./\\.}:${FRONTEND_PORT}$" \
  HOST="$BACKEND_HOST" \
  PORT="$BACKEND_PORT" \
  PYTHONPATH=src:shared/src \
  UV_CACHE_DIR=.uv-cache \
  uv run python -m transit_backend.api.server \
  > /tmp/halfway-backend-e2e.log 2>&1 &
backend_pid=$!

wait_for_url "${BACKEND_URL}/health" "backend"

cd "$FRONTEND_DIR"
NEXT_PUBLIC_BACKEND_URL="$BACKEND_URL" \
  npm run dev -- --hostname "$FRONTEND_HOST" --port "$FRONTEND_PORT" \
  > /tmp/halfway-frontend-e2e.log 2>&1 &
frontend_pid=$!

wait_for_url "$PLAYWRIGHT_BASE_URL" "frontend"

PLAYWRIGHT_BASE_URL="$PLAYWRIGHT_BASE_URL" PW_SKIP_WEBSERVER=1 npx playwright test "$@"
