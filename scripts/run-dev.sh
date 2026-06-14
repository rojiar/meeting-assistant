#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

BACKEND_PORT="${BACKEND_PORT:-8000}"
FRONTEND_PORT="${FRONTEND_PORT:-4321}"

stop_port() {
  local port="$1"
  if fuser "${port}/tcp" >/dev/null 2>&1; then
    echo "Port ${port} is in use — stopping existing process..."
    fuser -k "${port}/tcp" >/dev/null 2>&1 || true
    sleep 1
  fi
}

cleanup() {
  local exit_code=$?
  echo ""
  echo "Stopping dev servers..."
  if [[ -n "${BACKEND_PID:-}" ]]; then
    kill "$BACKEND_PID" 2>/dev/null || true
  fi
  if [[ -n "${FRONTEND_PID:-}" ]]; then
    kill "$FRONTEND_PID" 2>/dev/null || true
  fi
  stop_port "$BACKEND_PORT"
  stop_port "$FRONTEND_PORT"
  exit "$exit_code"
}
trap cleanup EXIT INT TERM

stop_port "$BACKEND_PORT"
stop_port "$FRONTEND_PORT"

echo "Starting backend on http://127.0.0.1:${BACKEND_PORT}"
"$ROOT/scripts/run-backend.sh" &
BACKEND_PID=$!

echo "Starting frontend on http://localhost:${FRONTEND_PORT}"
(
  cd "$ROOT/frontend"
  npm install --no-fund --no-audit --silent
  npm run dev -- --port "$FRONTEND_PORT" --host 127.0.0.1
) &
FRONTEND_PID=$!

echo ""
echo "Open http://localhost:${FRONTEND_PORT}"
echo "Press Ctrl+C to stop both."

wait "$BACKEND_PID" "$FRONTEND_PID"
