/**
 * Types for the customer-facing "API Keys" surface under Settings.
 *
 * Distinct from provider credentials (which live in Model Providers). A row here
 * represents one Bearer token a customer can send to the Tone API. The plaintext
 * key is only ever present on the create response — after that, only `masked` /
 * `key_prefix` are known.
 */

export type ApiKeyStatus = 'active' | 'expired' | 'revoked';

export interface ApiKeyRow {
  id: string;
  name: string;
  key_prefix: string;
  masked: string;
  status: ApiKeyStatus;
  created_by_user_id: string | null;
  expires_at: string | null;
  last_used_at: string | null;
  revoked_at: string | null;
  created_at: string | null;
}

/**
 * The one and only response that carries the raw `key`. The client MUST show it
 * to the user immediately and drop it — after this it is unrecoverable.
 */
export interface CreateApiKeyResponse extends ApiKeyRow {
  key: string;
}

export interface CreateApiKeyPayload {
  name: string;
  /** ISO 8601 UTC. `null` = never expires. */
  expires_at: string | null;
}
