import { writeFileSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

import { readCopy, renderModule } from './copy-ar.mjs';

const here = dirname(fileURLToPath(import.meta.url));
const target = resolve(here, '../src/i18n/ar.ts');

const entries = readCopy();
writeFileSync(target, renderModule(entries), 'utf8');
console.log(`i18n: wrote ${entries.length} keys to src/i18n/ar.ts`);
