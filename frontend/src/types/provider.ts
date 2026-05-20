export interface ApiKey {
  id?: number;
  uuid?: string;
  name?: string;
  api_key?: string;
  api_key_hint?: string;
  description?: string;
  service_provider_id?: number;
  additional_credentials?: Record<string, unknown> | null;
  rate_limit_config?: Record<string, unknown> | null;
  expires_at?: number | null;
  status?: string;
  is_valid?: boolean;
  created_at?: number;
  updated_at?: number;
}

export interface ServiceProviderModel {
  id: number;
  service_provider_id: number;
  name: string;
  service_type?: string;
  status?: string;
  meta_data: Record<string, unknown> | null;
  api_key_id?: number | null;
  created_at: number;
  updated_at: number;
}

export interface MetaDataSchemaField {
  name: string;
  type: string;
  format: string;
  required: number;
  data_type:
    | 'string'
    | 'float'
    | 'int'
    | 'integer'
    | 'boolean'
    | 'date'
    | 'date range'
    | 'datetime'
    | 'list'
    | 'rangepicker';
  validator: Record<string, unknown> | string;
  description: string;
  values?: { value: string; label: string }[];
}

export type ValidatorFn = (value: unknown, field: MetaDataSchemaField) => string | true;

export type ProviderType = 'llm' | 'tts' | 'stt';

export interface ServiceProvider {
  id: number;
  uuid: string;
  name: string;
  display_name: string;
  description: string;
  provider_type: ProviderType;
  service_provider_id?: number;
  logo_url?: string | null;
  website_url?: string | null;
  documentation_url?: string | null;
  auth_type?: string;
  status: string;
  is_system?: boolean;
  base_url?: string | null;
  supports_streaming?: boolean;
  config_schema?: Record<string, unknown> | null;
  created_at: number;
  updated_at?: number;
  meta_data_schema: MetaDataSchemaField[] | null;
  models: ServiceProviderModel[];
  api_key?: ApiKey | null;
}

export interface ApiKeyUpsertPayload {
  id?: number;
  name?: string;
  api_key?: string;
  description?: string;
  additional_credentials?: Record<string, unknown> | null;
  rate_limit_config?: Record<string, unknown> | null;
  expires_at?: number | null;
  status?: string;
}

export interface ServiceProviderUpsertPayload {
  id?: number;
  name: string;
  display_name: string;
  provider_type: ProviderType;
  auth_type: string;
  description?: string;
  base_url?: string;
  supports_streaming?: boolean;
  status?: string;
  api_key?: ApiKeyUpsertPayload;
}

export interface ModelUpsertPayload {
  id?: number;
  model_provider_menu_id: number;
  name: string;
  service_type?: string;
  status?: string;
  meta_data?: Record<string, unknown>;
  api_key_id?: number | null;
}

// ── Accounts (org-scoped provider instances, formerly "services") ──

export interface Account {
  id: number;
  uuid: string;
  name: string;
  display_name?: string;
  description?: string;
  service_type: ProviderType;
  service_provider_id?: number | null;
  model_provider_menu_id?: number | null;
  service_provider_name?: string;
  provider_type?: string;
  api_key_id?: number | null;
  api_key_hint?: string | null;
  config: Record<string, unknown>;
  status: string;
  is_default?: boolean;
  is_public?: boolean;
  tags?: string[] | null;
  usage_count?: number;
  last_used_at?: number | null;
  created_at: number;
  updated_at?: number;
  models: ServiceProviderModel[];
  meta_data_schema: MetaDataSchemaField[] | null;
}

export interface AccountUpsertPayload {
  uuid?: string;
  service_provider_id?: number | null;
  model_provider_menu_id?: number | null;
  name: string;
  service_type: string;
  config: Record<string, unknown>;
  description?: string;
  is_default?: boolean;
  is_public?: boolean;
  tags?: string[];
  status?: string;
  api_key_id?: number | null;
  api_key_value?: string;
  api_key_name?: string;
  additional_credentials?: Record<string, unknown> | null;
}

// ── Model Providers with Accounts (for agent form dropdowns) ──

export interface ModelMenuItem {
  id: number;
  model_provider_menu_id: number;
  name: string;
  meta_data: Record<string, unknown> | null;
  service_type?: string;
}

export interface ModelProviderWithAccounts {
  id: number;
  uuid: string;
  name: string;
  display_name: string;
  description?: string;
  provider_type: ProviderType;
  meta_data_schema: MetaDataSchemaField[] | null;
  models: ModelMenuItem[];
}

/** @deprecated Use Account — kept for backward compat */
export type Service = Account;
/** @deprecated Use AccountUpsertPayload — kept for backward compat */
export type ServiceUpsertPayload = AccountUpsertPayload;
