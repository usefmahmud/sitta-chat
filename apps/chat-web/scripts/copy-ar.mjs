import { readFileSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const here = dirname(fileURLToPath(import.meta.url));

/** docs/copy-ar.md is the single source of truth for UI copy. */
export const COPY_PATH = resolve(here, '../../../docs/copy-ar.md');

const ROW = /^\|\s*`([a-z][a-z0-9_.]*)`\s*\|\s*(.*?)\s*\|\s*.*\|\s*$/;

/** Parse the markdown tables into [key, arabic] pairs, in file order. */
export function parseCopy(markdown) {
  const entries = [];
  for (const line of markdown.split('\n')) {
    const match = ROW.exec(line);
    if (match) {
      entries.push([match[1], match[2]]);
    }
  }
  return entries;
}

export function readCopy() {
  return parseCopy(readFileSync(COPY_PATH, 'utf8'));
}

export function renderModule(entries) {
  const body = entries
    .map(([key, value]) => `  ${JSON.stringify(key)}: ${JSON.stringify(value)},`)
    .join('\n');

  return `// Generated from docs/copy-ar.md by scripts/generate-i18n.mjs.
// Do not edit by hand: change the markdown, then run \`npm run i18n:generate\`.
export const ar = {
${body}
} as const;

export type TranslationKey = keyof typeof ar;
`;
}
