'use client';

import type { NodeProps } from '@xyflow/react';

import { NODE_REGISTRY } from '@/components/workflows/nodeRegistry';
import BaseNode from './BaseNode';
import { type D, firstMsg, str, useNodeCommon } from './nodeShared';

function ConversationNode({ id, data, selected }: NodeProps) {
  const { d, base } = useNodeCommon(id, data);
  const output = ((d.variableExtractionPlan as D | undefined)?.output as D[] | undefined) ?? [];
  const variables = output.map((o) => str(o.title)).filter(Boolean);
  return (
    <BaseNode
      {...base}
      meta={NODE_REGISTRY.conversation}
      summary={firstMsg(d) || str(d.prompt)}
      variables={variables}
      selected={selected}
      isStart={Boolean(d.isStart)}
    />
  );
}

export default ConversationNode;
