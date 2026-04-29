import type {
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
    '/service-providers/list',
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
  const result = await listServiceProviders(
    providerType ? { provider_type: providerType, page_size: 100 } : { page_size: 100 },
  );
  return result.providers;
};

export const getServiceProvider = async (providerId: number): Promise<ServiceProvider> => {
  const { data } = await axiosInstance.post<ServiceProvider>('/service-providers/get', {
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

// ── Models ─────────────────────────────────────────────────────────

export interface ListModelsParams {
  service_provider_id: number;
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
  >('/model/get_models_by_provider', params);
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
    service_provider_id: serviceProviderId,
    page_size: 100,
  });
  return result.models;
};

export const upsertModel = async (payload: ModelUpsertPayload): Promise<ServiceProviderModel> => {
  const { data } = await axiosInstance.post<ServiceProviderModel>('/model/upsert_model', payload);
  return data;
};

export const deleteModel = async (modelId: number): Promise<void> => {
  await axiosInstance.delete('/model/delete_model', {
    params: { model_id: modelId },
  });
};
