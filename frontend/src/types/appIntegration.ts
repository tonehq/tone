/**
 * Shape returned by /api/v1/app-integration/* endpoints.
 *
 * Mirrors :class:`core.services.app_integration_service.AppIntegrationService.app_integration_response`
 * — keep field names in sync with the backend formatter.
 */

/** Single source of truth for both the OAuth flow shape AND the credential
 * format used by an integration. We intentionally don't have a separate
 * "credential type" field — the four values below cover every real case. */
export type AppIntegrationAuthType = 'oauth' | 'api_key' | 'bearer_token' | 'none';

export interface AppIntegration {
  id: string;
  slug: string;
  display_name: string;
  description: string | null;
  category: string | null;
  icon_url: string | null;
  auth_type: AppIntegrationAuthType;
  auth_url: string | null;
  token_url: string | null;
  userinfo_url: string | null;
  scopes: string[] | null;
  extra_auth_params: Record<string, unknown> | null;
  /** True if encrypted credentials are stored. Secrets themselves are never
   * returned — admins re-enter them to overwrite. */
  has_credentials: boolean;
  pkce_required: boolean;
  is_enabled: boolean;
  is_default: boolean;
  /** Derived server-side from the env vars referenced by the row. */
  is_configured: boolean;
  sort_order: number;
  created_at: string;
  updated_at: string;
}

/** Body for ``POST /create_app_integration``. */
export interface AppIntegrationCreatePayload {
  slug: string;
  display_name: string;
  auth_type: AppIntegrationAuthType;
  description?: string | null;
  category?: string | null;
  icon_url?: string | null;
  auth_url?: string | null;
  token_url?: string | null;
  userinfo_url?: string | null;
  scopes?: string[] | null;
  extra_auth_params?: Record<string, unknown> | null;
  /** Plain credential values — written to the encrypted blob on save.
   * Omit to leave the stored value unchanged. */
  client_id?: string | null;
  client_secret?: string | null;
  pkce_required?: boolean;
  is_enabled?: boolean;
  sort_order?: number;
}

/** Body for ``PUT /update_app_integration`` — all fields optional (PATCH semantics). */
export type AppIntegrationUpdatePayload = Partial<AppIntegrationCreatePayload>;
