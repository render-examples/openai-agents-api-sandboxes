#!/usr/bin/env bash
# Runs every step of the example for one client: ./run.sh python|typescript
set -euo pipefail

usage() {
  echo 'Usage: ./run.sh python|typescript' >&2
  exit 2
}

[[ $# -eq 1 ]] || usage
lang="$1"
case "$lang" in
  python)
    install() {
      python3 -m venv .venv
      .venv/bin/python -m pip install --quiet --disable-pip-version-check -r requirements.txt
    }
    client() { .venv/bin/python "$1.py"; }
    ;;
  typescript)
    install() { npm ci --no-audit --no-fund; }
    client() { npx tsx "$1.ts"; }
    ;;
  *) usage ;;
esac

# The clients read and write files relative to their own directory.
repo="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$repo/$lang"

install

# The key stays in this process. It is not written to disk.
if [[ -z "${OPENAI_API_KEY:-}" ]]; then
  read -rsp 'OpenAI application key: ' OPENAI_API_KEY
  printf '\n' >&2
fi
if [[ -z "$OPENAI_API_KEY" ]]; then
  echo 'Enter the OpenAI application key.' >&2
  exit 1
fi
export OPENAI_API_KEY

client create_session
SANDBOX_ID="$("$repo/scripts/create_sandbox.sh")"
export SANDBOX_ID
client wait_for_sandbox
"$repo/scripts/stage.sh"
client run_task
"$repo/scripts/verify.sh"
