'use client';

import React, { useState } from 'react';
import { AlertTriangle, CheckCircle2, ChevronLeft } from 'lucide-react';

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
  onFocusNode,
}) => {
  const [open, setOpen] = useState(false);
  const valid = issues.length === 0;

  return (
    <div className="flex h-14 shrink-0 items-center justify-between border-b border-border bg-card/80 px-4 backdrop-blur">
      <div className="flex min-w-0 items-center gap-3">
        <button
          onClick={onBack}
          className="rounded-md p-1.5 text-muted-foreground hover:bg-accent hover:text-foreground"
          aria-label="Back to workflows"
        >
          <ChevronLeft className="h-4 w-4" />
        </button>
        <div className="min-w-0">
          <div className="truncate text-sm font-semibold text-foreground">{name}</div>
          <div className="flex items-center gap-1.5 font-mono text-[11px] text-muted-foreground">
            <span
              className={cn(
                'h-1.5 w-1.5 rounded-full',
                status === 'published' ? 'bg-emerald-500' : 'bg-amber-500',
              )}
            />
            <span className="capitalize">{status}</span>
            <span>·</span>
            <span>
              {saving ? 'Saving…' : dirty ? 'Unsaved' : lastSavedAt ? 'Saved' : 'Up to date'}
            </span>
          </div>
        </div>
      </div>

      <div className="flex items-center gap-2">
        <CustomPopover
          open={open}
          onOpenChange={setOpen}
          align="end"
          width="w-80"
          trigger={
            <button
              className={cn(
                'inline-flex items-center gap-1.5 rounded-md px-2.5 py-1.5 text-sm transition-colors',
                valid
                  ? 'text-emerald-600 hover:bg-accent dark:text-emerald-400'
                  : 'text-destructive hover:bg-destructive/10',
              )}
            >
              {valid ? <CheckCircle2 className="h-4 w-4" /> : <AlertTriangle className="h-4 w-4" />}
              {valid ? 'Valid' : `${issues.length} issue${issues.length > 1 ? 's' : ''}`}
            </button>
          }
        >
          <div aria-live="polite" className="max-h-72 overflow-y-auto">
            {valid ? (
              <p className="px-1 py-2 text-sm text-muted-foreground">
                No problems found. Ready to publish.
              </p>
            ) : (
              <ul className="flex flex-col gap-1">
                {issues.map((iss, i) => (
                  <li key={i}>
                    <button
                      onClick={() => {
                        if (iss.node_name && onFocusNode) onFocusNode(iss.node_name);
                        setOpen(false);
                      }}
                      className="flex w-full items-start gap-2 rounded-md px-2 py-1.5 text-left text-sm hover:bg-accent"
                    >
                      <AlertTriangle className="mt-0.5 h-3.5 w-3.5 shrink-0 text-destructive" />
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
