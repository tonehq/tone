import type { AttachedAgentRef } from '@/types/agent';
import type { Tool, ToolAttachPayload, ToolUpsertPayload } from '@/types/tool';
import axiosInstance from '@/utils/axios';

export const upsertTool = async (payload: ToolUpsertPayload): Promise<Tool> => {
  const { data } = await axiosInstance.post<Tool>('/tool/upsert_tool', payload);
  return data;
};

export const getAllTools = async (): Promise<Tool[]> => {
  const res = await axiosInstance.get('/tool/get_all_tools');
  const data = res.data;
  if (Array.isArray(data)) return data;
  if (data && Array.isArray(data.data)) return data.data;
  return [];
};

export const getTool = async (toolId: string): Promise<Tool> => {
  const { data } = await axiosInstance.get<Tool>('/tool/get_tool', {
    params: { tool_id: toolId },
  });
  return data;
};

export const deleteTool = async (toolId: string): Promise<void> => {
  await axiosInstance.delete('/tool/delete_tool', { params: { tool_id: toolId } });
};

/** Agents whose published version carries this tool — feeds the edit form's
 * Agents section (counterpart of upsert_tool's `agent_ids`). */
export const getAgentsByTool = async (toolId: string): Promise<AttachedAgentRef[]> => {
  const { data } = await axiosInstance.get<AttachedAgentRef[]>('/tool/get_agents_by_tool', {
    params: { tool_id: toolId },
  });
  return Array.isArray(data) ? data : [];
};

export const attachToolToAgents = async (payload: ToolAttachPayload): Promise<void> => {
  await axiosInstance.post('/tool/attach_tool_to_agents', payload);
};

export const detachToolFromAgents = async (payload: ToolAttachPayload): Promise<void> => {
  await axiosInstance.delete('/tool/detach_tool_from_agents', { data: payload });
};

export const getTemplateTools = async (): Promise<Tool[]> => {
  const res = await axiosInstance.get('/tool/get_template_tools');
  const data = res.data;
  if (Array.isArray(data)) return data;
  if (data && Array.isArray(data.data)) return data.data;
  return [];
};

export const getToolsByAgent = async (agentId: string): Promise<Tool[]> => {
  const { data } = await axiosInstance.get<Tool[]>('/tool/get_tools_by_agent', {
    params: { agent_id: agentId },
  });
  return Array.isArray(data) ? data : [];
};
