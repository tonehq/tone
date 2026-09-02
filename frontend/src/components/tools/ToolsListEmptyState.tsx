'use client';

import { Plus, Wrench } from 'lucide-react';

import { CustomButton, IconChip } from '@/components/shared';

interface ToolsListEmptyStateProps {
  onAdd: () => void;
  hasFilter: boolean;
}

export default function ToolsListEmptyState({ onAdd, hasFilter }: ToolsListEmptyStateProps) {
  return (
    <div className="flex flex-col items-center gap-4 py-10">
      <IconChip icon={<Wrench strokeWidth={1.75} />} tone="muted" size="xl" />
      <div className="max-w-sm text-center">
        <p className="font-semibold text-foreground">
          {hasFilter ? 'No tools match your filters' : 'No tools yet'}
        </p>
        <p className="mt-1 text-sm text-muted-foreground">
          {hasFilter
            ? 'Try clearing the search or filters.'
            : 'Create your first tool to give your agents the ability to call external APIs.'}
        </p>
      </div>
      {!hasFilter && (
        <CustomButton type="primary" icon={<Plus className="size-4" />} onClick={onAdd}>
          Create New Tool
        </CustomButton>
      )}
    </div>
  );
}
