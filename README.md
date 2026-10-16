# OpenAI Agents API on Render Sandboxes

Run an OpenAI agent's commands and file operations in a Render Sandbox. Choose a
Python or TypeScript client; both run the same task.

The agent repairs a JavaScript program that skips the last row of a CSV file.
You verify the repair through Render and download the corrected code and report.

```text
                     +-------------------------------+
                     | OpenAI                        |
                     |   Agents API session          |
                     +-------------------------------+
                          ^                     ^
  session, task,          |                     |  executor connects out
  events (HTTPS)          |                     |  with the environment key
                          |                     |
+-------------------------+---+   +-------------+-------------+
| Your machine                |   | Render Sandbox            |
|   Python or TypeScript      |   |   Codex executor          |
|   client                    |   |   /workspace: task files  |
|   Render CLI ---------------+-->|                           |
+-----------------------------+   +---------------------------+
                      create, exec, copy
```

```text
run.sh        Runs all steps with one command
python/       Python client and requirements
typescript/   TypeScript client and lockfile
scripts/      Shell scripts for the sandbox steps and cleanup
fixture/      Input CSV, broken program, and four tests
prompt.txt    Task sent to the agent
verify.mjs    Independent report verification, run inside Render
```

## Quick start

Get the two keys in [Requirements](#requirements). Then clone the repository
and sign in to Render, as in the first three steps of
[Install your client](#1-install-your-client).

From the repository root, run one of these commands:

```shell
./run.sh python
./run.sh typescript
```

The script installs the client, asks for the application key and the
environment key, and runs steps 2 to 4. If `OPENAI_API_KEY` is set, the script
uses it and does not ask. The results go to `results/` at the repository root.

When the script exits, it stops the sandbox and deletes the session. This also
happens after a failure or Ctrl-C. If cleanup fails, the script prints the
command to run it again.

To run each step by hand, follow the numbered sections below.

## Requirements

- Render Sandboxes access and Render CLI 2.28.0 or later.
- Python 3.10 or later, or Node.js 22 or later. Use Bash for the shared commands.
- An OpenAI project with Agents API access, an application key, and an
  environment key. Both keys must belong to the same organization, project, and
  user or service account.

Create the application key in the OpenAI platform, on the **API keys** tab.
Choose a restricted key. Set **Agents** and **Responses** to **Write**, and turn
off all other permissions. The clients read it from `OPENAI_API_KEY`.

Create the environment key in the OpenAI platform. Open the **Agents** tab, then
**Environments** > **Keys** > **Create**, and choose a self-hosted key. The
sandbox stores the environment key as `CODEX_API_KEY`. See
[OpenAI self-hosted authentication](https://developers.openai.com/api/docs/guides/agents-api/environments/self-hosted#authentication).

The application key stays on your machine. Only the environment key goes into the
sandbox. Code running in the sandbox can read its environment variables.

## 1. Install your client

Run these steps separately in Bash or zsh:

1. Clone the example:

   ```shell
   git clone https://github.com/render-examples/openai-agents-api-sandboxes.git
   cd openai-agents-api-sandboxes
   ```

2. Sign in to Render. Complete the browser login before continuing:

   ```shell
   render login
   ```

3. Select your Render workspace. Replace the placeholder with your workspace ID from the Render Dashboard:

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
printf 'OpenAI application key: '
read -rs OPENAI_API_KEY
printf '\n'
export OPENAI_API_KEY
```

## 2. Create the session and sandbox

Create the OpenAI session.

**Python:**

```shell
python create_session.py
```

**TypeScript:**

```shell
npx tsx create_session.ts
```

The command prints the session ID and saves it to `session.json`. Keep this file
until cleanup succeeds. The command stops if `session.json` already exists. If
creation times out, check the OpenAI dashboard before you try again, because the
session might exist.

Create the sandbox. The script asks for the environment key and prints the
sandbox ID:

```shell
export SANDBOX_ID="$(../scripts/create_sandbox.sh)"
echo "$SANDBOX_ID"
```

The sandbox stops after 15 minutes. From now on, run [cleanup](#5-clean-up) even
if a later step fails. If creation fails or times out, look for the sandbox in the
[Render Dashboard](https://dashboard.render.com) before you try again.

Wait until the sandbox is running.

**Python:**

```shell
python wait_for_sandbox.py
```

**TypeScript:**

```shell
npx tsx wait_for_sandbox.ts
```

The command prints `Sandbox is running.` when the sandbox is ready.

## 3. Run the task

Install the executor and copy `fixture/` to `/workspace` in the sandbox:

```shell
../scripts/stage.sh
```

Submit the task and stream its events.

**Python:**

```shell
python run_task.py
```

**TypeScript:**

```shell
npx tsx run_task.ts
```

The client opens the event stream before it starts the executor and submits
`prompt.txt`. It waits up to three minutes for the root turn to complete. A
timeout ends only the local wait. Run cleanup if you stop here.

The model should fix the CSV total from `30` to `42`. Its response alone does not
prove success.

## 4. Verify and download

Restore the original input and tests, check the agent's program and report, and
download the results:

```shell
../scripts/verify.sh
```

All four tests must pass, followed by `Verified report: total=42, row_count=3`.
The script saves `report.json` and `total.mjs` to `results/` at the repository
root and prints the report. Expected report: `{"total":42,"row_count":3}`.

To send another task before cleanup, pass its text as the first argument to
`run_task.py` or `run_task.ts`. This reuses the session and executor. After a
connection failure, inspect the session before you submit more input, because
another run submits a new task.

## 5. Clean up

Stop the sandbox and delete the OpenAI session.

**Python:**

```shell
../scripts/cleanup.sh python
```

**TypeScript:**

```shell
../scripts/cleanup.sh typescript
```

The script does both steps, even if one fails, and exits with an error if
either fails. It skips the sandbox if `SANDBOX_ID` is not set, and it skips the
session if `session.json` does not exist. The client keeps `session.json` when
deletion fails, so you can run the script again. After the script succeeds:

```shell
unset OPENAI_API_KEY SANDBOX_ID
```

## Troubleshooting

For executor connection problems, inspect its log while the sandbox is running:

```shell
render ea sandboxes exec "$SANDBOX_ID" -- cat /tmp/codex-exec-server.log
```

Check that the environment key matches the session's organization, project, and
owner. The executor needs outbound access to OpenAI. This example uses the
`allow-all` network policy for package installation and the connection.

This tutorial creates one session and one sandbox by hand. Production
applications also need durable resource tracking, reconciliation of uncertain
allocations, and cleanup in failure paths.
