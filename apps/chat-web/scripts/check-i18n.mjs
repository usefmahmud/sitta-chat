import { readFileSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

import { readCopy } from './copy-ar.mjs';

const here = dirname(fileURLToPath(import.meta.url));
const modulePath = resolve(here, '../src/i18n/ar.ts');

const fromMarkdown = readCopy().map(([key]) => key);
const moduleSource = readFileSync(modulePath, 'utf8');
const fromModule = [...moduleSource.matchAll(/^\s*"([^"]+)":/gm)].map((m) => m[1]);

const missing = fromMarkdown.filter((key) => !fromModule.includes(key));
const extra = fromModule.filter((key) => !fromMarkdown.includes(key));
const duplicates = fromModule.filter(
  (key, index) => fromModule.indexOf(key) !== index,
);

if (missing.length || extra.length || duplicates.length) {
  console.error('i18n parity FAILED');
  if (missing.length) console.error('  missing from src/i18n/ar.ts:', missing);
  if (extra.length) console.error('  extra (not in docs/copy-ar.md):', extra);
  if (duplicates.length) console.error('  duplicated keys:', duplicates);
  console.error('  fix with: npm run i18n:generate');
  process.exit(1);
}

console.log(
  `i18n parity ok: ${fromMarkdown.length} keys, 0 missing / 0 extra / 0 duplicates`,
);
