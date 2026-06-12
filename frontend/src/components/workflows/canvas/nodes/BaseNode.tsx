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
  /** bottom source handles; defaults to a single unlabeled handle */
  sourceHandles?: { id?: string; label?: string }[];
}

const BaseNode: React.FC<BaseNodeProps> = ({
  meta,
  title,
  summary,
  selected,
  errorCount = 0,
  errorMessages = [],
  isStart,
  isGlobal,
  sourceHandles,
}) => {
  const Icon = meta.icon;
  const handles = meta.terminal ? [] : (sourceHandles ?? [{ id: undefined }]);

  return (
    <div
      className={cn(
        'group relative min-w-[240px] max-w-[300px] overflow-hidden rounded-xl border bg-card shadow-sm transition-all',
        'hover:-translate-y-px hover:shadow-md',
        selected
          ? 'border-primary ring-2 ring-primary ring-offset-2 ring-offset-background'
          : 'border-border',
      )}
    >
      {/* top accent bar */}
      <div className={cn('h-[2px] w-full', meta.accent.bar)} />

      {/* target handle */}
      {meta.hasTarget && (
        <Handle
          type="target"
          position={Position.Top}
          className="!h-2.5 !w-2.5 !border-2 !border-muted-foreground/50 !bg-background"
        />
      )}

      <div className="flex items-start gap-2.5 px-3.5 pb-2 pt-3">
        <span
          className={cn(
            'inline-flex h-7 w-7 shrink-0 items-center justify-center rounded-md',
            meta.accent.chip,
          )}
        >
          <Icon className="h-4 w-4" strokeWidth={2} />
        </span>
        <div className="min-w-0 flex-1">
          <div className="font-mono text-[10px] uppercase tracking-wide text-muted-foreground">
            {meta.label}
          </div>
          <div className="truncate text-sm font-semibold leading-tight text-foreground">
            {title}
          </div>
        </div>
        <div className="flex items-center gap-1">
          {isStart && (
            <span className="inline-flex items-center gap-0.5 rounded-full bg-emerald-500/10 px-1.5 py-0.5 text-[10px] font-medium text-emerald-600 ring-1 ring-inset ring-emerald-500/20 dark:text-emerald-300">
              <Play className="h-2.5 w-2.5" /> Start
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
              <span className="inline-flex h-5 min-w-5 items-center justify-center rounded-full bg-destructive/10 px-1 text-[10px] font-semibold text-destructive ring-1 ring-inset ring-destructive/20">
                {errorCount}
              </span>
            </CustomTooltip>
          )}
        </div>
      </div>

      {summary ? (
        <div className="px-3.5 pb-3 text-[13px] leading-snug text-muted-foreground line-clamp-2">
          {summary}
        </div>
      ) : (
        <div className="px-3.5 pb-3 text-[13px] italic leading-snug text-muted-foreground/60">
          No content yet
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
            className="!h-2.5 !w-2.5 !border-2 !border-muted-foreground/50 !bg-background transition-colors hover:!border-primary"
          />
        );
      })}
    </div>
  );
};

export default BaseNode;
