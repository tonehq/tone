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

export const getLanguagesByProvider = async (serviceProviderId: number): Promise<string[]> => {
  const { data } = await axiosInstance.get('/voice/get_languages_by_provider', {
    params: { service_provider_id: serviceProviderId },
  });
  return Array.isArray(data) ? data : (data?.languages ?? []);
};

export const getVoicesByLanguage = async (
  serviceProviderId: number,
  language: string,
): Promise<VoiceItem[]> => {
  const { data } = await axiosInstance.get('/voice/get_voices_by_language', {
    params: { service_provider_id: serviceProviderId, language },
  });
  return Array.isArray(data) ? data : (data?.voices ?? []);
};

// ── New path: by model_provider_menu_id ──────────────────────────

export const getLanguagesByModelProvider = async (
  modelProviderMenuId: number,
): Promise<string[]> => {
  const { data } = await axiosInstance.get('/voice/get_languages_by_model_provider', {
    params: { model_provider_menu_id: modelProviderMenuId },
  });
  return Array.isArray(data) ? data : (data?.languages ?? []);
};

export const getVoicesByLanguageAndModelProvider = async (
  modelProviderMenuId: number,
  language: string,
): Promise<VoiceItem[]> => {
  const { data } = await axiosInstance.get('/voice/get_voices_by_language_and_model_provider', {
    params: { model_provider_menu_id: modelProviderMenuId, language },
  });
  return Array.isArray(data) ? data : (data?.voices ?? []);
};
