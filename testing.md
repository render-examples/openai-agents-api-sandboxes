# Testing

## Automated tests

The automated tests run both clients against a fake Render CLI and a fake OpenAI server. They do not need real keys or a Render account.

Run these commands from the repo root in Bash or zsh:

```shell
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-dev.txt
ruff format --check .
ruff check .
npm ci --prefix typescript
npm run typecheck --prefix typescript
python -m pytest -q
```

Each test runs once for Python and once for TypeScript.

## Test coverage

The tests check that both clients send the same requests for session creation, task submission, follow-up tasks, readiness checks, and cleanup. These tests check error cases and file permissions:

- `test_missing_sandbox_id`: `run_task` and `wait_for_sandbox` exit with `Set SANDBOX_ID first.` when `SANDBOX_ID` is not set. They do not send a request or call the Render CLI. Python does not print a traceback.
- `test_cleanup[conflict]`: the fake server returns 409 to the first delete request. The SDK retries, so the client sends two delete requests and the cleanup succeeds.
- `test_create_and_no_overwrite`: `create_session` writes `session.json` with mode 600, and a second run fails without a new request.

## Manual end-to-end test

The manual test uses real keys and creates real resources.

1. Upgrade the Render CLI to 2.28.0 or later. Check the version with `render --version`.
2. Follow the [README](README.md) with real keys, one time for Python and one time for TypeScript.
3. After `create_session`, run `ls -l session.json`. The output must start with `-rw-------`.
4. After cleanup, confirm that the OpenAI session is deleted and that `session.json` no longer exists.
