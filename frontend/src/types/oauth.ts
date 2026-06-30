export type AuthType = 'oauth' | 'api_key' | 'bearer';

export type OAuthProviderCategory = 'google' | 'productivity' | 'dev_crm';

export interface OAuthPublicMetadata {
  user_email?: string | null;
  // Backend stores scopes as a list; legacy rows may still be a space/comma string.
  scopes?: string[] | string | null;
  token_expiry?: number | null;
  // Set to 'pending' on an in-flight generic MCP OAuth handshake, 'active' once completed.
  status?: 'pending' | 'active' | null;
  // Remote MCP server URL, stored on generic MCP (`mcp:<host>`) connections — used to re-run
  // discovery when reconnecting (the catalog authorize flow doesn't know mcp:/custom: slugs).
  server_url?: string | null;
}

/** A provider entry from the secret-free `/oauth/catalog` endpoint. */
export interface OAuthCatalogProvider {
  /** ``app_integrations.id`` — used by the catalog grid to navigate to the
   * edit page for inline edit/delete actions. */
  id: string;
  /** Default (seeded) rows are protected from deletion server-side; the UI
   * hides the Delete option for them. */
  is_default: boolean;
  slug: string;
  display_name: string;
  description: string;
  category: OAuthProviderCategory | string;
  auth_type: AuthType;
  scopes: string[];
  configured: boolean;
  /** Admin-supplied brand mark URL. When absent the frontend falls back to
   *  the static ``PROVIDER_LOGOS`` registry (favicon / bundled asset). */
  icon_url?: string | null;
}

export interface OAuthConnection {
  id: string;
  provider_slug: string;
  label: string | null;
  auth_type: AuthType;
  public_metadata: OAuthPublicMetadata;
  created_by_user_id: string | null;
  /** Catalog entry this connection belongs to. Drives the MCP / Tool form's
   *  connection-picker filter when an integration is selected. */
  app_integration_id: string | null;
  created_at: string;
  updated_at: string;
}

export interface OAuthProviderStatus extends Partial<OAuthConnection> {
  connected: boolean;
  provider: string;
}
