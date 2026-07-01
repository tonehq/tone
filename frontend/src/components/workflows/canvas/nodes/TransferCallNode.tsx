'use client';

import type { NodeProps } from '@xyflow/react';

import { NODE_REGISTRY } from '@/components/workflows/nodeRegistry';
import BaseNode from './BaseNode';
import { type D, firstMsg, str, useNodeCommon } from './nodeShared';

function TransferCallNode({ id, data, selected }: NodeProps) {
  const { d, base } = useNodeCommon(id, data);
  const dest = (d.destination as D | undefined)?.number;
  return (
    <BaseNode
      {...base}
      meta={NODE_REGISTRY.transferCall}
      summary={dest ? `Transfer to ${str(dest)}` : firstMsg(d)}
      selected={selected}
    />
  );
}

export default TransferCallNode;
