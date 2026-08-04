import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import { KNOWLEDGE_BASE_QUERY_KEY } from '@/lib/api/knowledge-base';
import {
  activateIngestionRun,
  createCustomIngestionRun,
  getPipelineOptions,
  listIngestionRuns,
  setAgentKbActiveRun,
  type AgentKnowledgeBaseRow,
} from '@/services/ingestionRunService';
import type {
  IngestionRun,
  ListIngestionRunsParams,
  PaginatedIngestionRuns,
} from '@/types/ingestionRun';
import type {
  CreateIngestionRunPayload,
  CreateIngestionRunResponse,
  PipelineOptions,
} from '@/types/pipelineOptions';

export const INGESTION_RUNS_QUERY_KEY = 'ingestion-runs';
export const PIPELINE_OPTIONS_QUERY_KEY = 'pipeline-options';

// Poll while any row is still processing so status flips arrive without a
// manual refresh — mirrors the KB list's polling behavior.
const RUNS_POLL_INTERVAL_MS = 4000;
function shouldPoll(data?: PaginatedIngestionRuns): number | false {
  const busy = data?.data.some((r) => r.status === 'pending' || r.status === 'running');
  return busy ? RUNS_POLL_INTERVAL_MS : false;
}

export function useIngestionRuns(uploadId: string | null, params: ListIngestionRunsParams = {}) {
  return useQuery({
    queryKey: [INGESTION_RUNS_QUERY_KEY, uploadId, params],
    queryFn: () => listIngestionRuns(uploadId as string, params),
    enabled: !!uploadId,
    placeholderData: (prev) => prev,
    refetchInterval: (query) => shouldPoll(query.state.data),
  });
}

export function useActivateIngestionRun(uploadId: string) {
  const qc = useQueryClient();
  return useMutation<IngestionRun, unknown, string>({
    mutationFn: (runId: string) => activateIngestionRun(uploadId, runId),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: [INGESTION_RUNS_QUERY_KEY, uploadId] });
      // KB row exposes the active pointer; refresh list/detail consumers too.
      qc.invalidateQueries({ queryKey: [KNOWLEDGE_BASE_QUERY_KEY] });
    },
  });
}

// Registry of parsers / tokenisers / embedders / vector stores is global and
// only changes on a backend deploy, so this cache never needs to refetch
// during a session.
export function usePipelineOptions(enabled: boolean = true) {
  return useQuery<PipelineOptions>({
    queryKey: [PIPELINE_OPTIONS_QUERY_KEY],
    queryFn: getPipelineOptions,
    enabled,
    staleTime: Infinity,
  });
}

export function useCreateCustomIngestionRun(uploadId: string) {
  const qc = useQueryClient();
  return useMutation<CreateIngestionRunResponse, unknown, CreateIngestionRunPayload>({
    mutationFn: (payload) => createCustomIngestionRun(uploadId, payload),
    onSuccess: () => {
      // Surface the new pending row immediately; existing shouldPoll logic
      // then follows its pending → running → ready transitions.
      qc.invalidateQueries({ queryKey: [INGESTION_RUNS_QUERY_KEY, uploadId] });
    },
  });
}

export function useSetAgentKbActiveRun() {
  // The per-agent pin only affects retrieval for that agent — it doesn't
  // change any list the FE caches today (the runs list content is per-upload,
  // not per-agent; the agent-detail response is loaded via Jotai atoms, not
  // React Query). Consumers hold the current value in local component state
  // and optimistically update on change, so no cache invalidation is needed.
  return useMutation<
    AgentKnowledgeBaseRow,
    unknown,
    { agentId: string; kbId: string; runId: string | null }
  >({
    mutationFn: ({ agentId, kbId, runId }) => setAgentKbActiveRun(agentId, kbId, runId),
  });
}
