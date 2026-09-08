/**
 * Per-agent CRM lookup settings used to fill empty profile variables at call
 * start. Backend model: `core/models/agent_profile_crm_config.py`.
 */
export interface AgentProfileCrmConfig {
  id: string;
  organization_id: string;
  agent_id: string;
  mcp_server_id: string | null;
  lookup_tool_name: string | null;
  phone_argument: string | null;
  is_enabled: boolean;
  created_at: string | null;
  updated_at: string | null;
}

/** Body for PUT /agents/{id}/profile-crm-config. */
export interface AgentProfileCrmConfigInput {
  mcp_server_id?: string | null;
  lookup_tool_name?: string | null;
  phone_argument?: string | null;
  is_enabled: boolean;
}

export interface GetProfileCrmConfigResponse {
  config: AgentProfileCrmConfig | null;
}
