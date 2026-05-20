import type {
  Account,
  AccountUpsertPayload,
  ModelProviderWithAccounts,
  ModelUpsertPayload,
  ServiceProvider,
  ServiceProviderModel,
  ServiceProviderUpsertPayload,
} from '@/types/provider';
import axiosInstance from '@/utils/axios';

export type { ServiceProvider, ServiceProviderModel } from '@/types/provider';

// ── Shared pagination types ────────────────────────────────────────

export interface PaginationInfo {
  page: number;
  page_size: number;
  total: number;
  total_pages: number;
}

interface PaginatedResponse<T> {
  data: T[];
  pagination: PaginationInfo;
}

// ── Service Providers ──────────────────────────────────────────────

export interface ListProvidersParams {
  provider_type?: string;
  name?: string;
  status?: string;
  sort?: string;
  page?: number;
  page_size?: number;
}

export interface ListProvidersResult {
  providers: ServiceProvider[];
  pagination: PaginationInfo;
}

export const listServiceProviders = async (
  params: ListProvidersParams = {},
): Promise<ListProvidersResult> => {
  const { data } = await axiosInstance.post<PaginatedResponse<ServiceProvider> | ServiceProvider[]>(
    '/model-providers-menu/list',
    params,
  );
  if (Array.isArray(data)) {
    return {
      providers: data,
      pagination: { page: 1, page_size: data.length, total: data.length, total_pages: 1 },
    };
  }
  return { providers: data?.data ?? [], pagination: data.pagination };
};

/** @deprecated Use listServiceProviders — kept for AgentFormPage loadable atom */
export const getServiceProviders = async (providerType?: string): Promise<ServiceProvider[]> => {
  const result = await listServiceProviders(providerType ? { provider_type: providerType } : {});
  return result.providers;
};

// ── Model Providers with Accounts (for agent form dropdowns) ─────

export const getProvidersWithAccounts = async (
  providerType?: string,
): Promise<ModelProviderWithAccounts[]> => {
  const { data } = await axiosInstance.post('/model-providers-menu/list-with-accounts', {
    provider_type: providerType,
  });
  return Array.isArray(data) ? data : (data?.data ?? []);
};

// ── Accounts (org-scoped provider instances) ─────────────────────

export interface ListAccountsParams {
  service_type?: string;
  name?: string;
  page?: number;
  page_size?: number;
}

export interface ListAccountsResult {
  accounts: Account[];
  pagination: PaginationInfo;
}

export const listAccounts = async (
  params: ListAccountsParams = {},
): Promise<ListAccountsResult> => {
  const { data } = await axiosInstance.post<PaginatedResponse<Account> | Account[]>(
    '/accounts/list',
    params,
  );
  if (Array.isArray(data)) {
    return {
      accounts: data,
      pagination: { page: 1, page_size: data.length, total: data.length, total_pages: 1 },
    };
  }
  return { accounts: data?.data ?? [], pagination: data.pagination };
};

/** Flat array of all accounts — used by AgentFormPage loadable atom */
export const getAccounts = async (serviceType?: string): Promise<Account[]> => {
  const result = await listAccounts(serviceType ? { service_type: serviceType } : {});
  return result.accounts;
};

export const upsertAccount = async (payload: AccountUpsertPayload): Promise<Account> => {
  const { data } = await axiosInstance.post<Account>('/accounts/upsert', payload);
  return data;
};

export const deleteAccount = async (accountUuid: string): Promise<void> => {
  await axiosInstance.delete('/accounts/delete', { params: { uuid: accountUuid } });
};

/** @deprecated Use listAccounts */
export const listServices = listAccounts as unknown as (
  params?: ListAccountsParams,
) => Promise<{ services: Account[]; pagination: PaginationInfo }>;
/** @deprecated Use getAccounts */
export const getServices = getAccounts;
/** @deprecated Use upsertAccount */
export const upsertService = upsertAccount;
/** @deprecated Use deleteAccount */
export const deleteService = deleteAccount;

export const getServiceProvider = async (providerId: number): Promise<ServiceProvider> => {
  const { data } = await axiosInstance.post<ServiceProvider>('/model-providers-menu/get', {
    provider_id: providerId,
  });
  return data;
};

export const upsertServiceProvider = async (
  payload: ServiceProviderUpsertPayload,
): Promise<ServiceProvider> => {
  const { data } = await axiosInstance.post<ServiceProvider>('/service-providers/upsert', payload);
  return data;
};

export const deleteServiceProvider = async (providerId: number): Promise<void> => {
  await axiosInstance.delete('/service-providers/delete', {
    params: { provider_id: providerId },
  });
};

