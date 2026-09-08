import axiosInstance from '@/utils/axios';

import type {
  AgentProfileCrmConfigInput,
  GetProfileCrmConfigResponse,
} from '@/types/agentProfileCrmConfig';

/**
 * HTTP layer for the per-agent CRM lookup config. Mirrors the router paths
 * under `/agents/{agent_id}/profile-crm-config`; components never call axios
 * directly.
 */

const base = (agentId: string) => `/agents/${agentId}/profile-crm-config`;

export const getAgentProfileCrmConfig = async (
  agentId: string,
): Promise<GetProfileCrmConfigResponse> => {
  const res = await axiosInstance.get<GetProfileCrmConfigResponse>(base(agentId));
  return res.data;
};

export const upsertAgentProfileCrmConfig = async (
  agentId: string,
  input: AgentProfileCrmConfigInput,
): Promise<GetProfileCrmConfigResponse> => {
  const res = await axiosInstance.put<GetProfileCrmConfigResponse>(base(agentId), input);
  return res.data;
};
