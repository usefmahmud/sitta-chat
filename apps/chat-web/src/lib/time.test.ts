import { describe, expect, it } from 'vitest';

import { dayLabelFor, relativeTime } from './time';

const NOW = new Date('2026-03-10T12:00:00Z').getTime();

describe('relativeTime', () => {
  it('formats minutes, hours and days in Arabic', () => {
    expect(relativeTime(new Date(NOW - 30_000).toISOString(), NOW)).toContain('الدقيقة');
    expect(relativeTime(new Date(NOW - 5 * 60_000).toISOString(), NOW)).toBe('قبل 5 دقائق');
    expect(relativeTime(new Date(NOW - 3 * 3_600_000).toISOString(), NOW)).toBe('قبل 3 ساعات');
    expect(relativeTime(new Date(NOW - 2 * 86_400_000).toISOString(), NOW)).toBe('أول أمس');
  });

  it('returns an empty string for a bad date instead of throwing', () => {
    expect(relativeTime('not-a-date', NOW)).toBe('');
  });
});

describe('dayLabelFor', () => {
  it('labels today and yesterday, and shows a date for older days', () => {
    const today = new Date();
    expect(dayLabelFor(today.toISOString())).toBe('اليوم');

    const yesterday = new Date(today);
    yesterday.setDate(today.getDate() - 1);
    expect(dayLabelFor(yesterday.toISOString())).toBe('امبارح');

    expect(dayLabelFor('2020-01-01T10:00:00Z')).toMatch(/\d/);
  });
});
