import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import {
  createAppIntegration,
  deleteAppIntegration,
  getAppIntegration,
  listAppIntegrations,
  updateAppIntegration,
} from '@/services/appIntegrationService';
import type {
  AppIntegration,
  AppIntegrationCreatePayload,
  AppIntegrationUpdatePayload,
} from '@/types/appIntegration';
import type { ListRequest } from '@/types/list';

export const appIntegrationKeys = {
  all: () => ['app-integrations'] as const,
  list: (request?: ListRequest) => ['app-integrations', 'list', request ?? {}] as const,
  detail: (id: string) => ['app-integrations', 'detail', id] as const,
};

/**
 * Full app-integration catalog. Returns just the rows (the list view never
 * renders totals), so callers read `data ?? []` exactly like the previous
 * useState-backed `integrations`.
 */
export function useAppIntegrations(request: ListRequest = {}) {
  return useQuery<AppIntegration[]>({
    queryKey: appIntegrationKeys.list(request),
    queryFn: async () => {
      const res = await listAppIntegrations(request);
      return res.rows;
    },
  });
}

export function useAppIntegration(id: string | null | undefined) {
  return useQuery<AppIntegration>({
    queryKey: appIntegrationKeys.detail(id ?? ''),
    queryFn: () => getAppIntegration(id as string),
    enabled: !!id,
  });
}

export function useCreateAppIntegration() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload: AppIntegrationCreatePayload) => createAppIntegration(payload),
    onSuccess: () => qc.invalidateQueries({ queryKey: appIntegrationKeys.all() }),
  });
}

export function useUpdateAppIntegration() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, payload }: { id: string; payload: AppIntegrationUpdatePayload }) =>
      updateAppIntegration(id, payload),
    onSuccess: (_data, { id }) => {
      qc.invalidateQueries({ queryKey: appIntegrationKeys.all() });
      qc.invalidateQueries({ queryKey: appIntegrationKeys.detail(id) });
    },
  });
}

export function useDeleteAppIntegration() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => deleteAppIntegration(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: appIntegrationKeys.all() }),
  });
}
