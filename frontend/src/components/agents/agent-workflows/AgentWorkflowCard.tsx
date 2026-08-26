'use client';

import React from 'react';
import { CircleCheck, Clock, TriangleAlert, Workflow as WorkflowIcon } from 'lucide-react';

import { IconChip } from '@/components/shared';
import ActionMenu from '@/components/shared/ActionMenu';
import CustomButton from '@/components/shared/CustomButton';
import { Card, CardContent } from '@/components/ui/card';
import type { WorkflowSummary } from '@/types/workflow';
import { cn } from '@/utils/cn';
import { formatRelative } from '@/utils/date';

interface AgentWorkflowCardProps {
  wf: WorkflowSummary;
  /** True when this workflow is the one assigned to the viewed agent version. */
  assigned: boolean;
  /** Version number of the agent version currently loaded in the editor. */
  viewedVersion: number | null;
  onOpen: (wf: WorkflowSummary) => void;
  onAssign: (wf: WorkflowSummary) => void;
  onUnassign: () => void;
  onClone: (wf: WorkflowSummary) => void;
  onDelete: (wf: WorkflowSummary) => Promise<void>;
}

const AgentWorkflowCard: React.FC<AgentWorkflowCardProps> = ({
  wf,
  assigned,
  viewedVersion,
  onOpen,
  onAssign,
  onUnassign,
  onClone,
  onDelete,
}) => {
  const versionLabel = viewedVersion != null ? `v${viewedVersion}` : 'this version';

  // "Used by" comes from the saved backend state; fold in the live (possibly
  // unsaved) assignment for the viewed version so the chips update the moment
  // the user assigns/unassigns — matching the "Active · vN" pill.
  const usedBy = (() => {
    const set = new Set(wf.assigned_versions ?? []);
    if (viewedVersion != null) {
      if (assigned) set.add(viewedVersion);
      else set.delete(viewedVersion);
    }
    return Array.from(set).sort((a, b) => a - b);
  })();

  // Cap the "Used by" chips so a workflow shared by many versions doesn't wrap
  // into a tall, cramped block — the rest collapse into a "+N" chip.
  const MAX_VERSION_CHIPS = 4;
  const shownVersions = usedBy.slice(0, MAX_VERSION_CHIPS);
  const extraVersions = usedBy.length - shownVersions.length;

  return (
    <Card
      className={cn(
        'group relative h-full cursor-pointer gap-0 overflow-hidden border-border/80 py-0',
        'transition-all duration-200 hover:-translate-y-0.5 hover:border-foreground/20',
        'hover:shadow-[0_10px_30px_-14px_rgba(99,102,241,0.35)]',
        'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/50 focus-visible:ring-offset-2 focus-visible:ring-offset-background',
        assigned && 'border-primary/40 bg-primary/[0.035] ring-1 ring-primary/25',
      )}
      role="button"
      tabIndex={0}
      aria-label={`Open workflow ${wf.name} in the builder`}
      onClick={() => onOpen(wf)}
      onKeyDown={(e) => {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault();
          onOpen(wf);
        }
      }}
    >
      {/* accent stripe: primary when active, emerald when valid, amber when it has issues */}
      <span
        className={cn(
          'absolute inset-y-0 left-0 w-1 transition-colors',
          assigned ? 'bg-primary' : wf.is_valid ? 'bg-emerald-500/70' : 'bg-amber-500/70',
        )}
        aria-hidden
      />
      <span
        className="pointer-events-none absolute -right-12 -top-12 size-32 rounded-full bg-indigo-500 opacity-0 blur-2xl transition-opacity duration-300 group-hover:opacity-15"
        aria-hidden
      />

      <CardContent className="flex h-full flex-col p-5 pl-6">
        <div className="flex items-start gap-3">
          <IconChip
            icon={<WorkflowIcon strokeWidth={1.75} />}
            tone="indigo"
            size="lg"
            className="transition-transform duration-300 group-hover:scale-[1.04]"
          />

          <div className="min-w-0 flex-1 pt-0.5">
            <p className="truncate text-[14px] font-semibold leading-tight tracking-tight text-foreground">
              {wf.name}
            </p>
            {usedBy.length > 0 ? (
              <div className="mt-1.5 flex items-center gap-1">
                <span className="shrink-0 text-[11px] text-muted-foreground">Used by</span>
                {shownVersions.map((v) => (
                  <span
                    key={v}
                    className="inline-flex shrink-0 items-center rounded-md bg-muted px-1.5 py-0.5 font-mono text-[10.5px] font-medium text-foreground ring-1 ring-inset ring-border/60"
                  >
                    v{v}
                  </span>
                ))}
                {extraVersions > 0 && (
                  <span
                    title={`Also used by ${usedBy.map((v) => `v${v}`).join(', ')}`}
                    className="inline-flex shrink-0 items-center rounded-md bg-muted px-1.5 py-0.5 font-mono text-[10.5px] font-medium text-muted-foreground ring-1 ring-inset ring-border/60"
                  >
                    +{extraVersions}
                  </span>
                )}
              </div>
            ) : (
              <p className="mt-1 text-[12px] italic text-muted-foreground/60">
                Not used by any version
              </p>
            )}
          </div>

          <div className="flex shrink-0 items-center gap-1.5">
            {assigned && (
              <span
                className="inline-flex items-center gap-1 rounded-full bg-primary px-2 py-0.5 text-[10.5px] font-semibold text-primary-foreground shadow-sm"
                aria-label={`Active workflow for ${versionLabel}`}
              >
                <CircleCheck className="size-3" />
                Active · {versionLabel}
              </span>
            )}
            <div
              onClick={(e) => e.stopPropagation()}
              className={assigned ? '' : 'opacity-60 transition-opacity group-hover:opacity-100'}
            >
              <ActionMenu
                itemName={wf.name}
                onEdit={() => onOpen(wf)}
                editLabel="Open in builder"
                onClone={() => onClone(wf)}
                cloneLabel="Duplicate workflow"
                onDelete={() => onDelete(wf)}
                deleteDescription={`This permanently removes "${wf.name}". Workflows still used by an agent version cannot be deleted.`}
              />
            </div>
          </div>
        </div>

        <p className="mt-4 line-clamp-2 min-h-[40px] text-[12.5px] leading-relaxed text-muted-foreground">
          {wf.description || (
            <span className="italic text-muted-foreground/60">No description provided.</span>
          )}
        </p>

        <div className="mt-auto flex items-center justify-between gap-2 pt-4">
          <span className="flex min-w-0 items-center gap-2">
            <span className="inline-flex items-center gap-1.5 rounded-md bg-muted px-2 py-1 text-[10.5px] font-medium text-muted-foreground ring-1 ring-inset ring-border/60">
              <Clock className="size-3" />
              {wf.updated_at ? formatRelative(wf.updated_at) : 'New'}
            </span>
            {wf.is_valid ? (
              <span className="inline-flex items-center gap-1.5 rounded-full bg-emerald-500/10 px-2 py-1 text-[10.5px] font-semibold text-emerald-600 dark:text-emerald-400">
                <span className="relative inline-flex size-1.5">
                  <span className="absolute inset-0 animate-ping rounded-full bg-emerald-500/60" />
                  <span className="relative inline-flex size-1.5 rounded-full bg-emerald-500" />
                </span>
                Ready
              </span>
            ) : (
              <span className="inline-flex items-center gap-1.5 rounded-full bg-destructive/10 px-2 py-1 text-[10.5px] font-semibold text-destructive ring-1 ring-inset ring-destructive/20">
                <TriangleAlert className="size-3" />
                Has issues
              </span>
            )}
          </span>

          <span onClick={(e) => e.stopPropagation()}>
            {assigned ? (
              <CustomButton
                type="text"
                size="sm"
                onClick={onUnassign}
                className="h-7 px-2 text-[11.5px] text-muted-foreground hover:text-destructive"
              >
                Unassign
              </CustomButton>
            ) : (
              <CustomButton
                type="default"
                size="sm"
                disabled={!wf.is_valid}
                onClick={() => onAssign(wf)}
                title={
                  wf.is_valid
                    ? `Run ${versionLabel} with this workflow`
                    : 'Resolve this workflow’s validation issues before assigning it'
                }
                className="h-7 px-2.5 text-[11.5px]"
              >
                Use for {versionLabel}
              </CustomButton>
            )}
          </span>
        </div>
      </CardContent>
    </Card>
  );
};

export default AgentWorkflowCard;
