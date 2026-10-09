import json
from pathlib import Path
from openai import OpenAI

path = Path("session.json")
if path.exists():
    raise RuntimeError("session.json already exists. Clean up that session first.")

with OpenAI(timeout=30, max_retries=0) as client:
    session = client.beta.agents.sessions.create(
        agent={
            "model": "gpt-6-astra",
            "instructions": (
                "Work only in /workspace. Create files under /workspace/outputs. "
                "Run commands to verify your work."
            ),
        },
        environment={
            "type": "self_hosted",
            "workspace_directory": "/workspace",
        },
    )

print("Created session:", session.id)
path.write_text(json.dumps({
    "session_id": session.id,
    "environment_id": session.environment.id,
    "remote_url": session.environment.remote_url,
}))
