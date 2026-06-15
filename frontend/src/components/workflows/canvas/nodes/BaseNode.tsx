'use client';

import React from 'react';
import { Handle, Position } from '@xyflow/react';
import { Globe, Play } from 'lucide-react';

import { cn } from '@/utils/cn';
import CustomTooltip from '@/components/shared/CustomTooltip';
import type { NodeTypeMeta } from '@/components/workflows/nodeRegistry';

export interface BaseNodeProps {
  meta: NodeTypeMeta;
  title: string;
  summary?: string;
  selected?: boolean;
  errorCount?: number;
  errorMessages?: string[];
  isStart?: boolean;
  isGlobal?: boolean;
  /** extracted-variable names, rendered as chips under the summary */
  variables?: string[];
  /** bottom source handles; defaults to a single unlabeled handle */
  sourceHandles?: { id?: string; label?: string }[];
}

const HANDLE_CLS =
  '!h-3.5 !w-3.5 !rounded-full !border-2 !border-card !bg-muted-foreground/55 !shadow-sm transition-all hover:!bg-primary hover:!scale-110';

const BaseNode: React.FC<BaseNodeProps> = ({
  meta,
  title,
  summary,
  selected,
  errorCount = 0,
  errorMessages = [],
  isStart,
  isGlobal,
  variables,
  sourceHandles,
}) => {
  const Icon = meta.icon;
  const handles = meta.terminal ? [] : (sourceHandles ?? [{ id: undefined }]);

  return (
    <div
      className={cn(
        'group relative w-[268px] cursor-grab overflow-hidden rounded-2xl border border-border bg-card shadow-sm transition-shadow active:cursor-grabbing',
        'hover:shadow-lg',
        selected ? 'shadow-md' : 'hover:border-primary/30',
      )}
    >
      {/* top accent strip */}
      <div className={cn('h-1 w-full', meta.accent.bar)} />

      {/* target handle */}
      {meta.hasTarget && <Handle type="target" position={Position.Top} className={HANDLE_CLS} />}

      <div className="flex items-start gap-3 px-4 pb-2.5 pt-3.5">
        <span
          className={cn(
            'inline-flex h-9 w-9 shrink-0 items-center justify-center rounded-xl',
            meta.accent.chip,
          )}
        >
          <Icon className="h-[18px] w-[18px]" strokeWidth={2} />
        </span>
        <div className="min-w-0 flex-1 pt-0.5">
          <div className="font-mono text-[10px] font-medium uppercase tracking-[0.08em] text-muted-foreground">
            {meta.label}
          </div>
          <div className="truncate text-[15px] font-semibold leading-tight text-foreground">
            {title}
          </div>
        </div>
        <div className="flex items-center gap-1">
          {isStart && (
            <span className="inline-flex items-center gap-0.5 rounded-full bg-emerald-500/10 px-1.5 py-0.5 text-[10px] font-medium text-emerald-600 ring-1 ring-inset ring-emerald-500/20 dark:text-emerald-300">
              <Play className="h-2.5 w-2.5 fill-current" /> Start
            </span>
          )}
          {isGlobal && (
            <CustomTooltip content="Global node — reachable from anywhere">
              <span className="inline-flex h-5 w-5 items-center justify-center rounded-full bg-muted text-muted-foreground ring-1 ring-inset ring-border">
                <Globe className="h-3 w-3" />
              </span>
            </CustomTooltip>
          )}
          {errorCount > 0 && (
            <CustomTooltip content={errorMessages.join('\n') || `${errorCount} issue(s)`}>
              <span className="inline-flex h-5 min-w-5 items-center justify-center rounded-full bg-amber-500/10 px-1 text-[10px] font-semibold text-amber-600 ring-1 ring-inset ring-amber-500/25 dark:text-amber-300">
                {errorCount}
              </span>
            </CustomTooltip>
          )}
        </div>
      </div>

      <div
        className={cn(
          'px-4 text-[13px] leading-relaxed line-clamp-2',
          variables && variables.length ? 'pb-2' : 'pb-3.5',
          summary ? 'text-muted-foreground' : 'italic text-muted-foreground/55',
        )}
      >
        {summary || 'No content yet'}
      </div>

      {variables && variables.length > 0 && (
        <div className="flex flex-wrap gap-1 px-4 pb-3.5">
          {variables.slice(0, 4).map((v) => (
            <span
              key={v}
              className="rounded-md bg-muted px-1.5 py-0.5 font-mono text-[10px] text-muted-foreground ring-1 ring-inset ring-border"
            >
              {`{{${v}}}`}
            </span>
          ))}
          {variables.length > 4 && (
            <span className="rounded-md px-1 py-0.5 text-[10px] text-muted-foreground">
              +{variables.length - 4}
            </span>
          )}
        </div>
      )}

      {/* source handle(s) */}
      {handles.map((h, i) => {
        const count = handles.length;
        const left = count === 1 ? 50 : ((i + 1) / (count + 1)) * 100;
        return (
          <Handle
            key={h.id ?? i}
            id={h.id}
            type="source"
            position={Position.Bottom}
            style={{ left: `${left}%` }}
            className={HANDLE_CLS}
          />
        );
      })}
    </div>
  );
};

export default BaseNode;
