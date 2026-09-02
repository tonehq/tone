import { useQuery } from '@tanstack/react-query';

import { listProviderCatalog, listProviderModels } from '@/services/servicesService';
import { listTtsLanguages, listTtsProviders, listTtsVoices } from '@/services/ttsService';
import type { ProviderCatalogItem, ProviderModel } from '@/types/service';

/**
 * Read-only voice/STT catalog queries used by the agent Voice step. All of
 * these are static-per-provider lookups (languages, providers, voices, models)
 * with no post-mutation staleness, so they live in TanStack Query instead of
 * ad-hoc `useState` + `useEffect` fetches. `retry: false` mirrors the previous
 * single-shot fetch semantics (one attempt, then the shared error toast).
 */
export const voiceCatalogKeys = {
  sttProviders: () => ['voice-catalog', 'stt-providers'] as const,
  ttsLanguages: () => ['voice-catalog', 'tts-languages'] as const,
  ttsProviders: (language: string) => ['voice-catalog', 'tts-providers', language] as const,
  ttsVoices: (providerId: string, language: string, modelId: string | null | undefined) =>
    ['voice-catalog', 'tts-voices', providerId, language, modelId ?? null] as const,
  ttsModels: (providerId: string) => ['voice-catalog', 'tts-models', providerId] as const,
  sttModels: (providerId: string) => ['voice-catalog', 'stt-models', providerId] as const,
};

// Module-level selects so the reference stays stable across renders (TanStack
// re-runs `select` only when it changes identity or the data changes).
const selectSttProviders = (items: ProviderCatalogItem[]): ProviderCatalogItem[] =>
  items.filter((p) => p.kinds.includes('stt'));

const selectActiveModels = (res: { rows: ProviderModel[] }): ProviderModel[] =>
  res.rows.filter((m) => m.is_active);

export function useSttProviderCatalog() {
  return useQuery({
    queryKey: voiceCatalogKeys.sttProviders(),
    queryFn: () => listProviderCatalog('stt'),
    select: selectSttProviders,
    retry: false,
  });
}

export function useTtsLanguages() {
  return useQuery({
    queryKey: voiceCatalogKeys.ttsLanguages(),
    queryFn: listTtsLanguages,
    retry: false,
  });
}

export function useTtsProviders(language: string) {
  return useQuery({
    queryKey: voiceCatalogKeys.ttsProviders(language),
    queryFn: () => listTtsProviders(language),
    enabled: !!language,
    retry: false,
  });
}

export function useTtsVoices(
  providerId: string,
  language: string,
  modelId: string | null | undefined,
) {
  return useQuery({
    queryKey: voiceCatalogKeys.ttsVoices(providerId, language, modelId),
    queryFn: () => listTtsVoices(providerId, language, modelId),
    enabled: !!providerId && !!language,
    retry: false,
  });
}

export function useTtsModels(providerId: string) {
  return useQuery({
    queryKey: voiceCatalogKeys.ttsModels(providerId),
    queryFn: () => listProviderModels(providerId, { service_type: 'tts', page: 1, page_size: 100 }),
    enabled: !!providerId,
    select: selectActiveModels,
    retry: false,
  });
}

export function useSttModels(providerId: string) {
  return useQuery({
    queryKey: voiceCatalogKeys.sttModels(providerId),
    queryFn: () => listProviderModels(providerId, { service_type: 'stt', page: 1, page_size: 100 }),
    enabled: !!providerId,
    select: selectActiveModels,
    retry: false,
  });
}
