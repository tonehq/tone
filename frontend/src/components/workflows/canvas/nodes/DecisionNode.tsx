'use client';

import type { NodeProps } from '@xyflow/react';

import { NODE_REGISTRY } from '@/components/workflows/nodeRegistry';
import BaseNode from './BaseNode';
import { str, useNodeCommon } from './nodeShared';

function DecisionNode({ id, data, selected }: NodeProps) {
  const { d, base } = useNodeCommon(id, data);
  return (
    <BaseNode
      {...base}
      meta={NODE_REGISTRY.decision}
      summary={str(d.prompt) || 'Routes on its outgoing edge conditions'}
      selected={selected}
      isStart={Boolean(d.isStart)}
    />
  );
}

export default DecisionNode;
