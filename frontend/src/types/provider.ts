export interface ServiceProviderModel {
  id: number;
  service_provider_id: number;
  name: string;
  meta_data: Record<string, unknown> | null;
  created_at: number;
  updated_at: number;
}

export interface ServiceProvider {
  id: number;
  uuid: string;
  name: string;
  display_name: string;
  description: string;
  provider_type: 'llm' | 'tts' | 'stt';
  status: string;
  created_at: number;
  models: ServiceProviderModel[];
}
