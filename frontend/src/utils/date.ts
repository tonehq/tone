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

/** Compact `<m>m <s>s` / `<s>s` rendering for a call duration in seconds. */
export function formatDuration(seconds: number | null): string {
  if (seconds == null) return '-';
  const mins = Math.floor(seconds / 60);
  const secs = seconds % 60;
  return mins > 0 ? `${mins}m ${secs}s` : `${secs}s`;
}