// ── API Keys (provider credentials) ────────────────────────────────

export interface ApiKeyDetail {
  id: number;
  uuid: string;
  name: string;
  description: string | null;
  api_key: string;
  api_key_hint: string;
  service_provider_id: number;
  service_provider_name?: string;
  provider_type?: string;
  status: string;
  is_valid: boolean;
  last_validated_at: number | null;
  validation_error: string | null;
  last_used_at: number | null;
  usage_count: number;
  additional_credentials: Record<string, unknown> | null;
  rate_limit_config: Record<string, unknown> | null;
  created_at: number;
  updated_at: number;
  expires_at: number | null;
}

export const getApiKeyPlaintext = async (apiKeyId: number): Promise<ApiKeyDetail> => {
  const { data } = await axiosInstance.get<ApiKeyDetail>('/api-keys/get', {
    params: { api_key_id: apiKeyId },
  });
  return data;
};

export interface ApiKeyListRow {
  id: number;
  uuid: string;
  name: string;
  description: string | null;
  api_key_hint: string;
  service_provider_id: number;
  status: string;
  is_valid: boolean;
  last_validated_at: number | null;
  validation_error: string | null;
  last_used_at: number | null;
  usage_count: number;
  expires_at: number | null;
  created_at: number;
  updated_at: number;
}

export interface ListApiKeysParams {
  account_id: number;
  status?: string;
  page?: number;
  page_size?: number;
}

export interface ListApiKeysResult {
  keys: ApiKeyListRow[];
  pagination: PaginationInfo;
}

export const listApiKeysByAccount = async (
  params: ListApiKeysParams,
): Promise<ListApiKeysResult> => {
  const { data } = await axiosInstance.post<{ data: ApiKeyListRow[]; pagination: PaginationInfo }>(
    '/api-keys/list_by_account',
    params,
  );
  return { keys: data.data ?? [], pagination: data.pagination };
};

/** @deprecated Use listApiKeysByAccount */
export const listApiKeysByProvider = listApiKeysByAccount as unknown as (params: {
  service_provider_id: number;
  status?: string;
  page?: number;
  page_size?: number;
}) => Promise<ListApiKeysResult>;

export interface ApiKeyUpsertInput {
  account_id: number;
  name: string;
  api_key: string;
  description?: string;
  status?: string;
  uuid?: string;
}

export const upsertApiKey = async (input: ApiKeyUpsertInput): Promise<ApiKeyListRow> => {
  // Backend uses multipart/form-data
  const form = new FormData();
  form.append('account_id', String(input.account_id));
  form.append('name', input.name);
  form.append('api_key', input.api_key);
  if (input.description) form.append('description', input.description);
  if (input.status) form.append('key_status', input.status);
  if (input.uuid) form.append('uuid', input.uuid);
  const { data } = await axiosInstance.post<ApiKeyListRow>('/api-keys/upsert', form);
  return data;
};

export const deleteApiKey = async (apiKeyId: number): Promise<void> => {
  await axiosInstance.delete('/api-keys/delete', { params: { api_key_id: apiKeyId } });
};

// ── Models ─────────────────────────────────────────────────────────

export interface ListModelsParams {
  model_provider_menu_id: number;
  name?: string;
  status?: string;
  service_type?: string;
  sort?: string;
  page?: number;
  page_size?: number;
}

export interface ListModelsResult {
  models: ServiceProviderModel[];
  pagination: PaginationInfo;
}

export const listModelsByProvider = async (params: ListModelsParams): Promise<ListModelsResult> => {
  const { data } = await axiosInstance.post<
    PaginatedResponse<ServiceProviderModel> | ServiceProviderModel[]
  >('/model-menu/get_models_by_provider', params);
  if (Array.isArray(data)) {
    return {
      models: data,
      pagination: { page: 1, page_size: data.length, total: data.length, total_pages: 1 },
    };
  }
  return { models: data?.data ?? [], pagination: data.pagination };
};

/** @deprecated Use listModelsByProvider — kept for backward compat */
export const getModelsByProvider = async (
  serviceProviderId: number,
): Promise<ServiceProviderModel[]> => {
  const result = await listModelsByProvider({
    model_provider_menu_id: serviceProviderId,
    page_size: 100,
  });
  return result.models;
};

export const upsertModel = async (payload: ModelUpsertPayload): Promise<ServiceProviderModel> => {
  const { data } = await axiosInstance.post<ServiceProviderModel>(
    '/model-menu/upsert_model',
    payload,
  );
  return data;
};

export const deleteModel = async (modelId: number): Promise<void> => {
  await axiosInstance.delete('/model-menu/delete_model', {
    params: { model_id: modelId },
  });
};
