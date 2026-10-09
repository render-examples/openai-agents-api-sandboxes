// Run inside the sandbox after restoring the original tests and input.
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { execFileSync } from 'node:child_process';

const expected = { total: 42, row_count: 3 };
const report = JSON.parse(readFileSync('/workspace/outputs/report.json', 'utf8'));
assert.deepEqual(report, expected);
const output = execFileSync(process.execPath, ['/workspace/total.mjs', '/workspace/orders.csv'],
  { encoding: 'utf8', timeout: 10_000 });
assert.deepEqual(JSON.parse(output), expected);
console.log('Verified report: total=42, row_count=3');
