export type MCPTransportType = 'sse' | 'streamable_http';

/** Explicit auth-method column. Mirrors ``tools.auth_type`` in the backend so
 * both entities share the same set. See ``core/utils/auth_types.py``. */
export type MCPAuthType = 'none' | 'api_key' | 'bearer' | 'basic' | 'oauth';

export interface MCPServer {
  id: string;
  name: string;
  description: string | null;
  server_url: string;
  endpoint?: string | null;
  icon?: string | null;
  transport_type: MCPTransportType;
  auth_type: MCPAuthType | null;
  auth_config: Record<string, string> | null;
  meta_data: Record<string, unknown> | null;
  oauth_connection_id?: string | null;
  /** Populated by list responses; ``null`` when the server has no OAuth link
   * OR when the response path didn't hydrate the connection summary. Shape
   * mirrors ``Tool.oauth_connection`` so both pages share one badge helper. */
  oauth_connection?: {
    id: string;
    provider_slug: string;
    token_expiry: number | null;
  } | null;
  /** Catalog entry this server belongs to. Optional. */
  app_integration_id?: string | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
  /** Present on upsert responses when an ``agent_ids`` sync skipped something
   * (unpublished agent, missing scopes, …). The server itself is still saved. */
  attachment_warnings?: string[];
  /** Present on upsert responses when ``agent_ids`` was sent — what the sync
   * actually changed on agents' published versions. */
  attachment_summary?: { attached: number; detached: number };
}

export interface MCPServerUpsertPayload {
  id?: string;
  name?: string;
  description?: string;
  server_url?: string;
  endpoint?: string | null;
  icon?: string | null;
  transport_type?: MCPTransportType;
  auth_type?: MCPAuthType;
  auth_config?: Record<string, string> | null;
  meta_data?: Record<string, unknown> | null;
  oauth_connection_id?: string | null;
  app_integration_id?: string | null;
  is_active?: boolean;
  /** Full sync of published-version agent attachments. Absent = attachments
   * untouched; present = this list becomes the exact set of agents whose live
   * version reaches the server. */
  agent_ids?: string[];
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
