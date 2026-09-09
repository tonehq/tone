import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import {
  createEvaluationConfig,
  deleteEvaluationConfig,
  listEvaluationConfigResults,
  listEvaluationConfigs,
  runEvaluationConfig,
  setDefaultEvaluationConfig,
  updateEvaluationConfig,
} from '@/services/evaluationConfigService';
import type {
  EvaluationConfigCreatePayload,
  EvaluationConfigUpdatePayload,
  RunEvaluationConfigPayload,
} from '@/types/evaluationConfig';

// The judge-model catalog hook lives in evalSettings (single source of truth);
// re-exported here so config-tab consumers have one import surface without a
// second hook/cache. See @/lib/api/evalSettings.useEvalModelOptions.
export { useEvalModelOptions } from '@/lib/api/evalSettings';

export const EVAL_CONFIG_QUERY_KEY = 'evaluation-configs';

// Org-wide config list (shown in every KB tab). staleTime keeps it stable while
// the user runs/compares; mutations invalidate it explicitly.
export function useEvaluationConfigs(search?: string) {
  return useQuery({
    queryKey: [EVAL_CONFIG_QUERY_KEY, 'list', search ?? null],
    queryFn: () => listEvaluationConfigs({ search: search ?? undefined }),
    staleTime: 30_000,
  });
}

function useInvalidateConfigs() {
  const qc = useQueryClient();
  return () => qc.invalidateQueries({ queryKey: [EVAL_CONFIG_QUERY_KEY, 'list'] });
}

export function useCreateEvaluationConfig() {
  const invalidate = useInvalidateConfigs();
  return useMutation({
    mutationFn: (payload: EvaluationConfigCreatePayload) => createEvaluationConfig(payload),
    onSuccess: invalidate,
  });
}

export function useUpdateEvaluationConfig() {
  const invalidate = useInvalidateConfigs();
  return useMutation({
    mutationFn: (args: { configId: string; payload: EvaluationConfigUpdatePayload }) =>
      updateEvaluationConfig(args.configId, args.payload),
    onSuccess: invalidate,
  });
}

export function useDeleteEvaluationConfig() {
  const invalidate = useInvalidateConfigs();
  return useMutation({
    mutationFn: (configId: string) => deleteEvaluationConfig(configId),
    onSuccess: invalidate,
  });
}

export function useSetDefaultEvaluationConfig() {
  const invalidate = useInvalidateConfigs();
  return useMutation({
    mutationFn: (configId: string) => setDefaultEvaluationConfig(configId),
    onSuccess: invalidate,
  });
}

// Config-results for a source run (optionally limited to up to 3 config passes
// for compare). Polls while a re-grade is in flight so fresh scores surface.
export function useEvaluationConfigResults(
  sourceRunId: string | null,
  configRunIds?: string[],
  pollWhileEmpty = false,
) {
  return useQuery({
    queryKey: [EVAL_CONFIG_QUERY_KEY, 'results', sourceRunId, configRunIds ?? null],
    queryFn: () => listEvaluationConfigResults(sourceRunId as string, configRunIds),
    enabled: !!sourceRunId,
    staleTime: 5_000,
    refetchInterval: pollWhileEmpty ? 4_000 : false,
  });
}

// Enqueues the background re-grade. The results query picks up the new pass on
// its next poll / an explicit invalidation.
export function useRunEvaluationConfig() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload: RunEvaluationConfigPayload) => runEvaluationConfig(payload),
    onSuccess: (_data, payload) => {
      qc.invalidateQueries({
        queryKey: [EVAL_CONFIG_QUERY_KEY, 'results', payload.source_run_id],
      });
    },
  });
}
