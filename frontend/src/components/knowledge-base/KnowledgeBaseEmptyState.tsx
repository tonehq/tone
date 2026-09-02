import { BookOpen, Plus } from 'lucide-react';

import { CustomButton, IconChip } from '@/components/shared';

interface KnowledgeBaseEmptyStateProps {
  onAdd: () => void;
  hasFilter: boolean;
}

export default function KnowledgeBaseEmptyState({
  onAdd,
  hasFilter,
}: KnowledgeBaseEmptyStateProps) {
  return (
    <div className="flex flex-col items-center gap-4 py-10">
      <IconChip icon={<BookOpen strokeWidth={1.75} />} tone="muted" size="xl" />
      <div className="max-w-sm text-center">
        <p className="font-semibold text-foreground">
          {hasFilter ? 'No matching documents' : 'No documents yet'}
        </p>
        <p className="mt-1 text-sm text-muted-foreground">
          {hasFilter
            ? 'Try clearing the search or status filter.'
            : 'Upload your first document to build your knowledge base.'}
        </p>
      </div>
      {!hasFilter && (
        <CustomButton type="primary" icon={<Plus className="size-4" />} onClick={onAdd}>
          Add Sources
        </CustomButton>
      )}
    </div>
  );
}
