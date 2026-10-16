#!/usr/bin/env bash
# Stops the sandbox and deletes the session: scripts/cleanup.sh python|typescript
# Both steps run even if one fails. Steps with nothing to remove are skipped.
set -euo pipefail

case "${1:-}" in
  python) delete_session() { .venv/bin/python cleanup.py; } ;;
  typescript) delete_session() { npx tsx cleanup.ts; } ;;
  *)
    echo 'Usage: scripts/cleanup.sh python|typescript' >&2
    exit 2
    ;;
esac
lang="$1"
repo="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$repo/$lang"

failed=0
# The retry command names the sandbox only if it is still running.
retry_env=''
if [[ -n "${SANDBOX_ID:-}" ]]; then
  if render ea sandboxes stop "$SANDBOX_ID" --confirm -o json; then
    echo "Stopped sandbox $SANDBOX_ID." >&2
  else
    echo "Could not stop sandbox $SANDBOX_ID." >&2
    failed=1
    retry_env="SANDBOX_ID='$SANDBOX_ID' "
  fi
fi
if [[ -e session.json ]]; then
  delete_session || failed=1
fi

if [[ "$failed" -ne 0 ]]; then
  echo 'Cleanup failed. Fix the error, then run this command again:' >&2
  echo "  ${retry_env}$repo/scripts/cleanup.sh $lang" >&2
  exit 1
fi
