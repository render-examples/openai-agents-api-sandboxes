import json
import os
import subprocess
import time

sandbox_id = os.environ["SANDBOX_ID"]
deadline = time.monotonic() + 120
while time.monotonic() < deadline:
    result = subprocess.run(
        ["render", "ea", "sandboxes", "list", "--all", "-o", "json"],
        check=True, capture_output=True, text=True,
        timeout=max(0.1, min(20, deadline - time.monotonic())),
    )
    rows = json.loads(result.stdout) or []
    sandbox = next((row for row in rows if row["id"] == sandbox_id), None)
    if sandbox:
        if sandbox["status"] == "running":
            print("Sandbox is running.")
            break
        if sandbox["status"] in {"errored", "terminated"}:
            raise RuntimeError(f"{sandbox_id}: {sandbox['status']}")
    time.sleep(min(4, max(0, deadline - time.monotonic())))
else:
    raise TimeoutError(f"{sandbox_id} did not reach running; run cleanup.")
