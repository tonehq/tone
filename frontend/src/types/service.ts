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
  api_key?: string;
  config?: Record<string, unknown>;
}

export interface ProviderCatalogItem {
  id: string;
  slug: string;
  display_name: string;
  description: string | null;
  kinds: ServiceKind[];
}

/** Aggregated "card" view — one row per provider the org has ≥1 ApiKey for. */
export interface ProviderUsage {
  provider: ServiceProviderRef;
  kinds: ServiceKind[];
  api_key_count: number;
  active_api_key_count: number;
  default_api_key: {
    id: string;
    label: string | null;
    service_type: ServiceKind;
  } | null;
  service_types: ServiceKind[];
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
  is_active: boolean;
  created_at: number;
  updated_at: number;
}
