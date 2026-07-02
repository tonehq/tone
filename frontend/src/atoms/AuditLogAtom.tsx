import { atom } from 'jotai';
import { loadable } from 'jotai/utils';

import { listAuditLogs } from '@/services/auditLogService';
import type {
  AuditLogAction,
  AuditLogResourceType,
  ListAuditLogsResponse,
} from '@/types/settings/auditLog';

const DEFAULT_PAGE_SIZE = 20;

export interface AuditLogListParams {
  agent_id: string | null;
  // Filter by broad action-verb group (create, update, delete, attach, version).
  // Maps to a concrete list<AuditLogAction> before hitting the backend.
  action_group: AuditLogActionGroup;
  // Filter by resource type — applied client-side against the current page
  // because the backend doesn't accept target_resource_type as a filter.
  resource_type: AuditLogResourceType | 'all';
  page: number;
  page_size: number;
}

// Grouping matches the reference UI's "All Actions" dropdown: users pick verbs,
// not the 18-item enum. Keeping the mapping here (not on the backend) means the
// UI can regroup without touching Python.
export type AuditLogActionGroup = 'all' | 'create' | 'update' | 'delete' | 'attach' | 'version';

export const AUDIT_ACTION_GROUPS: {
  value: AuditLogActionGroup;
  label: string;
  actions: AuditLogAction[];
}[] = [
  { value: 'all', label: 'All Actions', actions: [] },
  {
    value: 'create',
    label: 'Create',
    actions: ['agent.created', 'agent.version.created'],
  },
  {
    value: 'update',
    label: 'Update',
    actions: ['agent.updated', 'agent.config.updated', 'agent.version.updated'],
  },
  {
    value: 'delete',
    label: 'Delete',
    actions: ['agent.deleted', 'agent.version.deleted'],
  },
  {
    value: 'attach',
    label: 'Attach / Detach',
    actions: [
      'agent.tool.attached',
      'agent.tool.detached',
      'agent.mcp.attached',
      'agent.mcp.detached',
      'agent.knowledge_base.attached',
      'agent.knowledge_base.detached',
      'agent.phone_number.attached',
      'agent.phone_number.detached',
      'agent.web_channel.attached',
      'agent.web_channel.detached',
    ],
  },
  {
    value: 'version',
    label: 'Versions',
    actions: [
      'agent.version.created',
      'agent.version.updated',
      'agent.version.switched',
      'agent.version.deleted',
    ],
  },
];

// Backend actions bucketed by verb-group. Single source consumed by both the
// filter dropdown and the stats hook so a new action can't be added to one
// place and forgotten in the other.
export const ACTIONS_BY_GROUP: Record<
  Exclude<AuditLogActionGroup, 'all'>,
  AuditLogAction[]
> = AUDIT_ACTION_GROUPS.filter((g) => g.value !== 'all').reduce(
  (acc, g) => {
    acc[g.value as Exclude<AuditLogActionGroup, 'all'>] = g.actions;
    return acc;
  },
  {} as Record<Exclude<AuditLogActionGroup, 'all'>, AuditLogAction[]>,
);

// The Resources dropdown maps 1:1 to backend AuditLogResourceType plus 'all'.
export const AUDIT_RESOURCE_OPTIONS: { value: AuditLogResourceType | 'all'; label: string }[] = [
  { value: 'all', label: 'All Resources' },
  { value: 'tool', label: 'Tools' },
  { value: 'mcp_server', label: 'MCP Servers' },
  { value: 'knowledge_base', label: 'Knowledge Bases' },
  { value: 'phone_number', label: 'Phone Numbers' },
  { value: 'web_channel', label: 'Web Channels' },
  { value: 'agent_config', label: 'Agent Config' },
];

const DEFAULT_PARAMS: AuditLogListParams = {
  agent_id: null,
  action_group: 'all',
  resource_type: 'all',
  page: 1,
  page_size: DEFAULT_PAGE_SIZE,
};

export const auditLogParamsAtom = atom<AuditLogListParams>({ ...DEFAULT_PARAMS });

const auditLogRefreshAtom = atom(0);

// Empty payload returned when no agent is selected — the backend requires
// agent_id, so we short-circuit rather than fire a guaranteed-400.
const EMPTY_RESPONSE: ListAuditLogsResponse = {
  items: [],
  total: 0,
  page_no: 1,
  page_size: DEFAULT_PAGE_SIZE,
};

const auditLogPagedAtom = atom<Promise<ListAuditLogsResponse>>(async (get) => {
  get(auditLogRefreshAtom);
  const params = get(auditLogParamsAtom);
  if (!params.agent_id) return EMPTY_RESPONSE;

  const group = AUDIT_ACTION_GROUPS.find((g) => g.value === params.action_group);
  const actions = group?.actions.length ? group.actions : undefined;

  return listAuditLogs({
    agent_id: params.agent_id,
    actions,
    page_no: params.page,
    page_size: params.page_size,
  });
});

export const loadableAuditLogPagedAtom = loadable(auditLogPagedAtom);

// Any filter/search change resets to page 1 — otherwise the user can be
// stranded on page 4 with an empty result set.
export const setAuditLogParamsAtom = atom(null, (get, set, patch: Partial<AuditLogListParams>) => {
  const current = get(auditLogParamsAtom);
  const resetsPage =
    'action_group' in patch ||
    'resource_type' in patch ||
    'agent_id' in patch ||
    'page_size' in patch;
  set(auditLogParamsAtom, {
    ...current,
    ...patch,
    page: resetsPage ? 1 : (patch.page ?? current.page),
  });
});

export const refetchAuditLogAtom = atom(null, (_get, set) => {
  set(auditLogRefreshAtom, (c) => c + 1);
});
