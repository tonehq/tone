export interface ServiceProviderModel {
  id: number;
  service_provider_id: number;
  name: string;
  meta_data: Record<string, unknown> | null;
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

export interface ServiceProvider {
  id: number;
  uuid: string;
  name: string;
  display_name: string;
  description: string;
  provider_type: 'llm' | 'tts' | 'stt';
  status: string;
  created_at: number;
  meta_data_schema: MetaDataSchemaField[] | null;
  models: ServiceProviderModel[];
}
