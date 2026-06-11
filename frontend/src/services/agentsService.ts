import axiosInstance from '@/utils/axios';
import type {
  AgentDetail,
  AgentDropdownItem,
  AgentVersionSummary,
  CreateAgentPayload,
  ListAgentsParams,
  PaginatedAgents,
  UpdateAgentPayload,
} from '@/types/agent';

export const listAgents = async (params: ListAgentsParams = {}): Promise<PaginatedAgents> => {
  const res = await axiosInstance.post<PaginatedAgents>('/agent/list', params);
  return res.data;
};

export const getAllAgents = async (): Promise<AgentDropdownItem[]> => {
  const res = await axiosInstance.get<AgentDropdownItem[]>('/agent/get_all_agents');
  return Array.isArray(res.data) ? res.data : [];
};

/** Fetch an agent. When `configId` is passed, the agent is rendered against
 * that specific version instead of the live one. */
export const getAgent = async (agentId: string, configId?: string): Promise<AgentDetail> => {
  const res = await axiosInstance.get<AgentDetail>('/agent/get_agent', {
    params: { agent_id: agentId, ...(configId ? { config_id: configId } : {}) },
  });
  return res.data;
};

export const createAgent = async (payload: CreateAgentPayload): Promise<AgentDetail> => {
  const res = await axiosInstance.post<AgentDetail>('/agent/create_agent', payload);
  return res.data;
};

export const updateAgent = async (
  agentId: string,
  payload: UpdateAgentPayload,
): Promise<AgentDetail> => {
  const res = await axiosInstance.put<AgentDetail>('/agent/update_agent', payload, {
    params: { agent_id: agentId },
  });
  return res.data;
};

export const deleteAgent = async (agentId: string): Promise<void> => {
  await axiosInstance.delete('/agent/delete_agent', { params: { agent_id: agentId } });
};

// ─── versioning ────────────────────────────────────────────────────────────

export const listAgentVersions = async (agentId: string): Promise<AgentVersionSummary[]> => {
  const res = await axiosInstance.get<AgentVersionSummary[]>('/agent/list_versions', {
    params: { agent_id: agentId },
  });
  return Array.isArray(res.data) ? res.data : [];
};

/** Clone the live config, apply edits, persist as the next version, and make
 * it live. Body mirrors {@link UpdateAgentPayload} minus the top-level agent
 * attributes (name/description/agent_type/is_active). */
export const saveAgentAsNewVersion = async (
  agentId: string,
  payload: Pick<
    UpdateAgentPayload,
    'config' | 'tool_ids' | 'mcp_server_ids' | 'upload_ids' | 'phone_numbers'
  >,
): Promise<AgentDetail> => {
  const res = await axiosInstance.post<AgentDetail>('/agent/save_as_new_version', payload, {
    params: { agent_id: agentId },
  });
  return res.data;
};

export const switchActiveAgentVersion = async (
  agentId: string,
  configId: string,
): Promise<AgentDetail> => {
  const res = await axiosInstance.post<AgentDetail>(
    '/agent/switch_active_version',
    { config_id: configId },
    { params: { agent_id: agentId } },
  );
  return res.data;
};

export const deleteAgentVersion = async (agentId: string, configId: string): Promise<void> => {
  await axiosInstance.delete('/agent/delete_version', {
    params: { agent_id: agentId, config_id: configId },
  });
};
