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
  service_provider_id: number;
  name: string;
  service_type?: string;
  status?: string;
  meta_data?: Record<string, unknown>;
  api_key_id?: number | null;
}
