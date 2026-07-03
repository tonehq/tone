export type ToolType = 'custom' | 'send_sms' | 'google_calendar' | 'google_sheets' | 'mcp';

export interface Tool {
  id: string;
  uuid?: string;
  name: string;
  description: string;
  tool_type: ToolType;
  parameters: ToolParametersSchema;
  url: string | null;
  method: string | null;
  auth_type: ToolAuthType | null;
  auth_config: Record<string, string> | null;
  meta_data: Record<string, unknown> | null;
  oauth_connection_id: string | null;
  app_integration_id?: string | null;
  mcp_server_id?: string | null;
  is_active: boolean;
  is_template?: boolean;
  created_at: string;
  updated_at: string;
  /** Present on upsert responses when an ``agent_ids`` sync skipped something
   * (unpublished agent, missing scopes, …). The tool itself is still saved. */
  attachment_warnings?: string[];
  /** Present on upsert responses when ``agent_ids`` was sent — what the sync
   * actually changed on agents' published versions. */
  attachment_summary?: { attached: number; detached: number };
}

export type ToolAuthType = 'none' | 'api_key' | 'bearer' | 'basic' | 'oauth';

export type ToolHttpMethod = 'GET' | 'POST' | 'PUT' | 'DELETE' | 'PATCH';

export type ToolParameterType = 'string' | 'number' | 'integer' | 'boolean' | 'array';

export interface ToolParameterProperty {
  type: ToolParameterType;
  description: string;
  enum?: string[];
}

export interface ToolParametersSchema {
  type?: 'object';
  properties?: Record<string, ToolParameterProperty>;
  required?: string[];
}

export interface ToolUpsertPayload {
  id?: string;
  name?: string;
  description?: string;
  tool_type?: ToolType;
  parameters?: ToolParametersSchema;
  url?: string;
  method?: string;
  auth_type?: ToolAuthType;
  auth_config?: Record<string, string> | null;
  meta_data?: Record<string, unknown> | null;
  oauth_connection_id?: string | null;
  app_integration_id?: string | null;
  is_active?: boolean;
  /** Full sync of published-version agent attachments. Absent = attachments
   * untouched; present = this list becomes the exact set of agents whose live
   * version carries the tool. */
  agent_ids?: string[];
}

export interface ToolAttachPayload {
  tool_id: string;
  agent_ids: string[];
}

export interface ToolsState {
  tools: Tool[];
  loading: boolean;
}
