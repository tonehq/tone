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
}

export interface ToolAttachPayload {
  tool_id: string;
  agent_ids: string[];
}

export interface ToolsState {
  tools: Tool[];
  loading: boolean;
}
