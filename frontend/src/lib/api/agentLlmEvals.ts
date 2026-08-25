import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import {
  compareAgentLlmEvalRuns,
  createAgentLlmEvalScenario,
  createAgentLlmEvalScenariosBulk,
  deleteAgentLlmEvalScenario,
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
  CompareRunsPayload,
  GenerateScenariosPayload,
  ListScenariosRequest,
  RenameFolderPayload,
  ScenarioInput,
  ScenarioPatch,
  TriggerRunPayload,
} from '@/types/agentLlmEval';

export const AGENT_LLM_EVAL_QUERY_KEY = 'agent-llm-evals';

// ── Reads ────────────────────────────────────────────────────────────────

export function useAgentLlmEvalScenarios(agentId: string | null, body: ListScenariosRequest = {}) {
  const bodyKey = JSON.stringify(body);
  return useQuery({
    queryKey: [AGENT_LLM_EVAL_QUERY_KEY, 'scenarios', agentId, bodyKey],
    queryFn: () => listAgentLlmEvalScenarios(agentId as string, body),
    enabled: !!agentId,
    // Snappy invalidation — a create/update mutation → invalidate → refetch
    // should feel instant while the user is editing.
    staleTime: 0,
  });
}

export function useAgentLlmEvalRuns(agentId: string | null) {
  return useQuery({
    queryKey: [AGENT_LLM_EVAL_QUERY_KEY, 'runs', agentId],
    queryFn: () => listAgentLlmEvalRuns(agentId as string),
    enabled: !!agentId,
    // The worker takes seconds-to-minutes; a 15s staleTime lets the runs
    // table catch a fresh batch without hammering the API.
    staleTime: 15_000,
  });
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
    mutationFn: (scenarios: ScenarioInput[]) => createAgentLlmEvalScenariosBulk(agentId, scenarios),
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

export function useRenameAgentLlmEvalFolder(agentId: string) {
  const invalidate = useInvalidateAgentLlmEvals(agentId);
  return useMutation({
    mutationFn: (payload: RenameFolderPayload) => renameAgentLlmEvalFolder(agentId, payload),
    onSuccess: invalidate,
  });
}
