import { readFileSync, unlinkSync } from "node:fs";
import OpenAI from "openai";

// This deletes the OpenAI session. Stop the Render sandbox separately with the CLI.
const { session_id } = JSON.parse(readFileSync("session.json", "utf8"));
// The SDK retries 409 with backoff while the session state changes.
const client = new OpenAI({ timeout: 10_000, maxRetries: 5 });
try {
  const result = await client.beta.agents.sessions.delete(session_id);
  if (!result.deleted) throw new Error("Session deletion was not confirmed.");
} catch (error) {
  // An already-deleted session also counts as successful cleanup.
  if (!(error instanceof OpenAI.NotFoundError)) throw error;
}
// Retain session.json if deletion fails so cleanup can be retried.
unlinkSync("session.json");
console.log("Session deleted.");
