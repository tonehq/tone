export type MCPTransportType = 'sse' | 'streamable_http';

export interface MCPServer {
  id: string;
  name: string;
  description: string | null;
  server_url: string;
  endpoint?: string | null;
  icon?: string | null;
  transport_type: MCPTransportType;
  auth_config: Record<string, string> | null;
  meta_data: Record<string, unknown> | null;
  oauth_connection_id?: string | null;
  /** Catalog entry this server belongs to. Optional. */
  app_integration_id?: string | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface MCPServerUpsertPayload {
  id?: string;
  name?: string;
  description?: string;
  server_url?: string;
  endpoint?: string | null;
  icon?: string | null;
  transport_type?: MCPTransportType;
  auth_config?: Record<string, string> | null;
  meta_data?: Record<string, unknown> | null;
  oauth_connection_id?: string | null;
  app_integration_id?: string | null;
  is_active?: boolean;
}

export interface MCPServersState {
  servers: MCPServer[];
  loading: boolean;
}

export interface MCPTool {
  name: string;
  description: string | null;
  parameters: Record<string, unknown>;
  required: string[];
}

export interface MCPToolsResponse {
  server_name: string;
  server_url: string;
  transport_type: MCPTransportType;
  tools: MCPTool[];
  tool_count: number;
}
