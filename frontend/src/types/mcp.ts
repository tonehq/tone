export type MCPTransportType = 'sse' | 'streamable_http';

export interface MCPServer {
  id: string;
  name: string;
  description: string | null;
  server_url: string;
  transport_type: MCPTransportType;
  auth_config: Record<string, string> | null;
  meta_data: Record<string, unknown> | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface MCPServerUpsertPayload {
  id?: string;
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
