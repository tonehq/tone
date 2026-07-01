'use client';

import type { NodeProps } from '@xyflow/react';

import { NODE_REGISTRY } from '@/components/workflows/nodeRegistry';
import BaseNode from './BaseNode';
import { firstMsg, useNodeCommon } from './nodeShared';

function EndCallNode({ id, data, selected }: NodeProps) {
  const { d, base } = useNodeCommon(id, data);
  return (
    <BaseNode
      {...base}
      meta={NODE_REGISTRY.endCall}
      summary={firstMsg(d) || 'Ends the call'}
      selected={selected}
    />
  );
}

export default EndCallNode;
