import asyncio
import json
import os
import subprocess
import sys
from pathlib import Path
from uuid import uuid4
from openai import AsyncOpenAI

# Reuse the session created by create_session.py.
state = json.loads(Path("session.json").read_text())
# A command-line prompt sends a follow-up through the existing executor.
follow_up = len(sys.argv) > 1
prompt = sys.argv[1] if follow_up else (
    Path(__file__).resolve().parent.parent / "prompt.txt"
).read_text()
# Only the first run starts the executor, so only it needs the sandbox ID.
sandbox_id = os.environ.get("SANDBOX_ID")
if not follow_up and not sandbox_id:
    sys.exit("Set SANDBOX_ID first.")
# Each script invocation is a new submission. SDK retries reuse this key.
idempotency_key = str(uuid4())


async def run_task():
    async with AsyncOpenAI(timeout=30) as client:
        # Subscribe before starting the executor or submitting work.
        stream = await client.beta.agents.sessions.events.stream(state["session_id"])
        async with stream:
            # The Render CLI runs this command remotely, inside the sandbox.
            # The executor inherits CODEX_API_KEY from the sandbox environment.
            if not follow_up:
                # Detach the executor so it survives the CLI command finishing.
                # Write its diagnostics to /tmp/codex-exec-server.log in the sandbox.
                await asyncio.to_thread(
                    subprocess.run,
                    ["render", "ea", "sandboxes", "exec", sandbox_id,
                     "--", "bash", "-lc",
                     'nohup codex exec-server --remote "$1" --environment-id "$2" '
                     '> /tmp/codex-exec-server.log 2>&1 < /dev/null & '
                     'echo $! > /tmp/codex-exec-server.pid',
                     "_", state["remote_url"], state["environment_id"]],
                    check=True, timeout=30,
                )
            # Send the task to OpenAI.
            await client.beta.agents.sessions.events.create(
                state["session_id"],
                idempotency_key=idempotency_key,
                events=[{
                    "type": "agent.session.input.message",
                    "input": [{"role": "user", "content": [
                        {"type": "input_text", "text": prompt}
                    ]}],
                }],
            )
            async for event in stream:
                # Ignore other sessions and child-agent turns when checking completion.
                if getattr(event, "session_id", None) != state["session_id"]:
                    continue
                if getattr(getattr(event, "turn", None), "subagent_id", None):
                    continue
                # Text arrives in chunks; wait for the completion event before verifying files.
                if event.type == "agent.session.turn.output_text.delta":
                    print(event.delta, end="", flush=True)
                elif event.type == "agent.session.turn.completed":
                    print("\nTurn completed.")
                    return
                elif event.type in {
                    "agent.session.error", "agent.session.environment.failed",
                    "agent.session.turn.failed", "agent.session.turn.cancelled",
                }:
                    raise RuntimeError(event.model_dump_json())
        raise RuntimeError("The stream ended without a completed turn.")

async def main():
    # Bound the local wait. Timing out does not stop the sandbox or delete the session.
    await asyncio.wait_for(run_task(), timeout=180)

asyncio.run(main())
