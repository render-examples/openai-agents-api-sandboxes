import { execFileSync } from "node:child_process";
import { setTimeout as sleep } from "node:timers/promises";

type Sandbox = { id: string; status: string };
const sandboxId = process.env.SANDBOX_ID;
if (!sandboxId) throw new Error("Set SANDBOX_ID first.");
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
  const sandbox = rows.find((row) => row.id === sandboxId);
  if (sandbox?.status === "running") {
    ready = true;
    break;
  }
  if (sandbox && ["errored", "terminated"].includes(sandbox.status)) {
    throw new Error(`${sandboxId}: ${sandbox.status}`);
  }
  await sleep(Math.min(4_000, Math.max(0, deadline - performance.now())));
}
if (!ready) throw new Error(`${sandboxId} did not reach running; run cleanup.`);
console.log("Sandbox is running.");
