import { atom } from 'jotai';

import {
  createWorkflow,
  deleteWorkflow,
  getWorkflow,
  listWorkflows,
  publishWorkflow,
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

// ─── org-level workflow list ────────────────────────────────────────────────
interface WorkflowsState {
  list: WorkflowSummary[];
  loading: boolean;
}

export const workflowsAtom = atom<WorkflowsState>({ list: [], loading: false });

const listTracker = makeLatestTracker();
export const fetchWorkflowListAtom = atom(null, async (get, set): Promise<WorkflowSummary[]> => {
  const isLatest = listTracker();
  set(workflowsAtom, { ...get(workflowsAtom), loading: true });
  try {
    const rows = await listWorkflows();
    if (isLatest()) set(workflowsAtom, { list: rows, loading: false });
    return rows;
  } catch (err) {
    if (isLatest()) set(workflowsAtom, { ...get(workflowsAtom), loading: false });
    throw err;
  }
});

export const createWorkflowAtom = atom(
  null,
  async (_get, _set, payload: { name: string; description?: string }): Promise<WorkflowDetail> =>
    createWorkflow(payload.name, payload.description),
);

export const deleteWorkflowAtom = atom(null, async (_get, _set, workflowId: string) =>
  deleteWorkflow(workflowId),
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

export const publishWorkflowAtom = atom(
  null,
  async (_get, _set, workflowId: string): Promise<WorkflowDetail> => publishWorkflow(workflowId),
);

// ─── editor UI status (coarse, mirrored from the canvas) ────────────────────
export interface WorkflowEditorStatus {
  saving: boolean;
  dirty: boolean;
  issues: ValidationIssue[];
  selectedNodeId: string | null;
  lastSavedAt: number | null;
}

export const workflowEditorStatusAtom = atom<WorkflowEditorStatus>({
  saving: false,
  dirty: false,
  issues: [],
  selectedNodeId: null,
  lastSavedAt: null,
});
