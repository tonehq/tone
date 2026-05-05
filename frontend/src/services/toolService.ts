import type { Tool, ToolAttachPayload, ToolCreatePayload, ToolUpdatePayload } from '@/types/tool';
import axiosInstance from '@/utils/axios';

export const createTool = async (payload: ToolCreatePayload): Promise<Tool> => {
  const { data } = await axiosInstance.post<Tool>('/tool/create_tool', payload);
  return data;
};

export const getAllTools = async (): Promise<Tool[]> => {
  const { data } = await axiosInstance.get<Tool[]>('/tool/get_all_tools');
  return Array.isArray(data) ? data : [];
};

export const getTool = async (toolId: number): Promise<Tool> => {
  const { data } = await axiosInstance.get<Tool>('/tool/get_tool', {
    params: { tool_id: toolId },
  });
  return data;
};

export const updateTool = async (toolId: number, payload: ToolUpdatePayload): Promise<Tool> => {
  const { data } = await axiosInstance.put<Tool>('/tool/update_tool', payload, {
    params: { tool_id: toolId },
  });
  return data;
};

export const deleteTool = async (toolId: number): Promise<void> => {
  await axiosInstance.delete('/tool/delete_tool', { params: { tool_id: toolId } });
};

export const attachToolToAgents = async (payload: ToolAttachPayload): Promise<void> => {
  await axiosInstance.post('/tool/attach_tool_to_agents', payload);
};

export const detachToolFromAgents = async (payload: ToolAttachPayload): Promise<void> => {
  await axiosInstance.delete('/tool/detach_tool_from_agents', { data: payload });
};

export const getToolsByAgent = async (agentId: number): Promise<Tool[]> => {
  const { data } = await axiosInstance.get<Tool[]>('/tool/get_tools_by_agent', {
    params: { agent_id: agentId },
  });
  return Array.isArray(data) ? data : [];
};
