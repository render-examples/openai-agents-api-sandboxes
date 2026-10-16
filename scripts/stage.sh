#!/usr/bin/env bash
set -euo pipefail

if [[ -z "${SANDBOX_ID:-}" ]]; then
  echo 'Set SANDBOX_ID first.' >&2
  exit 1
fi
repo="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

render ea sandboxes exec "$SANDBOX_ID" -- bash -lc \
  'mkdir -p /workspace/outputs && npm install -g @openai/codex@0.162.0-alpha.16'
render ea sandboxes copy "$repo/fixture/" "$SANDBOX_ID:/workspace"
