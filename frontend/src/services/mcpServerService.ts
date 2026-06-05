import { listRequest } from '@/services/listHelpers';
import type { ListRequest } from '@/types/list';
import type { MCPServer, MCPServerUpsertPayload, MCPToolsResponse } from '@/types/mcp';
import axiosInstance from '@/utils/axios';

export const listMcpServers = (request: ListRequest = {}): Promise<MCPServer[]> =>
  listRequest<MCPServer>('/mcp-server/list', request);

export const getMcpServer = async (mcpServerId: string): Promise<MCPServer> => {
  const { data } = await axiosInstance.get<MCPServer>('/mcp-server/get_mcp_server', {
    params: { mcp_server_id: mcpServerId },
  });
  return data;
};

export const upsertMcpServer = async (payload: MCPServerUpsertPayload): Promise<MCPServer> => {
  const { data } = await axiosInstance.post<MCPServer>('/mcp-server/upsert_mcp_server', payload);
  return data;
};

export const deleteMcpServer = async (mcpServerId: string): Promise<void> => {
  await axiosInstance.delete('/mcp-server/delete_mcp_server', {
    params: { mcp_server_id: mcpServerId },
  });
};

export const discoverMcpTools = async (mcpServerId: string): Promise<MCPToolsResponse> => {
  const { data } = await axiosInstance.get<MCPToolsResponse>('/mcp-server/discover_tools', {
    params: { mcp_server_id: mcpServerId },
  });
  return data;
};
