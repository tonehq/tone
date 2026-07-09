import { atom } from 'jotai';

import {
  cloneAgent,
  createAgent,
  createAgentFromTemplate,
  createAgentVersion,
  deleteAgent,
  deleteAgentVersion,
  getAgent,
  getAllAgents,
  listAgentTemplates,
  listAgentVersions,
  listAgents,
  switchActiveAgentVersion,
  updateAgent,
  updateAgentVersion,
} from '@/services/agentsService';
import type {
  AgentDetail,
  AgentDropdownItem,
  AgentTemplateSummary,
  AgentVersionSummary,
  AgentsState,
  CreateAgentPayload,
  ListAgentsParams,
  PaginatedAgentsState,
  UpdateAgentPayload,
} from '@/types/agent';

// Same in-flight-token pattern as ServicesAtom — drops responses that aren't
// the most recent dispatch so rapid filter/page changes don't flash stale data.
function makeLatestTracker() {
  let latest = 0;
  return () => {
    latest += 1;
    const id = latest;
    return () => id === latest;
  };
}

// ─── dropdown list (id + name only) ────────────────────────────────────────

const agentsAtom = atom<AgentsState>({ agentList: [] });

export const fetchAllAgentsAtom = atom(null, async (_get, set): Promise<AgentDropdownItem[]> => {
  const rows = await getAllAgents();
  set(agentsAtom, { agentList: rows });
  return rows;
});

// ─── paginated listing (table) ─────────────────────────────────────────────

export const paginatedAgentsAtom = atom<PaginatedAgentsState>({
  items: [],
  total: 0,
  page: 1,
  pageSize: 10,
  loading: false,
});

const trackPaginatedAgents = makeLatestTracker();

export const fetchPaginatedAgentList = atom(null, async (_get, set, params: ListAgentsParams) => {
  const isLatest = trackPaginatedAgents();
  set(paginatedAgentsAtom, (prev) => ({ ...prev, loading: true }));
  try {
    const data = await listAgents(params);
    if (!isLatest()) return;
    set(paginatedAgentsAtom, {
      items: data.items,
      total: data.total,
      page: data.page,
      pageSize: data.page_size,
      loading: false,
    });
  } catch (error) {
    if (!isLatest()) return;
    set(paginatedAgentsAtom, (prev) => ({ ...prev, loading: false }));
    throw error;
  }
});

// ─── single-agent fetch (used by the edit page) ────────────────────────────

export const fetchAgentAtom = atom(
  null,
  async (
    _get,
    _set,
    args: string | { agentId: string; configId?: string; version?: number },
  ): Promise<AgentDetail> => {
    if (typeof args === 'string') return getAgent(args);
    return getAgent(args.agentId, args.configId, args.version);
  },
);

// ─── create / update / delete ──────────────────────────────────────────────

export const createAgentAtom = atom(
  null,
  async (_get, _set, payload: CreateAgentPayload): Promise<AgentDetail> => createAgent(payload),
);

export const updateAgentAtom = atom(
  null,
  async (_get, _set, args: { id: string; values: UpdateAgentPayload }): Promise<AgentDetail> =>
    updateAgent(args.id, args.values),
);

export const deleteAgentAtom = atom(null, async (_get, _set, agentId: string) => {
  await deleteAgent(agentId);
});

export const cloneAgentAtom = atom(
  null,
  async (_get, _set, args: { agentId: string; name?: string }): Promise<AgentDetail> =>
    cloneAgent(args.agentId, args.name),
);

export const listAgentTemplatesAtom = atom(
  null,
  async (_get, _set): Promise<AgentTemplateSummary[]> => listAgentTemplates(),
);

export const createAgentFromTemplateAtom = atom(
  null,
  async (_get, _set, args: { sourceConfigId: string; name?: string }): Promise<AgentDetail> =>
    createAgentFromTemplate(args.sourceConfigId, args.name),
);

// ─── versioning ────────────────────────────────────────────────────────────

export const listAgentVersionsAtom = atom(
  null,
  async (_get, _set, agentId: string): Promise<AgentVersionSummary[]> => listAgentVersions(agentId),
);

export const createAgentVersionAtom = atom(
  null,
  async (
    _get,
    _set,
    args: { agentId: string; values: Parameters<typeof createAgentVersion>[1] },
  ): Promise<AgentDetail> => createAgentVersion(args.agentId, args.values),
);

export const updateAgentVersionAtom = atom(
  null,
  async (
    _get,
    _set,
    args: { agentId: string; values: Parameters<typeof updateAgentVersion>[1] },
  ): Promise<AgentDetail> => updateAgentVersion(args.agentId, args.values),
);

export const switchActiveAgentVersionAtom = atom(
  null,
  async (_get, _set, args: { agentId: string; configId: string }): Promise<AgentDetail> =>
    switchActiveAgentVersion(args.agentId, args.configId),
);

export const deleteAgentVersionAtom = atom(
  null,
  async (_get, _set, args: { agentId: string; configId: string }) =>
    deleteAgentVersion(args.agentId, args.configId),
);

export default agentsAtom;
