import type { AuditLogItem, AuditLogAction, AuditLogResourceType } from '@/types/settings/auditLog';

// Every action badge shares one neutral tone — colour is not carrying
// meaning here (the label already names the action), so a single muted
// class keeps the table readable and consistent with the rest of the app.
export const ACTION_BADGE_CLASS = 'font-mono text-[11px] bg-muted text-muted-foreground';

// Short, human-friendly label per action. Kept as a lookup so the table
// cells, filter dropdown, and drawer header all read from the same source.
export const ACTION_LABEL: Record<AuditLogAction, string> = {
  'agent.created': 'agent.created',
  'agent.updated': 'agent.updated',
  'agent.deleted': 'agent.deleted',
  'agent.config.updated': 'config.updated',
  'agent.version.created': 'version.created',
  'agent.version.updated': 'version.updated',
  'agent.version.switched': 'version.switched',
  'agent.version.deleted': 'version.deleted',
  'agent.tool.attached': 'tool.attached',
  'agent.tool.detached': 'tool.detached',
  'agent.mcp.attached': 'mcp.attached',
  'agent.mcp.detached': 'mcp.detached',
  'agent.knowledge_base.attached': 'knowledge_base.attached',
  'agent.knowledge_base.detached': 'knowledge_base.detached',
  'agent.phone_number.attached': 'phone_number.attached',
  'agent.phone_number.detached': 'phone_number.detached',
  'agent.web_channel.attached': 'web_channel.attached',
  'agent.web_channel.detached': 'web_channel.detached',
};

// Human labels for the target-resource-type column and drawer header.
export const RESOURCE_LABEL: Record<AuditLogResourceType, string> = {
  tool: 'Tool',
  mcp_server: 'MCP Server',
  knowledge_base: 'Knowledge Base',
  phone_number: 'Phone Number',
  web_channel: 'Web Channel',
  agent_config: 'Agent Config',
};

// Short ID form used when we cannot resolve a full name (deleted resource,
// lookup still loading, etc.). Mirrors the reference UI's UUID display.
export function shortId(id: string | null | undefined, len = 24): string {
  if (!id) return '—';
  return id.length > len ? id.slice(0, len) : id;
}

// Actor resolution — null actor means "written by the system" (background
// jobs, migrations). Falls back to a short UUID when the user has been
// removed from the org since the event fired.
export function resolveActorName(
  userId: string | null,
  users: Map<string, string>,
): { name: string; isSystem: boolean } {
  if (!userId) return { name: 'System', isSystem: true };
  return { name: users.get(userId) || shortId(userId, 8), isSystem: false };
}

// Target resolution — looks the id up in the matching bucket, falls back to
// a short UUID if the resource has been hard-deleted (audit is append-only).
// Returns null when the event has no target (e.g. `agent.updated`).
export function resolveTargetName(
  row: AuditLogItem,
  targets: Record<AuditLogResourceType, Map<string, string>>,
): string | null {
  if (!row.target_resource_id) return null;
  const bucket = row.target_resource_type ? targets[row.target_resource_type] : null;
  return bucket?.get(row.target_resource_id) || shortId(row.target_resource_id, 12);
}
