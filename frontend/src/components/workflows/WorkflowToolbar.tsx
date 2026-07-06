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
  saving: boolean;
  dirty: boolean;
  lastSavedAt: number | null;
  issues: ValidationIssue[];
  onBack: () => void;
  onSave: () => void;
  onOpenGlobalPrompt: () => void;
  onExport: () => void;
  onFocusNode?: (nodeName: string) => void;
}

const WorkflowToolbar: React.FC<Props> = ({
  name,
  saving,
  dirty,
  lastSavedAt,
  issues,
  onBack,
  onSave,
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
        <CustomButton
          type="text"
          size="icon-sm"
          aria-label="Back"
          onClick={onBack}
          icon={<ChevronLeft className="h-4 w-4" />}
          className="text-muted-foreground"
        />
        <div className="h-6 w-px bg-border" />
        <div className="min-w-0 pl-1">
          <span className="block truncate text-sm font-semibold text-foreground">{name}</span>
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
            <CustomButton
              type="text"
              size="sm"
              icon={
                valid ? (
                  <CircleCheck className="h-3.5 w-3.5" />
                ) : (
                  <CircleAlert className="h-3.5 w-3.5" />
                )
              }
              className={cn(
                '!h-auto rounded-full px-2.5 py-1 text-xs font-medium ring-1 ring-inset',
                valid
                  ? 'bg-emerald-500/10 text-emerald-600 ring-emerald-500/20 hover:bg-emerald-500/15 dark:text-emerald-300'
                  : 'bg-amber-500/10 text-amber-600 ring-amber-500/25 hover:bg-amber-500/15 dark:text-amber-300',
              )}
            >
              {valid ? 'Valid' : `${issues.length} issue${issues.length > 1 ? 's' : ''}`}
            </CustomButton>
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
                    <CustomButton
                      type="text"
                      fullWidth
                      onClick={() => {
                        if (iss.node_name && onFocusNode) onFocusNode(iss.node_name);
                        setIssuesOpen(false);
                      }}
                      className="!h-auto !items-start !justify-start gap-2 whitespace-normal rounded-md px-2 py-1.5 text-left text-sm font-normal"
                      icon={<CircleAlert className="mt-0.5 h-3.5 w-3.5 shrink-0 text-amber-500" />}
                    >
                      <span className="break-words">
                        {iss.node_name && (
                          <span className="font-mono text-xs text-muted-foreground">
                            {iss.node_name}:{' '}
                          </span>
                        )}
                        <span className="text-foreground">{iss.message}</span>
                      </span>
                    </CustomButton>
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
            <CustomButton
              type="text"
              size="icon-sm"
              aria-label="More options"
              icon={<MoreHorizontal className="h-4 w-4" />}
              className="text-muted-foreground"
            />
          }
        >
          <div className="flex flex-col">
            <CustomButton
              type="text"
              fullWidth
              onClick={() => {
                onOpenGlobalPrompt();
                setMoreOpen(false);
              }}
              className="!justify-start gap-2.5 rounded-md px-2 py-1.5 text-left text-sm font-normal"
              icon={<Sparkles className="h-4 w-4 text-muted-foreground" />}
            >
              Global prompt
            </CustomButton>
            <CustomButton
              type="text"
              fullWidth
              onClick={() => {
                onExport();
                setMoreOpen(false);
              }}
              className="!justify-start gap-2.5 rounded-md px-2 py-1.5 text-left text-sm font-normal"
              icon={<FileDown className="h-4 w-4 text-muted-foreground" />}
            >
              Export JSON
            </CustomButton>
          </div>
        </CustomPopover>

        <CustomButton
          type="primary"
          size="sm"
          loading={saving}
          disabled={saving || !dirty}
          onClick={onSave}
          title={
            !dirty
              ? 'No unsaved changes'
              : valid
                ? 'Save — assigned agents use this on the next call'
                : 'Saves the graph — resolve the issues to make it assignable'
          }
        >
          Save
        </CustomButton>
      </div>
    </div>
  );
};

export default WorkflowToolbar;
