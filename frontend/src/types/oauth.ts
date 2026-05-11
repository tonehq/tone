export interface OAuthConnection {
  id: number;
  uuid: string;
  provider: string;
  user_email: string | null;
  scopes: string | null;
  token_expiry: number | null;
  is_active: boolean;
  meta_data: Record<string, unknown> | null;
  created_at: number;
  updated_at: number;
  connected?: boolean;
}

export interface OAuthProviderStatus {
  connected: boolean;
  provider: string;
  id?: number;
  uuid?: string;
  user_email?: string | null;
  scopes?: string | null;
  token_expiry?: number | null;
  is_active?: boolean;
  meta_data?: Record<string, unknown> | null;
  created_at?: number;
  updated_at?: number;
}
