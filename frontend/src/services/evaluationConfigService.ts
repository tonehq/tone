import axiosInstance from '@/utils/axios';

import type {
  EvaluationConfig,
  EvaluationConfigCreatePayload,
  EvaluationConfigListResponse,
  EvaluationConfigResultsResponse,
  EvaluationConfigUpdatePayload,
  RunEvaluationConfigPayload,
} from '@/types/evaluationConfig';

// All evaluation-config HTTP flows through here so components never call axios
// directly. Backend routes: core/api/v1/evaluation_configs.py.

export const listEvaluationConfigs = async (
  params: { search?: string; page?: number; page_size?: number } = {},
): Promise<EvaluationConfigListResponse> => {
  const res = await axiosInstance.post<EvaluationConfigListResponse>('/evaluation-configs/list', {
    search: params.search ?? null,
    page: params.page ?? 1,
    page_size: params.page_size ?? 100,
    sort_order: 'desc',
  });
  return res.data;
};

export const createEvaluationConfig = async (
  payload: EvaluationConfigCreatePayload,
): Promise<EvaluationConfig> => {
  const res = await axiosInstance.post<EvaluationConfig>('/evaluation-configs', payload);
  return res.data;
};

export const updateEvaluationConfig = async (
  configId: string,
  payload: EvaluationConfigUpdatePayload,
): Promise<EvaluationConfig> => {
  const res = await axiosInstance.put<EvaluationConfig>(`/evaluation-configs/${configId}`, payload);
  return res.data;
};

export const deleteEvaluationConfig = async (configId: string): Promise<void> => {
  await axiosInstance.delete(`/evaluation-configs/${configId}`);
};

export const setDefaultEvaluationConfig = async (configId: string): Promise<EvaluationConfig> => {
  const res = await axiosInstance.post<EvaluationConfig>(
    `/evaluation-configs/${configId}/set-default`,
  );
  return res.data;
};

export const runEvaluationConfig = async (
  payload: RunEvaluationConfigPayload,
): Promise<{ status: string; job_id: number }> => {
  const res = await axiosInstance.post<{ status: string; job_id: number }>(
    '/evaluation-configs/run',
    payload,
  );
  return res.data;
};

export const listEvaluationConfigResults = async (
  sourceRunId: string,
  configRunIds?: string[],
): Promise<EvaluationConfigResultsResponse> => {
  const res = await axiosInstance.post<EvaluationConfigResultsResponse>(
    '/evaluation-config-results/list',
    { source_run_id: sourceRunId, config_run_ids: configRunIds ?? null },
  );
  return res.data;
};
