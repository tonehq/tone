import { useMutation, useQueryClient } from '@tanstack/react-query';

import { apiKeyKeys } from '@/lib/api/queryKeys';
import { usePaginatedList } from '@/lib/api/usePaginatedList';
import { apiKeyService } from '@/services/apiKeyService';
import type { PaginatedListParams } from '@/types/contactList';
import type { CreateApiKeyPayload } from '@/types/settings/apiKey';

/** Paginated list of generated API keys for the current org. */
export function useApiKeysList(params: PaginatedListParams = {}) {
  return usePaginatedList(apiKeyKeys.list(params), () => apiKeyService.list(params), params);
}

/**
 * Mint a new API key. The success payload carries the raw `key` string — the
 * caller MUST show it once and then drop it. This hook does not stash the key.
 */
export function useCreateApiKey() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload: CreateApiKeyPayload) => apiKeyService.create(payload),
    onSuccess: () => qc.invalidateQueries({ queryKey: apiKeyKeys.lists() }),
  });
}

export function useRevokeApiKey() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => apiKeyService.revoke(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: apiKeyKeys.lists() }),
  });
}

export function useDeleteApiKey() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => apiKeyService.remove(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: apiKeyKeys.lists() }),
  });
}
