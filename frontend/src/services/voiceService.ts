import axiosInstance from '@/utils/axios';

export interface VoiceItem {
  id: number;
  uuid: string;
  voice_id: string;
  name: string;
  language: string;
  gender: string;
  accent: string;
  description: string;
  sample_url: string;
  created_at: number;
  updated_at: number;
}

export interface VoicesByProviderResponse {
  id: number;
  uuid: string;
  name: string;
  display_name: string;
  description: string;
  provider_type: string;
  logo_url: string;
  voices: VoiceItem[];
  languages: string[];
  genders: string[];
}

export const getVoicesByProvider = async (
  serviceProviderId: number,
): Promise<VoicesByProviderResponse> => {
  const { data } = await axiosInstance.get<VoicesByProviderResponse>(
    '/voice/get_voice_by_provider',
    { params: { service_provider_id: serviceProviderId } },
  );
  return data;
};
