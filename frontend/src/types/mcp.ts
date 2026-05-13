export type MCPTransportType = 'sse' | 'streamable_http';

export interface MCPServer {
  id: number;
  uuid: string;
  name: string;
  description: string | null;
  server_url: string;
  transport_type: MCPTransportType;
  auth_config: Record<string, string> | null;
  meta_data: Record<string, unknown> | null;
  is_active: boolean;
  created_at: number;
  updated_at: number;
}

export interface MCPServerUpsertPayload {
  id?: number;
  name?: string;
  description?: string;
  server_url?: string;
  transport_type?: MCPTransportType;
  auth_config?: Record<string, string> | null;
  meta_data?: Record<string, unknown> | null;
  is_active?: boolean;
}

export interface MCPServersState {
  servers: MCPServer[];
  loading: boolean;
}
