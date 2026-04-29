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
  validator: string;
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
  auth_type?: string;
  status: string;
  is_system?: boolean;
  base_url?: string;
  supports_streaming?: boolean;
  created_at: number;
  updated_at?: number;
  meta_data_schema: MetaDataSchemaField[] | null;
  models: ServiceProviderModel[];
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
