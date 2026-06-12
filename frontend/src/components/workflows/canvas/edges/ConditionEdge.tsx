'use client';

import React from 'react';
import { BaseEdge, EdgeLabelRenderer, getBezierPath, type EdgeProps } from '@xyflow/react';
import { Braces, Sparkles } from 'lucide-react';

import { cn } from '@/utils/cn';
import type { ConditionEdgeData } from '@/types/workflow';

function ConditionEdge({
  id,
  sourceX,
  sourceY,
  targetX,
  targetY,
  sourcePosition,
  targetPosition,
  data,
  selected,
  markerEnd,
}: EdgeProps) {
  const [edgePath, labelX, labelY] = getBezierPath({
    sourceX,
    sourceY,
    sourcePosition,
    targetX,
    targetY,
    targetPosition,
  });

  const condition = (data as ConditionEdgeData | undefined)?.condition ?? {
    type: 'ai',
    prompt: '',
  };
  const isLogic = condition.type === 'logic';
  const text = condition.prompt?.trim();

  return (
    <>
      <BaseEdge
        id={id}
        path={edgePath}
        markerEnd={markerEnd}
        style={{
          stroke: selected
            ? 'hsl(var(--primary))'
            : isLogic
              ? 'hsl(var(--muted-foreground) / 0.6)'
              : 'hsl(var(--primary) / 0.55)',
          strokeWidth: selected ? 2 : 1.5,
          strokeDasharray: isLogic ? '6 4' : undefined,
        }}
      />
      <EdgeLabelRenderer>
        <div
          className={cn(
            'nodrag nopan pointer-events-auto flex max-w-[200px] items-center gap-1 rounded-full border border-border bg-card/90 px-2 py-0.5 text-[11px] shadow-sm backdrop-blur',
            selected && 'border-primary',
          )}
          style={{
            position: 'absolute',
            transform: `translate(-50%, -50%) translate(${labelX}px, ${labelY}px)`,
          }}
        >
          {isLogic ? (
            <Braces className="h-3 w-3 shrink-0 text-muted-foreground" />
          ) : (
            <Sparkles className="h-3 w-3 shrink-0 text-primary" />
          )}
          <span
            className={cn(
              'truncate',
              isLogic ? 'font-mono text-muted-foreground' : 'text-foreground',
            )}
          >
            {text || (isLogic ? 'Logic' : 'AI · always')}
          </span>
        </div>
      </EdgeLabelRenderer>
    </>
  );
}

export const edgeTypes = { condition: ConditionEdge };
export default ConditionEdge;
