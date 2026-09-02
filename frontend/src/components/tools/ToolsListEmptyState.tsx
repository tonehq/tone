'use client';

import { Plus, Wrench } from 'lucide-react';

import { CustomButton } from '@/components/shared';

interface ToolsListEmptyStateProps {
  onAdd: () => void;
  hasFilter: boolean;
}

export default function ToolsListEmptyState({ onAdd, hasFilter }: ToolsListEmptyStateProps) {
  return (
    <div className="flex flex-col items-center gap-5 py-14">
      <span className="inline-flex size-12 items-center justify-center rounded-xl border border-border bg-surface text-muted-foreground">
        <Wrench className="size-5" strokeWidth={1.75} />
      </span>
      <div className="max-w-sm text-center">
        <p className="font-display text-[15px] font-semibold text-foreground">
          {hasFilter ? 'No tools match your filters' : 'No tools yet'}
        </p>
        <p className="mt-1.5 text-sm text-muted-foreground">
          {hasFilter
            ? 'Try clearing the search or filters.'
            : 'Create your first tool to give your agents the ability to call external APIs.'}
        </p>
      </div>
      {!hasFilter && (
        <CustomButton type="primary" icon={<Plus size={15} />} className="h-10" onClick={onAdd}>
          Create tool
        </CustomButton>
      )}
    </div>
  );
}
