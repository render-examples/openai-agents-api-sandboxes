import { execFileSync } from "node:child_process";
import { setTimeout as sleep } from "node:timers/promises";

type Sandbox = { id: string; status: string };
// Run locally using the Render CLI login or RENDER_API_KEY.
const sandboxId = process.env.SANDBOX_ID;
if (!sandboxId) throw new Error("Set SANDBOX_ID first.");
// Sandbox creation is asynchronous. Limit the readiness wait to two minutes.
const deadline = performance.now() + 120_000;
let ready = false;
while (performance.now() < deadline) {
  const output = execFileSync("render", [
    "ea", "sandboxes", "list", "--all", "-o", "json",
  ], {
    encoding: "utf8",
    timeout: Math.max(1, Math.min(20_000, deadline - performance.now())),
  });
  const rows: Sandbox[] = JSON.parse(output) ?? [];
  // Check only the sandbox created for this walkthrough.
  const sandbox = rows.find((row) => row.id === sandboxId);
  if (sandbox?.status === "running") {
    ready = true;
    break;
  }
  // These states cannot become ready without further action.
  if (sandbox && ["errored", "terminated"].includes(sandbox.status)) {
    throw new Error(`${sandboxId}: ${sandbox.status}`);
  }
  await sleep(Math.min(4_000, Math.max(0, deadline - performance.now())));
}
if (!ready) throw new Error(`${sandboxId} did not reach running; run cleanup.`);
console.log("Sandbox is running.");
