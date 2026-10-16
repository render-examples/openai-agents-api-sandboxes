import json
from pathlib import Path
from openai import NotFoundError, OpenAI

# This deletes the OpenAI session. Stop the Render sandbox separately with the CLI.
path = Path("session.json")
session_id = json.loads(path.read_text())["session_id"]
# The SDK retries 409 with backoff while the session state changes.
with OpenAI(timeout=10, max_retries=5) as client:
    try:
        result = client.beta.agents.sessions.delete(session_id)
        if not result.deleted:
            raise RuntimeError("Session deletion was not confirmed.")
    # An already-deleted session also counts as successful cleanup.
    except NotFoundError:
        pass
# Retain session.json if deletion fails so cleanup can be retried.
path.unlink()
print("Session deleted.")
