#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT/docs"

npm install --no-fund --no-audit --silent

if ! npx playwright install chromium 2>/dev/null; then
  npx playwright install chromium
fi

cd "$ROOT"
node scripts/capture-ui-screenshots.mjs
