#!/usr/bin/env bash
set -euo pipefail

if [[ -z "${SANDBOX_ID:-}" ]]; then
  echo 'Set SANDBOX_ID first.' >&2
  exit 1
fi
repo="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

# Restore the original input and tests so that edits by the agent cannot pass.
# The CLI copies one path per call.
render ea sandboxes copy "$repo/fixture/orders.csv" "$SANDBOX_ID:/workspace/orders.csv"
render ea sandboxes copy "$repo/fixture/test_total.mjs" "$SANDBOX_ID:/workspace/test_total.mjs"
render ea sandboxes copy "$repo/verify.mjs" "$SANDBOX_ID:/workspace/verify.mjs"
render ea sandboxes exec "$SANDBOX_ID" -- bash -lc \
  'cd /workspace && node --test test_total.mjs && node verify.mjs'

mkdir -p "$repo/results"
render ea sandboxes copy "$SANDBOX_ID:/workspace/outputs/report.json" "$repo/results/report.json"
render ea sandboxes copy "$SANDBOX_ID:/workspace/total.mjs" "$repo/results/total.mjs"
cat "$repo/results/report.json"
