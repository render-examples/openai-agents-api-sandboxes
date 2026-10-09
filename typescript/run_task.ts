import { execFileSync } from "node:child_process";
import { randomUUID } from "node:crypto";
import { readFileSync } from "node:fs";
import OpenAI from "openai";

const state = JSON.parse(readFileSync("session.json", "utf8"));
const followUp = process.argv[2];
const prompt = followUp ?? readFileSync(new URL("../prompt.txt", import.meta.url), "utf8");
const client = new OpenAI({ timeout: 30_000, maxRetries: 0 });
const signal = AbortSignal.timeout(180_000);
const stream = await client.beta.agents.sessions.events.stream(
  state.session_id, { signal },
);
let completed = false;
try {
  if (!followUp) {
    const sandboxId = process.env.SANDBOX_ID;
    if (!sandboxId) throw new Error("Set SANDBOX_ID first.");
    execFileSync("render", [
      "ea", "sandboxes", "exec", sandboxId, "--", "bash", "-lc",
      'nohup codex exec-server --remote "$1" --environment-id "$2" ' +
        '> /tmp/codex-exec-server.log 2>&1 < /dev/null & ' +
        'echo $! > /tmp/codex-exec-server.pid',
      "_", state.remote_url, state.environment_id,
    ], { stdio: "inherit", timeout: 30_000 });
  }
  await client.beta.agents.sessions.events.create(state.session_id, {
    "Idempotency-Key": randomUUID(),
    events: [{
      type: "agent.session.input.message",
      input: [{ role: "user", content: [{ type: "input_text", text: prompt }] }],
    }],
  }, { signal });
  for await (const event of stream) {
    if (!("session_id" in event) || event.session_id !== state.session_id) continue;
    if ("turn" in event && event.turn.subagent_id) continue;
    if (event.type === "agent.session.turn.output_text.delta") {
      process.stdout.write(event.delta);
    } else if (event.type === "agent.session.turn.completed") {
      completed = true;
      console.log("\nTurn completed.");
      break;
    } else if ([
      "agent.session.error", "agent.session.environment.failed",
      "agent.session.turn.failed", "agent.session.turn.cancelled",
    ].includes(event.type)) {
      throw new Error(JSON.stringify(event));
    }
  }
  if (!completed) throw new Error("The stream ended without a completed turn.");
} finally {
  stream.controller.abort();
}
