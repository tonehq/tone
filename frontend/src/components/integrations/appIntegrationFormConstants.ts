/** Constants + form-state shape for the app-integration create/edit form. */

import type { AppIntegrationAuthType } from '@/types/appIntegration';

export interface FormState {
  slug: string;
  display_name: string;
  description: string;
  category: string;
  icon_url: string;
  auth_type: AppIntegrationAuthType;
  auth_url: string;
  token_url: string;
  userinfo_url: string;
  scopes: string; // comma- or newline-separated; serialized to string[] on submit
  /** Plain credential value entered by the admin. Posted to the API as a
   * write-only field; the server never echoes it back. On edit mode the
   * inputs start empty — leaving them blank preserves the stored value. */
  client_id: string;
  client_secret: string;
  pkce_required: boolean;
  is_enabled: boolean;
  sort_order: number;
  extra_auth_params: string; // raw JSON; parsed on submit
}

// Radix Select reserves the empty string for "no selection". So when the user
// hasn't picked a category, the form state stays as ``NO_CATEGORY`` and we
// translate it to ``null`` on submit (and back on hydrate). Lets us still
// expose a real "Uncategorized" entry while keeping the placeholder UX intact.
export const NO_CATEGORY = '__none__';

export const DEFAULT_STATE: FormState = {
  slug: '',
  display_name: '',
  description: '',
  category: NO_CATEGORY,
  icon_url: '',
  auth_type: 'oauth',
  auth_url: '',
  token_url: '',
  userinfo_url: '',
  scopes: '',
  client_id: '',
  client_secret: '',
  pkce_required: true,
  is_enabled: true,
  sort_order: 100,
  extra_auth_params: '',
};

// Single source of truth for both the OAuth-flow shape AND the credential
// format. Kept flat (not nested across two selects) because a single choice
// fully describes how the integration authenticates.
export const AUTH_TYPE_OPTIONS = [
  { value: 'oauth', label: 'OAuth — provider login flow' },
  { value: 'api_key', label: 'API key — paste a static key in a custom header' },
  { value: 'bearer_token', label: 'Bearer token — paste a static token (e.g. PAT)' },
  { value: 'none', label: 'No auth — public / unauthenticated' },
];

export const CATEGORY_OPTIONS = [
  { value: NO_CATEGORY, label: 'Uncategorized' },
  { value: 'crm', label: 'CRM' },
  { value: 'calendar', label: 'Calendar' },
  { value: 'communication', label: 'Communication' },
  { value: 'dev_tools', label: 'Developer Tools' },
  { value: 'storage', label: 'Storage' },
  { value: 'analytics', label: 'Analytics' },
  { value: 'other', label: 'Other' },
];

// Lowercase letters, digits, ``-`` and ``_``; 2–64 chars. Matches the backend
// ``_SLUG_PATTERN`` so the user gets the same error client-side.
export const SLUG_RULE = {
  required: 'Slug is required',
  pattern: {
    value: /^[a-z0-9][a-z0-9_-]{1,63}$/,
    message: "2–64 chars: lowercase letters, digits, '-' or '_'",
  },
};
