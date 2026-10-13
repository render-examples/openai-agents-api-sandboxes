# OpenAI Agents API on Render Sandboxes

Run an OpenAI agent's commands and file operations in a Render Sandbox. Choose a
Python or TypeScript client; both run the same task.

The agent repairs a JavaScript program that skips the last row of a CSV file.
You verify the repair through Render and download the corrected code and report.

```text
python/       Python client and requirements
typescript/   TypeScript client and lockfile
fixture/      Input CSV, broken program, and four tests
prompt.txt    Task sent to the agent
verify.mjs    Independent report verification, run inside Render
```

## Requirements

- Render Sandboxes access and Render CLI 2.28.0 or later.
- Python 3.10 or later, or Node.js 22 or later. Use Bash for the shared commands.
- An OpenAI project with Agents API access, an application API key, and an
  environment key with matching organization, project, and user or service account.

The application key needs `api.agents.read`, `api.agents.write`, and
`api.responses.write`. The environment key needs environment connection access.
See [OpenAI self-hosted authentication](https://developers.openai.com/api/docs/guides/agents-api/environments/self-hosted#authentication).

The application key stays on your machine. Only the environment key goes into the
sandbox. Code running in the sandbox can read its environment variables.

## 1. Install your client

Run these steps separately in Bash or zsh:

1. Clone the example:

   ```shell
   git clone https://github.com/render-examples/openai-agents-api-sandboxes.git
   cd openai-agents-api-sandboxes
   ```

2. Limit access to files created in this shell:

   ```shell
   umask 077
   ```

3. Sign in to Render. Complete the browser login before continuing:

   ```shell
   render login
   ```

4. Select your Render workspace. Replace the placeholder with your workspace ID from the Render Dashboard:

   ```shell
   render workspace set '<your-workspace-id>'
   ```

**Python:**

```shell
cd python
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

**TypeScript:**

```shell
cd typescript
npm ci
```

Stay in the chosen language directory for the remaining steps. Enter the
application key without putting its value in shell history:

```shell
printf 'OpenAI application API key: '
read -rs OPENAI_API_KEY
printf '\n'
export OPENAI_API_KEY
```

## 2. Create the session and sandbox

Run the command for your language:

| Action | Python | TypeScript |
| --- | --- | --- |
| Create the OpenAI session | `python create_session.py` | `npx tsx create_session.ts` |

This saves `session.json`. Keep it until cleanup succeeds. Do not overwrite an
existing session file. If creation times out, inspect the OpenAI dashboard before
retrying; the session might already exist.

Enter the environment key and create a sandbox:

```shell
printf 'OpenAI environment key: '
read -rs ENVIRONMENT_KEY
printf '\n'
if [[ -n "$ENVIRONMENT_KEY" && ! "$ENVIRONMENT_KEY" =~ [[:space:]] ]]; then
  printf 'CODEX_API_KEY=%s\n' "$ENVIRONMENT_KEY" > executor.env
  unset ENVIRONMENT_KEY
  render ea sandboxes create --timeout=900 --network-policy=allow-all \
    --env-file executor.env -o json
  rm -f executor.env
else
  unset ENVIRONMENT_KEY
  echo 'Enter one environment key without spaces or newlines.'
fi
```

Save the returned sandbox ID:

```shell
export SANDBOX_ID='<returned-sandbox-id>'
```

If creation times out, inspect the Render Dashboard before retrying. From this
point, run cleanup even if a later step fails. The sandbox lifetime is 15 minutes.

| Action | Python | TypeScript |
| --- | --- | --- |
| Wait for this sandbox | `python wait_for_sandbox.py` | `npx tsx wait_for_sandbox.ts` |

## 3. Run the task

Install the executor and stage the input files:

```shell
render ea sandboxes exec "$SANDBOX_ID" -- bash -lc \
  'mkdir -p /workspace/outputs && npm install -g @openai/codex@0.162.0-alpha.16'
render ea sandboxes copy ../fixture/ "$SANDBOX_ID:/workspace"
```

| Action | Python | TypeScript |
| --- | --- | --- |
| Submit the task and stream events | `python run_task.py` | `npx tsx run_task.ts` |

The helper opens the event stream before starting the executor and submitting
`prompt.txt`. It waits up to three minutes for a completed root turn. A timeout
ends the local wait; run cleanup if you stop here.

The model should fix the CSV total from `30` to `42`. Its response alone is not
proof of success.

## 4. Verify and download

Restore the original input and tests, then check the agent's program and report:

```shell
render ea sandboxes copy ../fixture/orders.csv "$SANDBOX_ID:/workspace/orders.csv"
render ea sandboxes copy ../fixture/test_total.mjs "$SANDBOX_ID:/workspace/test_total.mjs"
render ea sandboxes copy ../verify.mjs "$SANDBOX_ID:/workspace/verify.mjs"
render ea sandboxes exec "$SANDBOX_ID" -- bash -lc \
  'cd /workspace && node --test test_total.mjs && node verify.mjs'
```

All four tests must pass, followed by `Verified report: total=42, row_count=3`.
Download the files before stopping the sandbox:

```shell
mkdir -p results
render ea sandboxes copy "$SANDBOX_ID:/workspace/outputs/report.json" results/report.json
render ea sandboxes copy "$SANDBOX_ID:/workspace/total.mjs" results/total.mjs
cat results/report.json
```

Expected report: `{"total":42,"row_count":3}`.

To send another task before cleanup, pass its text as the first argument to
`run_task.py` or `run_task.ts`. This reuses the session and executor. After a
connection failure, inspect the session before submitting more input; another run
submits a new task.

## 5. Clean up

Attempt both cleanup operations even if one fails:

```shell
render ea sandboxes stop "$SANDBOX_ID" --confirm -o json
```

| Action | Python | TypeScript |
| --- | --- | --- |
| Delete the OpenAI session | `python cleanup.py` | `npx tsx cleanup.ts` |

The helper retains `session.json` when deletion fails. Keep the sandbox ID until
Render confirms termination. After both operations succeed:

```shell
rm -f executor.env
unset OPENAI_API_KEY SANDBOX_ID
```

## Troubleshooting

For executor connection problems, inspect its log while the sandbox is running:

```shell
render ea sandboxes exec "$SANDBOX_ID" -- cat /tmp/codex-exec-server.log
```

Check that the environment key has connection access and matches the session's
ownership. The executor needs outbound access to OpenAI; this example uses
`allow-all` for package installation and the connection.

This tutorial demonstrates explicit provisioning of one session and sandbox.
Production applications also need durable resource tracking, reconciliation of
uncertain allocations, and cleanup in failure paths.
