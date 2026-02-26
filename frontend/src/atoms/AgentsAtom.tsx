import { deleteAgent, getAgents } from '@/services/agentsService';
import type { AgentsState, ApiAgent } from '@/types/agent';
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

export default agentsAtom;
