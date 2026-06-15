'use client';

import React, { createContext, useContext } from 'react';
import { BaseEdge, EdgeLabelRenderer, getBezierPath, type EdgeProps } from '@xyflow/react';
import { Braces, Plus, Sparkles, X } from 'lucide-react';

import { cn } from '@/utils/cn';
import CustomButton from '@/components/shared/CustomButton';
import type { ConditionEdgeData } from '@/types/workflow';

/** Lets the custom edge open the condition editor / delete itself. Provided by WorkflowBuilder. */
interface EdgeActions {
  onEdit?: (id: string) => void;
  onDelete?: (id: string) => void;
}
export const EdgeActionsContext = createContext<EdgeActions>({});

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
  const { onEdit, onDelete } = useContext(EdgeActionsContext);
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
          className="nodrag nopan group pointer-events-auto absolute flex items-center gap-1"
          style={{ transform: `translate(-50%, -50%) translate(${labelX}px, ${labelY}px)` }}
        >
          {text ? (
            <CustomButton
              type="text"
              onClick={() => onEdit?.(id)}
              title="Edit condition"
              className={cn(
                '!h-auto max-w-[220px] gap-1 rounded-full border bg-card/95 px-2 py-0.5 text-[11px] font-normal shadow-sm backdrop-blur',
                selected ? 'border-primary' : 'border-border',
              )}
            >
              {isLogic ? (
                <Braces className="h-3 w-3 shrink-0 text-muted-foreground" />
              ) : (
                <Sparkles className="h-3 w-3 shrink-0 text-primary" />
              )}
              <span className={cn('truncate', isLogic && 'font-mono text-muted-foreground')}>
                {text}
              </span>
            </CustomButton>
          ) : (
            <CustomButton
              type="text"
              onClick={() => onEdit?.(id)}
              className="!h-auto gap-1 rounded-full border border-dashed border-border bg-card/80 px-2 py-0.5 text-[11px] font-normal text-muted-foreground opacity-70 shadow-sm backdrop-blur transition-opacity hover:opacity-100"
            >
              <Plus className="h-3 w-3 shrink-0" />
              Add condition
            </CustomButton>
          )}

          {selected && onDelete && (
            <CustomButton
              type="text"
              onClick={() => onDelete(id)}
              aria-label="Delete connection"
              title="Delete connection"
              className="!h-auto size-5 rounded-full border border-border bg-card p-0 text-muted-foreground shadow-sm hover:bg-destructive/10 hover:text-destructive"
              icon={<X className="h-3 w-3" />}
            />
          )}
        </div>
      </EdgeLabelRenderer>
    </>
  );
}

export const edgeTypes = { condition: ConditionEdge };
export default ConditionEdge;
