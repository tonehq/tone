import { useQuery } from '@tanstack/react-query';

import {
  getEvalRunDetail,
  listEvalRunsForIngestion,
  listEvalSummariesByIngestion,
} from '@/services/evalService';

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
