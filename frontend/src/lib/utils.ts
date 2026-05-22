import { type ClassValue, clsx } from 'clsx';
import { twMerge } from 'tailwind-merge';
import { format, formatDistanceToNow } from 'date-fns';

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function formatDate(iso: string | null | undefined) {
  if (!iso) return '—';
  return format(new Date(iso), 'MMM d, yyyy');
}

export function formatDateTime(iso: string | null | undefined) {
  if (!iso) return '—';
  return format(new Date(iso), 'MMM d, yyyy HH:mm');
}

export function formatRelative(iso: string | null | undefined) {
  if (!iso) return '—';
  return formatDistanceToNow(new Date(iso), { addSuffix: true });
}

export function formatDuration(seconds: number | null | undefined) {
  if (seconds == null) return '—';
  if (seconds < 60) return `${seconds.toFixed(1)}s`;
  const m = Math.floor(seconds / 60);
  const s = Math.round(seconds % 60);
  return `${m}m ${s}s`;
}

export function formatCost(amount: number | null | undefined) {
  if (amount == null) return '—';
  return `$${amount.toFixed(4)}`;
}

export function formatPercent(value: number | null | undefined) {
  if (value == null) return '—';
  return `${value.toFixed(1)}%`;
}

export function formatLatency(ms: number | null | undefined) {
  if (ms == null) return '—';
  if (ms < 1000) return `${Math.round(ms)}ms`;
  return `${(ms / 1000).toFixed(2)}s`;
}

export function formatScore(score: number | null | undefined) {
  if (score == null) return '—';
  return score.toFixed(2);
}

export function truncate(str: string, length = 50) {
  if (str.length <= length) return str;
  return `${str.slice(0, length)}…`;
}

export function getInitials(first?: string | null, last?: string | null) {
  return `${(first ?? '').charAt(0)}${(last ?? '').charAt(0)}`.toUpperCase() || '?';
}

export function toSelectOptions<T extends Record<string, any>>(
  items: readonly T[] | T[] | undefined | null,
  opts?: {
    valueKey?: keyof T;
    labelKey?: keyof T;
    labelFn?: (item: T) => string;
  },
): { value: string; label: string }[] {
  if (!items || items.length === 0) return [];
  const vk = opts?.valueKey ?? ('value' in items[0] ? 'value' : 'id');
  const lk = opts?.labelKey ?? ('label' in items[0] ? 'label' : 'name');
  return items.map((item) => ({
    value: String(item[vk] ?? ''),
    label: opts?.labelFn ? opts.labelFn(item) : String(item[lk] ?? ''),
  }));
}
