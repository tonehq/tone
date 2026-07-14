export type ServiceKind = 'llm' | 'stt' | 'tts';

export interface ServiceProviderRef {
  id: string;
  slug: string;
  display_name: string;
  description?: string | null;
}

/** A single per-org ApiKey row (used on the detail page's API keys panel + drawer). */
export interface Service {
  id: string;
  label: string | null;
  service_type: ServiceKind;
  description: string | null;
  is_default: boolean;
  is_active: boolean;
  config: Record<string, unknown>;
  provider: ServiceProviderRef;
  kinds: ServiceKind[];
  created_at: number;
  updated_at: number;
}

export interface ServiceUpsertPayload {
  provider_id: string;
  service_type: ServiceKind;
  label?: string;
  description?: string;
  is_default?: boolean;
  is_active?: boolean;
  /** Plaintext API key. Mutually exclusive with `source_key_id` on create. */
  api_key?: string;
  /**
   * ID of an existing ApiKey for the same provider whose encrypted credential
   * should be copied into the new row. Mutually exclusive with `api_key`.
   */
  source_key_id?: string;
  config?: Record<string, unknown>;
}

export interface ProviderCatalogItem {
  id: string;
  slug: string;
  display_name: string;
  description: string | null;
  kinds: ServiceKind[];
  /** Provider-specific configurable fields, keyed by kind (llm/stt/tts). */
  meta_data_schema?: Record<string, import('@/types/provider').MetaDataSchemaField[]> | null;
}

/**
 * Aggregated "card" view — one row per (provider, service_type) the org has
 * ≥1 ApiKey for. A Deepgram STT key and a Deepgram TTS key therefore surface
 * as two separate cards. `id` is the composite `${providerId}:${serviceType}`
 * so React lists have a stable key.
 */
export interface ProviderUsage {
  id: string;
  provider: ServiceProviderRef;
  service_type: ServiceKind;
  api_key_count: number;
  active_api_key_count: number;
  default_api_key: {
    id: string;
    label: string | null;
    service_type: ServiceKind;
  } | null;
  model_count: number;
  last_used_at: number | null;
}

/** Read-only model from the global catalog (detail page Models panel). */
export interface ProviderModel {
  id: string;
  name: string;
  display_name: string | null;
  kind: ServiceKind;
  description: string | null;
  base_url: string | null;
  is_active: boolean;
  meta_data: Record<string, unknown> | null;
  meta_data_schema: import('@/types/provider').MetaDataSchemaField[] | null;
  created_at: number;
  updated_at: number;
}
