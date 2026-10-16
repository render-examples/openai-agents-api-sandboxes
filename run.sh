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

# Cleanup must remove only what this run creates.
if [[ -e session.json ]]; then
  echo "$lang/session.json is left from an earlier run. Run scripts/cleanup.sh $lang first." >&2
  exit 1
fi

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

# A SANDBOX_ID from the caller's shell is not from this run.
SANDBOX_ID=''
export SANDBOX_ID

on_exit() {
  local status=$?
  if ! "$repo/scripts/cleanup.sh" "$lang" && [[ "$status" -eq 0 ]]; then
    status=1
  fi
  exit "$status"
}
trap on_exit EXIT
# Exit on Ctrl-C or TERM so the EXIT trap runs cleanup.
trap 'exit 130' INT
trap 'exit 143' TERM

client create_session
SANDBOX_ID="$("$repo/scripts/create_sandbox.sh")"
client wait_for_sandbox
"$repo/scripts/stage.sh"
client run_task
"$repo/scripts/verify.sh"
