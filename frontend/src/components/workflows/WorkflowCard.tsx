'use client';

import React from 'react';
import { Clock, TriangleAlert, Users, Workflow as WorkflowIcon } from 'lucide-react';

import { cn } from '@/utils/cn';
import { Card, CardContent } from '@/components/ui/card';
import ActionMenu from '@/components/shared/ActionMenu';
import { formatRelative } from '@/utils/date';
import type { WorkflowSummary } from '@/types/workflow';

interface WorkflowCardProps {
  wf: WorkflowSummary;
  onOpen: (id: string) => void;
  onDelete: (wf: WorkflowSummary) => void;
  onClone: (wf: WorkflowSummary) => void;
}

const WorkflowCard: React.FC<WorkflowCardProps> = ({ wf, onOpen, onDelete, onClone }) => {
  const published = wf.status === 'published';
  return (
    <Card
      className={cn(
        'group relative h-full cursor-pointer gap-0 overflow-hidden border-border/80 py-0',
        'transition-all duration-200 hover:-translate-y-0.5 hover:border-foreground/20',
        'hover:shadow-[0_10px_30px_-14px_rgba(99,102,241,0.35)]',
        'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/50 focus-visible:ring-offset-2 focus-visible:ring-offset-background',
      )}
      role="button"
      tabIndex={0}
      aria-label={`Open workflow ${wf.name}`}
      onClick={() => onOpen(wf.id)}
      onKeyDown={(e) => {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault();
          onOpen(wf.id);
        }
      }}
    >
      {/* status accent stripe + soft hover glow */}
      <span
        className={cn(
          'absolute inset-y-0 left-0 w-1 transition-colors',
          published ? 'bg-emerald-500/70' : 'bg-amber-500/70',
        )}
        aria-hidden
      />
      <span
        className="pointer-events-none absolute -right-12 -top-12 size-32 rounded-full bg-indigo-500 opacity-0 blur-2xl transition-opacity duration-300 group-hover:opacity-15"
        aria-hidden
      />

      <CardContent className="flex h-full flex-col p-5 pl-6">
        {/* Header — icon + name + agents + actions */}
        <div className="flex items-start gap-3">
          <div className="flex size-10 shrink-0 items-center justify-center rounded-xl border border-indigo-500/20 bg-indigo-500/10 text-indigo-600 shadow-sm transition-all group-hover:scale-[1.04] dark:text-indigo-400">
            <WorkflowIcon size={18} strokeWidth={1.75} />
          </div>

          <div className="min-w-0 flex-1 pt-0.5">
            <p className="truncate text-[14px] font-semibold leading-tight tracking-tight text-foreground">
              {wf.name}
            </p>
            <p className="mt-1 flex items-center gap-1 text-[12px] text-muted-foreground">
              <Users className="size-3 shrink-0 opacity-70" />
              <span className="truncate">
                {wf.agents_using} agent{wf.agents_using === 1 ? '' : 's'}
              </span>
            </p>
          </div>

          <div
            onClick={(e) => e.stopPropagation()}
            className="opacity-60 transition-opacity group-hover:opacity-100"
          >
            <ActionMenu
              itemName={wf.name}
              onEdit={() => onOpen(wf.id)}
              onClone={() => onClone(wf)}
              cloneLabel="Duplicate workflow"
              onDelete={() => Promise.resolve(onDelete(wf))}
              deleteDescription={`This permanently removes "${wf.name}". Workflows assigned to an agent must be unassigned first.`}
            />
          </div>
        </div>

        {/* Description */}
        <p className="mt-4 line-clamp-2 min-h-[40px] text-[12.5px] leading-relaxed text-muted-foreground">
          {wf.description || (
            <span className="italic text-muted-foreground/60">No description provided.</span>
          )}
        </p>

        {/* Footer — validity/updated chip + status pill */}
        <div className="mt-auto flex items-center justify-between gap-2 pt-4">
          {wf.is_valid ? (
            <span className="inline-flex items-center gap-1.5 rounded-md bg-muted px-2 py-1 text-[10.5px] font-medium text-muted-foreground ring-1 ring-inset ring-border/60">
              <Clock className="size-3" />
              {wf.updated_at ? formatRelative(wf.updated_at) : 'New'}
            </span>
          ) : (
            <span className="inline-flex items-center gap-1.5 rounded-md bg-destructive/10 px-2 py-1 text-[10.5px] font-medium text-destructive ring-1 ring-inset ring-destructive/20">
              <TriangleAlert className="size-3" />
              Has issues
            </span>
          )}

          <span
            className={cn(
              'inline-flex items-center gap-1.5 rounded-full px-2 py-1 text-[10.5px] font-semibold',
              published
                ? 'bg-emerald-500/10 text-emerald-600 dark:text-emerald-400'
                : 'bg-amber-500/10 text-amber-600 dark:text-amber-400',
            )}
          >
            <span className="relative inline-flex size-1.5">
              {published && (
                <span className="absolute inset-0 animate-ping rounded-full bg-emerald-500/60" />
              )}
              <span
                className={cn(
                  'relative inline-flex size-1.5 rounded-full',
                  published ? 'bg-emerald-500' : 'bg-amber-500',
                )}
              />
            </span>
            {published ? 'Published' : 'Draft'}
          </span>
        </div>
      </CardContent>
    </Card>
  );
};

export default WorkflowCard;
