import { pagedListRequest } from '@/services/listHelpers';
import type {
  ProviderCatalogItem,
  ProviderModel,
  ProviderUsage,
  Service,
  ServiceUpsertPayload,
} from '@/types/service';
import axios from '@/utils/axios';

// ─── aggregated usage list (cards) ─────────────────────────────────────────
export interface ListServicesParams {
  page?: number;
  page_size?: number;
  search?: string;
  sort_by?: string;
  service_type?: 'llm' | 'stt' | 'tts' | 'all';
  status?: 'active' | 'inactive' | 'all';
}

export interface ListServicesResult {
  rows: ProviderUsage[];
  total: number;
  page: number;
  page_size: number;
}

export async function listServices(params: ListServicesParams = {}): Promise<ListServicesResult> {
  const body: Record<string, unknown> = {};
  for (const [k, v] of Object.entries(params)) {
    if (v !== undefined && v !== null && v !== '') body[k] = v;
  }
  return pagedListRequest<ProviderUsage>('/services/list', body);
}

// ─── CRUD on individual ApiKey rows ────────────────────────────────────────
export async function createService(payload: ServiceUpsertPayload): Promise<Service> {
  const { data } = await axios.post<Service>('/services', payload);
  return data;
}

export async function getService(id: string): Promise<Service> {
  const { data } = await axios.get<Service>(`/services/${id}`);
  return data;
}

export async function updateService(
  id: string,
  payload: Partial<ServiceUpsertPayload>,
): Promise<Service> {
  const { data } = await axios.patch<Service>(`/services/${id}`, payload);
  return data;
}

export async function deleteService(id: string): Promise<void> {
  await axios.delete(`/services/${id}`);
}

export async function deleteProviderServices(
  providerId: string,
  serviceType?: 'llm' | 'stt' | 'tts',
): Promise<{ deleted: number }> {
  const { data } = await axios.delete<{ deleted: number }>(
    `/services/providers/${providerId}`,
    serviceType ? { params: { service_type: serviceType } } : undefined,
  );
  return data;
}

// ─── provider catalog (drawer dropdown) ────────────────────────────────────
// Pass ``serviceType`` from the agent-form dropdowns (AiStep llm, VoiceStep stt)
// so the backend filters out providers the org has no active ApiKey for.
// Omit it from flows that need the full catalog — "add API key" drawer and the
// provider detail page.
export async function listProviderCatalog(
  serviceType?: 'llm' | 'stt' | 'tts',
): Promise<ProviderCatalogItem[]> {
  const { data } = await axios.get<ProviderCatalogItem[]>(
    '/services/providers/catalog',
    serviceType ? { params: { service_type: serviceType } } : undefined,
  );
  return data;
}

// ─── per-provider drill-down (detail page panels) ──────────────────────────
export interface ListProviderKeysParams {
  page?: number;
  page_size?: number;
  search?: string;
  sort_by?: string;
  service_type?: 'llm' | 'stt' | 'tts' | 'all';
  status?: 'active' | 'inactive' | 'all';
}

export async function listProviderKeys(
  providerId: string,
  params: ListProviderKeysParams = {},
): Promise<{ rows: Service[]; total: number; page: number; page_size: number }> {
  const body: Record<string, unknown> = {};
  for (const [k, v] of Object.entries(params)) {
    if (v !== undefined && v !== null && v !== '') body[k] = v;
  }
  return pagedListRequest<Service>(`/services/providers/${providerId}/keys`, body);
}

export async function listProviderKeyFilterValues(
  providerId: string,
  columnName: string,
  serviceType?: string,
): Promise<string[]> {
  const { data } = await axios.get<{ column: string; values: string[] }>(
    `/services/providers/${providerId}/keys/filter-values`,
    { params: { column_name: columnName, ...(serviceType ? { service_type: serviceType } : {}) } },
  );
  return data?.values ?? [];
}

export async function listProviderModelFilterValues(
  providerId: string,
  columnName: string,
  serviceType?: string,
): Promise<string[]> {
  const { data } = await axios.get<{ column: string; values: string[] }>(
    `/services/providers/${providerId}/models/filter-values`,
    { params: { column_name: columnName, ...(serviceType ? { service_type: serviceType } : {}) } },
  );
  return data?.values ?? [];
}

export interface ListProviderModelsParams {
  page?: number;
  page_size?: number;
  search?: string;
  sort_by?: string;
  service_type?: 'llm' | 'stt' | 'tts';
}

export async function listProviderModels(
  providerId: string,
  params: ListProviderModelsParams = {},
): Promise<{ rows: ProviderModel[]; total: number; page: number; page_size: number }> {
  const body: Record<string, unknown> = {};
  for (const [k, v] of Object.entries(params)) {
    if (v !== undefined && v !== null && v !== '') body[k] = v;
  }
  return pagedListRequest<ProviderModel>(`/services/providers/${providerId}/models`, body);
}

// ─── model CRUD ────────────────────────────────────────────────────────────
export interface ModelUpsertPayload {
  name: string;
  display_name?: string;
  kind: 'llm' | 'stt' | 'tts';
  description?: string;
  base_url?: string;
  is_active?: boolean;
}

export async function createProviderModel(
  providerId: string,
  payload: ModelUpsertPayload,
): Promise<ProviderModel> {
  const { data } = await axios.post<ProviderModel>(
    `/services/providers/${providerId}/models/create`,
    payload,
  );
  return data;
}

export async function updateProviderModel(
  providerId: string,
  modelId: string,
  payload: Partial<ModelUpsertPayload>,
): Promise<ProviderModel> {
  const { data } = await axios.patch<ProviderModel>(
    `/services/providers/${providerId}/models/${modelId}`,
    payload,
  );
  return data;
}

export async function deleteProviderModel(providerId: string, modelId: string): Promise<void> {
  await axios.delete(`/services/providers/${providerId}/models/${modelId}`);
}
