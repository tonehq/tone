import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import {
  compareAgentLlmEvalRuns,
  createAgentLlmEvalFolder,
  createAgentLlmEvalScenario,
  createAgentLlmEvalScenariosBulk,
  deleteAgentLlmEvalFolder,
  deleteAgentLlmEvalScenario,
  deleteAgentLlmEvalScenariosBulk,
  generateAgentLlmEvalScenarios,
  getAgentLlmEvalRunDetail,
  listAgentLlmEvalFolders,
  listAgentLlmEvalRuns,
  listAgentLlmEvalScenarios,
  renameAgentLlmEvalFolder,
  triggerAgentLlmEvalRun,
  updateAgentLlmEvalScenario,
  uploadAgentLlmEvalScenariosCsv,
} from '@/services/agentLlmEvalService';
import type {
  BulkCreateScenariosPayload,
  BulkDeleteScenariosPayload,
  CompareRunsPayload,
  CreateFolderPayload,
  DeleteFolderPayload,
  GenerateScenariosPayload,
  ListRunsRequest,
  ListScenariosRequest,
  RenameFolderPayload,
  ScenarioInput,
  ScenarioPatch,
  TriggerRunPayload,
} from '@/types/agentLlmEval';

export const AGENT_LLM_EVAL_QUERY_KEY = 'agent-llm-evals';

// ── Reads ────────────────────────────────────────────────────────────────

export function useAgentLlmEvalScenarios(agentId: string | null, body: ListScenariosRequest = {}) {
  // Stable key-order stringify — see the ``useAgentLlmEvalRuns`` note.
  const bodyKey = stableStringify(body);
  return useQuery({
    queryKey: [AGENT_LLM_EVAL_QUERY_KEY, 'scenarios', agentId, bodyKey],
    queryFn: () => listAgentLlmEvalScenarios(agentId as string, body),
    enabled: !!agentId,
    // Snappy invalidation — a create/update mutation → invalidate → refetch
    // should feel instant while the user is editing.
    staleTime: 0,
  });
}

export function useAgentLlmEvalRuns(agentId: string | null, params: ListRunsRequest = {}) {
  // Serialize the params in a KEY-ORDER-STABLE way so two callers that
  // pass semantically-identical params in different key order share the
  // same cache entry (naive JSON.stringify is order-sensitive).
  const paramsKey = stableStringify(params);
  return useQuery({
    queryKey: [AGENT_LLM_EVAL_QUERY_KEY, 'runs', agentId, paramsKey],
    queryFn: () => listAgentLlmEvalRuns(agentId as string, params),
    enabled: !!agentId,
    // The worker takes seconds-to-minutes; a 15s staleTime lets the runs
    // table catch a fresh batch without hammering the API.
    staleTime: 15_000,
    // Auto-refresh so ``pending`` / ``running`` rows transition to
    // ``completed`` / ``failed`` on-screen without a manual refresh.
    // Two triggers:
    //  1. The current page has an active row (obvious case).
    //  2. The user is on page 1 with no active rows — a run triggered
    //     just now lands at the TOP (COALESCE(started_at, created_at)
    //     DESC on the backend), so page 1 is the "arrivals" page and
    //     needs to poll for a moment even when the visible rows are
    //     terminal. Bounded because ``staleTime: 15_000`` still throttles
    //     the actual refetch — the interval mostly triggers cache checks.
    // Returns ``false`` for other-page views with all-terminal rows so
    // an idle agent doesn't waste polls.
    refetchInterval: (query) => {
      const rows = query.state.data?.items ?? [];
      const hasActive = rows.some((r) => r.status === 'pending' || r.status === 'running');
      const isFirstPage = (params.page_no ?? 1) === 1;
      return hasActive || isFirstPage ? 5_000 : false;
    },
    refetchIntervalInBackground: false,
  });
}

/** Stable JSON stringifier for TanStack Query cache keys — sorts object
 * keys recursively so ``{a:1, b:2}`` and ``{b:2, a:1}`` share the same
 * key. Guards against a caller that constructs the params object with a
 * different key order per render (would otherwise create duplicate cache
 * entries and duplicate polling). */
function stableStringify(value: unknown): string {
  if (value === null || typeof value !== 'object') return JSON.stringify(value);
  if (Array.isArray(value)) return `[${value.map(stableStringify).join(',')}]`;
  const keys = Object.keys(value as Record<string, unknown>).sort();
  return `{${keys
    .map((k) => `${JSON.stringify(k)}:${stableStringify((value as Record<string, unknown>)[k])}`)
    .join(',')}}`;
}

export function useAgentLlmEvalRunDetail(agentId: string | null, runId: string | null) {
  return useQuery({
    queryKey: [AGENT_LLM_EVAL_QUERY_KEY, 'detail', agentId, runId],
    queryFn: () => getAgentLlmEvalRunDetail(agentId as string, runId as string),
    enabled: !!agentId && !!runId,
    // A completed run's rows never change; long cache is safe.
    staleTime: 60_000,
  });
}

