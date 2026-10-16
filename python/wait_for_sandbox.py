import json
import os
import subprocess
import sys
import time

# Run locally using the Render CLI login or RENDER_API_KEY.
sandbox_id = os.environ.get("SANDBOX_ID")
if not sandbox_id:
    sys.exit("Set SANDBOX_ID first.")
# Sandbox creation is asynchronous. Limit the readiness wait to two minutes.
deadline = time.monotonic() + 120
ready = False
while time.monotonic() < deadline:
    result = subprocess.run(
        ["render", "ea", "sandboxes", "list", "--all", "-o", "json"],
        check=True,
        capture_output=True,
        text=True,
        timeout=max(0.1, min(20, deadline - time.monotonic())),
    )
    rows = json.loads(result.stdout) or []
    # Check only the sandbox created for this walkthrough.
    sandbox = next((row for row in rows if row["id"] == sandbox_id), None)
    if sandbox and sandbox["status"] == "running":
        ready = True
        break
    # These states cannot become ready without further action.
    if sandbox and sandbox["status"] in {"errored", "terminated"}:
        raise RuntimeError(f"{sandbox_id}: {sandbox['status']}")
    time.sleep(min(4, max(0, deadline - time.monotonic())))
if not ready:
    raise TimeoutError(f"{sandbox_id} did not reach running; run cleanup.")
print("Sandbox is running.")
