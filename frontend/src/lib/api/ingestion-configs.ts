import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import {
  createIngestionConfig,
  deleteIngestionConfig,
  listIngestionConfigs,
  updateIngestionConfig,
} from '@/services/ingestionConfigService';
import type {
  CreateIngestionConfigPayload,
  IngestionConfig,
  ListIngestionConfigsParams,
  PaginatedIngestionConfigs,
  UpdateIngestionConfigPayload,
} from '@/types/ingestionConfig';

export const INGESTION_CONFIGS_QUERY_KEY = 'ingestion-configs';

export function useIngestionConfigs(params: ListIngestionConfigsParams = {}) {
  return useQuery<PaginatedIngestionConfigs>({
    queryKey: [INGESTION_CONFIGS_QUERY_KEY, params],
    queryFn: () => listIngestionConfigs(params),
    placeholderData: (prev) => prev,
  });
}

export function useCreateIngestionConfig() {
  const qc = useQueryClient();
  return useMutation<IngestionConfig, unknown, CreateIngestionConfigPayload>({
    mutationFn: (payload) => createIngestionConfig(payload),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: [INGESTION_CONFIGS_QUERY_KEY] });
    },
  });
}

export function useUpdateIngestionConfig() {
  const qc = useQueryClient();
  return useMutation<
    IngestionConfig,
    unknown,
    { id: string; payload: UpdateIngestionConfigPayload }
  >({
    mutationFn: ({ id, payload }) => updateIngestionConfig(id, payload),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: [INGESTION_CONFIGS_QUERY_KEY] });
    },
  });
}

export function useDeleteIngestionConfig() {
  const qc = useQueryClient();
  return useMutation<{ id: string; deleted: boolean }, unknown, string>({
    mutationFn: (id) => deleteIngestionConfig(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: [INGESTION_CONFIGS_QUERY_KEY] });
    },
  });
}
