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
  slug: string;
  display_name: string;
  description: string;
  category: OAuthProviderCategory | string;
  auth_type: AuthType;
  scopes: string[];
  configured: boolean;
}

export interface OAuthConnection {
  id: string;
  provider_slug: string;
  label: string | null;
  auth_type: AuthType;
  public_metadata: OAuthPublicMetadata;
  created_by_user_id: string | null;
  created_at: string;
  updated_at: string;
}

export interface OAuthProviderStatus extends Partial<OAuthConnection> {
  connected: boolean;
  provider: string;
}
