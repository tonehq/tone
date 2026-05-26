import { deleteAgent, getAgents, listAgents } from '@/services/agentsService';
import type { AgentsState, ApiAgent, ListAgentsParams, PaginatedAgentsState } from '@/types/agent';
import { atom } from 'jotai';

const agentsAtom = atom<AgentsState>({
  agentList: [],
});

export const fetchAgentList = atom(null, async (_get, set) => {
  const res = await getAgents();
  if (Array.isArray(res)) {
    set(agentsAtom, (prev) => ({
      ...prev,
      agentList: res as ApiAgent[],
    }));
  } else if (res && Array.isArray(res.data)) {
    set(agentsAtom, (prev) => ({
      ...prev,
      agentList: res.data as ApiAgent[],
    }));
  } else {
    set(agentsAtom, (prev) => ({ ...prev, agentList: [] }));
  }
});

export const deleteAgentAtom = atom(null, async (_get, set, agentId: number) => {
  await deleteAgent(agentId);
  const res = await getAgents();
  if (Array.isArray(res)) {
    set(agentsAtom, (prev) => ({ ...prev, agentList: res as ApiAgent[] }));
  } else if (res && Array.isArray(res.data)) {
    set(agentsAtom, (prev) => ({ ...prev, agentList: res.data as ApiAgent[] }));
  } else {
    set(agentsAtom, (prev) => ({ ...prev, agentList: [] }));
  }
});

export const paginatedAgentsAtom = atom<PaginatedAgentsState>({
  items: [],
  total: 0,
  page: 1,
  pageSize: 10,
  loading: false,
});

export const fetchPaginatedAgentList = atom(null, async (_get, set, params: ListAgentsParams) => {
  set(paginatedAgentsAtom, (prev) => ({ ...prev, loading: true }));
  try {
    const data = await listAgents(params);
    set(paginatedAgentsAtom, {
      items: data.items,
      total: data.total,
      page: data.page,
      pageSize: data.page_size,
      loading: false,
    });
  } catch (error) {
    set(paginatedAgentsAtom, (prev) => ({ ...prev, loading: false }));
    throw error;
  }
});

export default agentsAtom;
