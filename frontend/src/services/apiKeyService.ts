import axios from '@/utils/axios';
import type { PaginatedListParams, PaginatedResponse } from '@/types/contactList';
import type { ApiKeyRow, CreateApiKeyPayload, CreateApiKeyResponse } from '@/types/settings/apiKey';

/**
 * Thin typed wrapper over the `/generated-api-keys/*` endpoints. All calls go through
 * `@/utils/axios` (never raw axios) so httpOnly auth cookies and the tenant_id hint
 * are attached automatically.
 */
export const apiKeyService = {
  list: async (params: PaginatedListParams = {}): Promise<PaginatedResponse<ApiKeyRow>> => {
    const body: Record<string, unknown> = {};
    for (const [key, value] of Object.entries(params)) {
      if (value !== undefined && value !== null && value !== '') body[key] = value;
    }
    const { data } = await axios.post<PaginatedResponse<ApiKeyRow>>(
      '/generated-api-keys/list',
      body,
    );
    return data;
  },

  create: async (payload: CreateApiKeyPayload): Promise<CreateApiKeyResponse> => {
    const { data } = await axios.post<CreateApiKeyResponse>(
      '/generated-api-keys/create_api_key',
      payload,
    );
    return data;
  },

  revoke: async (id: string): Promise<ApiKeyRow> => {
    const { data } = await axios.post<ApiKeyRow>('/generated-api-keys/revoke_api_key', undefined, {
      params: { api_key_id: id },
    });
    return data;
  },

  remove: async (id: string): Promise<{ message: string }> => {
    const { data } = await axios.delete<{ message: string }>('/generated-api-keys/delete_api_key', {
      params: { api_key_id: id },
    });
    return data;
  },
};
