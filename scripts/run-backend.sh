#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

PORT="${BACKEND_PORT:-8000}"

if fuser "${PORT}/tcp" >/dev/null 2>&1; then
  echo "Port ${PORT} is in use — stopping existing process..."
  fuser -k "${PORT}/tcp" >/dev/null 2>&1 || true
  sleep 1
fi

PYTHON="${PYTHON:-/home/arvinzaheri/miniconda3/bin/python3}"
if [ ! -x "$PYTHON" ]; then
  PYTHON="$(command -v python3)"
fi

export PYTHONPATH="$ROOT"

if [ -f "$ROOT/pyproject.toml" ] && command -v uv >/dev/null 2>&1; then
  (cd "$ROOT" && uv sync -q)
  exec uv run uvicorn backend.main:app --reload --host 127.0.0.1 --port "${PORT}"
fi

"$PYTHON" -m pip install -q -r backend/requirements.txt
exec "$PYTHON" -m uvicorn backend.main:app --reload --host 127.0.0.1 --port "${PORT}"
