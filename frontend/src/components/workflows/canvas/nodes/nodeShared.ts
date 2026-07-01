'use client';

import { createContext, useContext, useMemo } from 'react';
import { useAtomValue } from 'jotai';

import { workflowIssuesAtom } from '@/atoms/WorkflowAtom';

export type D = Record<string, unknown>;

/** Lets a node delete itself (hover trash button). Provided by WorkflowBuilder. */
export interface NodeActions {
  onDelete?: (id: string) => void;
}

export const NodeActionsContext = createContext<NodeActions>({});

export function useNodeIssues(id: string) {
  const issues = useAtomValue(workflowIssuesAtom);
  return useMemo(() => issues.filter((i) => i.node_name === id), [issues, id]);
}

export function useNodeDelete(id: string) {
  const { onDelete } = useContext(NodeActionsContext);
  return useMemo(() => (onDelete ? () => onDelete(id) : undefined), [onDelete, id]);
}

export const str = (v: unknown) => (typeof v === 'string' ? v : '');
export const firstMsg = (d: D) => str((d.messagePlan as D | undefined)?.firstMessage);

/**
 * Shared per-node wiring: casts `data`, subscribes to this node's issues, resolves its
 * delete handler, and pre-builds the `BaseNode` props every node type passes identically
 * (title, isGlobal, onDelete, errorCount, errorMessages). Each node then only supplies the
 * bits that differ — `meta`, `summary`, `selected`, and (where relevant) `isStart`/`variables`.
 */
export function useNodeCommon(id: string, data: unknown) {
  const d = (data ?? {}) as D;
  const issues = useNodeIssues(id);
  const onDelete = useNodeDelete(id);
  return {
    d,
    base: {
      title: str(d.name) || id,
      isGlobal: Boolean(d.isGlobal),
      onDelete,
      errorCount: issues.length,
      errorMessages: issues.map((i) => i.message),
    },
  };
}
