'use client';

import React, { useState } from 'react';
import {
  ChevronLeft,
  CircleAlert,
  CircleCheck,
  FileDown,
  MoreHorizontal,
  Sparkles,
} from 'lucide-react';

import { cn } from '@/utils/cn';
import CustomButton from '@/components/shared/CustomButton';
import CustomPopover from '@/components/shared/CustomPopover';
import type { ValidationIssue } from '@/types/workflow';

interface Props {
  name: string;
  status: 'draft' | 'published';
  saving: boolean;
  dirty: boolean;
  lastSavedAt: number | null;
  issues: ValidationIssue[];
  onBack: () => void;
  onSave: () => void;
  onPublish: () => void;
  onOpenGlobalPrompt: () => void;
  onExport: () => void;
  onFocusNode?: (nodeName: string) => void;
}

const WorkflowToolbar: React.FC<Props> = ({
  name,
  status,
  saving,
  dirty,
  lastSavedAt,
  issues,
  onBack,
  onSave,
  onPublish,
  onOpenGlobalPrompt,
  onExport,
  onFocusNode,
}) => {
  const [issuesOpen, setIssuesOpen] = useState(false);
  const [moreOpen, setMoreOpen] = useState(false);
  const valid = issues.length === 0;

  const savedLabel = saving
    ? 'Saving…'
    : dirty
      ? 'Unsaved changes'
      : lastSavedAt
        ? 'All changes saved'
        : 'Up to date';

  return (
    <div className="flex h-14 shrink-0 items-center justify-between gap-3 border-b border-border bg-card/80 px-3 backdrop-blur">
      {/* left: back + title + status */}
      <div className="flex min-w-0 items-center gap-2">
        <button
          onClick={onBack}
          aria-label="Back to workflows"
          className="rounded-lg p-2 text-muted-foreground transition-colors hover:bg-accent hover:text-foreground"
        >
          <ChevronLeft className="h-4 w-4" />
        </button>
        <div className="h-6 w-px bg-border" />
        <div className="min-w-0 pl-1">
          <div className="flex items-center gap-2">
            <span className="truncate text-sm font-semibold text-foreground">{name}</span>
            <span
              className={cn(
                'inline-flex shrink-0 items-center gap-1 rounded-full px-2 py-0.5 text-[10px] font-medium ring-1 ring-inset',
                status === 'published'
                  ? 'bg-emerald-500/10 text-emerald-600 ring-emerald-500/20 dark:text-emerald-300'
                  : 'bg-amber-500/10 text-amber-600 ring-amber-500/20 dark:text-amber-300',
              )}
            >
              <span
                className={cn(
                  'h-1.5 w-1.5 rounded-full',
                  status === 'published' ? 'bg-emerald-500' : 'bg-amber-500',
                )}
              />
              {status === 'published' ? 'Published' : 'Draft'}
            </span>
          </div>
          <div className="font-mono text-[11px] text-muted-foreground">{savedLabel}</div>
        </div>
      </div>

      {/* right: validation + more + actions */}
      <div className="flex items-center gap-1.5">
        <CustomPopover
          open={issuesOpen}
          onOpenChange={setIssuesOpen}
          align="end"
          width="w-80"
          trigger={
            <button
              className={cn(
                'inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-medium ring-1 ring-inset transition-colors',
                valid
                  ? 'bg-emerald-500/10 text-emerald-600 ring-emerald-500/20 hover:bg-emerald-500/15 dark:text-emerald-300'
                  : 'bg-amber-500/10 text-amber-600 ring-amber-500/25 hover:bg-amber-500/15 dark:text-amber-300',
              )}
            >
              {valid ? (
                <CircleCheck className="h-3.5 w-3.5" />
              ) : (
                <CircleAlert className="h-3.5 w-3.5" />
              )}
              {valid ? 'Valid' : `${issues.length} issue${issues.length > 1 ? 's' : ''}`}
            </button>
          }
        >
          <div aria-live="polite" className="max-h-72 overflow-y-auto">
            <div className="mb-1 px-1 text-xs font-medium text-foreground">
              {valid ? 'Ready to publish' : 'Resolve before publishing'}
            </div>
            {valid ? (
              <p className="px-1 py-1.5 text-sm text-muted-foreground">No problems found.</p>
            ) : (
              <ul className="flex flex-col gap-0.5">
                {issues.map((iss, i) => (
                  <li key={i}>
                    <button
                      onClick={() => {
                        if (iss.node_name && onFocusNode) onFocusNode(iss.node_name);
                        setIssuesOpen(false);
                      }}
                      className="flex w-full items-start gap-2 rounded-md px-2 py-1.5 text-left text-sm hover:bg-accent"
                    >
                      <CircleAlert className="mt-0.5 h-3.5 w-3.5 shrink-0 text-amber-500" />
                      <span>
                        {iss.node_name && (
                          <span className="font-mono text-xs text-muted-foreground">
                            {iss.node_name}:{' '}
                          </span>
                        )}
                        <span className="text-foreground">{iss.message}</span>
                      </span>
                    </button>
                  </li>
                ))}
              </ul>
            )}
          </div>
        </CustomPopover>

        <div className="mx-0.5 h-6 w-px bg-border" />

        <CustomPopover
          open={moreOpen}
          onOpenChange={setMoreOpen}
          align="end"
          width="w-52"
          trigger={
            <button
              aria-label="More options"
              className="rounded-lg p-2 text-muted-foreground transition-colors hover:bg-accent hover:text-foreground"
            >
              <MoreHorizontal className="h-4 w-4" />
            </button>
          }
        >
          <div className="flex flex-col">
            <button
              onClick={() => {
                onOpenGlobalPrompt();
                setMoreOpen(false);
              }}
              className="flex items-center gap-2.5 rounded-md px-2 py-1.5 text-left text-sm text-foreground hover:bg-accent"
            >
              <Sparkles className="h-4 w-4 text-muted-foreground" />
              Global prompt
            </button>
            <button
              onClick={() => {
                onExport();
                setMoreOpen(false);
              }}
              className="flex items-center gap-2.5 rounded-md px-2 py-1.5 text-left text-sm text-foreground hover:bg-accent"
            >
              <FileDown className="h-4 w-4 text-muted-foreground" />
              Export Vapi JSON
            </button>
          </div>
        </CustomPopover>

        <CustomButton type="default" size="sm" loading={saving} onClick={onSave}>
          Save draft
        </CustomButton>
        <CustomButton type="primary" size="sm" disabled={!valid} onClick={onPublish}>
          Publish
        </CustomButton>
      </div>
    </div>
  );
};

export default WorkflowToolbar;
