import { useMemo } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import {
  addManualEvalQuestions,
  approveAllEvalQuestions,
  approveEvalQuestion,
  deleteEvalQuestion,
  generateEvalVersion,
  getEvalRunDetail,
  listEvalQuestions,
  listEvalRunsFiltered,
  listEvalSummariesByIngestion,
  listEvalVersions,
  rejectAllEvalQuestions,
  setEvalRunLabel,
  triggerEvalRun,
  updateEvalQuestion,
  uploadEvalQuestionsCsv,
} from '@/services/evalService';
import type {
  GenerateEvalVersionPayload,
  ManualQuestionInput,
  SetHumanVerdictPayload,
  TriggerEvalRunPayload,
  UpdateQuestionPatch,
} from '@/types/eval';

import { EVAL_CONFIG_QUERY_KEY } from './evaluationConfigs';

export const EVAL_QUERY_KEY = 'evals';

// One aggregated call per visible page of ingestion runs — used by the KB
// Ingestion-Runs table to paint the per-row "Evals" chip without an N+1.
// The set of ingestion run ids is sorted so the same page reuses one cache
// entry regardless of insertion order.
export function useEvalSummariesByIngestion(uploadId: string | null, ingestionRunIds: string[]) {
  const sortedIds = [...ingestionRunIds].sort();
  return useQuery({
    queryKey: [EVAL_QUERY_KEY, 'by-ingestion', uploadId, sortedIds],
    queryFn: () => listEvalSummariesByIngestion(uploadId as string, sortedIds),
    enabled: !!uploadId && sortedIds.length > 0,
    // Cheap SQL aggregate; refetch on tab focus is enough for scored batches.
    staleTime: 15_000,
    // While any eval batch is queued/running its results don't exist yet, so
    // poll every 4s to swap the per-row spinner for the score the moment the
    // batch lands. Stops polling once nothing is in flight.
    refetchInterval: (query) =>
      (query.state.data?.in_flight_ingestion_run_ids?.length ?? 0) > 0 ? 4_000 : false,
  });
}

// Ingestion-run ids whose eval batch is queued/running (no score row yet), as a
// Set for O(1) membership. The one place the in-flight signal is derived so the
// Ingestion-Runs table, Manage-evals Run button, and Results-tab poll all read
// it the same way (and share the underlying poll).
export function useInFlightEvalRunIds(uploadId: string | null, ingestionRunIds: string[]) {
  const { data } = useEvalSummariesByIngestion(uploadId, ingestionRunIds);
  return useMemo(() => new Set(data?.in_flight_ingestion_run_ids ?? []), [data]);
}

// Batch detail — summary + per-question rows for one batch.
export function useEvalRunDetail(uploadId: string | null, runId: string | null) {
  return useQuery({
    queryKey: [EVAL_QUERY_KEY, 'detail', uploadId, runId],
    queryFn: () => getEvalRunDetail(uploadId as string, runId as string),
    enabled: !!uploadId && !!runId,
    staleTime: 60_000,
  });
}

// Set/clear the human Accept/Reject label on one scored answer. On success
// refresh the batch detail (so the mark sticks) AND the config-results for the
// same source run (so judge-agreement % recomputes) — the run_id being labeled
// IS the config re-grade's source_run_id.
export function useSetHumanVerdict(uploadId: string, runId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload: SetHumanVerdictPayload) => setEvalRunLabel(uploadId, runId, payload),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: [EVAL_QUERY_KEY, 'detail', uploadId, runId] });
      qc.invalidateQueries({ queryKey: [EVAL_CONFIG_QUERY_KEY, 'results', runId] });
    },
  });
}

// ── Eval versions (generate / review / approve) ────────────────────────

// Versions for an upload. Polls every 4s while any version is still
// generating (the async LLM job flips it generating → draft).
export function useEvalVersions(uploadId: string | null) {
  return useQuery({
    queryKey: [EVAL_QUERY_KEY, 'versions', uploadId],
    queryFn: () => listEvalVersions(uploadId as string),
    enabled: !!uploadId,
    staleTime: 5_000,
    refetchInterval: (query) =>
      (query.state.data ?? []).some((v) => v.status === 'generating') ? 4_000 : false,
  });
}

export function useGenerateEvalVersion(uploadId: string) {
  const invalidate = useInvalidateEvals(uploadId);
  return useMutation({
    mutationFn: (payload: GenerateEvalVersionPayload) => generateEvalVersion(uploadId, payload),
    onSuccess: invalidate,
  });
}

export function useApproveEvalQuestion(uploadId: string) {
  const invalidate = useInvalidateEvals(uploadId);
  return useMutation({
    mutationFn: (questionId: string) => approveEvalQuestion(uploadId, questionId),
    onSuccess: invalidate,
  });
}

