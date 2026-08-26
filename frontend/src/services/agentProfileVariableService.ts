import axiosInstance from '@/utils/axios';

import type {
  AgentProfileVariable,
  ListProfileVariablesResponse,
  ProfileVariableInput,
  ProfileVariablePatch,
} from '@/types/agentProfileVariable';

/**
 * HTTP layer for per-agent profile variables. All CRUD goes through here so
 * components never call axios directly — matches `src/services/*` conventions.
 * Mirrors the router paths under `/agents/{agent_id}/profile-variables`.
 */

const base = (agentId: string) => `/agents/${agentId}/profile-variables`;

export const listAgentProfileVariables = async (
  agentId: string,
): Promise<ListProfileVariablesResponse> => {
  const res = await axiosInstance.get<ListProfileVariablesResponse>(base(agentId));
  return res.data;
};

export const createAgentProfileVariable = async (
  agentId: string,
  input: ProfileVariableInput,
): Promise<AgentProfileVariable> => {
  const res = await axiosInstance.post<AgentProfileVariable>(base(agentId), input);
  return res.data;
};

export const updateAgentProfileVariable = async (
  agentId: string,
  variableId: string,
  patch: ProfileVariablePatch,
): Promise<AgentProfileVariable> => {
  const res = await axiosInstance.put<AgentProfileVariable>(
    `${base(agentId)}/${variableId}`,
    patch,
  );
  return res.data;
};

export const deleteAgentProfileVariable = async (
  agentId: string,
  variableId: string,
): Promise<{ deleted: string }> => {
  const res = await axiosInstance.delete<{ deleted: string }>(`${base(agentId)}/${variableId}`);
  return res.data;
};
