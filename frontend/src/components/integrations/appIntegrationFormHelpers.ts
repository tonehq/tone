/** Pure serialization helpers for the app-integration form (row ⇄ form ⇄ payload). */

import type { AppIntegration, AppIntegrationCreatePayload } from '@/types/appIntegration';

import { NO_CATEGORY, type FormState } from './appIntegrationFormConstants';

/**
 * Convert the persisted row into the flat string-based form shape. Done in
 * one place so the form fields don't have to special-case nullable columns.
 */
export function formStateFromRow(row: AppIntegration): FormState {
  return {
    slug: row.slug ?? '',
    display_name: row.display_name ?? '',
    description: row.description ?? '',
    category: row.category ?? NO_CATEGORY,
    icon_url: row.icon_url ?? '',
    auth_type: row.auth_type ?? 'oauth',
    auth_url: row.auth_url ?? '',
    token_url: row.token_url ?? '',
    userinfo_url: row.userinfo_url ?? '',
    scopes: (row.scopes ?? []).join(', '),
    // Secrets are never returned by the API — leave the inputs empty so the
    // admin re-types only what they want to change.
    client_id: '',
    client_secret: '',
    pkce_required: row.pkce_required,
    is_enabled: row.is_enabled,
    sort_order: row.sort_order ?? 100,
    extra_auth_params: row.extra_auth_params ? JSON.stringify(row.extra_auth_params, null, 2) : '',
  };
}

/**
 * Trim, parse, and shape the form values into the API payload.
 *
 * Empty strings become ``null`` for nullable fields so the server can tell
 * "cleared" apart from "untouched". ``scopes`` is split on commas or
 * newlines; ``extra_auth_params`` is parsed as JSON (throws a toast-friendly
 * error if malformed).
 */
export function serializePayload(values: FormState): AppIntegrationCreatePayload {
  const scopes = values.scopes
    .split(/[,\n]/)
    .map((s) => s.trim())
    .filter(Boolean);

  let extraAuthParams: Record<string, unknown> | null = null;
  const rawExtras = values.extra_auth_params.trim();
  if (rawExtras) {
    try {
      const parsed = JSON.parse(rawExtras);
      if (parsed && typeof parsed === 'object' && !Array.isArray(parsed)) {
        extraAuthParams = parsed as Record<string, unknown>;
      } else {
        throw new Error('Extra auth params must be a JSON object');
      }
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'Invalid JSON in extra auth params';
      throw Object.assign(new Error(msg), { response: { data: { detail: msg } } });
    }
  }

  return {
    slug: values.slug.trim().toLowerCase(),
    display_name: values.display_name.trim(),
    auth_type: values.auth_type,
    description: nullable(values.description),
    category: values.category === NO_CATEGORY ? null : nullable(values.category),
    icon_url: nullable(values.icon_url),
    auth_url: nullable(values.auth_url),
    token_url: nullable(values.token_url),
    userinfo_url: nullable(values.userinfo_url),
    scopes: scopes.length ? scopes : null,
    // Only POST credential fields when the admin actually typed something —
    // blank means "keep what's stored".
    client_id: nullable(values.client_id),
    client_secret: nullable(values.client_secret),
    pkce_required: values.pkce_required,
    is_enabled: values.is_enabled,
    sort_order: Number(values.sort_order) || 100,
    extra_auth_params: extraAuthParams,
  };
}

export function nullable(value: string): string | null {
  const trimmed = value.trim();
  return trimmed ? trimmed : null;
}