export function useApproveAllEvalQuestions(uploadId: string) {
  const invalidate = useInvalidateEvals(uploadId);
  return useMutation({
    mutationFn: (versionId: string) => approveAllEvalQuestions(uploadId, versionId),
    onSuccess: invalidate,
  });
}

export function useRejectAllEvalQuestions(uploadId: string) {
  const invalidate = useInvalidateEvals(uploadId);
  return useMutation({
    mutationFn: (versionId: string) => rejectAllEvalQuestions(uploadId, versionId),
    onSuccess: invalidate,
  });
}

// Eval batches for the results tab, filtered by ingestion run and/or version.
// Pass pollWhileInFlight=true (a batch is queued/running) to refetch every 5s so
// the finished batch surfaces without a manual refresh.
export function useEvalRunsFiltered(
  uploadId: string | null,
  filters: { ingestion_run_id?: string | null; eval_version_id?: string | null },
  pollWhileInFlight = false,
) {
  return useQuery({
    queryKey: [EVAL_QUERY_KEY, 'runs-filtered', uploadId, filters],
    queryFn: () => listEvalRunsFiltered(uploadId as string, filters),
    enabled: !!uploadId,
    staleTime: 15_000,
    refetchInterval: pollWhileInFlight ? 5_000 : false,
  });
}

// ── Eval-question authoring (scoped to a version) ──────────────────────

// Questions for one version — feeds the manage-evals review list. Short
// staleTime (0) so a mutation → invalidate → immediate refetch feels snappy.
export function useEvalQuestions(uploadId: string | null, versionId?: string | null) {
  return useQuery({
    queryKey: [EVAL_QUERY_KEY, 'questions', uploadId, versionId ?? null],
    queryFn: () => listEvalQuestions(uploadId as string, versionId),
    enabled: !!uploadId && !!versionId,
    staleTime: 0,
  });
}

// Invalidator shared by every question-mutation: refresh the questions list
// AND the ingestion-run summary chip (question_count is derived by SQL
// aggregate on eval_results, but the "any questions exist" state gates the
// Run button — safest to invalidate both).
function useInvalidateEvals(uploadId: string) {
  const qc = useQueryClient();
  return () => {
    qc.invalidateQueries({ queryKey: [EVAL_QUERY_KEY, 'questions', uploadId] });
    qc.invalidateQueries({ queryKey: [EVAL_QUERY_KEY, 'versions', uploadId] });
    qc.invalidateQueries({ queryKey: [EVAL_QUERY_KEY, 'by-ingestion', uploadId] });
    qc.invalidateQueries({ queryKey: [EVAL_QUERY_KEY, 'runs-filtered', uploadId] });
  };
}

export function useAddManualEvalQuestions(uploadId: string) {
  const invalidate = useInvalidateEvals(uploadId);
  return useMutation({
    mutationFn: (args: { versionId: string; questions: ManualQuestionInput[] }) =>
      addManualEvalQuestions(uploadId, args.versionId, args.questions),
    onSuccess: invalidate,
  });
}

// CSV upload → parsed + appended into the given version server-side.
export function useUploadEvalQuestionsCsv(uploadId: string) {
  const invalidate = useInvalidateEvals(uploadId);
  return useMutation({
    mutationFn: (args: { versionId: string; file: File }) =>
      uploadEvalQuestionsCsv(uploadId, args.versionId, args.file),
    onSuccess: invalidate,
  });
}

export function useUpdateEvalQuestion(uploadId: string) {
  const invalidate = useInvalidateEvals(uploadId);
  return useMutation({
    mutationFn: (args: { questionId: string; patch: UpdateQuestionPatch }) =>
      updateEvalQuestion(uploadId, args.questionId, args.patch),
    onSuccess: invalidate,
  });
}

export function useDeleteEvalQuestion(uploadId: string) {
  const invalidate = useInvalidateEvals(uploadId);
  return useMutation({
    mutationFn: (questionId: string) => deleteEvalQuestion(uploadId, questionId),
    onSuccess: invalidate,
  });
}

// Enqueues a Procrastinate eval-run job. Returns the queued job id — the
// actual scoring takes 5-10 minutes, and the KB Ingestion-Runs table will
// pick up the new batch on its next poll / focus refetch.
export function useTriggerEvalRun(uploadId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload?: TriggerEvalRunPayload) => triggerEvalRun(uploadId, payload ?? {}),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: [EVAL_QUERY_KEY, 'by-ingestion', uploadId] });
      qc.invalidateQueries({ queryKey: [EVAL_QUERY_KEY, 'runs', uploadId] });
    },
  });
}
