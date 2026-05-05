export interface Tool {
  id: number;
  uuid: string;
  name: string;
  description: string;
  parameters: ToolParametersSchema;
  url: string;
  method: string;
  auth_type: ToolAuthType;
  auth_config: Record<string, string> | null;
  meta_data: Record<string, unknown> | null;
  is_active: boolean;
  created_at: number;
  updated_at: number;
}

export type ToolAuthType = 'none' | 'api_key' | 'bearer' | 'basic';

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

export interface ToolCreatePayload {
  name: string;
  description: string;
  parameters?: ToolParametersSchema;
  url: string;
  method?: string;
  auth_type?: ToolAuthType;
  auth_config?: Record<string, string> | null;
  meta_data?: Record<string, unknown> | null;
  is_active?: boolean;
}

export interface ToolUpdatePayload {
  name?: string;
  description?: string;
  parameters?: ToolParametersSchema;
  url?: string;
  method?: string;
  auth_type?: ToolAuthType;
  auth_config?: Record<string, string> | null;
  meta_data?: Record<string, unknown> | null;
  is_active?: boolean;
}

export interface ToolAttachPayload {
  tool_id: number;
  agent_ids: number[];
}

export interface ToolsState {
  tools: Tool[];
  loading: boolean;
}
