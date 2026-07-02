// Mirrors the backend contract in:
//   core/services/audit_actions.py  — action names and resource types
//   core/api/v1/audit_logs.py       — list request/response shape
//   core/services/audit_log_service.py — row serialisation
//
// Kept in one file so a backend rename ripples to exactly one place.

export type AuditLogResourceType =
  | 'tool'
  | 'mcp_server'
  | 'knowledge_base'
  | 'phone_number'
  | 'web_channel'
  | 'agent_config';

// Values match AgentAuditAction constants on the backend.
export type AuditLogAction =
  | 'agent.created'
  | 'agent.updated'
  | 'agent.deleted'
  | 'agent.config.updated'
  | 'agent.version.created'
  | 'agent.version.updated'
  | 'agent.version.switched'
  | 'agent.version.deleted'
  | 'agent.tool.attached'
  | 'agent.tool.detached'
  | 'agent.mcp.attached'
  | 'agent.mcp.detached'
  | 'agent.knowledge_base.attached'
  | 'agent.knowledge_base.detached'
  | 'agent.phone_number.attached'
  | 'agent.phone_number.detached'
  | 'agent.web_channel.attached'
  | 'agent.web_channel.detached';

// The backend builds `changes` from before + after + extra.
// Secret-shaped keys are masked to "***" server-side before persist.
export interface AuditLogChanges {
  before?: Record<string, unknown> | null;
  after?: Record<string, unknown> | null;
  extra?: Record<string, unknown> | null;
}

export interface AuditLogItem {
  id: string;
  created_at: string | null;
  actor_user_id: string | null;
  action: AuditLogAction;
  agent_id: string | null;
  agent_config_id: string | null;
  target_resource_type: AuditLogResourceType | null;
  target_resource_id: string | null;
  changes: AuditLogChanges | null;
  request_id: string | null;
  ip_address: string | null;
  user_agent: string | null;
}

export interface ListAuditLogsRequest {
  agent_id: string;
  actions?: AuditLogAction[];
  actor_user_id?: string;
  start_date_time?: string;
  end_date_time?: string;
  page_no?: number;
  page_size?: number;
}

export interface ListAuditLogsResponse {
  items: AuditLogItem[];
  total: number;
  page_no: number;
  page_size: number;
}
