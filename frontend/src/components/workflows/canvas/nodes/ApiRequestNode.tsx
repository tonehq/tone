'use client';

import type { NodeProps } from '@xyflow/react';

import { NODE_REGISTRY } from '@/components/workflows/nodeRegistry';
import BaseNode from './BaseNode';
import { str, useNodeCommon } from './nodeShared';

function ApiRequestNode({ id, data, selected }: NodeProps) {
  const { d, base } = useNodeCommon(id, data);
  const method = (str(d.method) || 'GET').toUpperCase();
  const url = str(d.url);
  return (
    <BaseNode
      {...base}
      meta={NODE_REGISTRY.apiRequest}
      summary={url ? `${method} ${url}` : str(d.description) || 'No endpoint set'}
      selected={selected}
    />
  );
}

export default ApiRequestNode;
