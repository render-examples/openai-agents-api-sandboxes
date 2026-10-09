import asyncio
import json
import os
import subprocess
import sys
from pathlib import Path
from uuid import uuid4
from openai import AsyncOpenAI

state = json.loads(Path("session.json").read_text())
follow_up = len(sys.argv) > 1
prompt = sys.argv[1] if follow_up else (
    Path(__file__).resolve().parent.parent / "prompt.txt"
).read_text()


async def run_task():
    async with AsyncOpenAI(timeout=30, max_retries=0) as client:
        stream = await client.beta.agents.sessions.events.stream(state["session_id"])
        async with stream:
            if not follow_up:
                await asyncio.to_thread(
                    subprocess.run,
                    ["render", "ea", "sandboxes", "exec", os.environ["SANDBOX_ID"],
                     "--", "bash", "-lc",
                     'nohup codex exec-server --remote "$1" --environment-id "$2" '
                     '> /tmp/codex-exec-server.log 2>&1 < /dev/null & '
                     'echo $! > /tmp/codex-exec-server.pid',
                     "_", state["remote_url"], state["environment_id"]],
                    check=True, timeout=30,
                )
            await client.beta.agents.sessions.events.create(
                state["session_id"],
                idempotency_key=str(uuid4()),
                events=[{
                    "type": "agent.session.input.message",
                    "input": [{"role": "user", "content": [
                        {"type": "input_text", "text": prompt}
                    ]}],
                }],
            )
            async for event in stream:
                if getattr(event, "session_id", None) != state["session_id"]:
                    continue
                if getattr(getattr(event, "turn", None), "subagent_id", None):
                    continue
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
    await asyncio.wait_for(run_task(), timeout=180)

asyncio.run(main())
