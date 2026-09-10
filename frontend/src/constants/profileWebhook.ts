import type { SelectOption } from '@/types/components';

export const HTTP_METHOD_OPTIONS: SelectOption[] = [
  { value: 'GET', label: 'GET' },
  { value: 'POST', label: 'POST' },
];

export const REQUEST_IDENTIFIER_IN_OPTIONS: SelectOption[] = [
  { value: 'query', label: 'Query param' },
  { value: 'body', label: 'Request body' },
  { value: 'path', label: 'URL path ({param})' },
];

export const PROFILE_VARIABLE_SOURCE_OPTIONS: SelectOption[] = [
  { value: 'static', label: 'Static value' },
  { value: 'webhook', label: 'From webhook response' },
];

/** Shared tagline for the profile-variables surfaces (Advanced tab + workflow
 * drawer) so the copy stays in one place. */
export const PROFILE_VARIABLES_DESCRIPTION =
  'Reusable values referenced anywhere as {{profile.<key>}} — prompt, workflow nodes, and more. Update once, applied everywhere on the next call.';

export const DEFAULT_WEBHOOK_TIMEOUT_SECONDS = 3;
export const MIN_WEBHOOK_TIMEOUT_SECONDS = 1;
export const MAX_WEBHOOK_TIMEOUT_SECONDS = 30;
