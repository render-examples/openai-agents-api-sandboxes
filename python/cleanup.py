import json
import time
from pathlib import Path
from openai import ConflictError, NotFoundError, OpenAI

path = Path("session.json")
session_id = json.loads(path.read_text())["session_id"]
with OpenAI(timeout=10, max_retries=0) as client:
    for attempt in range(12):
        try:
            result = client.beta.agents.sessions.delete(session_id)
            if not result.deleted:
                raise RuntimeError("Session deletion was not confirmed.")
            break
        except NotFoundError:
            break
        except ConflictError:
            if attempt == 11:
                raise
            time.sleep(3)
path.unlink()
print("Session deleted.")
