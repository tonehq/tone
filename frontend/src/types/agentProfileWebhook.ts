/**
 * Shape of the per-agent webhook data source that fills webhook-sourced
 * profile variables at call start. Backend model lives at
 * `core/models/agent_profile_webhook.py`; keep in sync with `webhook_response()`.
 */

export type WebhookHttpMethod = 'GET' | 'POST';
export type RequestIdentifierLocation = 'query' | 'body';

/** One identifier mapping: which caller field to send, under what param name,
 * and where. v1 supports only `phone`. */
export interface RequestIdentifier {
  identifier: 'phone';
  param: string;
  in: RequestIdentifierLocation;
}

export interface WebhookDirections {
  inbound: boolean;
  outbound: boolean;
}

export interface AgentProfileWebhook {
  id: string;
  organization_id: string;
  agent_id: string;
  endpoint_url: string;
  http_method: WebhookHttpMethod;
  /** Decrypted header key→value map (owner-editing view). */
  headers: Record<string, string>;
  has_headers: boolean;
  request_identifiers: RequestIdentifier[];
  directions: WebhookDirections;
  timeout_seconds: number;
  is_enabled: boolean;
  created_at: string | null;
  updated_at: string | null;
}

/** Body for PUT /agents/{id}/profile-webhook (upsert). Headers are sent as a
 * plaintext map and full-replaced server-side (encrypted at rest). */
export interface ProfileWebhookUpsertInput {
  endpoint_url: string;
  http_method: WebhookHttpMethod;
  headers: Record<string, string>;
  request_identifiers: RequestIdentifier[];
  directions: WebhookDirections;
  timeout_seconds: number;
  is_enabled: boolean;
}

export interface GetProfileWebhookResponse {
  webhook: AgentProfileWebhook | null;
}

export interface WebhookPathResult {
  path: string;
  resolved: boolean;
  value: unknown;
}

export interface WebhookTestRequest {
  sample_phone: string;
}

export interface WebhookTestResponse {
  ok: boolean;
  status_code: number | null;
  raw_response: unknown;
  path_results: WebhookPathResult[];
  error?: string;
}
