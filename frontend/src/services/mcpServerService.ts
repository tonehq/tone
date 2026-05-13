import type { MCPServer, MCPServerUpsertPayload } from '@/types/mcp';
import axiosInstance from '@/utils/axios';

export const getAllMcpServers = async (): Promise<MCPServer[]> => {
  const res = await axiosInstance.get('/mcp-server/get_all_mcp_servers');
  const data = res.data;
  if (Array.isArray(data)) return data;
  if (data && Array.isArray(data.data)) return data.data;
  return [];
};

export const getMcpServer = async (mcpServerId: number): Promise<MCPServer> => {
  const { data } = await axiosInstance.get<MCPServer>('/mcp-server/get_mcp_server', {
    params: { mcp_server_id: mcpServerId },
  });
  return data;
};

export const upsertMcpServer = async (payload: MCPServerUpsertPayload): Promise<MCPServer> => {
  const { data } = await axiosInstance.post<MCPServer>('/mcp-server/upsert_mcp_server', payload);
  return data;
};

export const deleteMcpServer = async (mcpServerId: number): Promise<void> => {
  await axiosInstance.delete('/mcp-server/delete_mcp_server', {
    params: { mcp_server_id: mcpServerId },
  });
};
