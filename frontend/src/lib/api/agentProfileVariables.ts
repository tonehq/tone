import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import {
  createAgentProfileVariable,
  deleteAgentProfileVariable,
  listAgentProfileVariables,
  updateAgentProfileVariable,
} from '@/services/agentProfileVariableService';
import type {
  AgentProfileVariable,
  ProfileVariableInput,
  ProfileVariablePatch,
} from '@/types/agentProfileVariable';

export const AGENT_PROFILE_VARIABLES_QUERY_KEY = 'agent-profile-variables';

/** Stable prefix so any mutation can invalidate the whole scope with one call. */
const scope = (agentId: string) => [AGENT_PROFILE_VARIABLES_QUERY_KEY, agentId] as const;

// ── Reads ────────────────────────────────────────────────────────────────

/** List of one agent's profile variables. Backend returns a small set (no
 * pagination); the caller filters / sorts client-side. Enabled only when
 * `agentId` is truthy so create-mode pages don't fire a `null` request. */
export function useAgentProfileVariables(agentId: string | null | undefined) {
  return useQuery({
    queryKey: [...scope(agentId ?? ''), 'list'],
    queryFn: async (): Promise<AgentProfileVariable[]> => {
      const res = await listAgentProfileVariables(agentId as string);
      return res.items;
    },
    enabled: !!agentId,
    // Snappy invalidation so a mutation → refetch feels instant while the
    // user is editing variables in the Profile tab.
    staleTime: 0,
  });
}

// ── Shared invalidator ───────────────────────────────────────────────────

export function useInvalidateAgentProfileVariables(agentId: string) {
  const qc = useQueryClient();
  return () => qc.invalidateQueries({ queryKey: scope(agentId) });
}

// ── Mutations ────────────────────────────────────────────────────────────

export function useCreateAgentProfileVariable(agentId: string) {
  const invalidate = useInvalidateAgentProfileVariables(agentId);
  return useMutation({
    mutationFn: (input: ProfileVariableInput) => createAgentProfileVariable(agentId, input),
    onSuccess: invalidate,
  });
}

export function useUpdateAgentProfileVariable(agentId: string) {
  const invalidate = useInvalidateAgentProfileVariables(agentId);
  return useMutation({
    mutationFn: (args: { variableId: string; patch: ProfileVariablePatch }) =>
      updateAgentProfileVariable(agentId, args.variableId, args.patch),
    onSuccess: invalidate,
  });
}

export function useDeleteAgentProfileVariable(agentId: string) {
  const invalidate = useInvalidateAgentProfileVariables(agentId);
  return useMutation({
    mutationFn: (variableId: string) => deleteAgentProfileVariable(agentId, variableId),
    onSuccess: invalidate,
  });
}
