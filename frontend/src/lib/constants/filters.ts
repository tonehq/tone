import type { SelectOption } from '@/types/components';

export const KNOWLEDGE_BASE_STATUS_OPTIONS: SelectOption[] = [
  { value: 'all', label: 'All statuses' },
  { value: 'ready', label: 'Ready' },
  { value: 'processing', label: 'Processing' },
  { value: 'failed', label: 'Failed' },
];
