import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import {
  deleteAgentProfileWebhook,
  getAgentProfileWebhook,
  testAgentProfileWebhook,
  upsertAgentProfileWebhook,
} from '@/services/agentProfileWebhookService';
import type {
  AgentProfileWebhook,
  ProfileWebhookUpsertInput,
  WebhookTestRequest,
} from '@/types/agentProfileWebhook';

export const AGENT_PROFILE_WEBHOOK_QUERY_KEY = 'agent-profile-webhook';

const scope = (agentId: string) => [AGENT_PROFILE_WEBHOOK_QUERY_KEY, agentId] as const;

// ── Reads ────────────────────────────────────────────────────────────────

/** The agent's webhook config (or null). Enabled only when `agentId` is truthy
 * so create-mode pages don't fire a `null` request. */
export function useAgentProfileWebhook(agentId: string | null | undefined) {
  return useQuery({
    queryKey: [...scope(agentId ?? ''), 'config'],
    queryFn: (): Promise<AgentProfileWebhook | null> => getAgentProfileWebhook(agentId as string),
    enabled: !!agentId,
    staleTime: 0,
  });
}

// ── Shared invalidator ───────────────────────────────────────────────────

export function useInvalidateAgentProfileWebhook(agentId: string) {
  const qc = useQueryClient();
  return () => qc.invalidateQueries({ queryKey: scope(agentId) });
}

// ── Mutations ────────────────────────────────────────────────────────────

export function useUpsertAgentProfileWebhook(agentId: string) {
  const invalidate = useInvalidateAgentProfileWebhook(agentId);
  return useMutation({
    mutationFn: (input: ProfileWebhookUpsertInput) => upsertAgentProfileWebhook(agentId, input),
    onSuccess: invalidate,
  });
}

export function useDeleteAgentProfileWebhook(agentId: string) {
  const invalidate = useInvalidateAgentProfileWebhook(agentId);
  return useMutation({
    mutationFn: () => deleteAgentProfileWebhook(agentId),
    onSuccess: invalidate,
  });
}

/** Test the SAVED config with a sample phone. No cache write — the result is
 * held in component state. */
export function useTestAgentProfileWebhook(agentId: string) {
  return useMutation({
    mutationFn: (body: WebhookTestRequest) => testAgentProfileWebhook(agentId, body),
  });
}
