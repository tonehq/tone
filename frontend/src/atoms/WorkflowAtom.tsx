import { atom } from 'jotai';

import {
  cloneWorkflow,
  createWorkflow,
  deleteWorkflow,
  exportVapiWorkflow,
  getWorkflow,
  listWorkflows,
  saveWorkflowDraft,
} from '@/services/workflowService';
import type {
  ValidationIssue,
  WorkflowDetail,
  WorkflowGraph,
  WorkflowSummary,
} from '@/types/workflow';

function makeLatestTracker() {
  let latest = 0;
  return () => {
    latest += 1;
    const id = latest;
    return () => id === latest;
  };
}

// ─── agent-scoped workflow list ─────────────────────────────────────────────
interface WorkflowsState {
  list: WorkflowSummary[];
  loading: boolean;
}

export const workflowsAtom = atom<WorkflowsState>({ list: [], loading: false });

const listTracker = makeLatestTracker();
export const fetchWorkflowListAtom = atom(
  null,
  async (get, set, payload?: { agentId?: string }): Promise<WorkflowSummary[]> => {
    const isLatest = listTracker();
    set(workflowsAtom, { ...get(workflowsAtom), loading: true });
    try {
      const rows = await listWorkflows(payload?.agentId);
      if (isLatest()) set(workflowsAtom, { list: rows, loading: false });
      return rows;
    } catch (err) {
      if (isLatest()) set(workflowsAtom, { ...get(workflowsAtom), loading: false });
      throw err;
    }
  },
);

export const createWorkflowAtom = atom(
  null,
  async (
    _get,
    _set,
    payload: { name: string; description?: string; agentId?: string },
  ): Promise<WorkflowDetail> => createWorkflow(payload.name, payload.description, payload.agentId),
);

export const deleteWorkflowAtom = atom(null, async (_get, _set, workflowId: string) =>
  deleteWorkflow(workflowId),
);

export const cloneWorkflowAtom = atom(
  null,
  async (
    _get,
    _set,
    payload: { workflowId: string; name?: string; agentId?: string },
  ): Promise<WorkflowDetail> => cloneWorkflow(payload.workflowId, payload.name, payload.agentId),
);

// ─── editor (single workflow) ───────────────────────────────────────────────
export const fetchWorkflowAtom = atom(
  null,
  async (_get, _set, workflowId: string): Promise<WorkflowDetail> => getWorkflow(workflowId),
);

export const saveDraftAtom = atom(
  null,
  async (
    _get,
    _set,
    payload: { workflowId: string; graph: WorkflowGraph; expectedChecksum?: string | null },
  ): Promise<WorkflowDetail> =>
    saveWorkflowDraft(payload.workflowId, payload.graph, payload.expectedChecksum),
);

export const exportWorkflowAtom = atom(
  null,
  async (_get, _set, workflowId: string): Promise<Record<string, unknown>> =>
    exportVapiWorkflow(workflowId),
);

export const workflowIssuesAtom = atom<ValidationIssue[]>([]);
