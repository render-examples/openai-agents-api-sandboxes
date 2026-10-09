import { readFileSync } from 'node:fs';
import { pathToFileURL } from 'node:url';

export function summarize(csv) {
  const rows = csv.trim().split(/\r?\n/).slice(1);
  const amounts = rows.filter(Boolean).map(Number);
  return {
    total: amounts.slice(0, -1).reduce((sum, value) => sum + value, 0),
    row_count: amounts.length,
  };
}

if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) {
  console.log(JSON.stringify(summarize(readFileSync(process.argv[2], 'utf8'))));
}
