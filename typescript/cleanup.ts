import { readFileSync, unlinkSync } from "node:fs";
import { setTimeout as sleep } from "node:timers/promises";
import OpenAI from "openai";

// This deletes the OpenAI session. Stop the Render sandbox separately with the CLI.
const { session_id } = JSON.parse(readFileSync("session.json", "utf8"));
const client = new OpenAI({ timeout: 10_000, maxRetries: 0 });
for (let attempt = 0; attempt < 12; attempt++) {
  try {
    const result = await client.beta.agents.sessions.delete(session_id);
    if (!result.deleted) throw new Error("Session deletion was not confirmed.");
    break;
  } catch (error) {
    // An already-deleted session also counts as successful cleanup.
    if (error instanceof OpenAI.NotFoundError) break;
    // Retry briefly if deletion conflicts with a session state change.
    if (!(error instanceof OpenAI.ConflictError) || attempt === 11) throw error;
    await sleep(3_000);
  }
}
// Retain session.json if deletion fails so cleanup can be retried.
unlinkSync("session.json");
console.log("Session deleted.");
