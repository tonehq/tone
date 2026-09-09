import type { SelectOption } from '@/types/components';

export const HTTP_METHOD_OPTIONS: SelectOption[] = [
  { value: 'GET', label: 'GET' },
  { value: 'POST', label: 'POST' },
];

export const REQUEST_IDENTIFIER_IN_OPTIONS: SelectOption[] = [
  { value: 'query', label: 'Query param' },
  { value: 'body', label: 'Request body' },
];

export const PROFILE_VARIABLE_SOURCE_OPTIONS: SelectOption[] = [
  { value: 'static', label: 'Static value' },
  { value: 'webhook', label: 'From webhook response' },
];

export const DEFAULT_WEBHOOK_TIMEOUT_SECONDS = 3;
export const MIN_WEBHOOK_TIMEOUT_SECONDS = 1;
export const MAX_WEBHOOK_TIMEOUT_SECONDS = 30;
