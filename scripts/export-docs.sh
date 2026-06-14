#!/usr/bin/env bash
# Render Mermaid → SVG, then HTML → PDF (English LTR via Playwright).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT/docs"

echo "=== Installing doc tooling (first run may take a minute) ==="
npm install --no-fund --no-audit

if ! npx playwright install chromium 2>/dev/null; then
  npx playwright install chromium
fi

echo ""
echo "=== Mermaid → SVG ==="
npm run diagrams

echo ""
echo "=== HTML → PDF ==="
npm run pdf

echo ""
echo "Output:"
echo "  SVG:  $ROOT/docs/diagrams/"
echo "  PDF:  $ROOT/docs/pdf/"
