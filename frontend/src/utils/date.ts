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
