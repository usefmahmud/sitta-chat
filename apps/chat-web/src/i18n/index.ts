import { ar, type TranslationKey } from './ar';

export type { TranslationKey };

/**
 * Resolve a key from docs/copy-ar.md and fill `{placeholders}`.
 * A missing key renders the key itself, which makes gaps obvious in dev.
 */
export function t(
  key: TranslationKey,
  params?: Record<string, string | number>,
): string {
  const template: string = ar[key] ?? key;
  if (!params) return template;

  return template.replace(/\{(\w+)\}/g, (match, name: string) => {
    const value = params[name];
    return value === undefined ? match : String(value);
  });
}

export const translationKeys = Object.keys(ar) as TranslationKey[];
