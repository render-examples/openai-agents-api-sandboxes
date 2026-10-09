import { existsSync, writeFileSync } from "node:fs";
import OpenAI from "openai";

// Keep the existing session ID available for cleanup instead of overwriting it.
if (existsSync("session.json")) {
  throw new Error("session.json already exists. Clean up that session first.");
}
// Run locally: the SDK reads the application key from OPENAI_API_KEY.
// This creates an OpenAI session; the Render CLI creates the sandbox separately.
const client = new OpenAI({ timeout: 30_000, maxRetries: 0 });
const session = await client.beta.agents.sessions.create({
  agent: {
    model: "gpt-6-astra",
    instructions:
      "Work only in /workspace. Create files under /workspace/outputs. " +
      "Run commands to verify your work.",
  },
  environment: { type: "self_hosted", workspace_directory: "/workspace" },
});
console.log("Created session:", session.id);
if (session.environment.type !== "self_hosted") {
  throw new Error("Expected a self-hosted environment. Retain the session ID for cleanup.");
}
// Save the IDs and connection URL for run_task.ts and cleanup.ts.
writeFileSync("session.json", JSON.stringify({
  session_id: session.id,
  environment_id: session.environment.id,
  remote_url: session.environment.remote_url,
}), { mode: 0o600 });