export function useAgentLlmEvalFolders(agentId: string | null) {
  return useQuery({
    queryKey: [AGENT_LLM_EVAL_QUERY_KEY, 'folders', agentId],
    queryFn: () => listAgentLlmEvalFolders(agentId as string),
    enabled: !!agentId,
    // Same snappy semantics as the scenarios list — a create/edit/delete
    // can change folder membership + counts, so we want a fast refetch.
    staleTime: 0,
  });
}

// ── Shared invalidator ───────────────────────────────────────────────────

/** Invalidate scenarios + runs + folders — used by every mutation. A
 * scenario write can change folder counts (add/remove/rename), and a run
 * completion can add rows tagged with a folder that the results-view might
 * want to see. Keeping one invalidator prevents drift between call sites. */
export function useInvalidateAgentLlmEvals(agentId: string) {
  const qc = useQueryClient();
  return () => {
    qc.invalidateQueries({ queryKey: [AGENT_LLM_EVAL_QUERY_KEY, 'scenarios', agentId] });
    qc.invalidateQueries({ queryKey: [AGENT_LLM_EVAL_QUERY_KEY, 'runs', agentId] });
    qc.invalidateQueries({ queryKey: [AGENT_LLM_EVAL_QUERY_KEY, 'folders', agentId] });
  };
}

// ── Mutations ────────────────────────────────────────────────────────────

export function useCreateAgentLlmEvalScenario(agentId: string) {
  const invalidate = useInvalidateAgentLlmEvals(agentId);
  return useMutation({
    mutationFn: (input: ScenarioInput) => createAgentLlmEvalScenario(agentId, input),
    onSuccess: invalidate,
  });
}

export function useCreateAgentLlmEvalScenariosBulk(agentId: string) {
  const invalidate = useInvalidateAgentLlmEvals(agentId);
  return useMutation({
    mutationFn: (payload: BulkCreateScenariosPayload) =>
      createAgentLlmEvalScenariosBulk(agentId, payload),
    onSuccess: invalidate,
  });
}

export function useUpdateAgentLlmEvalScenario(agentId: string) {
  const invalidate = useInvalidateAgentLlmEvals(agentId);
  return useMutation({
    mutationFn: (args: { scenarioId: string; patch: ScenarioPatch }) =>
      updateAgentLlmEvalScenario(agentId, args.scenarioId, args.patch),
    onSuccess: invalidate,
  });
}

export function useDeleteAgentLlmEvalScenario(agentId: string) {
  const invalidate = useInvalidateAgentLlmEvals(agentId);
  return useMutation({
    mutationFn: (scenarioId: string) => deleteAgentLlmEvalScenario(agentId, scenarioId),
    onSuccess: invalidate,
  });
}

export function useDeleteAgentLlmEvalScenariosBulk(agentId: string) {
  const invalidate = useInvalidateAgentLlmEvals(agentId);
  return useMutation({
    mutationFn: (payload: BulkDeleteScenariosPayload) =>
      deleteAgentLlmEvalScenariosBulk(agentId, payload),
    onSuccess: invalidate,
  });
}

export function useUploadAgentLlmEvalScenariosCsv(agentId: string) {
  const invalidate = useInvalidateAgentLlmEvals(agentId);
  return useMutation({
    mutationFn: (file: File) => uploadAgentLlmEvalScenariosCsv(agentId, file),
    onSuccess: invalidate,
  });
}

export function useGenerateAgentLlmEvalScenarios(agentId: string) {
  const invalidate = useInvalidateAgentLlmEvals(agentId);
  return useMutation({
    mutationFn: (payload: GenerateScenariosPayload) =>
      generateAgentLlmEvalScenarios(agentId, payload),
    // Only invalidate on persisted (non-dry-run) results — a dry-run preview
    // doesn't change any server state.
    onSuccess: (data) => {
      if (!data.dry_run) invalidate();
    },
  });
}

export function useTriggerAgentLlmEvalRun(agentId: string) {
  const invalidate = useInvalidateAgentLlmEvals(agentId);
  return useMutation({
    mutationFn: (payload: TriggerRunPayload) => triggerAgentLlmEvalRun(agentId, payload),
    onSuccess: invalidate,
  });
}

export function useCompareAgentLlmEvalRuns(agentId: string) {
  return useMutation({
    mutationFn: (payload: CompareRunsPayload) => compareAgentLlmEvalRuns(agentId, payload),
  });
}

export function useCreateAgentLlmEvalFolder(agentId: string) {
  const invalidate = useInvalidateAgentLlmEvals(agentId);
  return useMutation({
    mutationFn: (payload: CreateFolderPayload) => createAgentLlmEvalFolder(agentId, payload),
    onSuccess: invalidate,
  });
}

export function useRenameAgentLlmEvalFolder(agentId: string) {
  const invalidate = useInvalidateAgentLlmEvals(agentId);
  return useMutation({
    mutationFn: (payload: RenameFolderPayload) => renameAgentLlmEvalFolder(agentId, payload),
    onSuccess: invalidate,
  });
}

export function useDeleteAgentLlmEvalFolder(agentId: string) {
  const invalidate = useInvalidateAgentLlmEvals(agentId);
  return useMutation({
    mutationFn: (payload: DeleteFolderPayload) => deleteAgentLlmEvalFolder(agentId, payload),
    onSuccess: invalidate,
  });
}
