import axiosInstance from '@/utils/axios';

export interface TtsLanguage {
  name: string;
  codes: string[];
}

export interface TtsProvider {
  id: string;
  slug: string;
  display_name: string;
  description?: string | null;
  language_code: string;
}

export interface TtsVoice {
  id: string;
  name: string;
  gender?: string | null;
  accent?: string | null;
  description?: string | null;
  language_list: string[];
  sample_url?: string | null;
}

export const listTtsLanguages = async (): Promise<TtsLanguage[]> => {
  const res = await axiosInstance.get<TtsLanguage[]>('/services/tts/languages');
  return Array.isArray(res.data) ? res.data : [];
};

export const listTtsProviders = async (language: string): Promise<TtsProvider[]> => {
  const res = await axiosInstance.get<TtsProvider[]>('/services/tts/providers', {
    params: { language },
  });
  return Array.isArray(res.data) ? res.data : [];
};

export const listTtsVoices = async (
  providerId: string,
  language: string,
  modelId?: string | null,
): Promise<TtsVoice[]> => {
  const params: Record<string, string> = { provider_id: providerId, language };
  if (modelId) params.model_id = modelId;
  const res = await axiosInstance.get<TtsVoice[]>('/services/tts/voices', { params });
  return Array.isArray(res.data) ? res.data : [];
};
