const MINUTE = 60_000;
const HOUR = 60 * MINUTE;
const DAY = 24 * HOUR;

const relative = new Intl.RelativeTimeFormat('ar', { numeric: 'auto' });
const dayLabel = new Intl.DateTimeFormat('ar', {
  weekday: 'long',
  day: 'numeric',
  month: 'long',
});

/** Arabic relative time for the conversation list ("قبل ٣ دقايق"). */
export function relativeTime(iso: string, now: number = Date.now()): string {
  const then = new Date(iso).getTime();
  if (Number.isNaN(then)) return '';

  const diff = then - now;
  const magnitude = Math.abs(diff);

  if (magnitude < MINUTE) return relative.format(0, 'minute');
  if (magnitude < HOUR) return relative.format(Math.round(diff / MINUTE), 'minute');
  if (magnitude < DAY) return relative.format(Math.round(diff / HOUR), 'hour');
  if (magnitude < 7 * DAY) return relative.format(Math.round(diff / DAY), 'day');
  return dayLabel.format(new Date(then));
}

/** "اليوم" / "امبارح" / the date — the divider between days in a thread. */
export function dayKey(iso: string): string {
  const date = new Date(iso);
  return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}-${String(
    date.getDate(),
  ).padStart(2, '0')}`;
}

export function dayLabelFor(iso: string): string {
  const date = new Date(iso);
  const today = new Date();
  const yesterday = new Date(today);
  yesterday.setDate(today.getDate() - 1);

  if (dayKey(iso) === dayKey(today.toISOString())) return 'اليوم';
  if (dayKey(iso) === dayKey(yesterday.toISOString())) return 'امبارح';
  return dayLabel.format(date);
}

export function clockTime(iso: string): string {
  return new Intl.DateTimeFormat('ar', { hour: '2-digit', minute: '2-digit' }).format(
    new Date(iso),
  );
}
