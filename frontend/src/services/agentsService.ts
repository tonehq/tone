import axiosInstance from '@/utils/axios';
import type {
  AgentDetail,
  AgentDropdownItem,
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

export const getAgent = async (agentId: string): Promise<AgentDetail> => {
  const res = await axiosInstance.get<AgentDetail>('/agent/get_agent', {
    params: { agent_id: agentId },
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
