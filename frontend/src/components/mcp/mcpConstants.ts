import type { SelectOption } from '@/types/components';

export const SORT_OPTIONS: SelectOption[] = [
  { value: 'created_at:desc', label: 'Newest' },
  { value: 'created_at:asc', label: 'Oldest' },
  { value: 'name:asc', label: 'Name A–Z' },
  { value: 'name:desc', label: 'Name Z–A' },
  { value: 'updated_at:desc', label: 'Recently updated' },
];

export const CHIP_TONES = {
  sky: 'bg-sky-500/10 text-sky-600 ring-sky-500/20 dark:text-sky-400',
  amber: 'bg-amber-500/10 text-amber-600 ring-amber-500/20 dark:text-amber-400',
} as const;
