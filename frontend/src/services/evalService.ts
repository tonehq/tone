import { postMultipart } from '@/utils/apiHelpers';
import axiosInstance from '@/utils/axios';

import type {
  EvalQuestion,
  EvalQuestionsResponse,
  EvalRunDetail,
  EvalRunSummary,
  EvalSetSummary,
  EvalSummaryByIngestionResponse,
  EvalVersion,
  EvalVersionsResponse,
  GenerateEvalVersionPayload,
  GenerateEvalVersionResponse,
  ManualQuestionInput,
  SetHumanVerdictPayload,
  TriggerEvalRunPayload,
  TriggerEvalRunResponse,
  UpdateQuestionPatch,
} from '@/types/eval';

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

export const getEvalRunDetail = async (uploadId: string, runId: string): Promise<EvalRunDetail> => {
  const res = await axiosInstance.get<EvalRunDetail>(
    `/knowledge-base/${uploadId}/eval-runs/${runId}`,
  );
  return res.data;
};

// Set (or clear, verdict=null) the human Accept/Reject label on one scored
// answer. Returns the updated eval_results row.
export const setEvalRunLabel = async (
  uploadId: string,
  runId: string,
  payload: SetHumanVerdictPayload,
): Promise<Record<string, unknown>> => {
  const res = await axiosInstance.post<Record<string, unknown>>(
    `/knowledge-base/${uploadId}/eval-runs/${runId}/label`,
    payload,
  );
  return res.data;
};

// ── Eval versions (generate / review / approve) ────────────────────────

export const listEvalVersions = async (uploadId: string): Promise<EvalVersion[]> => {
  const res = await axiosInstance.get<EvalVersionsResponse>(
    `/knowledge-base/${uploadId}/eval-versions`,
  );
  return res.data.items;
};

export const generateEvalVersion = async (
  uploadId: string,
  payload: GenerateEvalVersionPayload,
): Promise<GenerateEvalVersionResponse> => {
  const res = await axiosInstance.post<GenerateEvalVersionResponse>(
    `/knowledge-base/${uploadId}/eval-versions/generate`,
    payload,
  );
  return res.data;
};

export const approveEvalQuestion = async (
  uploadId: string,
  questionId: string,
): Promise<EvalQuestion> => {
  const res = await axiosInstance.post<EvalQuestion>(
    `/knowledge-base/${uploadId}/evals/questions/${questionId}/approve`,
  );
  return res.data;
};

export const approveAllEvalQuestions = async (
  uploadId: string,
  versionId: string,
): Promise<{ approved: number }> => {
  const res = await axiosInstance.post<{ approved: number }>(
    `/knowledge-base/${uploadId}/eval-versions/${versionId}/approve-all`,
  );
  return res.data;
};

export const rejectAllEvalQuestions = async (
  uploadId: string,
  versionId: string,
): Promise<{ rejected: number }> => {
  const res = await axiosInstance.post<{ rejected: number }>(
    `/knowledge-base/${uploadId}/eval-versions/${versionId}/reject-all`,
  );
  return res.data;
};

// ── Eval-question authoring (scoped to a version) ──────────────────────

export const listEvalQuestions = async (
  uploadId: string,
  versionId?: string | null,
): Promise<EvalQuestion[]> => {
  const res = await axiosInstance.get<EvalQuestionsResponse>(
    `/knowledge-base/${uploadId}/evals/questions`,
    { params: versionId ? { version_id: versionId } : undefined },
  );
  return res.data.items;
};

export const addManualEvalQuestions = async (
  uploadId: string,
  versionId: string,
  questions: ManualQuestionInput[],
): Promise<EvalSetSummary> => {
  const res = await axiosInstance.post<EvalSetSummary>(`/knowledge-base/${uploadId}/evals/manual`, {
    questions,
    eval_version_id: versionId,
  });
  return res.data;
};

// Multipart upload — server parses the CSV and appends into the given version.
export const uploadEvalQuestionsCsv = async (
  uploadId: string,
  versionId: string,
  file: File,
): Promise<EvalSetSummary> =>
  postMultipart<EvalSetSummary>(`/knowledge-base/${uploadId}/evals/upload-csv`, file, {
    eval_version_id: versionId,
  });

// Eval batches for the results tab, optionally filtered by ingestion + version.
export const listEvalRunsFiltered = async (
  uploadId: string,
  filters: { ingestion_run_id?: string | null; eval_version_id?: string | null },
): Promise<EvalRunSummary[]> => {
  const res = await axiosInstance.post<{ items: EvalRunSummary[] }>(
    `/knowledge-base/${uploadId}/eval-runs/list`,
    filters,
  );
  return res.data.items;
};

export const updateEvalQuestion = async (
  uploadId: string,
  questionId: string,
  patch: UpdateQuestionPatch,
): Promise<EvalQuestion> => {
  const res = await axiosInstance.put<EvalQuestion>(
    `/knowledge-base/${uploadId}/evals/questions/${questionId}`,
    patch,
  );
  return res.data;
};

export const deleteEvalQuestion = async (
  uploadId: string,
  questionId: string,
): Promise<{ ok: boolean }> => {
  const res = await axiosInstance.delete<{ ok: boolean }>(
    `/knowledge-base/${uploadId}/evals/questions/${questionId}`,
  );
  return res.data;
};

export const triggerEvalRun = async (
  uploadId: string,
  payload: TriggerEvalRunPayload = {},
): Promise<TriggerEvalRunResponse> => {
  const res = await axiosInstance.post<TriggerEvalRunResponse>(
    `/knowledge-base/${uploadId}/evals/run`,
    payload,
  );
  return res.data;
};
