import { pruneParams } from '@/utils/apiHelpers';
import axiosInstance from '@/utils/axios';

import type {
  CreateIngestionConfigPayload,
  IngestionConfig,
  ListIngestionConfigsParams,
  PaginatedIngestionConfigs,
  UpdateIngestionConfigPayload,
} from '@/types/ingestionConfig';

// All ingestion-config HTTP flows through here so components never call axios
// directly (project convention — see frontend/CLAUDE.md § service layer).

export const listIngestionConfigs = async (
  params: ListIngestionConfigsParams = {},
): Promise<PaginatedIngestionConfigs> => {
  const body = pruneParams(params);
  const res = await axiosInstance.post<PaginatedIngestionConfigs>('/ingestion-configs/list', body);
  return res.data;
};

export const getIngestionConfig = async (id: string): Promise<IngestionConfig> => {
  const res = await axiosInstance.get<IngestionConfig>(`/ingestion-configs/${id}`);
  return res.data;
};

export const createIngestionConfig = async (
  payload: CreateIngestionConfigPayload,
): Promise<IngestionConfig> => {
  const res = await axiosInstance.post<IngestionConfig>(
    '/ingestion-configs/create_ingestion_config',
    payload,
  );
  return res.data;
};

export const updateIngestionConfig = async (
  id: string,
  payload: UpdateIngestionConfigPayload,
): Promise<IngestionConfig> => {
  const res = await axiosInstance.put<IngestionConfig>(
    `/ingestion-configs/update_ingestion_config/${id}`,
    payload,
  );
  return res.data;
};

export const deleteIngestionConfig = async (
  id: string,
): Promise<{ id: string; deleted: boolean }> => {
  const res = await axiosInstance.delete<{ id: string; deleted: boolean }>(
    `/ingestion-configs/${id}`,
  );
  return res.data;
};
