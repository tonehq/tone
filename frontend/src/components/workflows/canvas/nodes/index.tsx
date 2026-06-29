'use client';

import React, { createContext, useContext, useMemo } from 'react';
import type { NodeProps } from '@xyflow/react';
import { useAtomValue } from 'jotai';

import { workflowIssuesAtom } from '@/atoms/WorkflowAtom';
import { NODE_REGISTRY } from '@/components/workflows/nodeRegistry';
import BaseNode from './BaseNode';

/** Lets a node delete itself (hover trash button). Provided by WorkflowBuilder. */
interface NodeActions {
  onDelete?: (id: string) => void;
}
export const NodeActionsContext = createContext<NodeActions>({});

function useNodeIssues(id: string) {
  const issues = useAtomValue(workflowIssuesAtom);
  return useMemo(() => issues.filter((i) => i.node_name === id), [issues, id]);
}

function useNodeDelete(id: string) {
  const { onDelete } = useContext(NodeActionsContext);
  return useMemo(() => (onDelete ? () => onDelete(id) : undefined), [onDelete, id]);
}

type D = Record<string, unknown>;
const str = (v: unknown) => (typeof v === 'string' ? v : '');
const firstMsg = (d: D) => str((d.messagePlan as D | undefined)?.firstMessage);

function ConversationNode({ id, data, selected }: NodeProps) {
  const d = data as D;
  const issues = useNodeIssues(id);
  const onDelete = useNodeDelete(id);
  const summary = firstMsg(d) || str(d.prompt);
  const output = ((d.variableExtractionPlan as D | undefined)?.output as D[] | undefined) ?? [];
  const variables = output.map((o) => str(o.title)).filter(Boolean);
  return (
    <BaseNode
      meta={NODE_REGISTRY.conversation}
      title={str(d.name) || id}
      summary={summary}
      variables={variables}
      selected={selected}
      isStart={Boolean(d.isStart)}
      isGlobal={Boolean(d.isGlobal)}
      onDelete={onDelete}
      errorCount={issues.length}
      errorMessages={issues.map((i) => i.message)}
    />
  );
}

function DecisionNode({ id, data, selected }: NodeProps) {
  const d = data as D;
  const issues = useNodeIssues(id);
  const onDelete = useNodeDelete(id);
  return (
    <BaseNode
      meta={NODE_REGISTRY.decision}
      title={str(d.name) || id}
      summary={str(d.prompt) || 'Routes on its outgoing edge conditions'}
      selected={selected}
      isStart={Boolean(d.isStart)}
      isGlobal={Boolean(d.isGlobal)}
      onDelete={onDelete}
      errorCount={issues.length}
      errorMessages={issues.map((i) => i.message)}
    />
  );
}

function ToolNode({ id, data, selected }: NodeProps) {
  const d = data as D;
  const issues = useNodeIssues(id);
  const onDelete = useNodeDelete(id);
  const inline = (d.tool as D | undefined)?.type;
  const summary = inline
    ? `Built-in: ${str(inline)}`
    : str(d.toolId)
      ? `Tool ${str(d.toolId).slice(0, 8)}…`
      : '';
  return (
    <BaseNode
      meta={NODE_REGISTRY.tool}
      title={str(d.name) || id}
      summary={summary}
      selected={selected}
      isStart={Boolean(d.isStart)}
      isGlobal={Boolean(d.isGlobal)}
      onDelete={onDelete}
      errorCount={issues.length}
      errorMessages={issues.map((i) => i.message)}
    />
  );
}

function TransferCallNode({ id, data, selected }: NodeProps) {
  const d = data as D;
  const issues = useNodeIssues(id);
  const onDelete = useNodeDelete(id);
  const dest = (d.destination as D | undefined)?.number;
  return (
    <BaseNode
      meta={NODE_REGISTRY.transferCall}
      title={str(d.name) || id}
      summary={dest ? `Transfer to ${str(dest)}` : firstMsg(d)}
      selected={selected}
      isGlobal={Boolean(d.isGlobal)}
      onDelete={onDelete}
      errorCount={issues.length}
      errorMessages={issues.map((i) => i.message)}
    />
  );
}

function EndCallNode({ id, data, selected }: NodeProps) {
  const d = data as D;
  const issues = useNodeIssues(id);
  const onDelete = useNodeDelete(id);
  return (
    <BaseNode
      meta={NODE_REGISTRY.endCall}
      title={str(d.name) || id}
      summary={firstMsg(d) || 'Ends the call'}
      selected={selected}
      isGlobal={Boolean(d.isGlobal)}
      onDelete={onDelete}
      errorCount={issues.length}
      errorMessages={issues.map((i) => i.message)}
    />
  );
}

export const nodeTypes = {
  conversation: ConversationNode,
  decision: DecisionNode,
  tool: ToolNode,
  transferCall: TransferCallNode,
  endCall: EndCallNode,
};
