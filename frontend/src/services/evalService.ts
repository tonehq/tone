import axiosInstance from '@/utils/axios';

import type { EvalRunDetail, EvalRunSummary, EvalSummaryByIngestionResponse } from '@/types/eval';

// All eval-view HTTP flows through here so components never `axios.post`
// directly. Mirrors the KB router endpoints under `/knowledge-base/...`.

export const listEvalSummariesByIngestion = async (
  uploadId: string,
  ingestionRunIds: string[],
): Promise<EvalSummaryByIngestionResponse> => {
  const res = await axiosInstance.post<EvalSummaryByIngestionResponse>(
    `/knowledge-base/${uploadId}/eval-summary/by-ingestion`,
    { ingestion_run_ids: ingestionRunIds },
  );
  return res.data;
};

export const listEvalRunsForIngestion = async (
  uploadId: string,
  ingestionRunId: string,
): Promise<EvalRunSummary[]> => {
  const res = await axiosInstance.get<{ items: EvalRunSummary[] }>(
    `/knowledge-base/${uploadId}/runs/${ingestionRunId}/eval-runs`,
  );
  return res.data.items;
};

export const getEvalRunDetail = async (uploadId: string, runId: string): Promise<EvalRunDetail> => {
  const res = await axiosInstance.get<EvalRunDetail>(
    `/knowledge-base/${uploadId}/eval-runs/${runId}`,
  );
  return res.data;
};
