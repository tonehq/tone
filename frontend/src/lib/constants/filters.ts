import type { SelectOption } from '@/types/components';

export const KNOWLEDGE_BASE_STATUS_OPTIONS: SelectOption[] = [
  { value: 'all', label: 'All statuses' },
  { value: 'ready', label: 'Ready' },
  { value: 'processing', label: 'Processing' },
  { value: 'failed', label: 'Failed' },
];

export const TOOL_TYPE_OPTIONS: SelectOption[] = [
  { value: 'all', label: 'All types' },
  { value: 'custom', label: 'Custom' },
  { value: 'send_sms', label: 'Send SMS' },
  { value: 'google_calendar', label: 'Google Calendar' },
  { value: 'google_sheets', label: 'Google Sheets' },
];

export const TOOL_STATUS_OPTIONS: SelectOption[] = [
  { value: 'all', label: 'All statuses' },
  { value: 'active', label: 'Active' },
  { value: 'inactive', label: 'Inactive' },
];
