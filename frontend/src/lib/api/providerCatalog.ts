import { useQuery } from '@tanstack/react-query';

import { listProviderCatalog, listProviderModels } from '@/services/servicesService';
import type { ProviderModel } from '@/types/service';

/**
 * Read-only LLM provider catalog queries used by the agent AI step. These are
 * static-per-provider lookups (providers, models) with no post-mutation
 * staleness, so they live in TanStack Query instead of ad-hoc `useState` +
 * `useEffect` fetches — the LLM analog of the voice catalog hooks. `retry:
 * false` mirrors the previous single-shot fetch semantics (one attempt, then
 * the shared error toast).
 */
export const providerCatalogKeys = {
  catalog: (kind: string) => ['provider-catalog', kind] as const,
  models: (providerId: string, serviceType: string) =>
    ['provider-catalog', 'models', providerId, serviceType] as const,
};

const selectActiveModels = (res: { rows: ProviderModel[] }): ProviderModel[] =>
  res.rows.filter((m) => m.is_active);

export function useLlmProviderCatalog() {
  return useQuery({
    queryKey: providerCatalogKeys.catalog('llm'),
    queryFn: () => listProviderCatalog('llm'),
    retry: false,
  });
}

export function useLlmModels(providerId: string | null | undefined) {
  return useQuery({
    queryKey: providerCatalogKeys.models(providerId ?? '', 'llm'),
    queryFn: () =>
      listProviderModels(providerId as string, {
        service_type: 'llm',
        page: 1,
        page_size: 100,
      }),
    enabled: !!providerId,
    select: selectActiveModels,
    retry: false,
  });
}
