import json
from pathlib import Path
from openai import OpenAI

# Keep the existing session ID available for cleanup instead of overwriting it.
path = Path("session.json")
if path.exists():
    raise RuntimeError("session.json already exists. Clean up that session first.")

# Run locally: the SDK reads the application key from OPENAI_API_KEY.
# This creates an OpenAI session; the Render CLI creates the sandbox separately.
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
# Save the IDs and connection URL for run_task.py and cleanup.py.
path.write_text(json.dumps({
    "session_id": session.id,
    "environment_id": session.environment.id,
    "remote_url": session.environment.remote_url,
}))
