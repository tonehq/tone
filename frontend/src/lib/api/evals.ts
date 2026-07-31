import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import {
  addManualEvalQuestions,
  deleteEvalQuestion,
  getEvalRunDetail,
  listEvalQuestions,
  listEvalRunsForIngestion,
  listEvalSummariesByIngestion,
  triggerEvalRun,
  updateEvalQuestion,
  uploadEvalQuestionsCsv,
} from '@/services/evalService';
import type { ManualQuestionInput, TriggerEvalRunPayload, UpdateQuestionPatch } from '@/types/eval';

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
    // Cheap SQL aggregate; refetch on tab focus is enough — no polling
    // (the table already polls ingestion runs, which drives this refetch
    // via the changed id list).
    staleTime: 15_000,
  });
}

// Runs-picker for the drawer.
export function useEvalRunsForIngestion(uploadId: string | null, ingestionRunId: string | null) {
  return useQuery({
    queryKey: [EVAL_QUERY_KEY, 'runs', uploadId, ingestionRunId],
    queryFn: () => listEvalRunsForIngestion(uploadId as string, ingestionRunId as string),
    enabled: !!uploadId && !!ingestionRunId,
    staleTime: 15_000,
  });
}

// Drawer body — summary + per-question rows for one batch.
export function useEvalRunDetail(uploadId: string | null, runId: string | null) {
  return useQuery({
    queryKey: [EVAL_QUERY_KEY, 'detail', uploadId, runId],
    queryFn: () => getEvalRunDetail(uploadId as string, runId as string),
    enabled: !!uploadId && !!runId,
    staleTime: 60_000,
  });
}

// ── Manual eval-question authoring ─────────────────────────────────────

// Every question for one upload — feeds the manual-authoring modal's list.
// Short staleTime (0) so a mutation → invalidate → immediate refetch feels
// snappy to the user typing.
export function useEvalQuestions(uploadId: string | null) {
  return useQuery({
    queryKey: [EVAL_QUERY_KEY, 'questions', uploadId],
    queryFn: () => listEvalQuestions(uploadId as string),
    enabled: !!uploadId,
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
    qc.invalidateQueries({ queryKey: [EVAL_QUERY_KEY, 'by-ingestion', uploadId] });
  };
}

export function useAddManualEvalQuestions(uploadId: string) {
  const invalidate = useInvalidateEvals(uploadId);
  return useMutation({
    mutationFn: (questions: ManualQuestionInput[]) => addManualEvalQuestions(uploadId, questions),
    onSuccess: invalidate,
  });
}

// CSV upload → parsed + appended server-side via the same manual-append path
// (identical validation + audit tag). Invalidates the same queries so the
// list refreshes as soon as the upload completes.
export function useUploadEvalQuestionsCsv(uploadId: string) {
  const invalidate = useInvalidateEvals(uploadId);
  return useMutation({
    mutationFn: (file: File) => uploadEvalQuestionsCsv(uploadId, file),
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
