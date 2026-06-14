#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

echo "=== Unit tests ==="
"$ROOT/scripts/run-tests.sh"

echo ""
echo "=== Live API tests (Google + Jira) ==="
"$ROOT/scripts/run-live-tests.sh"
