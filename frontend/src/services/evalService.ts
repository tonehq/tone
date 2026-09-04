import { postMultipart } from '@/utils/apiHelpers';
import axiosInstance from '@/utils/axios';

import type {
  EvalQuestion,
  EvalQuestionsResponse,
  EvalRunDetail,
  EvalRunSummary,
  EvalSetSummary,
  EvalSummaryByIngestionResponse,
  ManualQuestionInput,
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

// ── Manual eval-question authoring ─────────────────────────────────────

export const listEvalQuestions = async (uploadId: string): Promise<EvalQuestion[]> => {
  const res = await axiosInstance.get<EvalQuestionsResponse>(
    `/knowledge-base/${uploadId}/evals/questions`,
  );
  return res.data.items;
};

export const addManualEvalQuestions = async (
  uploadId: string,
  questions: ManualQuestionInput[],
): Promise<EvalSetSummary> => {
  const res = await axiosInstance.post<EvalSetSummary>(`/knowledge-base/${uploadId}/evals/manual`, {
    questions,
  });
  return res.data;
};

// Multipart upload — server parses the CSV and reuses the manual-append path,
// so validation and audit tags match a hand-typed entry exactly. The
// multipart/form-data + boundary handling lives in `postMultipart`.
export const uploadEvalQuestionsCsv = async (
  uploadId: string,
  file: File,
): Promise<EvalSetSummary> => {
  return postMultipart<EvalSetSummary>(`/knowledge-base/${uploadId}/evals/upload-csv`, file);
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
