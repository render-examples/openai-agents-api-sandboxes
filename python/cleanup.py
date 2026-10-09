import json
import time
from pathlib import Path
from openai import ConflictError, NotFoundError, OpenAI

# This deletes the OpenAI session. Stop the Render sandbox separately with the CLI.
path = Path("session.json")
session_id = json.loads(path.read_text())["session_id"]
with OpenAI(timeout=10, max_retries=0) as client:
    for attempt in range(12):
        try:
            result = client.beta.agents.sessions.delete(session_id)
            if not result.deleted:
                raise RuntimeError("Session deletion was not confirmed.")
            break
        # An already-deleted session also counts as successful cleanup.
        except NotFoundError:
            break
        # A session can briefly reject deletion while its state is changing.
        except ConflictError:
            if attempt == 11:
                raise
            time.sleep(3)
# Retain session.json if deletion fails so cleanup can be retried.
path.unlink()
print("Session deleted.")
