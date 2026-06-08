import dayjs from 'dayjs';
import relativeTime from 'dayjs/plugin/relativeTime';
import utc from 'dayjs/plugin/utc';

dayjs.extend(utc);
dayjs.extend(relativeTime);

export const DATE_FORMAT = 'DD MMM YYYY, HH:mm A';

export function formatDate(value: number | string, format: string = DATE_FORMAT): string {
  if (typeof value === 'number') {
    return dayjs.unix(value).format(format);
  }
  return dayjs.utc(value).local().format(format);
}

export function formatNow(format: string = DATE_FORMAT): string {
  return dayjs().format(format);
}

export function formatRelative(value: number | string | null | undefined): string {
  if (value === null || value === undefined) return '—';
  const d = typeof value === 'number' ? dayjs.unix(value) : dayjs.utc(value).local();
  return d.fromNow();
}

/** Locale-aware timestamp used by call-history, call-detail-drawer and call-metrics tables. */
export function formatTimestamp(ts: string | null): string {
  if (!ts) return '-';
  return new Date(ts).toLocaleString();
}

/**
 * The browser's resolved IANA timezone (e.g. `Asia/Kolkata`), falling back to
 * `UTC` on older runtimes that don't expose it. Shared by the DateRangePicker
 * and Call History so the default zone is resolved in one place.
 */
export function getBrowserTimeZone(): string {
  try {
    return Intl.DateTimeFormat().resolvedOptions().timeZone || 'UTC';
  } catch {
    return 'UTC';
  }
}

/**
 * Format a UTC ISO instant for display in a specific IANA timezone
 * (e.g. `Jun 5, 4:44 PM`). Used by the shared DateRangePicker trigger so the
 * label always reflects the user's chosen zone, not the browser default.
 */
export function formatTzDateTime(iso: string, timeZone: string): string {
  return new Intl.DateTimeFormat(undefined, {
    month: 'short',
    day: 'numeric',
    hour: 'numeric',
    minute: '2-digit',
    timeZone,
  }).format(new Date(iso));
}

/** Compact `<m>m <s>s` / `<s>s` rendering for a call duration in seconds. */
export function formatDuration(seconds: number | null): string {
  if (seconds == null) return '-';
  const mins = Math.floor(seconds / 60);
  const secs = seconds % 60;
  return mins > 0 ? `${mins}m ${secs}s` : `${secs}s`;
}
