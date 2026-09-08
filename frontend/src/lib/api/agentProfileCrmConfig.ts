import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import {
  getAgentProfileCrmConfig,
  upsertAgentProfileCrmConfig,
} from '@/services/agentProfileCrmConfigService';
import type {
  AgentProfileCrmConfig,
  AgentProfileCrmConfigInput,
} from '@/types/agentProfileCrmConfig';

export const AGENT_PROFILE_CRM_CONFIG_QUERY_KEY = 'agent-profile-crm-config';

const scope = (agentId: string) => [AGENT_PROFILE_CRM_CONFIG_QUERY_KEY, agentId] as const;

/** The agent's CRM lookup config (or `null` if unset). Enabled only when
 * `agentId` is truthy so create-mode pages don't fire a `null` request. */
export function useAgentProfileCrmConfig(agentId: string | null | undefined) {
  return useQuery({
    queryKey: [...scope(agentId ?? ''), 'detail'],
    queryFn: async (): Promise<AgentProfileCrmConfig | null> => {
      const res = await getAgentProfileCrmConfig(agentId as string);
      return res.config;
    },
    enabled: !!agentId,
    staleTime: 0,
  });
}

export function useUpsertAgentProfileCrmConfig(agentId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (input: AgentProfileCrmConfigInput) => upsertAgentProfileCrmConfig(agentId, input),
    onSuccess: () => qc.invalidateQueries({ queryKey: scope(agentId) }),
  });
}
