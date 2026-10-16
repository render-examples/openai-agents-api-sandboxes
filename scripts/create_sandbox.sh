#!/usr/bin/env bash
# Prints only the sandbox ID on stdout, so callers can use $(...).
set -euo pipefail

read -rsp 'OpenAI environment key: ' key
printf '\n' >&2
if [[ -z "$key" || "$key" =~ [[:space:]] ]]; then
  echo 'Enter one environment key without spaces or newlines.' >&2
  exit 1
fi

# The key is on disk only while the CLI reads it.
umask 077
env_file="$(mktemp "${TMPDIR:-/tmp}/executor.env.XXXXXX")"
trap 'rm -f "$env_file"' EXIT
printf 'CODEX_API_KEY=%s\n' "$key" > "$env_file"
unset key

if ! output="$(render ea sandboxes create --timeout=900 --network-policy=allow-all \
  --env-file "$env_file" -o json)"; then
  printf '%s\n' "$output" >&2
  echo 'Sandbox creation failed. Check the Render Dashboard before you try again.' >&2
  exit 1
fi

# Match the ID in the JSON so jq is not required.
if [[ "$output" =~ \"id\"[[:space:]]*:[[:space:]]*\"(sbx-[^\"]+)\" ]]; then
  echo "Created sandbox ${BASH_REMATCH[1]}." >&2
  printf '%s\n' "${BASH_REMATCH[1]}"
else
  printf '%s\n' "$output" >&2
  echo 'No sandbox ID in the CLI output. Check the Render Dashboard.' >&2
  exit 1
fi
