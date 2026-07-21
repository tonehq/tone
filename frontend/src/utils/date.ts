import { TZDate } from '@date-fns/tz';
import dayjs from 'dayjs';
import relativeTime from 'dayjs/plugin/relativeTime';
import utc from 'dayjs/plugin/utc';

dayjs.extend(utc);
dayjs.extend(relativeTime);

const pad = (n: number) => String(n).padStart(2, '0');

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
 * Combine a calendar day + `HH:mm` time, interpreted in `tz`, into a `Z`-normalized
 * UTC ISO instant (e.g. `2026-06-05T11:14:00.000Z`). Shared by the DateRangePicker and
 * the single-instant DateTimePicker so both emit the same UTC form the backend expects.
 */
export function combineToIso(day: Date, time: string, tz: string): string {
  const [h, m] = time.split(':').map((s) => parseInt(s, 10));
  const tzDate = TZDate.tz(
    tz,
    day.getFullYear(),
    day.getMonth(),
    day.getDate(),
    Number.isFinite(h) ? h : 0,
    Number.isFinite(m) ? m : 0,
  );
  return new Date(tzDate.getTime()).toISOString();
}

/** Split a UTC ISO instant into its wall-clock day + `HH:mm` time within `tz`. */
export function splitFromIso(iso: string, tz: string): { day: Date; time: string } {
  const d = new TZDate(new Date(iso), tz);
  return {
    day: new Date(d.getFullYear(), d.getMonth(), d.getDate()),
    time: `${pad(d.getHours())}:${pad(d.getMinutes())}`,
  };
}

/** All IANA timezones the runtime exposes, falling back to `['UTC', browserTz]`. */
export function getTimeZones(): string[] {
  try {
    const supported = (Intl as unknown as { supportedValuesOf?: (k: string) => string[] })
      .supportedValuesOf;
    if (typeof supported === 'function') return supported('timeZone');
  } catch {
    /* older runtimes — fall through */
  }
  return ['UTC', getBrowserTimeZone()];
}

/**
 * Short timezone abbreviation (e.g. `EDT`, `IST`) for `timeZone` at instant `at`
 * (defaults to now, so DST is resolved correctly). Returns `''` on unsupported
 * runtimes/invalid zones. Used to show `Zone (ABBR)` under the schedule-time field.
 */
export function getTimeZoneAbbreviation(timeZone: string, at?: string | Date): string {
  try {
    const date = at ? new Date(at) : new Date();
    const parts = new Intl.DateTimeFormat('en-US', {
      timeZone,
      timeZoneName: 'short',
    }).formatToParts(date);
    return parts.find((p) => p.type === 'timeZoneName')?.value ?? '';
  } catch {
    return '';
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

// Hoisted to module scope so a long transcript doesn't reconstruct the
// formatter per message render.
const CHAT_TIMESTAMP_FORMATTER = new Intl.DateTimeFormat(undefined, {
  weekday: 'short',
  month: 'short',
  day: 'numeric',
  hour: 'numeric',
  minute: '2-digit',
});

// Time-only display (e.g. `2:03:47 PM`) for places where the surrounding
// context already implies the date — call detail header chips, transcript
// bubbles, per-sample timestamps. Hoisted to module scope so long lists
// don't reconstruct the formatter per render.
const TIME_ONLY_FORMATTER = new Intl.DateTimeFormat(undefined, {
  hour: 'numeric',
  minute: '2-digit',
  second: '2-digit',
});

/**
 * Compact, human-readable timestamp for chat/transcript bubbles
 * (e.g. `Wed, Jun 10 · 2:03 PM`). Returns `null` for empty / invalid input
 * so callers can decide whether to render anything at all.
 */
export function formatChatTimestamp(ts: string | null | undefined): string | null {
  if (!ts) return null;
  const date = new Date(ts);
  if (Number.isNaN(date.getTime())) return null;
  return CHAT_TIMESTAMP_FORMATTER.format(date);
}

/**
 * Time-only timestamp (e.g. `2:03:47 PM`) for places where the surrounding
 * context already conveys the date — call detail header chips, transcript
 * bubbles, per-sample charts. Returns `null` for empty / invalid input.
 */
export function formatTimeOnly(ts: string | null | undefined): string | null {
  if (!ts) return null;
  const date = new Date(ts);
  if (Number.isNaN(date.getTime())) return null;
  return TIME_ONLY_FORMATTER.format(date);
}
