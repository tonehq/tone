'use client';

import React, { useMemo } from 'react';
import type { NodeProps } from '@xyflow/react';
import { useAtomValue } from 'jotai';

import { workflowEditorStatusAtom } from '@/atoms/WorkflowAtom';
import { NODE_REGISTRY } from '@/components/workflows/nodeRegistry';
import BaseNode from './BaseNode';

function useNodeIssues(id: string) {
  const status = useAtomValue(workflowEditorStatusAtom);
  return useMemo(() => status.issues.filter((i) => i.node_name === id), [status.issues, id]);
}

type D = Record<string, unknown>;
const str = (v: unknown) => (typeof v === 'string' ? v : '');
const firstMsg = (d: D) => str((d.messagePlan as D | undefined)?.firstMessage);

function ConversationNode({ id, data, selected }: NodeProps) {
  const d = data as D;
  const issues = useNodeIssues(id);
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
      errorCount={issues.length}
      errorMessages={issues.map((i) => i.message)}
    />
  );
}

function DecisionNode({ id, data, selected }: NodeProps) {
  const d = data as D;
  const issues = useNodeIssues(id);
  return (
    <BaseNode
      meta={NODE_REGISTRY.decision}
      title={str(d.name) || id}
      summary={str(d.prompt) || 'Routes on its outgoing edge conditions'}
      selected={selected}
      isStart={Boolean(d.isStart)}
      isGlobal={Boolean(d.isGlobal)}
      errorCount={issues.length}
      errorMessages={issues.map((i) => i.message)}
    />
  );
}

function ToolNode({ id, data, selected }: NodeProps) {
  const d = data as D;
  const issues = useNodeIssues(id);
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
      errorCount={issues.length}
      errorMessages={issues.map((i) => i.message)}
    />
  );
}

function TransferCallNode({ id, data, selected }: NodeProps) {
  const d = data as D;
  const issues = useNodeIssues(id);
  const dest = (d.destination as D | undefined)?.number;
  return (
    <BaseNode
      meta={NODE_REGISTRY.transferCall}
      title={str(d.name) || id}
      summary={dest ? `Transfer to ${str(dest)}` : firstMsg(d)}
      selected={selected}
      isGlobal={Boolean(d.isGlobal)}
      errorCount={issues.length}
      errorMessages={issues.map((i) => i.message)}
    />
  );
}

function EndCallNode({ id, data, selected }: NodeProps) {
  const d = data as D;
  const issues = useNodeIssues(id);
  return (
    <BaseNode
      meta={NODE_REGISTRY.endCall}
      title={str(d.name) || id}
      summary={firstMsg(d) || 'Ends the call'}
      selected={selected}
      isGlobal={Boolean(d.isGlobal)}
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
