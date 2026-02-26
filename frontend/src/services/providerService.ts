import axiosInstance from '@/utils/axios';

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

export interface ServiceProviderModel {
  id: number;
  service_provider_id: number;
  name: string;
  meta_data: Record<string, unknown> | null;
  created_at: number;
  updated_at: number;
}

export const getServiceProviders = async (): Promise<ServiceProvider[]> => {
  const { data } = await axiosInstance.get<ServiceProvider[]>('/service-providers/list');
  return data ?? [];
};
