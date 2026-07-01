'use client';

import type { NodeProps } from '@xyflow/react';

import { NODE_REGISTRY } from '@/components/workflows/nodeRegistry';
import BaseNode from './BaseNode';
import { type D, str, useNodeCommon } from './nodeShared';

function ToolNode({ id, data, selected }: NodeProps) {
  const { d, base } = useNodeCommon(id, data);
  const inline = (d.tool as D | undefined)?.type;
  const summary = inline
    ? `Built-in: ${str(inline)}`
    : str(d.mcpServerId)
      ? `MCP server ${str(d.mcpServerId).slice(0, 8)}…`
      : str(d.toolId)
        ? `Tool ${str(d.toolId).slice(0, 8)}…`
        : '';
  return (
    <BaseNode
      {...base}
      meta={NODE_REGISTRY.tool}
      summary={summary}
      selected={selected}
      isStart={Boolean(d.isStart)}
    />
  );
}

export default ToolNode;
