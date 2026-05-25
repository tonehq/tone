export type AuthType = 'oauth' | 'api_key' | 'bearer';

export interface OAuthPublicMetadata {
  user_email?: string | null;
  scopes?: string | null;
  token_expiry?: number | null;
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
