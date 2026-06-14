#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

PYTHON="${PYTHON:-/home/arvinzaheri/miniconda3/bin/python3}"
if [ ! -x "$PYTHON" ]; then
  PYTHON="$(command -v python3)"
fi

export PYTHONPATH="$ROOT"
exec "$PYTHON" -m pytest backend/tests -v "$@"
