import { readFileSync, unlinkSync } from "node:fs";
import { setTimeout as sleep } from "node:timers/promises";
import OpenAI from "openai";

const { session_id } = JSON.parse(readFileSync("session.json", "utf8"));
const client = new OpenAI({ timeout: 10_000, maxRetries: 0 });
for (let attempt = 0; attempt < 12; attempt++) {
  try {
    const result = await client.beta.agents.sessions.delete(session_id);
    if (!result.deleted) throw new Error("Session deletion was not confirmed.");
    break;
  } catch (error) {
    if (error instanceof OpenAI.NotFoundError) break;
    if (!(error instanceof OpenAI.ConflictError) || attempt === 11) throw error;
    await sleep(3_000);
  }
}
unlinkSync("session.json");
console.log("Session deleted.");
